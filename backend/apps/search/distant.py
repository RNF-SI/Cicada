"""
Écrans réels d'un plan distant (#683, #693).

Un résultat d'exploration qui vient d'une autre instance (#636) s'ouvre dans
les **mêmes écrans** qu'un plan local : page du plan, arborescence, fiche
action. Ces écrans appellent l'API des plans (`/api/plans/…`) ; or le plan
n'est pas dans cette base. Le frontend redirige donc leurs appels vers

    GET /api/exploration/distant/<instance:slug>/<chemin de l'API des plans>

et cette vue y répond à partir de l'**instantané publié** par l'instance
émettrice (`apps.search.ecrans`) et stocké par le hub — des réponses d'API
déjà élaguées des données sensibles, resservies sous les chemins attendus.

Seuls les chemins que ces écrans utilisent en lecture d'exploration sont
servis ; tout le reste répond 404, comme le ferait l'API locale pour un
lecteur sans droits. Le `slug` servi est la **référence** complète
(« rnf:camargue ») : c'est elle que les pages mettent dans leurs liens, et
c'est elle qui fait reconnaître au frontend qu'il est sur un plan distant.
"""

import logging
import re

import requests
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .raccordement import hub_url, jeton_lecture, raccordement
from .relay import DELAI, relais_actif

logger = logging.getLogger(__name__)

#: Durée de conservation d'un instantané lu sur le hub. Les écrans d'un plan
#: enchaînent plusieurs appels (plan, enjeux, actions) : les servir d'une
#: seule lecture du hub, et laisser l'utilisateur naviguer sans le solliciter
#: à chaque clic. L'instantané lui-même ne change qu'à la publication suivante.
DUREE_CACHE = 10 * 60

#: Chemins servis, et la partie de l'instantané qui y répond.
CHEMINS = (
    (re.compile(r'^plans/by-slug/[^/]+/?$'), 'plan'),
    (re.compile(r'^plans/(?P<id>\d+)/?$'), 'plan'),
    (re.compile(r'^enjeux/by-plan/(?P<id>\d+)/?$'), 'enjeux'),
    (re.compile(r'^operations/by-plan/(?P<id>\d+)/?$'), 'operations_par_type'),
    (re.compile(r'^operations/(?P<id>\d+)/?$'), 'operation'),
)

#: Métadonnées de provenance recopiées sur chaque réponse servie, pour que
#: la page dise d'où vient ce qu'elle montre et de quand il date.
PROVENANCE = ('reference', 'instance_id', 'instance_libelle', 'url_instance', 'date_publication')


def lire_ecrans(reference):
    """
    Instantané des écrans d'un plan distant, lu sur le hub (ou en cache).

    ``None`` si le hub ne le connaît pas — ou si l'instance émettrice est
    antérieure à la publication des écrans : la fiche publique reste alors le
    seul rendu possible de ce plan.
    """
    cle = f'exploration:distant:{reference}'
    ecrans = cache.get(cle)
    if ecrans is not None:
        return ecrans

    ligne = raccordement()
    url = f"{hub_url(ligne)}/api/exploration/plans/{reference}/ecrans/"
    try:
        reponse = requests.get(
            url, headers={'X-Hub-Token': jeton_lecture(ligne) or ''}, timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.error("Hub injoignable pour les écrans de %s : %s", reference, erreur)
        return None
    if reponse.status_code != 200:
        return None
    try:
        ecrans = reponse.json()
    except ValueError:
        return None
    cache.set(cle, ecrans, DUREE_CACHE)
    return ecrans


def repondre(ecrans, chemin, reference):
    """
    La partie de l'instantané qui répond à un chemin de l'API des plans.

    ``None`` si le chemin n'est pas servi. Le `slug` du plan est remplacé par
    la référence complète, et la provenance ajoutée.
    """
    provenance = {cle: ecrans.get(cle) for cle in PROVENANCE if cle in ecrans}
    for motif, partie in CHEMINS:
        correspondance = motif.match(chemin)
        if not correspondance:
            continue
        if partie == 'operation':
            donnees = (ecrans.get('operations') or {}).get(correspondance.group('id'))
        else:
            donnees = ecrans.get(partie)
        if not donnees:
            return None
        donnees = {**donnees, **provenance}
        if partie == 'plan':
            donnees['slug'] = reference
        elif partie == 'enjeux':
            donnees['plan_slug'] = reference
        return donnees
    return None


class EcransDistantsView(APIView):
    """``GET /api/exploration/distant/<reference>/<chemin>``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, reference=None, chemin=''):
        if not relais_actif():
            return Response(
                {'detail': "Aucune exploration centralisée n'est configurée."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ecrans = lire_ecrans(reference)
        if ecrans is None:
            return Response(
                {'detail': "Ce plan distant n'est pas consultable ici."},
                status=status.HTTP_404_NOT_FOUND,
            )
        donnees = repondre(ecrans, chemin.strip('/') + '/', reference)
        if donnees is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(donnees)
