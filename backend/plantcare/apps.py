from django.apps import AppConfig


class PlantcareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plantcare"

    def ready(self):
        from . import schema  # noqa: F401
