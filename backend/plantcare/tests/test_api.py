from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from plantcare.models import CareLog, CareTask, Collection, PlantSpecies, UserPlant
from plantcare.services import WeatherSnapshot


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="alice", email="alice@example.com", password="secret-pass")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def species():
    return PlantSpecies.objects.create(name="Монстера", watering_interval_days=7, humidity=60)


@pytest.mark.django_db
def test_register_and_me_endpoint():
    client = APIClient()
    response = client.post(
        reverse("register"),
        {"username": "new-user", "email": "new@example.com", "password": "strong-pass"},
        format="json",
    )
    assert response.status_code == 201

    user = get_user_model().objects.get(username="new-user")
    client.force_authenticate(user=user)
    me = client.get(reverse("me"))

    assert me.status_code == 200
    assert me.data["email"] == "new@example.com"


@pytest.mark.django_db
def test_species_are_public_and_plants_are_private(auth_client, user, species):
    other = get_user_model().objects.create_user(username="bob", password="secret-pass")
    UserPlant.objects.create(owner=other, species=species, nickname="Чужая монстера")

    public_response = APIClient().get("/api/species/")
    create_response = auth_client.post(
        "/api/plants/",
        {"species": species.id, "nickname": "Моя монстера", "location_type": "indoor"},
        format="json",
    )
    list_response = auth_client.get("/api/plants/")

    assert public_response.status_code == 200
    assert create_response.status_code == 201
    assert len(list_response.data["results"]) == 1
    assert list_response.data["results"][0]["nickname"] == "Моя монстера"


@pytest.mark.django_db
def test_task_completion_creates_care_log(auth_client, user, species):
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Монстера")
    task = CareTask.objects.create(plant=plant, task_type="water", due_date=date.today())

    response = auth_client.post(f"/api/care-tasks/{task.id}/complete/")
    plant.refresh_from_db()

    assert response.status_code == 200
    assert CareLog.objects.filter(plant=plant, task_type="water").exists()
    assert plant.last_watered_at is not None


@pytest.mark.django_db
def test_collection_api_persists_many_to_many(auth_client, user, species):
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Монстера")

    response = auth_client.post(
        "/api/collections/",
        {"name": "Гостиная", "description": "Растения у окна", "plant_ids": [plant.id]},
        format="json",
    )

    assert response.status_code == 201
    collection = Collection.objects.get(name="Гостиная")
    assert list(collection.plants.values_list("id", flat=True)) == [plant.id]


@pytest.mark.django_db
def test_csv_import_creates_plants(auth_client, user):
    csv_file = SimpleUploadedFile(
        "plants.csv",
        "species_name,nickname,location_type,watering_interval_days,notes\nБазилик,Кухня,balcony,2,Любит солнце\n".encode(),
        content_type="text/csv",
    )

    response = auth_client.post("/api/import/plants/", {"file": csv_file}, format="multipart")

    assert response.status_code == 201
    assert response.data["created_count"] == 1
    assert UserPlant.objects.filter(owner=user, nickname="Кухня", species__name="Базилик").exists()


@pytest.mark.django_db
def test_cannot_create_log_for_another_user(auth_client, species):
    other = get_user_model().objects.create_user(username="bob", password="secret-pass")
    plant = UserPlant.objects.create(owner=other, species=species, nickname="Чужой фикус")

    response = auth_client.post("/api/care-logs/", {"plant": plant.id, "task_type": "water"}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_weather_recommendation_endpoint(auth_client, user, species, monkeypatch):
    plant = UserPlant.objects.create(
        owner=user,
        species=species,
        nickname="Балконная монстера",
        location_type="balcony",
        last_watered_at=timezone.now() - timedelta(days=8),
    )
    monkeypatch.setattr(
        "plantcare.views.WeatherService.fetch_weather",
        lambda self, lat, lon: WeatherSnapshot(
            temperature_c=18.2,
            humidity_percent=76,
            precipitation_today_mm=4.0,
            precipitation_tomorrow_mm=1.5,
        ),
    )

    response = auth_client.get(f"/api/weather/recommendation/?plant_id={plant.id}&latitude=55.7&longitude=37.6")

    assert response.status_code == 200
    assert response.data["should_water_today"] is False
    assert response.data["precipitation_mm"] == 4.0
    assert response.data["precipitation_tomorrow_mm"] == 1.5
    assert response.data["temperature_c"] == 18.2
    assert response.data["humidity_percent"] == 76
    assert response.data["rain_expected"] is True


@pytest.mark.django_db
def test_openapi_schema_is_generated(auth_client):
    response = auth_client.get("/api/schema/")

    assert response.status_code == 200
    assert "PlantCare API" in response.content.decode()
