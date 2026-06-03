from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from plantcare.models import Collection, PlantSpecies, UserPlant
from plantcare.services import WeatherService, WeatherSnapshot


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

    weather = WeatherSnapshot(temperature_c=19.4, humidity_percent=68, precipitation_today_mm=5.5, precipitation_tomorrow_mm=0)
    recommendation = WeatherService().build_recommendation(plant, weather)

    assert recommendation.should_water_today is False
    assert "дожд" in recommendation.message.lower()
    assert recommendation.temperature_c == 19.4
    assert recommendation.precipitation_mm == 5.5
    assert recommendation.rain_expected is True


@pytest.mark.django_db
def test_indoor_plant_still_gets_weather_context_for_high_humidity():
    user = get_user_model().objects.create_user(username="indoor", password="secret-pass")
    species = PlantSpecies.objects.create(name="Сансевиерия", watering_interval_days=14)
    plant = UserPlant.objects.create(owner=user, species=species, nickname="Комнатная сансевиерия")
    weather = WeatherSnapshot(temperature_c=22.0, humidity_percent=82, precipitation_today_mm=0, precipitation_tomorrow_mm=0)

    recommendation = WeatherService().build_recommendation(plant, weather)

    assert recommendation.humidity_percent == 82
    assert "Влажность высокая" in recommendation.weather_summary
    assert "Растение в комнате" in recommendation.message


def test_weather_fetch_weather(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "current": {"temperature_2m": 21.7, "relative_humidity_2m": 78, "precipitation": 0},
                "daily": {"precipitation_sum": [2.3, 4.1]},
            }

    def fake_get(url, params, timeout):
        assert "open-meteo" in url
        assert params["current"] == "temperature_2m,relative_humidity_2m,precipitation"
        assert params["daily"] == "precipitation_sum"
        assert params["forecast_days"] == 2
        assert timeout == 4
        return Response()

    monkeypatch.setattr("plantcare.services.requests.get", fake_get)
    weather = WeatherService().fetch_weather(55.7, 37.6)

    assert weather.temperature_c == 21.7
    assert weather.humidity_percent == 78
    assert weather.precipitation_today_mm == 2.3
    assert weather.precipitation_tomorrow_mm == 4.1
    assert weather.rain_expected is True
