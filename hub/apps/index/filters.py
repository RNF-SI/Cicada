"""
Traduction des paramètres de l'exploration en filtres de requête.

Reprise de ``apps.search.filters`` de CICADA, avec **une seule différence de
fond** : les deux modes de recherche interrogent ici le même schéma dénormalisé.

Côté CICADA, le mode « plan de gestion » attaque `PlanGestion` par jointures
(sites → organismes → zones) tandis que le mode « contenu » attaque l'index. Le
hub n'a pas de modèle de plan : ses plans sont eux-mêmes une table d'index, avec
les mêmes colonnes de facettes. Les deux modes partagent donc la même logique,
ce qui supprime la classe de bugs où une facette filtrait différemment selon le
mode.
"""

import datetime

from django.contrib.postgres.search import (
    SearchHeadline, SearchQuery, SearchRank, SearchVector,
)
from django.db.models import BooleanField, Case, F, Q, Value, When

from apps.geo.models import LArea

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
#: sans faire disparaître les pressions ou les actions.
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
# Facettes communes aux deux modes
# --------------------------------------------------------------------------- #

def q_statuts(statuts, champ_statut, annee=None):
    """
    Q correspondant au filtre « statut du plan de gestion ».

    ``en_cours`` n'est pas un statut en base : c'est un plan validé dont l'année
    courante tombe dans sa période. Il recoupe donc volontairement ``valide``.

    :param champ_statut: ``statut_pg`` sur le contenu, ``statut`` sur le plan —
        les champs d'années portent le même nom des deux côtés.
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


def appliquer_facettes(queryset, params, champ_statut):
    """
    Applique les facettes partagées : zones, organismes, types de site, statut.

    Les colonnes portent les mêmes noms sur les deux tables d'index — c'est
    délibéré, et c'est ce qui permet aux deux modes de partager cette fonction.
    """
    zones = entiers(params, 'zones')
    if zones:
        queryset = queryset.filter(area_ids__overlap=zones)

    organismes = liste(params, 'organismes')
    if organismes:
        # Les codes d'organisme sont vides tant que leur identité nationale
        # n'est pas tranchée : ce filtre ne rend donc rien, ce qui est le
        # comportement voulu — une absence visible plutôt qu'un appariement
        # faux. Il est écrit maintenant pour que la décision, le jour où elle
        # tombe, n'ait à toucher que l'ingestion.
        queryset = queryset.filter(organisme_codes__overlap=organismes)

    types_site = liste(params, 'types_site')
    if types_site:
        queryset = queryset.filter(type_site_codes__overlap=types_site)

    instances = liste(params, 'instances')
    if instances:
        # Facette propre au hub : filtrer par instance d'origine. CICADA n'en a
        # pas l'usage, un index local n'ayant qu'une seule provenance.
        queryset = queryset.filter(instance_id__in=instances)

    statuts = liste(params, 'statuts')
    if statuts:
        queryset = queryset.filter(q_statuts(statuts, champ_statut))

    return queryset


# --------------------------------------------------------------------------- #
# Mode « contenu d'un plan de gestion »
# --------------------------------------------------------------------------- #

def _avec_mot_cle(queryset, mot_cle, champ, requete, info=None):
    """
    Recherche plein texte, avec repli approximatif **seulement si elle ne rend rien**.

    La similarité par trigramme était jusqu'ici unie au plein texte : tout
    document *proche* remontait au même titre qu'un document correspondant. Le
    résultat était incompréhensible sur les mots courts, qui portent peu de
    trigrammes — chercher « fleur » remontait « … et de **leur** faune
    associée », `word_similarity` valant 0,667 pour un seuil à 0,6 (#651). Un
    résultat sans rapport visible avec la requête se lit comme un défaut de
    l'outil, et c'est bien ainsi qu'il a été rapporté.

    Relever le seuil ne suffisait pas : une vraie faute de frappe score à peine
    plus haut (« eutotrophes » / « eutrophes » = 0,69) et serait tombée avec le
    bruit. Ce qui distingue les deux cas n'est pas le score, c'est le
    **contexte** — on ne cherche un mot approchant que faute d'avoir trouvé le
    mot. Le trigramme redevient donc ce qu'il aurait dû rester : un repli.

    L'approximation porte sur le libellé **et sur les objets rattachés** (#634) :
    espèces, habitats et protocoles sont des noms longs, souvent latins, qu'on
    tape rarement juste.

    :param info: dictionnaire optionnel, renseigné avec ``approximatif`` pour
        que l'interface puisse dire à l'utilisateur qu'aucun résultat exact
        n'existe — sans quoi il croirait avoir trouvé ce qu'il cherchait.
    """
    exact = queryset.filter(**{champ: requete})

    # Décidé AVANT les facettes, volontairement : si le mot-clé correspond mais
    # qu'une facette exclut tout, la bonne réponse est « aucun résultat », pas
    # une liste de termes approchants que l'utilisateur n'a pas demandés.
    if exact.exists():
        if info is not None:
            info['approximatif'] = False
        return exact.annotate(pertinence=SearchRank(F(champ), requete))

    if info is not None:
        info['approximatif'] = True
    return queryset.filter(
        Q(titre__trigram_word_similar=mot_cle)
        | Q(rattachements__trigram_word_similar=mot_cle)
    ).annotate(pertinence=SearchRank(F(champ), requete))


def filtrer_contenus(queryset, params, info=None):
    """
    Applique au queryset d'index tous les filtres SAUF l'onglet actif.

    L'onglet est exclu pour que les compteurs affichés au-dessus de la liste
    restent ceux de la recherche entière : sans cela, sélectionner « Pressions »
    ferait tomber à zéro tous les autres onglets.

    :param info: dictionnaire optionnel renseigné avec ``approximatif``
        (cf. :func:`_avec_mot_cle`).
    """
    mot_cle = (params.get('q') or '').strip()
    titres_seulement = booleen(params, 'titres_seulement', defaut=True)

    if mot_cle:
        champ = 'search_titre' if titres_seulement else 'search_full'
        requete = SearchQuery(mot_cle, config=SEARCH_CONFIG, search_type='websearch')
        queryset = _avec_mot_cle(queryset, mot_cle, champ, requete, info)

    types = liste(params, 'types')
    if types:
        queryset = queryset.filter(type_contenu__in=types)

    queryset = appliquer_facettes(queryset, params, champ_statut='statut_pg')
    return queryset.filter(q_sous_types(params))


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


#: Champs interrogés, dans l'ordre où on les présente à l'utilisateur.
#: `contexte` (libellés des ancêtres) n'est lu qu'en mode élargi.
CHAMPS_CORRESPONDANCE = ('titre', 'rattachements', 'description', 'contexte')


def annoter_correspondances(queryset, params, approximatif=False):
    """
    Dit, pour chaque résultat, **quel champ a répondu** (#650).

    « Pour "fleur" on ne sait pas si c'est lié au mot, ou bien si une des
    espèces est une fleur. » Le problème est réel et propre à cet index : les
    objets rattachés — espèces, habitats, protocoles — sont interrogés mais
    **jamais affichés**. Une tuile dont le titre n'a aucun rapport visible avec
    la requête paraît donc arbitraire, alors qu'elle est parfaitement pertinente.

    On annote donc un booléen par champ, plus un extrait des rattachements
    découpé par `ts_headline` autour de la correspondance : c'est la seule
    façon d'isoler l'élément qui a répondu, le champ étant un bloc de texte sans
    séparateur.

    L'extrait est renvoyé **sans balisage** : le surlignage est fait côté
    interface, sur des segments de texte, ce qui évite d'injecter du HTML venu
    de la base.

    À appeler **après** le calcul des compteurs d'onglets : ces annotations
    entreraient sinon dans le `GROUP BY` et fausseraient les totaux.
    """
    mot_cle = (params.get('q') or '').strip()
    if not mot_cle:
        return queryset

    titres_seulement = booleen(params, 'titres_seulement', defaut=True)
    # Le mode restreint n'interroge que le libellé et les objets rattachés :
    # annoncer une correspondance sur la description y serait un mensonge.
    champs = ('titre', 'rattachements') if titres_seulement else CHAMPS_CORRESPONDANCE
    requete = SearchQuery(mot_cle, config=SEARCH_CONFIG, search_type='websearch')

    for champ in champs:
        if approximatif:
            # En repli, c'est la similarité qui a répondu, pas le plein texte.
            condition = Q(**{f'{champ}__trigram_word_similar': mot_cle})
        else:
            queryset = queryset.annotate(
                **{f'vecteur_{champ}': SearchVector(champ, config=SEARCH_CONFIG)}
            )
            condition = Q(**{f'vecteur_{champ}': requete})
        queryset = queryset.annotate(**{
            f'correspond_{champ}': Case(
                When(condition, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        })

    return queryset.annotate(
        extrait_rattachements=SearchHeadline(
            'rattachements', requete, config=SEARCH_CONFIG,
            start_sel='', stop_sel='', max_words=14, min_words=5,
            highlight_all=False,
        )
    )


def trier_contenus(queryset, params):
    """Applique le tri demandé. « Pertinence » sans mot-clé retombe sur l'alphabétique."""
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

    Le mot-clé porte sur trois choses : le nom du plan, le nom d'un de ses sites
    et le nom d'une de ses zones. Les deux dernières sont dénormalisées ici
    (JSON pour les sites, identifiants pour les zones), là où CICADA les atteint
    par jointure — le résultat est le même, en moins de jointures.
    """
    mot_cle = (params.get('q') or '').strip()
    if mot_cle:
        # Les zones sont stockées par identifiant : on résout d'abord les noms
        # correspondants, en une requête sur un référentiel de 135 lignes.
        zones_nommees = list(
            LArea.objects
            .filter(area_name__unaccent__icontains=mot_cle)
            .values_list('id_area', flat=True)
        )
        recherche = (
            Q(nom__unaccent__icontains=mot_cle)
            | Q(sites_noms__unaccent__icontains=mot_cle)
        )
        if zones_nommees:
            recherche |= Q(area_ids__overlap=zones_nommees)
        queryset = queryset.filter(recherche)

    return appliquer_facettes(queryset, params, champ_statut='statut')


def trier_plans(queryset, params):
    """Tri des plans. Faute de score textuel, « pertinence » = alphabétique."""
    tri = params.get('tri') or TRI_PERTINENCE
    if tri == TRI_RECENT:
        return queryset.order_by(F('annee_debut').desc(nulls_last=True), 'nom')
    return queryset.order_by('nom')
