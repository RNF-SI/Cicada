"""
URLs pour les vues de démonstration du système de permissions.
"""
from django.urls import path
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

app_name = 'users'

urlpatterns = [
    # Vues avec permissions DRF
    path('test/super-admin/', super_admin_only_view, name='test_super_admin'),
    path('test/admin-organisme/', admin_organisme_view, name='test_admin_organisme'),
    path('test/referent/', referent_view, name='test_referent'),
    
    # Vues avec décorateurs
    path('test/decorator-super-admin/', decorator_super_admin_view, name='test_decorator_super_admin'),
    path('test/decorator-admin-organisme/', decorator_admin_organisme_view, name='test_decorator_admin_organisme'),
    path('test/decorator-referent/', decorator_referent_view, name='test_decorator_referent'),
    
    # Vues avec permissions d'objet
    path('organismes/<int:organisme_id>/', organisme_detail_view, name='organisme_detail'),
    path('sites/<int:site_id>/', site_detail_view, name='site_detail'),
    
    # Vue d'information sur les permissions
    path('permissions/', permissions_info_view, name='permissions_info'),
]