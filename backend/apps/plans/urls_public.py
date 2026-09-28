"""URLs de l'API publique des métadonnées des plans (#645)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_public import PlanPublicViewSet

router = DefaultRouter()
router.register(r'plans', PlanPublicViewSet, basename='public-plans')

urlpatterns = [
    path('', include(router.urls)),
]
