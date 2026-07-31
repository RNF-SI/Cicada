"""
Publication de l'index vers une exploration centralisée (#636).

CICADA est déployé en plusieurs instances (RNF, un CEN, une DREAL…), chacune
avec sa propre base. L'exploration des données doit pourtant être transverse :
une recherche doit remonter le contenu des plans validés de **toutes** les
instances. La topologie retenue pour ce premier test est l'**index central** :
chaque instance publie ses documents, un portail les agrège et sert la
recherche. C'est la seule des trois options qui préserve le tri par pertinence
transverse et l'exactitude des compteurs d'onglets, parce qu'elle garde tous les
documents dans un même index.

## Ce que ce module traite, et ce qu'il ne traite pas

Le blocage central de la fédération est que **rien n'est identifiant entre
instances** : `id_pg`, `id_objet`, `id_site`, `id_organisme`, `id_area` et même
`uuid_organisme` sont des séquences (ou des `uuid4()`) tirées localement. Le
plan n° 42 de RNF n'a aucun rapport avec le plan n° 42 du CEN.

Trois traitements différents en découlent, selon qu'une clé stable existe ou non :

| Facette | Clé | Traitement |
|---|---|---|
| Type d'aire protégée | mnémonique (`RNN`, `RNR`…) | transmise telle quelle ✅ |
| Statut du plan | chaîne (`valide`…) | transmise telle quelle ✅ |
| Zone géographique | `l_areas.area_code` (INSEE), unique par `(type, code)` | publiée en **codes**, re-résolue en identifiants locaux à l'ingestion ✅ |
| Sites | `id_site` local (`id_inpn` est nullable) | **vidée** à l'ingestion ⚠️ |
| Organismes gestionnaires | aucune — `uuid_organisme` est tiré localement | **vidée** à l'ingestion ⚠️ |

Les deux dernières sont volontairement **vidées plutôt que recopiées**. Recopier
un identifiant local ferait matcher un document distant sur le mauvais
organisme — une corruption silencieuse. Un tableau vide, lui, produit une
absence visible : le document ne ressort simplement pas quand on filtre par
organisme. Tant que la question de l'identité nationale des organismes n'est pas
tranchée (#636), c'est le seul comportement défendable.

## Authentification

Un jeton partagé (`CICADA_FEDERATION_TOKEN`), volontairement rudimentaire.
L'authentification entre instances est une question ouverte de #636 qui dépend
de #514 (OAuth2 / OIDC) : il s'agit ici de tester la mécanique de transport sans
préjuger de la solution retenue. Ne pas déployer tel quel.
"""

import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.geo.models import LArea

from .models import ContenuIndexe
from .serializers import SiteResumeSerializer, _sites_du_plan

logger = logging.getLogger(__name__)

#: Version du contrat d'échange. Les instances sont mises à jour indépendamment
#: (paquet Debian) et ne seront jamais toutes à la même version : l'ingestion
#: doit pouvoir refuser explicitement un format qu'elle ne sait pas lire, plutôt
#: que d'écrire des documents à moitié compris.
FORMAT_VERSION = 1

#: Champs de l'index transmis tels quels — ni identifiants locaux, ni vecteurs
#: de recherche (ceux-ci sont des colonnes générées, recalculées à l'arrivée).
CHAMPS_TRANSMIS = [
    'type_contenu', 'id_objet',
    'titre', 'description', 'contexte', 'rattachements',
    'parent_type', 'parent_libelle', 'sous_type', 'sous_type_libelle',
    'statut_pg', 'annee_debut', 'annee_fin',
    'type_site_codes',
]


class HasFederationToken(BasePermission):
    """Jeton partagé entre instances. Refuse tout si aucun jeton n'est configuré."""

    message = "Jeton de fédération absent ou invalide."

    def has_permission(self, request, view):
        attendu = settings.CICADA_FEDERATION_TOKEN
        if not attendu:
            return False
        return request.headers.get('X-Federation-Token') == attendu


# --------------------------------------------------------------------------- #
# Côté émetteur : construire le document publié
# --------------------------------------------------------------------------- #

def _codes_zones(area_ids):
    """
    Traduit des identifiants ref_geo locaux en codes stables entre instances.

    `l_areas.id_area` est une séquence locale, mais `(id_type, area_code)` porte
    une contrainte d'unicité et `area_code` est le code INSEE : c'est lui qui
    voyage. Le type est préfixé parce qu'un code de département et un code de
    région peuvent se ressembler.
    """
    if not area_ids:
        return []
    zones = (
        LArea.objects
        .filter(id_area__in=area_ids)
        .select_related('id_type')
        .values_list('id_type__type_code', 'area_code')
    )
    return [f"{type_code}:{code}" for type_code, code in zones]


def _bandeau_du_plan(plan):
    """
    Snapshot du bandeau « plan / gestionnaire / période » d'une tuile.

    Les documents locaux joignent ces libellés à la lecture, pour qu'ils ne
    puissent pas devenir obsolètes. Un document distant n'a pas ce luxe : le
    plan n'existe pas dans la base du portail. On capture donc l'affichage au
    moment de la publication, en assumant qu'il vieillira jusqu'à la
    republication suivante.
    """
    sites = _sites_du_plan(plan)
    gestionnaire = None
    for site in sites:
        liens = getattr(site, 'gestionnaires_principaux', None)
        if liens:
            gestionnaire = liens[0].uuid_og.nom_organisme
            break
    return {
        'id_pg': plan.pk,
        'nom': plan.nom,
        'slug': plan.slug,
        'statut': plan.statut,
        'annee_debut': plan.annee_debut,
        'annee_fin': plan.annee_fin,
        'type_document': (
            plan.id_type_document.label if plan.id_type_document_id else None
        ),
        'sites': SiteResumeSerializer(sites, many=True).data,
        'gestionnaire_principal': gestionnaire,
    }


def document_publie(contenu, bandeaux):
    """Sérialise une ligne d'index pour la publication."""
    charge = {champ: getattr(contenu, champ) for champ in CHAMPS_TRANSMIS}
    charge['area_codes'] = _codes_zones(contenu.area_ids)
    charge['plan'] = bandeaux.get(contenu.id_pg_id, {})
    return charge


# --------------------------------------------------------------------------- #
# Côté récepteur : ingérer un document reçu
# --------------------------------------------------------------------------- #

def _resoudre_zones(codes):
    """
    Retraduit les codes de zones publiés en identifiants ref_geo **locaux**.

    Possible parce que le découpage administratif vient du même référentiel
    national dans toutes les instances : seuls les identifiants techniques
    diffèrent, pas les codes.
    """
    if not codes:
        return []
    paires = [code.split(':', 1) for code in codes if ':' in code]
    if not paires:
        return []
    ids = []
    for type_code, area_code in paires:
        ids += list(
            LArea.objects
            .filter(id_type__type_code=type_code, area_code=area_code)
            .values_list('id_area', flat=True)
        )
    return ids


def contenu_depuis_document(document, instance_id):
    """
    Construit une ligne d'index locale à partir d'un document reçu.

    `id_pg` reste NULL : le plan n'existe pas dans cette base. Les facettes sans
    clé stable (sites, organismes) sont laissées vides — voir la docstring du
    module.
    """
    champs = {champ: document.get(champ) for champ in CHAMPS_TRANSMIS}
    champs['type_site_codes'] = champs.get('type_site_codes') or []
    return ContenuIndexe(
        instance_id=instance_id,
        id_pg=None,
        plan_denorm=document.get('plan') or {},
        area_ids=_resoudre_zones(document.get('area_codes')),
        site_ids=[],
        organisme_ids=[],
        **champs,
    )
