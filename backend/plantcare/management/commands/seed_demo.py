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
        "image_url": "https://images.unsplash.com/photo-1614594895304-fe7116ac3b58?auto=format&fit=crop&w=900&q=80",
    },
    {
        "name": "Сансевиерия",
        "latin_name": "Dracaena trifasciata",
        "description": "Выносливое растение, хорошо переносит редкий полив и сухой воздух.",
        "light": "low",
        "humidity": 40,
        "watering_interval_days": 14,
        "pet_safe": False,
        "image_url": "https://images.unsplash.com/photo-1593482892290-f54927ae2b87?auto=format&fit=crop&w=900&q=80",
    },
    {
        "name": "Базилик",
        "latin_name": "Ocimum basilicum",
        "description": "Ароматная зелень для балкона и кухни, любит солнце и регулярный полив.",
        "light": "high",
        "humidity": 55,
        "watering_interval_days": 2,
        "pet_safe": True,
        "image_url": "https://images.unsplash.com/photo-1618164435735-413d3b066c9a?auto=format&fit=crop&w=900&q=80",
    },
    {
        "name": "Фикус Бенджамина",
        "latin_name": "Ficus benjamina",
        "description": "Комнатное дерево для стабильного места без сквозняков.",
        "light": "medium",
        "humidity": 55,
        "watering_interval_days": 8,
        "pet_safe": False,
        "image_url": "https://images.unsplash.com/photo-1597305877032-0668b3c6413a?auto=format&fit=crop&w=900&q=80",
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
