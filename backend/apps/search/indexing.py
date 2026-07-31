"""
Construction de l'index de recherche d'un plan de gestion.

L'indexation est un **traitement par lot au niveau du plan** : on supprime puis
on réécrit toutes les lignes du plan. C'est possible parce qu'un plan n'est
indexable qu'une fois validé, et que le contenu d'un plan validé est verrouillé
en lecture seule (#248) — il n'y a donc pas de flux de petites mises à jour à
suivre, seulement des transitions de statut.

Le « contexte » (interrogé uniquement en mode élargi) propage vers toute la
branche le libellé de l'enjeu et les taxons/habitats qui lui sont rattachés.
C'est ce qui permet la recherche décrite dans l'aide de la maquette : « les
indicateurs pour lesquels il y a un enjeu autour des limicoles ».
"""

import logging

from django.db import transaction
from django.db.models import Q

from apps.geo.models import CorSiteArea
from apps.plans.access import INDICATEUR_TO_PG_PATHS, OPERATION_TO_PG_PATHS
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, ObjectifLongTerme, ObjectifOperationnel, Pression,
)
from apps.plans.models_indicateurs import Indicateur
from apps.plans.models_operations import Operation
from apps.users.models import CorOgSite

from .models import ContenuIndexe

logger = logging.getLogger(__name__)

#: Statuts dont le contenu est explorable. Un brouillon n'est jamais indexé :
#: il n'est pas encore public, et son contenu bouge encore.
INDEXED_STATUSES = PlanGestion.VALIDATED_STATUSES

#: Version des extracteurs ci-dessous. **À incrémenter dès qu'une évolution
#: change ce qui est écrit dans l'index** (nouveau champ indexé, nouveau
#: rattachement, correction d'un extracteur…).
#:
#: L'index n'est reconstruit ni par une migration ni par un signal : une ligne
#: n'est réécrite qu'au changement de statut de son plan, et un plan validé ne
#: bouge plus. Sans ce numéro, un déploiement qui enrichit l'indexation laisse
#: donc l'index de production dans son **ancien** état, indéfiniment — les
#: recherches ajoutées ne trouvent rien alors que le code est bien déployé.
#: `rebuild_search_index --if-stale`, lancé au démarrage, compare cette valeur
#: à celle stockée sur les lignes et rebâtit l'index quand elle a bougé.
#:
#: Historique : 1 = version initiale, 2 = #634 (rattachements espèces /
#: protocoles / habitats / géologie / PressRef + héritage de l'enjeu par les
#: actions).
INDEX_VERSION = 2


def _texte(*parts):
    """Assemble des fragments de texte en ignorant les vides et les doublons."""
    vus, sortie = set(), []
    for part in parts:
        if not part:
            continue
        part = str(part).strip()
        if part and part.lower() not in vus:
            vus.add(part.lower())
            sortie.append(part)
    return ' '.join(sortie)


def _q_pour_plan(paths, plan):
    """OR des chemins ORM menant au plan (cf. apps.plans.access)."""
    q = Q()
    for path in paths:
        q |= Q(**{path: plan})
    return q


# --------------------------------------------------------------------------- #
# Facettes héritées du plan
# --------------------------------------------------------------------------- #

def facettes_du_plan(plan):
    """
    Valeurs de filtrage communes à toutes les lignes indexées d'un plan.

    Le dictionnaire est développé (``**facettes``) dans chaque ``ContenuIndexe``
    du plan : les listes qu'il contient sont donc partagées entre les instances.
    C'est sans conséquence — elles ne sont jamais modifiées après construction,
    et les instances sont écrites puis jetées — mais il ne faut pas les muter.
    """
    site_ids = list(
        plan.sites.values_list('site_id', flat=True).distinct()
    )
    type_site_codes = sorted(set(
        code for code in plan.sites.values_list(
            'site__id_type_site__mnemonique', flat=True
        ).distinct() if code
    ))
    organisme_ids = sorted(set(
        CorOgSite.objects.filter(id_site__in=site_ids)
        .values_list('uuid_og__id_organisme', flat=True)
    ))
    area_ids = sorted(set(
        CorSiteArea.objects.filter(id_site__in=site_ids)
        .values_list('id_area_id', flat=True)
    ))
    return {
        'id_pg': plan,
        'statut_pg': plan.statut,
        'annee_debut': plan.annee_debut,
        'annee_fin': plan.annee_fin,
        'site_ids': sorted(site_ids),
        'organisme_ids': organisme_ids,
        'type_site_codes': type_site_codes,
        'area_ids': area_ids,
    }


