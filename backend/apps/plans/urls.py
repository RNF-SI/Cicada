"""
URLs pour l'API Plans de Gestion.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlanGestionViewSet, CorPgFichierViewSet,
    bulk_assign_sites, export_geojson
)
from .views_enjeux import (
    EnjeuViewSet, ResponsabiliteViewSet,
    FacteurInfluenceViewSet, PressionViewSet,
    ObjectifLongTermeViewSet, NiveauExigenceViewSet,
    ObjectifOperationnelViewSet, ResultatAttenduViewSet,
    CorEnjeuFichierViewSet
)
from .views_indicateurs import IndicateurViewSet, MetriqueViewSet, MesureViewSet, IndicateurMesureViewSet
from .views_operations import (
    OperationViewSet,
    RealisationOperationAnneeViewSet,
    RealisationOperationAnneeOrganismeViewSet,
    FonctionViewSet,
    PersonnePlanViewSet,
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'plans', PlanGestionViewSet, basename='plangestion')
router.register(r'fichiers', CorPgFichierViewSet, basename='corpgfichier')
router.register(r'enjeux', EnjeuViewSet, basename='enjeu')
router.register(r'enjeux-fichiers', CorEnjeuFichierViewSet, basename='enjeu-fichier')
router.register(r'responsabilites', ResponsabiliteViewSet, basename='responsabilite')
router.register(r'facteurs-influence', FacteurInfluenceViewSet, basename='facteurinfluence')
router.register(r'pressions', PressionViewSet, basename='pression')
router.register(r'objectifs-long-terme', ObjectifLongTermeViewSet, basename='objectiflongterme')
router.register(r'niveaux-exigence', NiveauExigenceViewSet, basename='niveauexigence')
router.register(r'indicateurs', IndicateurViewSet, basename='indicateur')
router.register(r'metriques', MetriqueViewSet, basename='metrique')
router.register(r'mesures', MesureViewSet, basename='mesure')
router.register(r'indicateur-mesures', IndicateurMesureViewSet, basename='indicateur-mesure')
router.register(r'objectifs-operationnels', ObjectifOperationnelViewSet, basename='objectifoperationnel')
router.register(r'resultats-attendus', ResultatAttenduViewSet, basename='resultatattendu')
router.register(r'operations', OperationViewSet, basename='operation')
router.register(r'realisations', RealisationOperationAnneeViewSet, basename='realisation')
router.register(r'realisations-organismes', RealisationOperationAnneeOrganismeViewSet, basename='realisation-organisme')
router.register(r'fonctions', FonctionViewSet, basename='fonction')
router.register(r'personnes', PersonnePlanViewSet, basename='personne-plan')

# URLs spécifiques
# NOTE: Specific paths must come BEFORE the router to avoid being captured by router patterns
urlpatterns = [
    # Actions en masse (MUST be before router)
    path('plans/bulk_assign_sites/', bulk_assign_sites, name='bulk_assign_sites'),

    # Exports (MUST be before router)
    path('plans/export_geojson/', export_geojson, name='export_geojson'),

    # Routes des ViewSets (comes last)
    path('', include(router.urls)),
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

# GET /api/plans/enjeux/ - Liste des enjeux/FCR
# POST /api/plans/enjeux/ - Créer un enjeu/FCR
# GET /api/plans/enjeux/{id}/ - Détail d'un enjeu/FCR
# PUT/PATCH /api/plans/enjeux/{id}/ - Modifier un enjeu/FCR
# DELETE /api/plans/enjeux/{id}/ - Supprimer un enjeu/FCR
# GET /api/plans/enjeux/by-plan/{plan_id}/ - Enjeux d'un plan
# POST /api/plans/enjeux/{id}/add_taxon/ - Ajouter un taxon
# DELETE /api/plans/enjeux/{id}/remove_taxon/{cd_nom}/ - Supprimer un taxon
# POST /api/plans/enjeux/{id}/add_habitat/ - Ajouter un habitat
# DELETE /api/plans/enjeux/{id}/remove_habitat/{cd_hab}/ - Supprimer un habitat
# GET /api/plans/enjeux/stats/ - Statistiques des enjeux

# GET /api/plans/responsabilites/ - Liste des responsabilités
# POST /api/plans/responsabilites/ - Créer une responsabilité
# GET /api/plans/responsabilites/{id}/ - Détail d'une responsabilité
# PUT/PATCH /api/plans/responsabilites/{id}/ - Modifier une responsabilité
# DELETE /api/plans/responsabilites/{id}/ - Supprimer une responsabilité
# GET /api/plans/responsabilites/by-site/{site_id}/ - Responsabilités d'un site
# GET /api/plans/responsabilites/stats/ - Statistiques des responsabilités