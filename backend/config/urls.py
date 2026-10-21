"""
URL configuration for CICADA project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.search.urls import federation_urlpatterns
from apps.search.views import DocumentPublicView


def health_check(request):
    """Simple health check endpoint for Docker."""
    return JsonResponse({'status': 'healthy', 'service': 'cicada'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    # Schéma OpenAPI + Swagger UI, ouverts sans connexion (#750). La documentation statique
    # servie sous /aide/ embarque une copie du schéma (documentation/docs/api/).
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/plans/', include('apps.plans.urls')),
    path('api/inventaires/', include('apps.plans.urls_suivis')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.core.urls')),
    path('api/taxref/', include('apps.taxonomy.urls')),
    path('api/habref/', include('apps.habitats.urls')),
    path('api/inpg/', include('apps.geology.urls')),
    path('api/geo/', include('apps.geo.urls')),
    path('api/exploration/', include('apps.search.urls')),
    # #696 / #698 — raccordement de l'instance au hub (super admin).
    path('api/federation/', include(federation_urlpatterns)),
    # #645 — API ouverte des métadonnées des plans (GED tierce type DOCenCEN).
    # #747 — documents des plans explorables, par leur adresse publique.
    path('api/public/documents/<uuid:uuid>/', DocumentPublicView.as_view(),
         name='public-document'),
    path('api/public/', include('apps.plans.urls_public')),
    path('api/campanule/', include('apps.campanule.urls')),
    path('admin/system/', include('apps.system.urls')),
    path('api/system/', include('apps.system.api_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)