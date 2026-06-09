import csv
from io import TextIOWrapper

import requests
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import permissions, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CareLog, CareTask, Collection, PlantSpecies, UserPlant
from .serializers import (
    CareLogSerializer,
    CareTaskSerializer,
    CollectionSerializer,
    CookieTokenObtainPairSerializer,
    PlantSpeciesSerializer,
    PLANT_NICKNAME_MAX_LENGTH,
    RegisterSerializer,
    TEXT_NOTE_MAX_LENGTH,
    UserPlantSerializer,
    UserSerializer,
    WATERING_INTERVAL_MAX_DAYS,
    WATERING_INTERVAL_MIN_DAYS,
)
from .services import EncyclopediaService, WeatherService

User = get_user_model()


def set_access_cookie(response, access_token):
    max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        str(access_token),
        max_age=max_age,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )


def set_refresh_cookie(response, refresh_token):
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        str(refresh_token),
        max_age=max_age,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/api/auth/token/refresh/",
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.JWT_ACCESS_COOKIE, path="/", samesite=settings.JWT_COOKIE_SAMESITE)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path="/api/auth/token/refresh/", samesite=settings.JWT_COOKIE_SAMESITE)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Авторизация"],
        summary="Регистрация пользователя",
        description=(
            "Создает нового пользователя Django. В теле запроса передаются username, email и password. "
            "Логин должен быть длиной 3-30 символов, пароль - 8-128 символов. "
            "Пароль сохраняется не в открытом виде: Django хеширует его через create_user. "
            "После регистрации frontend обычно сразу вызывает ручку входа, чтобы получить HttpOnly cookies."
        ),
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class CookieTokenObtainPairView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Авторизация"],
        summary="Вход и создание JWT-cookie сессии",
        description=(
            "Проверяет username и password через SimpleJWT. Если данные верные, backend создает refresh token, "
            "из него получает access token и кладет оба токена в HttpOnly cookies: plantcare_access и "
            "plantcare_refresh. Логин принимается длиной 3-30 символов, пароль - 8-128 символов. "
            "Токены не возвращаются в JSON, чтобы frontend не хранил их в localStorage."
        ),
        request=CookieTokenObtainPairSerializer,
        responses=inline_serializer(
            name="CookieTokenLoginResult",
            fields={"user": UserSerializer(), "detail": drf_serializers.CharField()},
        ),
    )
    def post(self, request):
        serializer = CookieTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken(serializer.validated_data["refresh"])
        response = Response(
            {"user": UserSerializer(serializer.user).data, "detail": "Сессия создана в HttpOnly cookies."}
        )
        set_access_cookie(response, refresh.access_token)
        set_refresh_cookie(response, refresh)
        return response


class CookieTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Авторизация"],
        summary="Обновление access token",
        description=(
            "Берет refresh token из cookie plantcare_refresh и, если он валиден, выпускает новый access token "
            "в cookie plantcare_access. Используется frontend-клиентом автоматически, когда приватный запрос "
            "получил 401 из-за истекшего access token."
        ),
        request=None,
        responses=inline_serializer(
            name="CookieTokenRefreshResult",
            fields={"detail": drf_serializers.CharField()},
        )
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw_refresh:
            raise InvalidToken("Refresh cookie is missing.")

        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError as exc:
            raise InvalidToken("Refresh cookie is invalid.") from exc

        response = Response({"detail": "Сессия обновлена."})
        set_access_cookie(response, refresh.access_token)
        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Авторизация"],
        summary="Выход из аккаунта",
        description=(
            "Удаляет auth cookies plantcare_access и plantcare_refresh на стороне браузера. "
            "Ручка доступна без авторизации, чтобы можно было очистить даже старые или испорченные cookies."
        ),
        request=None,
        responses=inline_serializer(
            name="LogoutResult",
            fields={"detail": drf_serializers.CharField()},
        )
    )
    def post(self, request):
        response = Response({"detail": "Сессия завершена."})
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Авторизация"],
        summary="Текущий пользователь",
        description=(
            "Возвращает профиль пользователя, определенного по JWT access token из HttpOnly cookie. "
            "Frontend вызывает эту ручку при загрузке приложения, чтобы понять, есть ли активная сессия."
        ),
        responses=UserSerializer,
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)


