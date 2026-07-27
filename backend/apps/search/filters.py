"""
Traduction des paramètres de l'exploration en filtres de requête.

Isolé des vues pour rester testable sans HTTP, et parce que les deux modes de
recherche (contenu / plan de gestion) partagent les mêmes facettes de plan
exprimées sur des schémas différents : colonnes dénormalisées côté index,
jointures côté `PlanGestion`.
"""

import datetime

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q

from .models import SEARCH_CONFIG, ContenuIndexe

#: Valeurs acceptées par le filtre « statut du plan de gestion » de la maquette.
STATUT_EN_COURS = 'en_cours'
STATUT_VALIDE = 'valide'
STATUT_ARCHIVE = 'archive'

#: Statuts en base considérés comme « validé » côté interface. `modifie` est un
#: plan validé qui a été révisé : l'utilisateur ne fait pas la distinction.
STATUTS_VALIDES = ('valide', 'modifie')

TRI_PERTINENCE = 'pertinence'
TRI_ALPHABETIQUE = 'alphabetique'
TRI_RECENT = 'recent'

#: Sous-type applicable à chaque groupe de facettes de la barre latérale, et
#: type de contenu qu'il raffine. Cocher « Écologiques » restreint les enjeux
#: sans faire disparaître les pressions ou les actions : chaque groupe raffine
#: son propre type et laisse les autres intacts.
GROUPES_SOUS_TYPES = {
    'categories_enjeu': ContenuIndexe.TYPE_ENJEU,
    'types_indicateur': ContenuIndexe.TYPE_INDICATEUR,
    'categories_action': ContenuIndexe.TYPE_ACTION,
}


def liste(params, cle):
    """Lit un paramètre multi-valeurs (`?types=enjeu,pression` ou répété)."""
    valeurs = []
    for brut in params.getlist(cle):
        valeurs += [v.strip() for v in brut.split(',') if v.strip()]
    return valeurs


def entiers(params, cle):
    """Idem, en ne gardant que les valeurs numériques."""
    return [int(v) for v in liste(params, cle) if v.lstrip('-').isdigit()]


def booleen(params, cle, defaut=False):
    brut = params.get(cle)
    if brut is None:
        return defaut
    return brut.strip().lower() in ('1', 'true', 'vrai', 'oui', 'on')


# --------------------------------------------------------------------------- #
# Statut du plan
# --------------------------------------------------------------------------- #

def q_statuts(statuts, champ_statut='statut_pg', annee=None):
    """
    Q correspondant au filtre « statut du plan de gestion ».

    ``en_cours`` n'est pas un statut en base : c'est un plan validé dont
    l'année courante tombe dans sa période. Il recoupe donc volontairement
    ``valide``.

    :param champ_statut: ``statut_pg`` sur l'index, ``statut`` sur
        ``PlanGestion`` — les champs d'années portent le même nom des deux côtés.
    """
    if not statuts:
        return Q()

    annee = annee or datetime.date.today().year
    scope = Q()

    for statut in statuts:
        if statut == STATUT_ARCHIVE:
            scope |= Q(**{champ_statut: 'archive'})
        elif statut == STATUT_VALIDE:
            scope |= Q(**{f'{champ_statut}__in': STATUTS_VALIDES})
        elif statut == STATUT_EN_COURS:
            scope |= (
                Q(**{f'{champ_statut}__in': STATUTS_VALIDES})
                & Q(annee_debut__lte=annee)
                & Q(annee_fin__gte=annee)
            )
    return scope


# --------------------------------------------------------------------------- #
# Mode « contenu d'un plan de gestion »
# --------------------------------------------------------------------------- #

