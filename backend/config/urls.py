"""
URL configuration for CICADA project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for Docker."""
    return JsonResponse({'status': 'healthy', 'service': 'cicada'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/plans/', include('apps.plans.urls')),
    path('api/inventaires/', include('apps.plans.urls_suivis')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.core.urls')),
    path('api/taxref/', include('apps.taxonomy.urls')),
    path('api/habref/', include('apps.habitats.urls')),
    path('api/inpg/', include('apps.geology.urls')),
    path('api/campanule/', include('apps.campanule.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)