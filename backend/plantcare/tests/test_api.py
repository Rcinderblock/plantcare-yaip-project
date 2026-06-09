from datetime import date, timedelta

import pytest
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve, reverse
from django.utils import timezone
from rest_framework.test import APIClient

from plantcare.models import CareLog, CareTask, Collection, PlantSpecies, UserPlant
from plantcare.services import EncyclopediaEntry, WeatherSnapshot


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

    login_response = client.post(
        reverse("token_obtain_pair"),
        {"username": "new-user", "password": "strong-pass"},
        format="json",
    )
    assert login_response.status_code == 200
    assert "plantcare_access" in login_response.cookies
    assert "plantcare_refresh" in login_response.cookies
    assert login_response.cookies["plantcare_access"]["httponly"]
    assert login_response.cookies["plantcare_refresh"]["httponly"]
    client.cookies.update(login_response.cookies)

    me = client.get(reverse("me"))

    assert me.status_code == 200
    assert me.data["email"] == "new@example.com"

    logout_response = client.post(reverse("logout"))
    assert logout_response.status_code == 200
    assert logout_response.cookies["plantcare_access"]["max-age"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"username": "ab", "email": "short@example.com", "password": "strong-pass"}, "username"),
        ({"username": "a" * 31, "email": "long@example.com", "password": "strong-pass"}, "username"),
        ({"username": "short-pass", "email": "shortpass@example.com", "password": "a" * 7}, "password"),
        ({"username": "long-pass", "email": "longpass@example.com", "password": "a" * 129}, "password"),
    ],
)
def test_register_rejects_invalid_username_or_password_length(payload, field):
    response = APIClient().post(reverse("register"), payload, format="json")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.django_db
def test_register_rejects_duplicate_username():
    get_user_model().objects.create_user(username="duplicate", password="secret-pass")

    response = APIClient().post(
        reverse("register"),
        {"username": "duplicate", "email": "duplicate@example.com", "password": "strong-pass"},
        format="json",
    )

    assert response.status_code == 400
    assert "username" in response.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"username": "ab", "password": "secret-pass"}, "username"),
        ({"username": "a" * 31, "password": "secret-pass"}, "username"),
        ({"username": "alice", "password": "a" * 7}, "password"),
        ({"username": "alice", "password": "a" * 129}, "password"),
    ],
)
def test_login_rejects_invalid_username_or_password_length(payload, field):
    get_user_model().objects.create_user(username="alice", password="secret-pass")

    response = APIClient().post(reverse("token_obtain_pair"), payload, format="json")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.django_db
def test_refresh_cookie_issues_new_access_cookie():
    user = get_user_model().objects.create_user(username="refresh-user", password="secret-pass")
    client = APIClient()
    login_response = client.post(
        reverse("token_obtain_pair"),
        {"username": user.username, "password": "secret-pass"},
        format="json",
    )
    client.cookies.update(login_response.cookies)

    refresh_response = client.post(reverse("token_refresh"))

    assert refresh_response.status_code == 200
    assert "plantcare_access" in refresh_response.cookies


@pytest.mark.django_db
def test_stale_access_cookie_does_not_block_public_endpoints(species):
    client = APIClient()
    client.cookies[settings.JWT_ACCESS_COOKIE] = "stale-token-from-previous-build"

    species_response = client.get("/api/species/")
    register_response = client.post(
        reverse("register"),
        {"username": "stale-cookie-user", "email": "stale@example.com", "password": "strong-pass"},
        format="json",
    )
    login_response = client.post(
        reverse("token_obtain_pair"),
        {"username": "stale-cookie-user", "password": "strong-pass"},
        format="json",
    )

    assert species_response.status_code == 200
    assert register_response.status_code == 201
    assert login_response.status_code == 200
    assert settings.JWT_ACCESS_COOKIE in login_response.cookies


@pytest.mark.django_db
def test_private_endpoints_reject_anonymous_users():
    client = APIClient()

    assert client.get(reverse("me")).status_code == 401
    assert client.get("/api/plants/").status_code == 401
    assert client.get("/api/care-tasks/").status_code == 401
    assert client.get("/api/care-logs/").status_code == 401


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
def test_stats_endpoint_returns_project_counters(auth_client, user, species):
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Монстера")
    CareTask.objects.create(plant=plant, task_type="water", due_date=date.today())
    CareLog.objects.create(plant=plant, task_type="water")
    Collection.objects.create(owner=user, name="Гостиная")

    response = APIClient().get(reverse("stats"))

    assert response.status_code == 200
    assert response.data["species"] >= 1
    assert response.data["plants"] >= 1
    assert response.data["care_tasks"] >= 1
    assert response.data["care_logs"] >= 1
    assert response.data["collections"] >= 1
    assert response.data["users"] >= 1


