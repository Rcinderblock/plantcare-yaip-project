from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import PasswordField, TokenObtainPairSerializer

from .models import CareLog, CareTask, Collection, PlantSpecies, UserPlant

User = get_user_model()

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PLANT_NICKNAME_MAX_LENGTH = 120
TEXT_NOTE_MAX_LENGTH = 1000
COLLECTION_NAME_MAX_LENGTH = 120
WATERING_INTERVAL_MIN_DAYS = 1
WATERING_INTERVAL_MAX_DAYS = 365


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)
    password = serializers.CharField(
        write_only=True,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким логином уже существует.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CookieTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(
            write_only=True,
            min_length=USERNAME_MIN_LENGTH,
            max_length=USERNAME_MAX_LENGTH,
        )
        self.fields["password"] = PasswordField(
            min_length=PASSWORD_MIN_LENGTH,
            max_length=PASSWORD_MAX_LENGTH,
        )


class PlantSpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantSpecies
        fields = (
            "id",
            "name",
            "latin_name",
            "description",
            "light",
            "humidity",
            "watering_interval_days",
            "pet_safe",
            "image_url",
        )


class UserPlantSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(max_length=PLANT_NICKNAME_MAX_LENGTH)
    notes = serializers.CharField(max_length=TEXT_NOTE_MAX_LENGTH, allow_blank=True, required=False)
    watering_interval_override = serializers.IntegerField(
        min_value=WATERING_INTERVAL_MIN_DAYS,
        max_value=WATERING_INTERVAL_MAX_DAYS,
        allow_null=True,
        required=False,
    )
    species_detail = PlantSpeciesSerializer(source="species", read_only=True)
    next_watering_due = serializers.SerializerMethodField()

    class Meta:
        model = UserPlant
        fields = (
            "id",
            "species",
            "species_detail",
            "nickname",
            "location_type",
            "planted_at",
            "notes",
            "watering_interval_override",
            "last_watered_at",
            "next_watering_due",
            "created_at",
        )
        read_only_fields = ("last_watered_at", "created_at")
        validators = []

    @extend_schema_field(serializers.DateTimeField)
    def get_next_watering_due(self, obj):
        return obj.next_watering_due()

    def validate(self, attrs):
        request = self.context.get("request")
        owner = getattr(request, "user", None)
        nickname = attrs.get("nickname", getattr(self.instance, "nickname", None))

        if owner and owner.is_authenticated and nickname:
            queryset = UserPlant.objects.filter(owner=owner, nickname__iexact=nickname)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"nickname": "У вас уже есть растение с таким именем."})
        return attrs


class CareTaskSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(max_length=TEXT_NOTE_MAX_LENGTH, allow_blank=True, required=False)
    plant_name = serializers.CharField(source="plant.nickname", read_only=True)

    class Meta:
        model = CareTask
        fields = ("id", "plant", "plant_name", "task_type", "due_date", "status", "notes", "created_at")
        read_only_fields = ("created_at",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["plant"].queryset = UserPlant.objects.filter(owner=request.user)


class CareLogSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(max_length=TEXT_NOTE_MAX_LENGTH, allow_blank=True, required=False)
    plant_name = serializers.CharField(source="plant.nickname", read_only=True)

    class Meta:
        model = CareLog
        fields = ("id", "plant", "plant_name", "task_type", "performed_at", "notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["plant"].queryset = UserPlant.objects.filter(owner=request.user)


class CollectionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=COLLECTION_NAME_MAX_LENGTH)
    description = serializers.CharField(max_length=TEXT_NOTE_MAX_LENGTH, allow_blank=True, required=False)
    plant_ids = serializers.PrimaryKeyRelatedField(
        source="plants",
        queryset=UserPlant.objects.none(),
        many=True,
        write_only=True,
        required=False,
    )
    plants = UserPlantSerializer(read_only=True, many=True)

    class Meta:
        model = Collection
        fields = ("id", "name", "description", "plant_ids", "plants", "created_at")
        read_only_fields = ("created_at",)
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            field = self.fields["plant_ids"]
            field.child_relation.queryset = UserPlant.objects.filter(owner=request.user)

    def validate(self, attrs):
        request = self.context.get("request")
        owner = getattr(request, "user", None)
        name = attrs.get("name", getattr(self.instance, "name", None))

        if owner and owner.is_authenticated and name:
            queryset = Collection.objects.filter(owner=owner, name__iexact=name)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"name": "У вас уже есть коллекция с таким названием."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        plants = validated_data.pop("plants", [])
        collection = Collection.objects.create(**validated_data)
        collection.plants.set(plants)
        return collection

    @transaction.atomic
    def update(self, instance, validated_data):
        plants = validated_data.pop("plants", None)
        instance = super().update(instance, validated_data)
        if plants is not None:
            instance.plants.set(plants)
        return instance