# --------------------------------------------------------------------------- #
# Ce qu'un enjeu transmet à sa branche
#
# Deux textes bien distincts, qui n'ont pas la même portée de recherche (#634) :
#
# - les *rattachements* — espèces, habitats, géologie — descendent dans le
#   `rattachements` de toute la branche, actions comprises, et sont donc
#   trouvables y compris en mode « titres uniquement » : chercher une espèce
#   doit remonter les enjeux ET les actions qui la concernent ;
# - le *contexte* — le libellé de l'enjeu — ne descend que dans le `contexte`,
#   réservé au mode élargi.
# --------------------------------------------------------------------------- #

def _rattachements_enjeu(enjeu):
    """Espèces, habitats et patrimoine géologique rattachés à un enjeu.

    Les taxons sont indexés sous leurs deux noms : chercher « Bécasseau
    variable » doit marcher aussi bien que « Calidris alpina » (#634).
    """
    parts = []
    for taxon in enjeu.taxons.all():
        parts += [taxon.nom_complet, taxon.nom_vern]
    for habitat in enjeu.habitats.all():
        parts += [habitat.lb_hab_fr, habitat.cd_hab]
    for geologie in enjeu.geologies.all():
        parts += [geologie.nom, geologie.id_inpg]
    parts += [
        enjeu.autre_ecologique_precision,
        enjeu.autre_socioeco_precision,
        enjeu.geo_autre_precision,
    ]
    return _texte(*parts)


class _Branche:
    """
    Ce que les enjeux transmettent à leur descendance pendant l'extraction.

    Les extracteurs tournent dans l'ordre de `EXTRACTEURS` : les enjeux
    remplissent `enjeux`, les indicateurs remplissent `enjeu_par_indicateur`,
    et les actions — qui pendent d'un indicateur ou d'une métrique — s'en
    servent pour retrouver l'enjeu dont elles héritent les rattachements.
    """

    def __init__(self):
        self.enjeux = {}
        self.enjeu_par_indicateur = {}


def _protocole_texte(protocole):
    """Noms d'un protocole standardisé, côté saisie libre comme côté CAMPanule."""
    return _texte(protocole.nom_protocole, protocole.protocole_campanule_nom)


def _herite(branche, ids, cle):
    """Texte hérité (`contexte` ou `rattachements`) des enjeux donnés."""
    return _texte(*(branche.enjeux.get(id_enjeu, {}).get(cle, '') for id_enjeu in ids))


# --------------------------------------------------------------------------- #
# Extraction, type par type
# --------------------------------------------------------------------------- #

def _documents_enjeux(plan, facettes, branche):
    enjeux = (
        Enjeu.objects.filter(id_pg=plan)
        .select_related('id_categorie')
        .prefetch_related('taxons', 'habitats', 'geologies')
    )
    documents = []
    for enjeu in enjeux:
        rattachements = _rattachements_enjeu(enjeu)
        branche.enjeux[enjeu.pk] = {
            'contexte': enjeu.libelle,
            'rattachements': rattachements,
        }
        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_ENJEU,
            id_objet=enjeu.pk,
            titre=enjeu.libelle,
            description=_texte(enjeu.description, enjeu.etat_enjeu),
            rattachements=rattachements,
            contexte=enjeu.intitule_court or '',
            sous_type=(
                'ecologique' if enjeu.categorie_ecologique else 'socioeco'
            ),
            sous_type_libelle=(
                "Conservation du patrimoine naturel"
                if enjeu.categorie_ecologique else "Socio-économique"
            ),
            **facettes,
        ))
    return documents


