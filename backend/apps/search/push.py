"""
Publication de l'index vers le hub d'exploration (#636).

Remplace la publication « en tirage » (`FederationDocumentViewSet`, que le hub
venait interroger) par un **dépôt** : c'est l'instance qui va vers le hub. Le
sens compte pour le déploiement réel — une instance derrière un pare-feu ou sans
adresse publique peut publier, alors qu'elle ne peut pas être interrogée.

## L'unité d'échange est le plan

Un plan part avec **tout ce qui le concerne** : son bandeau, ses facettes, la
liste complète de ses objets explorables, et sa fiche rendue. Le hub remplace
alors intégralement ce qu'il savait de lui. Un enjeu supprimé ici disparaît
là-bas parce qu'il n'est plus dans la liste, sans message de retrait à émettre
ni à faire survivre au réseau.

## La fiche voyage rendue, pas en modèle

`FichePubliqueSerializer` produit déjà un arbre JSON autonome. On l'envoie tel
quel, et le hub le range sans l'inspecter. C'est ce qui lui permet de servir la
fiche complète d'un plan qu'il n'héberge pas, sans qu'il ait à connaître les
enjeux, les objectifs ni les actions — donc sans qu'il ait à suivre le modèle
métier de CICADA à chaque évolution.

Elle est en revanche **coûteuse à construire** : une fiche bien remplie mobilise
plusieurs centaines d'objets. C'est ce qui fixe la taille des pages, bien plus
petite que celle d'une synchronisation d'index nu.

## Ce qui ne voyage pas

Les identifiants locaux. `id_site`, `id_organisme`, `id_area` et le `slug` d'un
site sont des séquences propres à cette base. Seuls voyagent les codes
nationaux — INSEE pour les zones, INPN pour les sites — que le hub sait
re-résoudre. Les organismes n'ayant aucune clé nationale tranchée, seul leur
**nom** part, pour l'affichage : il ne sert pas à filtrer.
"""

import logging

from django.conf import settings

from .fiche import construire_fiche
from .indexing import INDEX_VERSION, INDEXED_STATUSES, facettes_du_plan
from .models import ContenuIndexe
from .serializers import SiteResumeSerializer, _sites_du_plan
from .serializers_fiche import FichePubliqueSerializer

logger = logging.getLogger(__name__)

#: Version du contrat de dépôt. Doit être connue du hub (`FORMATS_ACCEPTES`).
FORMAT_VERSION = 1

#: Champs de l'index transmis tels quels — ni identifiants locaux, ni vecteurs
#: de recherche, qui sont des colonnes générées recalculées à l'arrivée.
CHAMPS_CONTENU = [
    'type_contenu', 'id_objet',
    'titre', 'description', 'rattachements', 'contexte',
    'parent_type', 'parent_libelle', 'sous_type', 'sous_type_libelle',
]


def plans_a_publier():
    """
    Les plans que cette instance rend explorables.

    Même périmètre que l'indexation locale : un brouillon n'est pas explorable,
    donc pas publiable. Le hub ne doit jamais recevoir un plan que l'instance ne
    montrerait pas elle-même.
    """
    from apps.plans.models import PlanGestion

    return (
        PlanGestion.objects
        .filter(statut__in=INDEXED_STATUSES)
        .select_related('id_type_document')
        .order_by('pk')
    )


def _codes_zones(area_ids):
    """Traduit les identifiants ref_geo locaux en codes nationaux préfixés."""
    from apps.geo.models import LArea

    if not area_ids:
        return []
    zones = (
        LArea.objects
        .filter(id_area__in=area_ids)
        .select_related('id_type')
        .values_list('id_type__type_code', 'area_code')
    )
    # Le type préfixe le code : un code de département et un code de région
    # peuvent se ressembler (« 93 » désigne les deux).
    return sorted(f"{type_code}:{code}" for type_code, code in zones)


def _codes_sites(site_ids):
    """
    Traduit les identifiants de sites locaux en codes INPN.

    `id_inpn` vient du référentiel national et porte une contrainte d'unicité :
    il désigne le même espace protégé dans toutes les instances. Il est en
    revanche *nullable*, et beaucoup de sites n'en portent pas — ceux-là sont
    omis. La liste publiée dit « ces sites-là », jamais « seulement ceux-là ».
    """
    from apps.users.models import Site

    if not site_ids:
        return []
    return sorted(
        Site.objects
        .filter(id_site__in=site_ids)
        .exclude(id_inpn__isnull=True)
        .exclude(id_inpn='')
        .values_list('id_inpn', flat=True)
    )


def _gestionnaire_principal(sites):
    """Nom de l'organisme gestionnaire du site principal, s'il y en a un."""
    for site in sites:
        liens = getattr(site, 'gestionnaires_principaux', None)
        if liens:
            return liens[0].uuid_og.nom_organisme
    return None


def charge_utile(plan, avec_fiche=True):
    """
    Construit la charge utile d'un plan : bandeau, facettes, contenu, fiche.

    Les facettes viennent de `facettes_du_plan`, la même fonction qui alimente
    l'indexation locale : les deux chemins ne peuvent donc pas diverger.

    Elles ne sont **pas** lues sur les lignes d'index, bien qu'elles y figurent.
    Un plan validé mais vide n'a aucune ligne, et publierait alors des facettes
    vides : il disparaîtrait de tous les filtres par zone ou par type d'aire
    protégée, alors qu'il doit rester trouvable en mode « plan de gestion ».
    """
    facettes = facettes_du_plan(plan)
    area_ids = facettes['area_ids']
    site_ids = facettes['site_ids']
    type_site_codes = facettes['type_site_codes']

    documents = list(
        ContenuIndexe.objects
        .filter(id_pg=plan, instance_id=settings.CICADA_INSTANCE_ID)
        .order_by('type_contenu', 'id_objet')
    )

    sites = _sites_du_plan(plan)

    charge = {
        'id_pg': plan.pk,
        'nom': plan.nom,
        'slug': plan.slug,
        'statut': plan.statut,
        'rang': plan.rang,
        'annee_debut': plan.annee_debut,
        'annee_fin': plan.annee_fin,
        'type_document': (
            plan.id_type_document.label if plan.id_type_document_id else None
        ),
        'url_instance': settings.CICADA_PUBLIC_URL,
        'sites': SiteResumeSerializer(sites, many=True).data,
        'gestionnaire_principal': _gestionnaire_principal(sites),
        'site_inpn_codes': _codes_sites(site_ids),
        'type_site_codes': list(type_site_codes or []),
        'area_codes': _codes_zones(area_ids),
        'contenus': [
            {
                **{champ: getattr(doc, champ) for champ in CHAMPS_CONTENU},
                'index_version': doc.index_version or INDEX_VERSION,
            }
            for doc in documents
        ],
    }

    if avec_fiche:
        charge['fiche'] = FichePubliqueSerializer(construire_fiche(plan)).data

    return charge
