from django.contrib import admin

from .models import CareLog, CareTask, Collection, CollectionPlant, PlantSpecies, UserPlant


@admin.register(PlantSpecies)
class PlantSpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "latin_name", "light", "watering_interval_days", "pet_safe")
    search_fields = ("name", "latin_name")
    list_filter = ("light", "pet_safe")


@admin.register(UserPlant)
class UserPlantAdmin(admin.ModelAdmin):
    list_display = ("nickname", "owner", "species", "location_type", "last_watered_at")
    search_fields = ("nickname", "owner__username", "species__name")
    list_filter = ("location_type", "species")


@admin.register(CareTask)
class CareTaskAdmin(admin.ModelAdmin):
    list_display = ("plant", "task_type", "due_date", "status")
    list_filter = ("task_type", "status", "due_date")


@admin.register(CareLog)
class CareLogAdmin(admin.ModelAdmin):
    list_display = ("plant", "task_type", "performed_at")
    list_filter = ("task_type",)


class CollectionPlantInline(admin.TabularInline):
    model = CollectionPlant
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username")
    inlines = [CollectionPlantInline]