def _documents_facteurs(plan, facettes, branche):
    facteurs = (
        FacteurInfluence.objects.filter(enjeux__id_pg=plan)
        .distinct().prefetch_related('enjeux')
    )
    documents = []
    for facteur in facteurs:
        enjeux = list(facteur.enjeux.all())
        parent = enjeux[0] if enjeux else None
        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_FACTEUR,
            id_objet=facteur.pk,
            titre=facteur.libelle,
            description=facteur.description or '',
            rattachements=_herite(branche, [e.pk for e in enjeux], 'rattachements'),
            contexte=_herite(branche, [e.pk for e in enjeux], 'contexte'),
            parent_type=ContenuIndexe.TYPE_ENJEU if parent else None,
            parent_libelle=parent.libelle if parent else None,
            **facettes,
        ))
    return documents


def _documents_pressions(plan, facettes, branche):
    pressions = (
        Pression.objects.filter(id_facteur_influence__enjeux__id_pg=plan)
        .distinct()
        .select_related('id_facteur_influence', 'id_type_pression')
        .prefetch_related('id_facteur_influence__enjeux')
    )
    documents = []
    for pression in pressions:
        facteur = pression.id_facteur_influence
        enjeux = list(facteur.enjeux.all()) if facteur else []
        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_PRESSION,
            id_objet=pression.pk,
            titre=pression.libelle,
            description=pression.description or '',
            # La référence PressRef est un rattachement à un référentiel, pas
            # du texte de contexte : elle doit être trouvable en mode titres.
            rattachements=_texte(
                pression.id_type_pression.label
                if pression.id_type_pression_id else None,
                pression.id_pressref,
                _herite(branche, [e.pk for e in enjeux], 'rattachements'),
            ),
            contexte=_texte(
                facteur.libelle if facteur else None,
                _herite(branche, [e.pk for e in enjeux], 'contexte'),
            ),
            parent_type=ContenuIndexe.TYPE_FACTEUR if facteur else None,
            parent_libelle=facteur.libelle if facteur else None,
            sous_type=(
                pression.id_type_pression.mnemonique
                if pression.id_type_pression_id else None
            ),
            sous_type_libelle=(
                pression.id_type_pression.label
                if pression.id_type_pression_id else None
            ),
            **facettes,
        ))
    return documents


def _documents_objectifs_lt(plan, facettes, branche):
    objectifs = (
        ObjectifLongTerme.objects.filter(id_enjeu__id_pg=plan)
        .select_related('id_enjeu')
    )
    return [
        ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_OBJECTIF_LT,
            id_objet=olt.pk,
            titre=olt.libelle,
            description=olt.description or '',
            rattachements=_herite(branche, [olt.id_enjeu_id], 'rattachements'),
            contexte=_herite(branche, [olt.id_enjeu_id], 'contexte'),
            parent_type=ContenuIndexe.TYPE_ENJEU,
            parent_libelle=olt.id_enjeu.libelle if olt.id_enjeu_id else None,
            **facettes,
        )
        for olt in objectifs
    ]


def _documents_objectifs_op(plan, facettes, branche):
    objectifs = (
        ObjectifOperationnel.objects.filter(
            Q(id_enjeu__id_pg=plan)
            | Q(pressions__id_facteur_influence__enjeux__id_pg=plan)
        )
        .distinct()
        .select_related('id_enjeu')
        .prefetch_related('pressions')
    )
    return [
        ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_OBJECTIF_OP,
            id_objet=oo.pk,
            titre=oo.libelle,
            description=oo.description or '',
            rattachements=_herite(branche, [oo.id_enjeu_id], 'rattachements'),
            contexte=_texte(
                _herite(branche, [oo.id_enjeu_id], 'contexte'),
                *(pression.libelle for pression in oo.pressions.all()),
            ),
            parent_type=ContenuIndexe.TYPE_ENJEU if oo.id_enjeu_id else None,
            parent_libelle=oo.id_enjeu.libelle if oo.id_enjeu_id else None,
            **facettes,
        )
        for oo in objectifs
    ]


