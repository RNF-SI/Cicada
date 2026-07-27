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
# Contexte taxonomique d'un enjeu, propagé à sa branche
# --------------------------------------------------------------------------- #

def _contexte_taxo(enjeu):
    """Taxons, habitats, patrimoine géologique et précisions libres d'un enjeu."""
    parts = []
    for taxon in enjeu.taxons.all():
        parts += [taxon.nom_complet, taxon.nom_vern]
    parts += [habitat.lb_hab_fr for habitat in enjeu.habitats.all()]
    parts += [geol.nom for geol in enjeu.geologies.all()]
    parts += [
        enjeu.autre_ecologique_precision,
        enjeu.autre_socioeco_precision,
        enjeu.geo_autre_precision,
    ]
    return _texte(*parts)


# --------------------------------------------------------------------------- #
# Extraction, type par type
# --------------------------------------------------------------------------- #

def _documents_enjeux(plan, facettes, contexte_branche):
    enjeux = (
        Enjeu.objects.filter(id_pg=plan)
        .select_related('id_categorie')
        .prefetch_related('taxons', 'habitats', 'geologies')
    )
    documents = []
    for enjeu in enjeux:
        taxo = _contexte_taxo(enjeu)
        contexte_branche[enjeu.pk] = _texte(enjeu.libelle, taxo)
        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_ENJEU,
            id_objet=enjeu.pk,
            titre=enjeu.libelle,
            description=_texte(enjeu.description, enjeu.etat_enjeu),
            contexte=_texte(enjeu.intitule_court, taxo),
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


def _documents_facteurs(plan, facettes, contexte_branche):
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
            contexte=_texte(*(contexte_branche.get(e.pk, '') for e in enjeux)),
            parent_type=ContenuIndexe.TYPE_ENJEU if parent else None,
            parent_libelle=parent.libelle if parent else None,
            **facettes,
        ))
    return documents


def _documents_pressions(plan, facettes, contexte_branche):
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
            contexte=_texte(
                facteur.libelle if facteur else None,
                *(contexte_branche.get(e.pk, '') for e in enjeux),
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


def _documents_objectifs_lt(plan, facettes, contexte_branche):
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
            contexte=contexte_branche.get(olt.id_enjeu_id, ''),
            parent_type=ContenuIndexe.TYPE_ENJEU,
            parent_libelle=olt.id_enjeu.libelle if olt.id_enjeu_id else None,
            **facettes,
        )
        for olt in objectifs
    ]


def _documents_objectifs_op(plan, facettes, contexte_branche):
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
            contexte=_texte(
                contexte_branche.get(oo.id_enjeu_id, ''),
                *(pression.libelle for pression in oo.pressions.all()),
            ),
            parent_type=ContenuIndexe.TYPE_ENJEU if oo.id_enjeu_id else None,
            parent_libelle=oo.id_enjeu.libelle if oo.id_enjeu_id else None,
            **facettes,
        )
        for oo in objectifs
    ]


def _documents_indicateurs(plan, facettes, contexte_branche):
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
        .prefetch_related('metriques')
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

        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_INDICATEUR,
            id_objet=indicateur.pk,
            titre=indicateur.nom_indicateur,
            description=indicateur.description or '',
            contexte=_texte(
                contexte_branche.get(enjeu_id, ''),
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


def _documents_actions(plan, facettes, contexte_branche):
    operations = (
        Operation.objects
        .filter(_q_pour_plan(OPERATION_TO_PG_PATHS, plan))
        .distinct()
        .select_related(
            'id_categorie_action_reserve', 'id_type_action',
            'id_suivi', 'id_indicateur',
        )
        .prefetch_related('metriques')
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
        documents.append(ContenuIndexe(
            type_contenu=ContenuIndexe.TYPE_ACTION,
            id_objet=operation.pk,
            titre=operation.libelle,
            description=operation.description or '',
            contexte=_texte(
                operation.code_operation,
                operation.id_type_action.label if operation.id_type_action_id else None,
                operation.id_suivi.intitule if operation.id_suivi_id else None,
                *(m.nom_metrique for m in operation.metriques.all()),
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
    # Les enjeux d'abord : ils alimentent `contexte_branche` pour les autres.
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
    contexte_branche = {}
    documents = []
    for extracteur in EXTRACTEURS:
        documents += extracteur(plan, facettes, contexte_branche)
    return documents


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
