"""
URLs pour l'API des utilisateurs, organismes et sites.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
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

urlpatterns = [
    # API REST principale
    path('', include(router.urls)),
    
    # Routes manuelles pour relations organismes-sites
    path('organismes/<int:organisme_pk>/sites/',
         SiteViewSet.as_view({'get': 'list'}),
         name='organisme_sites_list'),
    # Route pour désassigner un site d'un organisme
    path('organismes/<int:organisme_pk>/sites/<int:site_pk>/',
         OrganismeViewSet.as_view({'delete': 'unassign_site'}),
         name='organisme_unassign_site'),
    path('sites/<int:pk>/users/<int:user_pk>/',
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
    path('permissions/', permissions_info_view, name='permissions_info'),
]