def _documents_indicateurs(plan, facettes, branche):
    indicateurs = (
        Indicateur.objects
        .filter(_q_pour_plan(INDICATEUR_TO_PG_PATHS, plan))
        .distinct()
        .select_related(
            'type_indicateur',
            'id_ne', 'id_ne__id_olt', 'id_ne__id_olt__id_enjeu',
            'id_resultat_attendu', 'id_resultat_attendu__id_oo',
            'id_resultat_attendu__id_oo__id_enjeu',
        )
        .prefetch_related('metriques', 'geologies')
    )
    documents = []
    for indicateur in indicateurs:
        # Un indicateur pend soit sous un niveau d'exigence (branche OLT),
        # soit sous un résultat attendu (branche OO).
        if indicateur.id_ne_id:
            intermediaire = indicateur.id_ne
            objectif = intermediaire.id_olt
            parent_type = ContenuIndexe.TYPE_OBJECTIF_LT
            enjeu_id = objectif.id_enjeu_id if objectif else None
        elif indicateur.id_resultat_attendu_id:
            intermediaire = indicateur.id_resultat_attendu
            objectif = intermediaire.id_oo
            parent_type = ContenuIndexe.TYPE_OBJECTIF_OP
            enjeu_id = objectif.id_enjeu_id if objectif else None
        else:
            intermediaire = objectif = parent_type = enjeu_id = None

        branche.enjeu_par_indicateur[indicateur.pk] = enjeu_id

        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_INDICATEUR,
            id_objet=indicateur.pk,
            titre=indicateur.nom_indicateur,
            description=indicateur.description or '',
            rattachements=_texte(
                indicateur.type_indicateur.label
                if indicateur.type_indicateur_id else None,
                *(g.nom for g in indicateur.geologies.all()),
                *(g.id_inpg for g in indicateur.geologies.all()),
                _herite(branche, [enjeu_id], 'rattachements'),
            ),
            contexte=_texte(
                _herite(branche, [enjeu_id], 'contexte'),
                intermediaire.libelle if intermediaire else None,
                *(m.nom_metrique for m in indicateur.metriques.all()),
            ),
            parent_type=parent_type,
            parent_libelle=objectif.libelle if objectif else None,
            sous_type=(
                indicateur.type_indicateur.mnemonique
                if indicateur.type_indicateur_id else None
            ),
            sous_type_libelle=(
                indicateur.type_indicateur.label
                if indicateur.type_indicateur_id else None
            ),
            **facettes,
        ))
    return documents


def _documents_actions(plan, facettes, branche):
    operations = (
        Operation.objects
        .filter(_q_pour_plan(OPERATION_TO_PG_PATHS, plan))
        .distinct()
        .select_related(
            'id_categorie_action_reserve', 'id_type_action',
            'id_suivi', 'id_indicateur',
        )
        .prefetch_related('metriques', 'id_suivi__protocoles')
    )
    documents = []
    for operation in operations:
        if operation.id_indicateur_id:
            parent_type, parent = 'indicateur', operation.id_indicateur.nom_indicateur
        elif operation.id_suivi_id:
            parent_type, parent = 'suivi', operation.id_suivi.intitule
        else:
            parent_type, parent = None, None

        categorie = operation.id_categorie_action_reserve
        suivi = operation.id_suivi

        # Une action hérite des rattachements de l'enjeu dont elle dépend,
        # qu'elle y soit reliée par son indicateur ou par une de ses métriques
        # (#634 : « chercher une espèce doit ressortir les actions »).
        indicateurs = [operation.id_indicateur_id] + [
            metrique.id_indicateur_id for metrique in operation.metriques.all()
        ]
        enjeux = {
            branche.enjeu_par_indicateur.get(id_indicateur)
            for id_indicateur in indicateurs
            if id_indicateur is not None
        }

        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_ACTION,
            id_objet=operation.pk,
            titre=operation.libelle,
            description=operation.description or '',
            rattachements=_texte(
                # Catégorie et type d'action : « CS », « Suivi des plantes »…
                f"{categorie.mnemonique} {categorie.label}" if categorie else None,
                operation.id_type_action.label if operation.id_type_action_id else None,
                # Protocoles standardisés du suivi : chercher « STOC » doit
                # remonter les actions qui l'appliquent, pas seulement celles
                # qui le nomment.
                *(_protocole_texte(protocole) for protocole in (
                    suivi.protocoles.all() if suivi else []
                )),
                # Cibles du suivi : espèce et habitat saisis sur l'inventaire.
                suivi.taxon_taxref if suivi else None,
                suivi.habitat_ref if suivi else None,
                suivi.cibles_principales if suivi else None,
                _herite(branche, enjeux, 'rattachements'),
            ),
            contexte=_texte(
                operation.code_operation,
                suivi.intitule if suivi else None,
                *(m.nom_metrique for m in operation.metriques.all()),
                _herite(branche, enjeux, 'contexte'),
            ),
            parent_type=parent_type,
            parent_libelle=parent,
            sous_type=categorie.mnemonique if categorie else None,
            sous_type_libelle=(
                f"{categorie.mnemonique} - {categorie.label}" if categorie else None
            ),
            **facettes,
        ))
    return documents


