"""URLs de l'index : dépôt par les instances, et lecture de l'exploration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_exploration import ExplorationContenuViewSet, ExplorationPlanViewSet
from .views_federation import LotPublicationViewSet

federation = DefaultRouter()
federation.register(r'lots', LotPublicationViewSet, basename='federation-lots')

exploration = DefaultRouter()
exploration.register(
    r'contenus', ExplorationContenuViewSet, basename='exploration-contenus'
)
exploration.register(r'plans', ExplorationPlanViewSet, basename='exploration-plans')

urlpatterns = [
    path('federation/', include(federation.urls)),
    path('exploration/', include(exploration.urls)),
]
