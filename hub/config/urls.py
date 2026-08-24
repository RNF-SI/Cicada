"""
Racine des URL du hub.

Le hub n'expose que des API. Deux familles, aux droits distincts :

- ``/api/federation/`` — le **dépôt** : réservé aux instances émettrices,
  authentifié par un jeton propre à chacune ;
- ``/api/exploration/`` — la **lecture** : recherche transverse et fiche d'un
  plan, servies aux instances qui relaient l'exploration de leurs utilisateurs.

Il n'y a délibérément pas d'interface d'administration : rien ici ne se saisit
à la main, tout arrive par publication.
"""

from django.http import JsonResponse
from django.urls import include, path

from django.conf import settings


def health(_request):
    """Sonde de disponibilité, sans jeton — utilisée par Docker et le déploiement."""
    return JsonResponse({
        'statut': 'ok',
        'service': 'cicada-hub',
        'instance': settings.HUB_INSTANCE_ID,
    })


urlpatterns = [
    path('api/health/', health, name='health'),
    path('api/', include('apps.index.urls')),
    path('api/geo/', include('apps.geo.urls')),
]