@extend_schema_view(
    list=extend_schema(
        tags=["Каталог видов"],
        summary="Получить список видов растений",
        description=(
            "Публичная ручка каталога. Возвращает справочник видов растений: название, латинское название, "
            "описание, свет, влажность, базовый интервал полива, безопасность для животных и image_url. "
            "Эти данные используются на странице каталога и в форме добавления личного растения."
        ),
    ),
    retrieve=extend_schema(
        tags=["Каталог видов"],
        summary="Получить один вид растения",
        description=(
            "Публичная ручка для просмотра конкретного вида растения из общего каталога по id. "
            "Не зависит от пользователя и не требует авторизации."
        ),
    ),
)
class PlantSpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = []
    queryset = PlantSpecies.objects.all()
    serializer_class = PlantSpeciesSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Каталог видов"],
        summary="Получить энциклопедическую справку о виде",
        description=(
            "Ищет краткую справку о виде растения во внешнем сервисе Wikipedia. Backend пробует русское "
            "название вида и латинское название. Если внешний сервис недоступен или статья не найдена, "
            "ручка возвращает available=false и понятное fallback-сообщение, не ломая страницу."
        ),
        responses=inline_serializer(
            name="SpeciesEncyclopedia",
            fields={
                "title": drf_serializers.CharField(),
                "extract": drf_serializers.CharField(),
                "source_url": drf_serializers.CharField(),
                "provider": drf_serializers.CharField(),
                "available": drf_serializers.BooleanField(),
            },
        ),
    )
    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def encyclopedia(self, request, pk=None):
        species = self.get_object()
        service = EncyclopediaService()
        try:
            entry = service.fetch_species_entry(species)
        except requests.RequestException:
            entry = service.build_fallback_entry(species)
        return Response(entry.__dict__)


class EncyclopediaSearchView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Справка"],
        summary="Найти растение в Wikipedia",
        description=(
            "Выполняет полнотекстовый поиск по русской Wikipedia и возвращает до пяти наиболее релевантных "
            "статей о растениях. Если обычный поиск не дал результатов, backend повторяет запрос с fuzzy-поиском, "
            "поэтому небольшие опечатки не требуют точного совпадения названия."
        ),
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Название растения или его часть, от 2 до 120 символов.",
            ),
        ],
        responses=inline_serializer(
            name="EncyclopediaSearchResponse",
            fields={
                "query": drf_serializers.CharField(),
                "available": drf_serializers.BooleanField(),
                "message": drf_serializers.CharField(),
                "results": inline_serializer(
                    name="EncyclopediaSearchItem",
                    many=True,
                    fields={
                        "title": drf_serializers.CharField(),
                        "extract": drf_serializers.CharField(),
                        "source_url": drf_serializers.CharField(),
                        "provider": drf_serializers.CharField(),
                        "available": drf_serializers.BooleanField(),
                        "thumbnail_url": drf_serializers.CharField(),
                    },
                ),
            },
        ),
    )
    def get(self, request):
        query = " ".join(request.query_params.get("q", "").split())
        if len(query) < 2:
            return Response({"q": ["Введите не менее 2 символов."]}, status=status.HTTP_400_BAD_REQUEST)
        if len(query) > 120:
            return Response({"q": ["Введите не более 120 символов."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = EncyclopediaService().search(query)
        except requests.RequestException:
            return Response(
                {
                    "query": query,
                    "available": False,
                    "message": "Wikipedia временно недоступна. Попробуйте еще раз позже.",
                    "results": [],
                }
            )

        return Response(
            {
                "query": query,
                "available": True,
                "message": "Ничего не найдено. Попробуйте другое или латинское название." if not results else "",
                "results": [entry.__dict__ for entry in results],
            }
        )


class StatsView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Статистика"],
        summary="Получить статистику проекта",
        description=(
            "Возвращает агрегированные счетчики по основным сущностям PlantCare. Ручка нужна для главной "
            "страницы и для быстрой демонстрации, что backend работает с реальной PostgreSQL-базой."
        ),
        responses=inline_serializer(
            name="PlantCareStats",
            fields={
                "species": drf_serializers.IntegerField(),
                "plants": drf_serializers.IntegerField(),
                "care_tasks": drf_serializers.IntegerField(),
                "care_logs": drf_serializers.IntegerField(),
                "collections": drf_serializers.IntegerField(),
                "users": drf_serializers.IntegerField(),
            },
        ),
    )
    def get(self, request):
        return Response(
            {
                "species": PlantSpecies.objects.count(),
                "plants": UserPlant.objects.count(),
                "care_tasks": CareTask.objects.count(),
                "care_logs": CareLog.objects.count(),
                "collections": Collection.objects.count(),
                "users": User.objects.count(),
            }
        )


class UserOwnedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    owner_lookup = "owner"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_lookup: self.request.user})


