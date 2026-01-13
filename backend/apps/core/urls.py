"""
URLs pour les modeles du core.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ModuleViewSet

router = DefaultRouter()
router.register(r'modules', ModuleViewSet, basename='module')

urlpatterns = [
    path('', include(router.urls)),
]
