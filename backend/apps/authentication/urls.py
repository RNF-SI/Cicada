"""
URLs pour l'authentification JWT.
"""
from django.urls import path

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    logout_view,
    user_info_view,
    health_check_view,
    start_impersonation_view,
    stop_impersonation_view,
    impersonation_logs_view,
    public_stats_view
)
from apps.notifications.views import (
    public_registration_view,
    check_registration_status_view
)

app_name = 'authentication'

urlpatterns = [
    # Authentification JWT
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),

    # Inscription publique
    path('register/', public_registration_view, name='register'),
    path('registration-status/', check_registration_status_view, name='registration_status'),

    # Informations utilisateur
    path('me/', user_info_view, name='user_info'),

    # Impersonation (super_admin uniquement)
    path('impersonate/<int:user_id>/', start_impersonation_view, name='start_impersonation'),
    path('stop-impersonation/', stop_impersonation_view, name='stop_impersonation'),
    path('impersonation-logs/', impersonation_logs_view, name='impersonation_logs'),

    # Health check
    path('health/', health_check_view, name='health_check'),

    # Public stats (accessible without authentication)
    path('stats/', public_stats_view, name='public_stats'),
]