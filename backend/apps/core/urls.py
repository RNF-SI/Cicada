"""
URLs pour les modeles du core.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ModuleViewSet, ErrorLogViewSet, ActivityLogViewSet

router = DefaultRouter()
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'activity', ActivityLogViewSet, basename='activity')

# Router pour les endpoints admin (sous /api/admin/)
admin_router = DefaultRouter()
admin_router.register(r'error-logs', ErrorLogViewSet, basename='error-log')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', include(admin_router.urls)),
]