@extend_schema_view(
    list=extend_schema(
        tags=["Мои растения"],
        summary="Список моих растений",
        description=(
            "Возвращает только растения текущего пользователя. Фильтрация выполняется на backend по request.user, "
            "поэтому пользователь не может увидеть растения других аккаунтов."
        ),
    ),
    retrieve=extend_schema(
        tags=["Мои растения"],
        summary="Получить мое растение",
        description=(
            "Возвращает карточку одного растения текущего пользователя: выбранный вид, имя, место, заметки, "
            "последний полив и рассчитанную дату следующего полива."
        ),
    ),
    create=extend_schema(
        tags=["Мои растения"],
        summary="Добавить растение",
        description=(
            "Создает личное растение текущего пользователя. Поле owner не передается с frontend: backend сам "
            "ставит owner=request.user, чтобы нельзя было создать растение от имени другого пользователя."
        ),
    ),
    update=extend_schema(
        tags=["Мои растения"],
        summary="Полностью обновить растение",
        description=(
            "Полностью заменяет данные личного растения. Доступ разрешен только владельцу записи."
        ),
    ),
    partial_update=extend_schema(
        tags=["Мои растения"],
        summary="Частично обновить растение",
        description=(
            "Обновляет только переданные поля личного растения, например заметки или интервал полива."
        ),
    ),
    destroy=extend_schema(
        tags=["Мои растения"],
        summary="Удалить растение",
        description=(
            "Удаляет личное растение текущего пользователя вместе с зависимыми задачами и логами ухода."
        ),
    ),
)
class UserPlantViewSet(UserOwnedModelViewSet):
    queryset = UserPlant.objects.select_related("species", "owner").all()
    serializer_class = UserPlantSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    list=extend_schema(
        tags=["Задачи ухода"],
        summary="Список задач ухода",
        description=(
            "Возвращает задачи ухода только для растений текущего пользователя. Используется календарем ухода."
        ),
    ),
    retrieve=extend_schema(
        tags=["Задачи ухода"],
        summary="Получить задачу ухода",
        description="Возвращает одну задачу ухода, если она относится к растению текущего пользователя.",
    ),
    create=extend_schema(
        tags=["Задачи ухода"],
        summary="Создать задачу ухода",
        description=(
            "Создает задачу ухода: полив, удобрение, пересадка или обрезка. Backend проверяет, что plant "
            "принадлежит текущему пользователю; для чужого растения вернется 403."
        ),
    ),
    update=extend_schema(
        tags=["Задачи ухода"],
        summary="Полностью обновить задачу ухода",
        description="Полностью обновляет задачу ухода текущего пользователя.",
    ),
    partial_update=extend_schema(
        tags=["Задачи ухода"],
        summary="Частично обновить задачу ухода",
        description="Обновляет отдельные поля задачи, например дату, статус или заметки.",
    ),
    destroy=extend_schema(
        tags=["Задачи ухода"],
        summary="Удалить задачу ухода",
        description="Удаляет задачу ухода, если она относится к растению текущего пользователя.",
    ),
    complete=extend_schema(
        tags=["Задачи ухода"],
        summary="Отметить задачу выполненной",
        description=(
            "Переводит задачу в статус done и автоматически создает CareLog с фактом выполнения. "
            "Если задача была поливом, backend дополнительно обновляет last_watered_at у растения."
        ),
    ),
)
class CareTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CareTask.objects.select_related("plant", "plant__owner", "plant__species").all()
    serializer_class = CareTaskSerializer

    def get_queryset(self):
        return self.queryset.filter(plant__owner=self.request.user)

    def perform_create(self, serializer):
        plant = serializer.validated_data["plant"]
        if plant.owner != self.request.user:
            raise PermissionDenied("Нельзя создать задачу для чужого растения.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = CareTask.Status.DONE
        task.save(update_fields=["status"])
        log = CareLog.objects.create(plant=task.plant, task_type=task.task_type, notes=task.notes)
        if task.task_type == CareTask.TaskType.WATER:
            task.plant.last_watered_at = timezone.now()
            task.plant.save(update_fields=["last_watered_at"])
        return Response({"task": CareTaskSerializer(task).data, "log": CareLogSerializer(log).data})


@extend_schema_view(
    list=extend_schema(
        tags=["Журнал ухода"],
        summary="Список записей ухода",
        description=(
            "Возвращает журнал выполненных действий только по растениям текущего пользователя. "
            "Записи отсортированы от новых к старым."
        ),
    ),
    retrieve=extend_schema(
        tags=["Журнал ухода"],
        summary="Получить запись ухода",
        description="Возвращает одну запись ухода, если она относится к растению текущего пользователя.",
    ),
    create=extend_schema(
        tags=["Журнал ухода"],
        summary="Добавить запись ухода",
        description=(
            "Добавляет факт выполненного ухода вручную. Backend проверяет владельца растения. "
            "Если запись имеет тип water, last_watered_at у растения обновляется временем записи."
        ),
    ),
    update=extend_schema(
        tags=["Журнал ухода"],
        summary="Полностью обновить запись ухода",
        description="Полностью обновляет запись журнала ухода текущего пользователя.",
    ),
    partial_update=extend_schema(
        tags=["Журнал ухода"],
        summary="Частично обновить запись ухода",
        description="Обновляет отдельные поля записи ухода, например заметку или дату выполнения.",
    ),
    destroy=extend_schema(
        tags=["Журнал ухода"],
        summary="Удалить запись ухода",
        description="Удаляет запись журнала ухода текущего пользователя.",
    ),
)
class CareLogViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CareLog.objects.select_related("plant", "plant__owner").all()
    serializer_class = CareLogSerializer

    def get_queryset(self):
        return self.queryset.filter(plant__owner=self.request.user)

    def perform_create(self, serializer):
        plant = serializer.validated_data["plant"]
        if plant.owner != self.request.user:
            raise PermissionDenied("Нельзя добавить запись для чужого растения.")
        log = serializer.save()
        if log.task_type == CareTask.TaskType.WATER:
            plant.last_watered_at = log.performed_at
            plant.save(update_fields=["last_watered_at"])


@extend_schema_view(
    list=extend_schema(
        tags=["Коллекции"],
        summary="Список моих коллекций",
        description=(
            "Возвращает коллекции текущего пользователя вместе с растениями внутри них. "
            "Коллекции нужны для группировки личных растений, например 'Гостиная' или 'Балкон'."
        ),
    ),
    retrieve=extend_schema(
        tags=["Коллекции"],
        summary="Получить коллекцию",
        description="Возвращает одну коллекцию текущего пользователя и список растений внутри нее.",
    ),
    create=extend_schema(
        tags=["Коллекции"],
        summary="Создать коллекцию",
        description=(
            "Создает коллекцию текущего пользователя. Для привязки растений передается plant_ids; serializer "
            "разрешает выбрать только растения владельца текущей сессии."
        ),
    ),
    update=extend_schema(
        tags=["Коллекции"],
        summary="Полностью обновить коллекцию",
        description="Полностью обновляет коллекцию и, если передан plant_ids, заменяет состав растений.",
    ),
    partial_update=extend_schema(
        tags=["Коллекции"],
        summary="Частично обновить коллекцию",
        description="Обновляет отдельные поля коллекции или ее состав через plant_ids.",
    ),
    destroy=extend_schema(
        tags=["Коллекции"],
        summary="Удалить коллекцию",
        description="Удаляет коллекцию текущего пользователя. Сами растения при этом не удаляются.",
    ),
)
class CollectionViewSet(UserOwnedModelViewSet):
    queryset = Collection.objects.prefetch_related("plants", "plants__species").all()
    serializer_class = CollectionSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PlantImportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["Импорт"],
        summary="Импортировать растения из CSV",
        description=(
            "Принимает CSV-файл в multipart-поле file. Минимальные обязательные колонки: species_name и nickname. "
            "Дополнительно поддерживаются location_type, watering_interval_days и notes. Если вида растения еще "
            "нет в каталоге, backend создаст его автоматически с базовым описанием."
        ),
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={
            201: inline_serializer(
                name="PlantImportResult",
                fields={
                    "created_count": drf_serializers.IntegerField(),
                    "created": UserPlantSerializer(many=True),
                    "errors": drf_serializers.ListField(child=drf_serializers.DictField()),
                },
            )
        },
    )
    @transaction.atomic
    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Необходимо передать CSV-файл в поле file."}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.lower().endswith(".csv"):
            return Response({"detail": "Поддерживаются только CSV-файлы."}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        errors = []
        try:
            reader = csv.DictReader(TextIOWrapper(upload.file, encoding="utf-8-sig"))
            required_columns = {"species_name", "nickname"}
            if not required_columns.issubset(reader.fieldnames or set()):
                return Response(
                    {"detail": "CSV должен содержать колонки species_name и nickname."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for row_number, row in enumerate(reader, start=2):
                try:
                    species_name = (row.get("species_name") or "").strip()
                    nickname = (row.get("nickname") or "").strip()
                    notes = (row.get("notes") or "").strip()
                    interval_raw = (row.get("watering_interval_days") or "").strip()
                    interval = int(interval_raw) if interval_raw else None

                    if not species_name or not nickname:
                        raise ValueError("species_name и nickname обязательны")
                    if len(species_name) > 120:
                        raise ValueError("species_name должен быть не длиннее 120 символов")
                    if len(nickname) > PLANT_NICKNAME_MAX_LENGTH:
                        raise ValueError(f"nickname должен быть не длиннее {PLANT_NICKNAME_MAX_LENGTH} символов")
                    if len(notes) > TEXT_NOTE_MAX_LENGTH:
                        raise ValueError(f"notes должен быть не длиннее {TEXT_NOTE_MAX_LENGTH} символов")
                    if interval is not None and not WATERING_INTERVAL_MIN_DAYS <= interval <= WATERING_INTERVAL_MAX_DAYS:
                        raise ValueError(
                            f"watering_interval_days должен быть от {WATERING_INTERVAL_MIN_DAYS} "
                            f"до {WATERING_INTERVAL_MAX_DAYS}"
                        )

                    # Импорт допускает новые виды растений: это ускоряет массовое
                    # заполнение каталога без ручной подготовки справочника.
                    species, _ = PlantSpecies.objects.get_or_create(
                        name=species_name,
                        defaults={
                            "description": "Добавлено через CSV-импорт.",
                            "watering_interval_days": interval or 7,
                        },
                    )
                    serializer = UserPlantSerializer(
                        data={
                            "species": species.id,
                            "nickname": nickname,
                            "location_type": row.get("location_type") or UserPlant.LocationType.INDOOR,
                            "watering_interval_override": interval,
                            "notes": notes,
                        },
                        context={"request": request},
                    )
                    serializer.is_valid(raise_exception=True)
                    plant = serializer.save(owner=request.user)
                    created.append(UserPlantSerializer(plant).data)
                except Exception as exc:
                    errors.append({"row": row_number, "error": str(exc)})
        except UnicodeDecodeError:
            return Response({"detail": "Не удалось прочитать CSV в кодировке UTF-8."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"created_count": len(created), "created": created, "errors": errors}, status=status.HTTP_201_CREATED)


class WeatherRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Погода"],
        summary="Получить погодную рекомендацию по поливу",
        description=(
            "Строит рекомендацию по поливу для растения текущего пользователя. Ручка берет plant_id, а latitude "
            "и longitude опциональны; по умолчанию используются координаты Москвы. Backend вызывает Open-Meteo, "
            "получает температуру, влажность и осадки. Для балконных растений дождь может отложить полив. "
            "Для комнатных растений погода показывается как контекст, но решение остается по графику ухода. "
            "Если Open-Meteo не отвечает, возвращается fallback-рекомендация с weather_available=false."
        ),
        parameters=[
            OpenApiParameter("plant_id", int, required=True),
            OpenApiParameter("latitude", float, required=False),
            OpenApiParameter("longitude", float, required=False),
        ],
        responses=inline_serializer(
            name="WeatherRecommendation",
            fields={
                "should_water_today": drf_serializers.BooleanField(),
                "next_watering_date": drf_serializers.DateField(),
                "precipitation_mm": drf_serializers.FloatField(),
                "precipitation_tomorrow_mm": drf_serializers.FloatField(),
                "temperature_c": drf_serializers.FloatField(),
                "humidity_percent": drf_serializers.IntegerField(),
                "rain_expected": drf_serializers.BooleanField(),
                "weather_available": drf_serializers.BooleanField(),
                "weather_summary": drf_serializers.CharField(),
                "message": drf_serializers.CharField(),
            },
        ),
    )
    def get(self, request):
        plant_id = request.query_params.get("plant_id")
        if not plant_id:
            return Response({"detail": "Параметр plant_id обязателен."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            plant_id = int(plant_id)
            latitude = float(request.query_params.get("latitude", 55.7558))
            longitude = float(request.query_params.get("longitude", 37.6173))
        except ValueError:
            return Response(
                {"detail": "plant_id, latitude и longitude должны быть числами."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plant = get_object_or_404(UserPlant, id=plant_id, owner=request.user)
        service = WeatherService()
        try:
            weather = service.fetch_weather(latitude, longitude)
            recommendation = service.build_recommendation(plant, weather)
        except requests.RequestException:
            recommendation = service.build_fallback_recommendation(plant)
        return Response(recommendation.__dict__)
