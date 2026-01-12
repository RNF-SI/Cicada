"""
URLs pour les notifications et validations.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    ValidationRequestViewSet,
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'validations', ValidationRequestViewSet, basename='validation')

urlpatterns = [
    path('', include(router.urls)),
]
