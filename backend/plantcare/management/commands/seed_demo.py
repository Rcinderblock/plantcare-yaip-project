from django.core.management.base import BaseCommand

from plantcare.models import PlantSpecies


DEMO_SPECIES = [
    {
        "name": "Монстера",
        "latin_name": "Monstera deliciosa",
        "description": "Крупное декоративное растение для светлой комнаты без прямого солнца.",
        "light": "medium",
        "humidity": 65,
        "watering_interval_days": 7,
        "pet_safe": False,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Monstera_deliciosa2.jpg/960px-Monstera_deliciosa2.jpg",
    },
    {
        "name": "Сансевиерия",
        "latin_name": "Dracaena trifasciata",
        "description": "Выносливое растение, хорошо переносит редкий полив и сухой воздух.",
        "light": "low",
        "humidity": 40,
        "watering_interval_days": 14,
        "pet_safe": False,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Snake_Plant_I_%28crop_version%29.png/960px-Snake_Plant_I_%28crop_version%29.png",
    },
    {
        "name": "Базилик",
        "latin_name": "Ocimum basilicum",
        "description": "Ароматная зелень для балкона и кухни, любит солнце и регулярный полив.",
        "light": "high",
        "humidity": 55,
        "watering_interval_days": 2,
        "pet_safe": True,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Basil-Basilico-Ocimum_basilicum-albahaca.jpg/960px-Basil-Basilico-Ocimum_basilicum-albahaca.jpg",
    },
    {
        "name": "Фикус Бенджамина",
        "latin_name": "Ficus benjamina",
        "description": "Комнатное дерево для стабильного места без сквозняков.",
        "light": "medium",
        "humidity": 55,
        "watering_interval_days": 8,
        "pet_safe": False,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/25/Ficus_benjamina.jpg",
    },
]


class Command(BaseCommand):
    help = "Create demo plant species for local development."

    def handle(self, *args, **options):
        created = 0
        for item in DEMO_SPECIES:
            _, was_created = PlantSpecies.objects.update_or_create(name=item["name"], defaults=item)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Demo species ready. Created: {created}"))
