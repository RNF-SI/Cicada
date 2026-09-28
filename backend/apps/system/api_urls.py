"""
URLs API pour le module system (version, mise à jour).
Montées sous /api/system/
"""
from django.urls import path
from . import api_views

urlpatterns = [
    path('version/', api_views.SystemVersionView.as_view(), name='api_system_version'),
    path('app-version/', api_views.SystemAppVersionView.as_view(), name='api_system_app_version'),
    path('trigger-update/', api_views.SystemTriggerUpdateView.as_view(), name='api_system_trigger_update'),
]
