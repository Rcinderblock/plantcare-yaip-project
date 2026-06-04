import csv
from io import TextIOWrapper

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import permissions, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CareLog, CareTask, Collection, PlantSpecies, UserPlant
from .serializers import (
    CareLogSerializer,
    CareTaskSerializer,
    CollectionSerializer,
    PlantSpeciesSerializer,
    RegisterSerializer,
    UserPlantSerializer,
    UserSerializer,
)
from .services import WeatherService


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

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class CookieTokenObtainPairView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=TokenObtainPairSerializer,
        responses=inline_serializer(
            name="CookieTokenLoginResult",
            fields={"user": UserSerializer(), "detail": drf_serializers.CharField()},
        ),
    )
    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
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

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PlantSpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = []
    queryset = PlantSpecies.objects.all()
    serializer_class = PlantSpeciesSerializer
    permission_classes = [permissions.AllowAny]


class UserOwnedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    owner_lookup = "owner"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_lookup: self.request.user})


class UserPlantViewSet(UserOwnedModelViewSet):
    queryset = UserPlant.objects.select_related("species", "owner").all()
    serializer_class = UserPlantSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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


class CollectionViewSet(UserOwnedModelViewSet):
    queryset = Collection.objects.prefetch_related("plants", "plants__species").all()
    serializer_class = CollectionSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PlantImportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        description="CSV columns: species_name,nickname,location_type,watering_interval_days,notes",
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

        created = []
        errors = []
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
                if not species_name or not nickname:
                    raise ValueError("species_name и nickname обязательны")

                # Импорт допускает новые виды растений: это ускоряет массовое
                # заполнение каталога без ручной подготовки справочника.
                species, _ = PlantSpecies.objects.get_or_create(
                    name=species_name,
                    defaults={
                        "description": "Добавлено через CSV-импорт.",
                        "watering_interval_days": int(row.get("watering_interval_days") or 7),
                    },
                )
                plant = UserPlant.objects.create(
                    owner=request.user,
                    species=species,
                    nickname=nickname,
                    location_type=row.get("location_type") or UserPlant.LocationType.INDOOR,
                    watering_interval_override=int(row["watering_interval_days"]) if row.get("watering_interval_days") else None,
                    notes=row.get("notes") or "",
                )
                created.append(UserPlantSerializer(plant).data)
            except Exception as exc:
                errors.append({"row": row_number, "error": str(exc)})

        return Response({"created_count": len(created), "created": created, "errors": errors}, status=status.HTTP_201_CREATED)


class WeatherRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
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
        plant = UserPlant.objects.get(id=request.query_params["plant_id"], owner=request.user)
        latitude = float(request.query_params.get("latitude", 55.7558))
        longitude = float(request.query_params.get("longitude", 37.6173))
        service = WeatherService()
        try:
            weather = service.fetch_weather(latitude, longitude)
            recommendation = service.build_recommendation(plant, weather)
        except requests.RequestException:
            recommendation = service.build_fallback_recommendation(plant)
        return Response(recommendation.__dict__)
