"""URLs de l'API d'exploration des données."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ExplorationContenuViewSet, ExplorationPlanViewSet, FederationDocumentViewSet,
)

router = DefaultRouter()
router.register(r'contenus', ExplorationContenuViewSet, basename='exploration-contenus')
router.register(r'plans', ExplorationPlanViewSet, basename='exploration-plans')
# Publication vers une exploration centralisée (#636) : machine à machine,
# authentifiée par jeton partagé et non par compte utilisateur.
router.register(
    r'federation/documents', FederationDocumentViewSet,
    basename='federation-documents',
)

urlpatterns = [
    path('', include(router.urls)),
]
