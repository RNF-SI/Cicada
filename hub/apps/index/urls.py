"""URLs de l'index : dépôt par les instances."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_federation import LotPublicationViewSet

router = DefaultRouter()
router.register(r'lots', LotPublicationViewSet, basename='federation-lots')

urlpatterns = [
    path('', include(router.urls)),
]
