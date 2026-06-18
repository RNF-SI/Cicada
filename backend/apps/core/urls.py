"""
URLs pour les modeles du core.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ModuleViewSet,
    ErrorLogViewSet,
    ActivityLogViewSet,
    NomenclatureViewSet,
    SiteConfigurationView,
    AdminOrphansView,
    AdminOrphansCountsView,
)

router = DefaultRouter()
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'activity', ActivityLogViewSet, basename='activity')
router.register(r'nomenclatures', NomenclatureViewSet, basename='nomenclature')

# Router pour les endpoints admin (sous /api/admin/)
admin_router = DefaultRouter()
admin_router.register(r'error-logs', ErrorLogViewSet, basename='error-log')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', include(admin_router.urls)),
    # Sites et plans orphelins (admin_og+) - remplace l'audit hebdomadaire par email
    path('admin/orphans/', AdminOrphansView.as_view(), name='admin-orphans'),
    path('admin/orphans/counts/', AdminOrphansCountsView.as_view(), name='admin-orphans-counts'),
    # Site configuration (public GET, super_admin PATCH)
    path('settings/', SiteConfigurationView.as_view(), name='site-configuration'),
]
