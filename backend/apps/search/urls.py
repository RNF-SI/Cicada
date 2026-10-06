"""URLs de l'API d'exploration des données."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .distant import EcransDistantsView
from .views import (
    ExplorationContenuViewSet, ExplorationPlanViewSet, FederationDocumentViewSet,
    InstancesExplorationView,
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
    # Avant le routeur : « instances » n'est pas un plan ni un contenu.
    path('instances/', InstancesExplorationView.as_view(),
         name='exploration-instances'),
    # #683 — écrans réels d'un plan distant, resservis sous les chemins de
    # l'API des plans (cf. `distant.py`).
    path('distant/<str:reference>/<path:chemin>', EcransDistantsView.as_view(),
         name='exploration-distant'),
    path('', include(router.urls)),
]
