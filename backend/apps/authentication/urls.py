"""
URLs pour l'authentification JWT.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    logout_view,
    user_info_view,
    health_check_view
)

app_name = 'authentication'

urlpatterns = [
    # Authentification JWT
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    
    # Informations utilisateur
    path('me/', user_info_view, name='user_info'),
    
    # Health check
    path('health/', health_check_view, name='health_check'),
]