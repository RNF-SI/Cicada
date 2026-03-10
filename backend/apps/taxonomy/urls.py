"""URLs pour l'API TaxRef."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TaxrefViewSet

router = DefaultRouter()
router.register(r'', TaxrefViewSet, basename='taxref')

urlpatterns = [
    path('', include(router.urls)),
]
