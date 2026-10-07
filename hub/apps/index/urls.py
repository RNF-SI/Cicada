"""URLs de l'index : dépôt par les instances, et lecture de l'exploration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_exploration import (
    ExplorationContenuViewSet, ExplorationPlanViewSet, InstancesExplorationView,
)
from .views_federation import (
    EnrolementInstance, LotPublicationViewSet, RegistreDesInstances,
)

federation = DefaultRouter()
federation.register(r'lots', LotPublicationViewSet, basename='federation-lots')

exploration = DefaultRouter()
exploration.register(
    r'contenus', ExplorationContenuViewSet, basename='exploration-contenus'
)
exploration.register(r'plans', ExplorationPlanViewSet, basename='exploration-plans')

urlpatterns = [
    # Avant le routeur : « instances » n'est pas un lot, et un routeur DRF
    # ne capture que ses propres préfixes — l'ordre reste explicite.
    path('federation/instances/', RegistreDesInstances.as_view(),
         name='federation-instances'),
    # Avant le routeur, pour la même raison : enrôlement délégué à l'API de
    # suivi RNF (#696).
    path('federation/enrolements/', EnrolementInstance.as_view(),
         name='federation-enrolements'),
    path('federation/', include(federation.urls)),
    # Avant le routeur, pour la même raison que « federation/instances/ ».
    path('exploration/instances/', InstancesExplorationView.as_view(),
         name='exploration-instances'),
    path('exploration/', include(exploration.urls)),
]
