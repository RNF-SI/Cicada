"""
URLs pour l'API Plans de Gestion.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlanGestionViewSet, CorPgFichierViewSet,
    bulk_assign_sites, export_geojson
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'plans', PlanGestionViewSet, basename='plangestion')
router.register(r'fichiers', CorPgFichierViewSet, basename='corpgfichier')

# URLs spécifiques
urlpatterns = [
    # Routes des ViewSets
    path('', include(router.urls)),
    
    # Actions en masse
    path('plans/bulk_assign_sites/', bulk_assign_sites, name='bulk_assign_sites'),
    
    # Exports
    path('plans/export_geojson/', export_geojson, name='export_geojson'),
]

# URLs générées par le router:
# GET /api/plans/plans/ - Liste des plans
# POST /api/plans/plans/ - Créer un plan
# GET /api/plans/plans/{id}/ - Détail d'un plan
# PUT/PATCH /api/plans/plans/{id}/ - Modifier un plan
# DELETE /api/plans/plans/{id}/ - Supprimer un plan
# GET /api/plans/plans/geojson_list/ - Liste GeoJSON
# GET /api/plans/plans/{id}/geojson/ - GeoJSON individuel
# POST /api/plans/plans/{id}/assign_site/ - Assigner site
# DELETE /api/plans/plans/{id}/remove_site/ - Retirer site
# POST /api/plans/plans/{id}/assign_referent/ - Assigner référent
# GET /api/plans/plans/stats/ - Statistiques

# GET /api/plans/fichiers/ - Liste des fichiers
# POST /api/plans/fichiers/ - Upload fichier
# GET /api/plans/fichiers/{id}/ - Détail fichier
# PUT/PATCH /api/plans/fichiers/{id}/ - Modifier fichier
# DELETE /api/plans/fichiers/{id}/ - Supprimer fichier
# GET /api/plans/fichiers/{id}/download/ - Télécharger fichier