@pytest.mark.django_db
def test_species_encyclopedia_endpoint_returns_external_summary(species, monkeypatch):
    monkeypatch.setattr(
        "plantcare.views.EncyclopediaService.fetch_species_entry",
        lambda self, item: EncyclopediaEntry(
            title="Монстера",
            extract="Монстера - род тропических растений.",
            source_url="https://ru.wikipedia.org/wiki/Монстера",
            provider="Wikipedia",
            available=True,
        ),
    )

    response = APIClient().get(f"/api/species/{species.id}/encyclopedia/")

    assert response.status_code == 200
    assert response.data["available"] is True
    assert response.data["provider"] == "Wikipedia"
    assert "Монстера" in response.data["title"]


@pytest.mark.django_db
def test_species_encyclopedia_endpoint_falls_back_when_wikipedia_times_out(species, monkeypatch):
    def raise_timeout(self, item):
        raise requests.Timeout("Wikipedia timeout")

    monkeypatch.setattr("plantcare.views.EncyclopediaService.fetch_species_entry", raise_timeout)

    response = APIClient().get(f"/api/species/{species.id}/encyclopedia/")

    assert response.status_code == 200
    assert response.data["available"] is False
    assert response.data["provider"] == "Wikipedia"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"species": 1, "nickname": "x" * 121, "location_type": "indoor"}, "nickname"),
        ({"species": 1, "nickname": "Фикус", "location_type": "indoor", "notes": "x" * 1001}, "notes"),
        ({"species": 1, "nickname": "Фикус", "location_type": "indoor", "watering_interval_override": 0}, "watering_interval_override"),
        ({"species": 1, "nickname": "Фикус", "location_type": "indoor", "watering_interval_override": 366}, "watering_interval_override"),
    ],
)
def test_plant_serializer_rejects_bad_user_input(auth_client, species, payload, field):
    payload["species"] = species.id

    response = auth_client.post("/api/plants/", payload, format="json")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.django_db
def test_collection_rejects_duplicate_name(auth_client, user):
    Collection.objects.create(owner=user, name="Гостиная")

    response = auth_client.post("/api/collections/", {"name": "гостиная"}, format="json")

    assert response.status_code == 400
    assert "name" in response.data


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
def test_csv_import_reports_bad_rows_without_500(auth_client):
    csv_file = SimpleUploadedFile(
        "plants.csv",
        f"species_name,nickname,watering_interval_days,notes\nБазилик,{'x' * 121},500,{'y' * 1001}\n".encode(),
        content_type="text/csv",
    )

    response = auth_client.post("/api/import/plants/", {"file": csv_file}, format="multipart")

    assert response.status_code == 201
    assert response.data["created_count"] == 0
    assert response.data["errors"]


@pytest.mark.django_db
def test_csv_import_rejects_non_csv_file(auth_client):
    upload = SimpleUploadedFile("plants.txt", b"hello", content_type="text/plain")

    response = auth_client.post("/api/import/plants/", {"file": upload}, format="multipart")

    assert response.status_code == 400
    assert "CSV" in response.data["detail"]


@pytest.mark.django_db
def test_cannot_create_log_for_another_user(auth_client, species):
    other = get_user_model().objects.create_user(username="bob", password="secret-pass")
    plant = UserPlant.objects.create(owner=other, species=species, nickname="Чужой фикус")

    response = auth_client.post("/api/care-logs/", {"plant": plant.id, "task_type": "water"}, format="json")

    assert response.status_code == 400


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
    assert response.data["weather_available"] is True


@pytest.mark.django_db
def test_weather_recommendation_falls_back_when_open_meteo_times_out(auth_client, user, species, monkeypatch):
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Комнатная монстера")

    def raise_timeout(self, lat, lon):
        raise requests.ReadTimeout("Open-Meteo timeout")

    monkeypatch.setattr("plantcare.views.WeatherService.fetch_weather", raise_timeout)

    response = auth_client.get(f"/api/weather/recommendation/?plant_id={plant.id}")

    assert response.status_code == 200
    assert response.data["weather_available"] is False
    assert "Open-Meteo" in response.data["weather_summary"]


@pytest.mark.django_db
def test_weather_recommendation_validates_required_and_numeric_params(auth_client):
    missing = auth_client.get("/api/weather/recommendation/")
    invalid = auth_client.get("/api/weather/recommendation/?plant_id=1&latitude=bad&longitude=37.6")

    assert missing.status_code == 400
    assert invalid.status_code == 400


@pytest.mark.django_db
def test_openapi_schema_is_generated(auth_client):
    response = auth_client.get("/api/schema/")

    assert response.status_code == 200
    assert "PlantCare API" in response.content.decode()


@pytest.mark.skipif(not settings.DEBUG, reason="Static files are served by Django only in local debug mode.")
def test_admin_static_css_is_available():
    match = resolve("/static/admin/css/base.css")

    assert "static" in match.route
    assert finders.find("admin/css/base.css")
