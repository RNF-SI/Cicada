"""URLs pour l'API HabRef."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import HabrefViewSet

router = DefaultRouter()
router.register(r'', HabrefViewSet, basename='habref')

urlpatterns = [
    path('', include(router.urls)),
]
