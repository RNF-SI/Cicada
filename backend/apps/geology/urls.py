"""URLs pour l'API INPG (géologie)."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import InpgViewSet

router = DefaultRouter()
router.register(r'', InpgViewSet, basename='inpg')

urlpatterns = [
    path('', include(router.urls)),
]
