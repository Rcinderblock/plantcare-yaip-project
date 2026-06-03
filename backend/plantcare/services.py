from dataclasses import dataclass
from datetime import timedelta

import requests
from django.utils import timezone


@dataclass
class WeatherSnapshot:
    temperature_c: float
    humidity_percent: int
    precipitation_today_mm: float
    precipitation_tomorrow_mm: float

    @property
    def rain_expected(self) -> bool:
        return self.precipitation_today_mm >= 1 or self.precipitation_tomorrow_mm >= 1


@dataclass
class WateringRecommendation:
    should_water_today: bool
    next_watering_date: str
    precipitation_mm: float
    precipitation_tomorrow_mm: float
    temperature_c: float
    humidity_percent: int
    rain_expected: bool
    weather_summary: str
    message: str


class WeatherService:
    endpoint = "https://api.open-meteo.com/v1/forecast"

    def fetch_weather(self, latitude: float, longitude: float) -> WeatherSnapshot:
        response = requests.get(
            self.endpoint,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,precipitation",
                "daily": "precipitation_sum",
                "forecast_days": 2,
                "timezone": "auto",
            },
            timeout=4,
        )
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        daily_precipitation = data.get("daily", {}).get("precipitation_sum", [])
        precipitation_today = float(daily_precipitation[0] if daily_precipitation else current.get("precipitation", 0) or 0)
        precipitation_tomorrow = float(daily_precipitation[1] if len(daily_precipitation) > 1 else 0)
        return WeatherSnapshot(
            temperature_c=float(current.get("temperature_2m", 0) or 0),
            humidity_percent=int(current.get("relative_humidity_2m", 0) or 0),
            precipitation_today_mm=precipitation_today,
            precipitation_tomorrow_mm=precipitation_tomorrow,
        )

    def build_recommendation(self, plant, weather: WeatherSnapshot) -> WateringRecommendation:
        due_at = plant.next_watering_due()
        due_date = due_at.date()
        today = timezone.localdate()
        should_water = due_date <= today
        summary = self._build_weather_summary(weather)

        # Балконные растения получают воду от дождя, поэтому заметные осадки
        # переносят следующий полив; для комнатных растений погода остается
        # контекстом, но решение принимает график ухода.
        if plant.location_type == "balcony" and (weather.precipitation_today_mm >= 3 or weather.precipitation_tomorrow_mm >= 3):
            postponed = today + timedelta(days=2)
            return WateringRecommendation(
                should_water_today=False,
                next_watering_date=postponed.isoformat(),
                precipitation_mm=weather.precipitation_today_mm,
                precipitation_tomorrow_mm=weather.precipitation_tomorrow_mm,
                temperature_c=weather.temperature_c,
                humidity_percent=weather.humidity_percent,
                rain_expected=weather.rain_expected,
                weather_summary=summary,
                message="Балконное растение можно не поливать сейчас: скоро дождь поможет с поливом.",
            )

        if plant.location_type == "balcony":
            message = (
                "По графику пора поливать, а заметного дождя не ожидается."
                if should_water
                else "По графику полив пока не нужен; погоду можно использовать как дополнительную подсказку."
            )
        else:
            message = (
                "Растение в комнате: погода не заменяет полив, по графику сегодня стоит проверить грунт."
                if should_water
                else "Растение в комнате: погода показана для контекста, по графику полив пока не нужен."
            )
        return WateringRecommendation(
            should_water_today=should_water,
            next_watering_date=due_date.isoformat(),
            precipitation_mm=weather.precipitation_today_mm,
            precipitation_tomorrow_mm=weather.precipitation_tomorrow_mm,
            temperature_c=weather.temperature_c,
            humidity_percent=weather.humidity_percent,
            rain_expected=weather.rain_expected,
            weather_summary=summary,
            message=message,
        )

    def _build_weather_summary(self, weather: WeatherSnapshot) -> str:
        if weather.precipitation_today_mm >= 3:
            return "Сегодня ожидается заметный дождь."
        if weather.precipitation_today_mm >= 1:
            return "Сегодня возможен небольшой дождь."
        if weather.precipitation_tomorrow_mm >= 3:
            return "Скоро дождь: осадки вероятны завтра."
        if weather.precipitation_tomorrow_mm >= 1:
            return "Скоро дождь: завтра возможны небольшие осадки."
        if weather.humidity_percent >= 75:
            return "Влажность высокая: грунт может просыхать медленнее."
        if weather.temperature_c >= 28 and weather.humidity_percent < 45:
            return "Жарко и сухо: растения могут быстрее терять влагу."
        return "Дождя не ожидается, ориентируйтесь на график ухода и состояние грунта."
