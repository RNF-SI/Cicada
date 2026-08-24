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
| Sites | `t_espace_protege.id_inpn`, unique et national — mais *nullable* | publiés en **codes INPN**, re-résolus en identifiants locaux ✅ *(partiel)* |
| Organismes gestionnaires | aucune — `uuid_organisme` est tiré localement | **vidée** à l'ingestion ⚠️ |

La dernière ligne est volontairement **vidée plutôt que recopiée**. Recopier un
identifiant local ferait matcher un document distant sur le mauvais organisme —
une corruption silencieuse. Un tableau vide, lui, produit une absence visible :
le document ne ressort simplement pas quand on filtre par organisme. Tant que la
question de l'identité nationale des organismes n'est pas tranchée (#636), c'est
le seul comportement défendable.

Les sites suivent désormais le modèle des zones, avec une réserve qui leur est
propre : `id_inpn` est *nullable*. Un site qui n'en porte pas n'est pas
publiable, et le document reçu le passe donc sous silence. La liste transmise
dit « ces sites-là », jamais « seulement ceux-là » — c'est une couverture
partielle due à un référentiel incomplet, pas un périmètre. Contrairement aux
organismes, l'appariement obtenu est en revanche *juste* : un code INPN désigne
le même espace protégé dans toutes les instances.

## Versionner le contrat d'échange

`FORMAT_VERSION` ne bouge que si un document ancien risquerait d'être **mal
compris** par un lecteur récent, ou l'inverse. Ajouter un champ *optionnel* n'est
pas ce cas : un lecteur ancien l'ignore, un lecteur récent retombe sur une liste
vide quand l'émetteur ne l'envoie pas encore. Les instances étant mises à jour
indépendamment (paquet Debian), faire l'inverse — bumper à chaque ajout — aurait
pour seul effet d'interrompre la publication entre deux instances qui se
comprenaient parfaitement.

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
from apps.users.models import Site

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

def _table_codes_zones(area_ids):
    """
    Table « identifiant ref_geo local → code national », pour toute une page.

    `l_areas.id_area` est une séquence locale, mais `(id_type, area_code)` porte
    une contrainte d'unicité et `area_code` est le code INSEE : c'est lui qui
    voyage. Le type est préfixé parce qu'un code de département et un code de
    région peuvent se ressembler.
    """
    if not area_ids:
        return {}
    zones = (
        LArea.objects
        .filter(id_area__in=area_ids)
        .select_related('id_type')
        .values_list('id_area', 'id_type__type_code', 'area_code')
    )
    return {pk: f"{type_code}:{code}" for pk, type_code, code in zones}


def _table_codes_sites(site_ids):
    """
    Table « identifiant de site local → code INPN », pour toute une page.

    `id_site` est une séquence locale ; `id_inpn` vient du référentiel national
    de l'INPN et porte une contrainte d'unicité : c'est lui qui voyage, comme
    `area_code` pour les zones.

    Il est en revanche *nullable*, et beaucoup de sites n'en portent pas. Ceux-là
    sont absents de la table, donc omis du document : sans clé stable, les
    publier reviendrait à réintroduire l'identifiant local que tout ce module
    s'attache à ne pas transmettre. La liste publiée est **partielle par
    construction**.
    """
    if not site_ids:
        return {}
    return dict(
        Site.objects
        .filter(id_site__in=site_ids)
        .exclude(id_inpn__isnull=True)
        .exclude(id_inpn='')
        .values_list('id_site', 'id_inpn')
    )


def codes_de_la_page(page):
    """
    Traduit les identifiants locaux de toute une page en **deux** requêtes.

    Traduire document par document en coûterait deux *par document* — un millier
    pour une page de 500, alors que l'index a vocation à porter ~1,3 M de
    documents une fois les ~4 400 plans repris. Le bandeau du plan est déjà
    groupé de cette façon par la vue : c'est la même contrainte.
    """
    zones, sites = set(), set()
    for contenu in page:
        zones.update(contenu.area_ids or [])
        sites.update(contenu.site_ids or [])
    return _table_codes_zones(zones), _table_codes_sites(sites)


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


def document_publie(contenu, bandeaux, codes_zones, codes_sites):
    """
    Sérialise une ligne d'index pour la publication.

    Les tables de codes viennent de `codes_de_la_page` : un identifiant qui n'y
    figure pas est sans code national et disparaît donc du document.
    """
    charge = {champ: getattr(contenu, champ) for champ in CHAMPS_TRANSMIS}
    charge['area_codes'] = sorted(
        codes_zones[pk] for pk in (contenu.area_ids or []) if pk in codes_zones
    )
    charge['site_inpn_codes'] = sorted(
        codes_sites[pk] for pk in (contenu.site_ids or []) if pk in codes_sites
    )
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


def _resoudre_sites(codes):
    """
    Retraduit les codes INPN publiés en identifiants de sites **locaux**.

    Un code INPN désigne le même espace protégé partout : quand le site existe
    aussi dans cette base — cas de la co-gestion, fréquent — le document distant
    se rattache au bon site local. Sinon il ne se rattache à rien, ce qui est le
    résultat correct : le portail n'a pas à inventer un site qu'il ne connaît pas.
    """
    if not codes:
        return []
    return sorted(
        Site.objects.filter(id_inpn__in=codes).values_list('id_site', flat=True)
    )


def contenu_depuis_document(document, instance_id):
    """
    Construit une ligne d'index locale à partir d'un document reçu.

    `id_pg` reste NULL : le plan n'existe pas dans cette base. Zones et sites
    sont re-résolus depuis leurs codes nationaux ; les organismes, faute de clé
    stable, restent vides — voir la docstring du module.
    """
    champs = {champ: document.get(champ) for champ in CHAMPS_TRANSMIS}
    champs['type_site_codes'] = champs.get('type_site_codes') or []
    return ContenuIndexe(
        instance_id=instance_id,
        id_pg=None,
        plan_denorm=document.get('plan') or {},
        area_ids=_resoudre_zones(document.get('area_codes')),
        site_ids=_resoudre_sites(document.get('site_inpn_codes')),
        organisme_ids=[],
        **champs,
    )