EXTRACTEURS = (
    # L'ordre compte : chaque extracteur alimente `branche` pour les suivants.
    _documents_enjeux,
    _documents_facteurs,
    _documents_pressions,
    _documents_objectifs_lt,
    _documents_objectifs_op,
    _documents_indicateurs,
    _documents_actions,
)


def construire_documents(plan):
    """Retourne toutes les lignes d'index d'un plan, sans rien écrire."""
    facettes = facettes_du_plan(plan)
    branche = _Branche()
    documents = []
    for extracteur in EXTRACTEURS:
        documents += extracteur(plan, facettes, branche)
    # Toutes les lignes portent la version des extracteurs qui les a produites :
    # c'est ce qui permet de repérer un index resté à l'ancien format.
    for document in documents:
        document.index_version = INDEX_VERSION
    return documents


def index_est_perime():
    """
    L'index a-t-il été produit par une version antérieure des extracteurs ?

    Vrai aussi pour un index vide alors que des plans sont indexables : les deux
    cas appellent la même réponse, une reconstruction complète.
    """
    if not ContenuIndexe.objects.exists():
        return PlanGestion.objects.filter(statut__in=INDEXED_STATUSES).exists()
    return ContenuIndexe.objects.exclude(index_version=INDEX_VERSION).exists()


# --------------------------------------------------------------------------- #
# Écriture
# --------------------------------------------------------------------------- #

@transaction.atomic
def index_plan(plan):
    """(Ré)indexe intégralement un plan. Retourne le nombre de lignes écrites."""
    ContenuIndexe.objects.filter(id_pg=plan).delete()
    documents = construire_documents(plan)
    ContenuIndexe.objects.bulk_create(documents, batch_size=500)
    logger.info("Plan %s indexé : %s objets", plan.pk, len(documents))
    return len(documents)


def desindexer_plan(plan):
    """Retire un plan de l'index. Retourne le nombre de lignes supprimées."""
    supprimees, _ = ContenuIndexe.objects.filter(id_pg=plan).delete()
    return supprimees


def synchroniser_plan(plan):
    """
    Aligne l'index sur le statut courant du plan.

    Indexe si le plan est validé, modifié ou archivé ; le retire sinon (retour
    en brouillon, workflow CSRPN).
    """
    if plan.statut in INDEXED_STATUSES:
        return index_plan(plan)
    return -desindexer_plan(plan)


def rafraichir_facettes(plan):
    """
    Met à jour les seules facettes d'un plan déjà indexé.

    Les rattachements de sites et de référents restent modifiables après
    validation (ils sont exemptés du verrou #248) : ils changent les facettes
    sans toucher au texte, une simple mise à jour suffit donc.
    """
    lignes = ContenuIndexe.objects.filter(id_pg=plan)
    if not lignes.exists():
        return 0
    facettes = facettes_du_plan(plan)
    facettes.pop('id_pg')
    return lignes.update(**facettes)
