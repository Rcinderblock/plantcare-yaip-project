from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CareLogViewSet,
    CareTaskViewSet,
    CollectionViewSet,
    MeView,
    PlantImportView,
    PlantSpeciesViewSet,
    RegisterView,
    UserPlantViewSet,
    WeatherRecommendationView,
)

router = DefaultRouter()
router.register("species", PlantSpeciesViewSet, basename="species")
router.register("plants", UserPlantViewSet, basename="plants")
router.register("care-tasks", CareTaskViewSet, basename="care-tasks")
router.register("care-logs", CareLogViewSet, basename="care-logs")
router.register("collections", CollectionViewSet, basename="collections")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("import/plants/", PlantImportView.as_view(), name="plant-import"),
    path("weather/recommendation/", WeatherRecommendationView.as_view(), name="weather-recommendation"),
]
