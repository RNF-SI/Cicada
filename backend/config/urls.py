"""
URL configuration for Outil Plan de Gestion project.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for Docker."""
    return JsonResponse({'status': 'healthy', 'service': 'outil-plan-gestion'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/plans/', include('apps.plans.urls')),
]