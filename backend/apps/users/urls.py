"""
URLs pour l'API des utilisateurs, organismes et sites.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    super_admin_only_view,
    admin_organisme_view,
    referent_view,
    decorator_super_admin_view,
    decorator_admin_organisme_view,
    decorator_referent_view,
    organisme_detail_view,
    site_detail_view,
    permissions_info_view,
)
from .viewsets import RoleViewSet
from .viewsets_org_sites import OrganismeViewSet, SiteViewSet

app_name = 'users'

# Router principal
router = DefaultRouter()
router.register(r'users', RoleViewSet, basename='users')
router.register(r'organismes', OrganismeViewSet, basename='organismes')
router.register(r'sites', SiteViewSet, basename='sites')

# Routes nested pour organismes/{id}/sites
try:
    organismes_router = routers.NestedDefaultRouter(
        router, r'organismes', lookup='organisme'
    )
    organismes_router.register(
        r'sites', SiteViewSet, basename='organisme-sites'
    )
    NESTED_ROUTES_AVAILABLE = True
except ImportError:
    # Fallback si drf-nested-routers n'est pas installé
    organismes_router = None
    NESTED_ROUTES_AVAILABLE = False

urlpatterns = [
    # API REST principale
    path('', include(router.urls)),
    
    # Routes nested si disponibles
    path('', include(organismes_router.urls)) if NESTED_ROUTES_AVAILABLE else path('', lambda r: None),
    
    # Routes manuelles pour sites d'un organisme (fallback)
    path('organismes/<int:organisme_pk>/sites/', 
         SiteViewSet.as_view({'get': 'list'}), 
         name='organisme_sites_list'),
    path('organismes/<int:organisme_pk>/sites/<int:pk>/', 
         SiteViewSet.as_view({'get': 'retrieve'}), 
         name='organisme_sites_detail'),
    
    # Routes pour désassignation (nested)
    path('organismes/<int:organisme_pk>/sites/<int:site_pk>/',
         OrganismeViewSet.as_view({'delete': 'unassign_site'}),
         name='organisme_unassign_site'),
    path('sites/<int:site_pk>/users/<int:user_pk>/',
         SiteViewSet.as_view({'delete': 'unassign_user'}),
         name='site_unassign_user'),
    
    # Vues de test/démonstration avec permissions DRF
    path('test/super-admin/', super_admin_only_view, name='test_super_admin'),
    path('test/admin-organisme/', admin_organisme_view, name='test_admin_organisme'),
    path('test/referent/', referent_view, name='test_referent'),
    
    # Vues de test avec décorateurs
    path('test/decorator-super-admin/', decorator_super_admin_view, name='test_decorator_super_admin'),
    path('test/decorator-admin-organisme/', decorator_admin_organisme_view, name='test_decorator_admin_organisme'),
    path('test/decorator-referent/', decorator_referent_view, name='test_decorator_referent'),
    
    # Vues de test avec permissions d'objet
    path('test/organismes/<int:organisme_id>/', organisme_detail_view, name='organisme_detail'),
    path('test/sites/<int:site_id>/', site_detail_view, name='site_detail'),
    
    # Vue d'information sur les permissions
    path('test/permissions/', permissions_info_view, name='permissions_info'),
]