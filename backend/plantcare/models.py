from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PlantSpecies(models.Model):
    class LightLevel(models.TextChoices):
        LOW = "low", "Тень"
        MEDIUM = "medium", "Рассеянный свет"
        HIGH = "high", "Яркий свет"

    name = models.CharField(max_length=120, unique=True)
    latin_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    light = models.CharField(max_length=20, choices=LightLevel.choices, default=LightLevel.MEDIUM)
    humidity = models.PositiveSmallIntegerField(default=50)
    watering_interval_days = models.PositiveSmallIntegerField(default=7)
    pet_safe = models.BooleanField(default=False)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "вид растения"
        verbose_name_plural = "виды растений"

    def __str__(self) -> str:
        return self.name


class UserPlant(models.Model):
    class LocationType(models.TextChoices):
        INDOOR = "indoor", "В помещении"
        BALCONY = "balcony", "На балконе"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plants")
    species = models.ForeignKey(PlantSpecies, on_delete=models.PROTECT, related_name="user_plants")
    nickname = models.CharField(max_length=120)
    location_type = models.CharField(max_length=20, choices=LocationType.choices, default=LocationType.INDOOR)
    planted_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    watering_interval_override = models.PositiveSmallIntegerField(null=True, blank=True)
    last_watered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    collections = models.ManyToManyField("Collection", through="CollectionPlant", related_name="plants")

    class Meta:
        ordering = ["nickname"]
        unique_together = ("owner", "nickname")
        verbose_name = "растение пользователя"
        verbose_name_plural = "растения пользователя"

    def __str__(self) -> str:
        return f"{self.nickname} ({self.owner})"

    @property
    def watering_interval_days(self) -> int:
        return self.watering_interval_override or self.species.watering_interval_days

    def next_watering_due(self):
        base = self.last_watered_at or self.created_at or timezone.now()
        return base + timedelta(days=self.watering_interval_days)


class CareTask(models.Model):
    class TaskType(models.TextChoices):
        WATER = "water", "Полив"
        FERTILIZE = "fertilize", "Удобрение"
        REPOT = "repot", "Пересадка"
        PRUNE = "prune", "Обрезка"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        DONE = "done", "Выполнено"
        SKIPPED = "skipped", "Пропущено"

    plant = models.ForeignKey(UserPlant, on_delete=models.CASCADE, related_name="tasks")
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.WATER)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "plant__nickname"]
        verbose_name = "задача ухода"
        verbose_name_plural = "задачи ухода"

    def __str__(self) -> str:
        return f"{self.get_task_type_display()} для {self.plant.nickname}"


class CareLog(models.Model):
    plant = models.ForeignKey(UserPlant, on_delete=models.CASCADE, related_name="logs")
    task_type = models.CharField(max_length=20, choices=CareTask.TaskType.choices, default=CareTask.TaskType.WATER)
    performed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_at"]
        verbose_name = "запись ухода"
        verbose_name_plural = "записи ухода"

    def __str__(self) -> str:
        return f"{self.get_task_type_display()} {self.plant.nickname}"


class Collection(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plant_collections")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("owner", "name")
        verbose_name = "коллекция"
        verbose_name_plural = "коллекции"

    def __str__(self) -> str:
        return self.name


class CollectionPlant(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    plant = models.ForeignKey(UserPlant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("collection", "plant")
        verbose_name = "растение в коллекции"
        verbose_name_plural = "растения в коллекциях"

    def __str__(self) -> str:
        return f"{self.plant.nickname} в {self.collection.name}"