def filtrer_contenus(queryset, params):
    """
    Applique au queryset d'index tous les filtres SAUF l'onglet actif.

    L'onglet est exclu pour que les compteurs affichés au-dessus de la liste
    restent ceux de la recherche entière : sans cela, sélectionner « Pressions »
    ferait tomber à zéro tous les autres onglets.
    """
    mot_cle = (params.get('q') or '').strip()
    titres_seulement = booleen(params, 'titres_seulement', defaut=True)

    if mot_cle:
        champ = 'search_titre' if titres_seulement else 'search_full'
        requete = SearchQuery(mot_cle, config=SEARCH_CONFIG, search_type='websearch')
        # La similarité par mot rattrape les fautes de frappe que la
        # radicalisation ne couvre pas ; elle s'appuie sur l'index trigramme.
        queryset = queryset.filter(
            Q(**{champ: requete}) | Q(titre__trigram_word_similar=mot_cle)
        ).annotate(pertinence=SearchRank(F(champ), requete))

    types = liste(params, 'types')
    if types:
        queryset = queryset.filter(type_contenu__in=types)

    zones = entiers(params, 'zones')
    if zones:
        queryset = queryset.filter(area_ids__overlap=zones)

    organismes = entiers(params, 'organismes')
    if organismes:
        queryset = queryset.filter(organisme_ids__overlap=organismes)

    types_site = liste(params, 'types_site')
    if types_site:
        queryset = queryset.filter(type_site_codes__overlap=types_site)

    statuts = liste(params, 'statuts')
    if statuts:
        queryset = queryset.filter(q_statuts(statuts))

    queryset = queryset.filter(q_sous_types(params))
    return queryset


def q_sous_types(params):
    """
    Q des groupes de facettes propres à un type (enjeux, indicateurs, actions).

    Chaque groupe raffine son type et laisse les autres passer : cocher
    « Indicateur d'état » ne doit pas faire disparaître les enjeux de la liste.
    """
    scope = Q()
    types_raffines = []

    for cle, type_contenu in GROUPES_SOUS_TYPES.items():
        valeurs = liste(params, cle)
        if not valeurs:
            continue
        types_raffines.append(type_contenu)
        scope |= Q(type_contenu=type_contenu, sous_type__in=valeurs)

    if not types_raffines:
        return Q()

    # Les types dont aucun groupe n'est utilisé restent intégralement visibles.
    return scope | ~Q(type_contenu__in=types_raffines)


def trier_contenus(queryset, params):
    """Applique le tri demandé. « Pertinence » sans mot-clé retombe sur l'ordre alphabétique."""
    tri = params.get('tri') or TRI_PERTINENCE

    if tri == TRI_ALPHABETIQUE:
        return queryset.order_by('titre', 'id')
    if tri == TRI_RECENT:
        return queryset.order_by(
            F('annee_debut').desc(nulls_last=True), 'titre', 'id'
        )
    if 'pertinence' in queryset.query.annotations:
        return queryset.order_by('-pertinence', 'titre', 'id')
    return queryset.order_by('titre', 'id')


# --------------------------------------------------------------------------- #
# Mode « plan de gestion »
# --------------------------------------------------------------------------- #

def filtrer_plans(queryset, params):
    """
    Filtre les plans par nom, site, département ou région, plus les facettes.

    Le mot-clé porte sur quatre champs distincts, ce qui n'est pas modélisable
    par l'index de contenu : la recherche reste une jointure `ILIKE` sans
    accents. À l'échelle du référentiel (quelques milliers de plans) elle est
    largement assez rapide.
    """
    mot_cle = (params.get('q') or '').strip()
    if mot_cle:
        queryset = queryset.filter(
            Q(nom__unaccent__icontains=mot_cle)
            | Q(sites__site__nom_site__unaccent__icontains=mot_cle)
            | Q(sites__site__areas__id_area__area_name__unaccent__icontains=mot_cle)
        )

    zones = entiers(params, 'zones')
    if zones:
        queryset = queryset.filter(sites__site__areas__id_area__in=zones)

    organismes = entiers(params, 'organismes')
    if organismes:
        queryset = queryset.filter(
            sites__site__corogsite__uuid_og__id_organisme__in=organismes
        )

    types_site = liste(params, 'types_site')
    if types_site:
        queryset = queryset.filter(
            sites__site__id_type_site__mnemonique__in=types_site
        )

    statuts = liste(params, 'statuts')
    if statuts:
        queryset = queryset.filter(q_statuts(statuts, champ_statut='statut'))

    return queryset.distinct()


def trier_plans(queryset, params):
    """Tri des plans. Faute de score textuel, « pertinence » = alphabétique."""
    tri = params.get('tri') or TRI_PERTINENCE
    if tri == TRI_RECENT:
        return queryset.order_by(F('annee_debut').desc(nulls_last=True), 'nom')
    return queryset.order_by('nom')
