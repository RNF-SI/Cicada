"""URLs de l'API d'exploration des données."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExplorationContenuViewSet, ExplorationPlanViewSet

router = DefaultRouter()
router.register(r'contenus', ExplorationContenuViewSet, basename='exploration-contenus')
router.register(r'plans', ExplorationPlanViewSet, basename='exploration-plans')

urlpatterns = [
    path('', include(router.urls)),
]
