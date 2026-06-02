from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import CareLog, CareTask, Collection, PlantSpecies, UserPlant

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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


class CareTaskSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.nickname", read_only=True)

    class Meta:
        model = CareTask
        fields = ("id", "plant", "plant_name", "task_type", "due_date", "status", "notes", "created_at")
        read_only_fields = ("created_at",)


class CareLogSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.nickname", read_only=True)

    class Meta:
        model = CareLog
        fields = ("id", "plant", "plant_name", "task_type", "performed_at", "notes")


class CollectionSerializer(serializers.ModelSerializer):
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
