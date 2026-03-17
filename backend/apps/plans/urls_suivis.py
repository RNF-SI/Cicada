"""
URLs pour l'API Suivis/Inventaires (standalone).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_suivis import SuiviInventaireViewSet

router = DefaultRouter()
router.register(r'suivis', SuiviInventaireViewSet, basename='suiviinventaire')

urlpatterns = [
    path('', include(router.urls)),
]

# URLs générées par le router:
# GET /api/inventaires/suivis/ - Liste des suivis/inventaires
# POST /api/inventaires/suivis/ - Créer un suivi/inventaire
# GET /api/inventaires/suivis/{id}/ - Détail d'un suivi/inventaire
# PUT/PATCH /api/inventaires/suivis/{id}/ - Modifier un suivi/inventaire
# DELETE /api/inventaires/suivis/{id}/ - Supprimer un suivi/inventaire
