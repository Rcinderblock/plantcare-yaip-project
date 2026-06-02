from dataclasses import dataclass
from datetime import timedelta

import requests
from django.utils import timezone


@dataclass
class WateringRecommendation:
    should_water_today: bool
    next_watering_date: str
    precipitation_mm: float
    message: str


class WeatherService:
    endpoint = "https://api.open-meteo.com/v1/forecast"

    def fetch_precipitation(self, latitude: float, longitude: float) -> float:
        response = requests.get(
            self.endpoint,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "precipitation_sum",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=4,
        )
        response.raise_for_status()
        data = response.json()
        return float(data.get("daily", {}).get("precipitation_sum", [0])[0] or 0)

    def build_recommendation(self, plant, precipitation_mm: float) -> WateringRecommendation:
        due_at = plant.next_watering_due()
        due_date = due_at.date()
        today = timezone.localdate()

        # Балконные растения получают воду от дождя, поэтому сильные осадки
        # переносят следующий полив; для комнатных растений погода не влияет.
        if plant.location_type == "balcony" and precipitation_mm >= 3:
            postponed = today + timedelta(days=2)
            return WateringRecommendation(
                should_water_today=False,
                next_watering_date=postponed.isoformat(),
                precipitation_mm=precipitation_mm,
                message="Ожидается дождь: полив балконного растения можно отложить.",
            )

        should_water = due_date <= today
        message = "Сегодня стоит полить растение." if should_water else "Полив пока не требуется."
        return WateringRecommendation(
            should_water_today=should_water,
            next_watering_date=due_date.isoformat(),
            precipitation_mm=precipitation_mm,
            message=message,
        )
