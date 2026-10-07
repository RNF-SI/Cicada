"""URLs de l'API d'exploration des données."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .distant import EcransDistantsView
from .views_raccordement import (
    RaccordementAdhesionView, RaccordementVerifierView, RaccordementView,
)
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

#: Monté sous `/api/federation/` (cf. `config/urls.py`) : le raccordement au
#: hub n'est pas de l'exploration, et ce préfixe est celui des échanges avec le
#: hub — côté hub comme ici (#696, #698).
federation_urlpatterns = [
    path('raccordement/', RaccordementView.as_view(), name='federation-raccordement'),
    path('raccordement/verifier/', RaccordementVerifierView.as_view(),
         name='federation-raccordement-verifier'),
    path('raccordement/adhesion/', RaccordementAdhesionView.as_view(),
         name='federation-raccordement-adhesion'),
]
