from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from plantcare.models import Collection, PlantSpecies, UserPlant
from plantcare.services import WeatherService


@pytest.mark.django_db
def test_next_watering_uses_override_interval():
    user = get_user_model().objects.create_user(username="vera", password="secret-pass")
    species = PlantSpecies.objects.create(name="Базилик", watering_interval_days=4)
    watered_at = timezone.now() - timedelta(days=1)
    plant = UserPlant.objects.create(
        owner=user,
        species=species,
        nickname="Кухонный базилик",
        watering_interval_override=2,
        last_watered_at=watered_at,
    )

    assert plant.watering_interval_days == 2
    assert plant.next_watering_due().date() == (watered_at + timedelta(days=2)).date()


@pytest.mark.django_db
def test_collection_many_to_many_relation():
    user = get_user_model().objects.create_user(username="mark", password="secret-pass")
    species = PlantSpecies.objects.create(name="Монстера")
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Большая монстера")
    collection = Collection.objects.create(owner=user, name="Гостиная")

    collection.plants.add(plant)

    assert collection.plants.count() == 1
    assert plant.collections.first() == collection


@pytest.mark.django_db
def test_weather_postpones_balcony_watering_after_rain():
    user = get_user_model().objects.create_user(username="rain", password="secret-pass")
    species = PlantSpecies.objects.create(name="Мята", watering_interval_days=1)
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Балконная мята", location_type="balcony")

    recommendation = WeatherService().build_recommendation(plant, precipitation_mm=5.5)

    assert recommendation.should_water_today is False
    assert "дожд" in recommendation.message.lower()


def test_weather_fetch_precipitation(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"daily": {"precipitation_sum": [2.3]}}

    def fake_get(url, params, timeout):
        assert "open-meteo" in url
        assert params["daily"] == "precipitation_sum"
        assert timeout == 4
        return Response()

    monkeypatch.setattr("plantcare.services.requests.get", fake_get)

    assert WeatherService().fetch_precipitation(55.7, 37.6) == 2.3
