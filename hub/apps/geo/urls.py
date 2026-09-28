"""URLs de l'API du référentiel géographique."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ZoneGeographiqueViewSet

router = DefaultRouter()
router.register(r'zones', ZoneGeographiqueViewSet, basename='geo-zones')

urlpatterns = [
    path('', include(router.urls)),
]
