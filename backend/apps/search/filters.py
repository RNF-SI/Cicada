"""
Traduction des paramètres de l'exploration en filtres de requête.

Isolé des vues pour rester testable sans HTTP, et parce que les deux modes de
recherche (contenu / plan de gestion) partagent les mêmes facettes de plan
exprimées sur des schémas différents : colonnes dénormalisées côté index,
jointures côté `PlanGestion`.
"""

import datetime

from django.conf import settings
from django.contrib.postgres.search import (
    SearchHeadline, SearchQuery, SearchRank, SearchVector, SearchVectorField,
)
from django.db.models import BooleanField, Case, F, Func, Q, Value, When

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
    l'année courante tombe dans sa période, prolongation comprise (#676 :
    ``annee_fin + annees_extension``). Il recoupe donc volontairement
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
                & Q(annee_fin__gte=annee - F('annees_extension'))
            )
    return scope


# --------------------------------------------------------------------------- #
# Structure d'origine (#636)
# --------------------------------------------------------------------------- #

def instance_exclue(params):
    """
    Vrai si le filtre « structure d'origine » exclut cette instance.

    Ce filtre n'a de sens que sur le hub, où l'index agrège plusieurs
    provenances. Il est néanmoins honoré ici, pour une raison précise : une URL
    de recherche est faite pour être partagée, et un lien produit sur
    l'exploration nationale peut être ouvert sur une instance qui explore en
    local. L'ignorer rendrait alors les plans de cette instance sous un filtre
    qui demandait ceux d'une autre — une réponse fausse, et silencieuse.

    Le mode « plan de gestion » interroge `PlanGestion`, qui ne porte pas de
    colonne d'instance : localement, *tous* les plans sont ceux de cette
    instance. La question se réduit donc à « suis-je dans la liste ? ».
    """
    instances = liste(params, 'instances')
    return bool(instances) and settings.CICADA_INSTANCE_ID not in instances


# --------------------------------------------------------------------------- #
# Mode « contenu d'un plan de gestion »
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Portée de la recherche (#681 / #686)
# --------------------------------------------------------------------------- #

#: Les trois axes que l'utilisateur peut cocher en plus de l'objet lui-même
#: (libellé + objets rattachés, toujours interrogés).
PORTEE_DESCRIPTION = 'description'
PORTEE_PARENTS = 'parents'
PORTEE_ENFANTS = 'enfants'
PORTEES = (PORTEE_DESCRIPTION, PORTEE_PARENTS, PORTEE_ENFANTS)

#: Colonne de texte et vecteur généré correspondant à chaque axe.
CHAMP_PAR_PORTEE = {
    PORTEE_DESCRIPTION: 'description',
    PORTEE_PARENTS: 'contexte',
    PORTEE_ENFANTS: 'enfants',
}
VECTEUR_PAR_PORTEE = {
    PORTEE_DESCRIPTION: 'search_description',
    PORTEE_PARENTS: 'search_contexte',
    PORTEE_ENFANTS: 'search_enfants',
}


def portees(params):
    """
    Axes de portée demandés, sous forme d'ensemble (vide = l'objet seul).

    Le paramètre historique ``titres_seulement`` reste compris : ``false``
    valait « tout élargir », c'est-à-dire les trois axes. Une URL de recherche
    est faite pour être partagée, celles déjà envoyées doivent encore marcher.
    """
    valeurs = {v for v in liste(params, 'portee') if v in PORTEES}
    if valeurs:
        return valeurs
    if params.get('titres_seulement') is not None and not booleen(
        params, 'titres_seulement', defaut=True
    ):
        return set(PORTEES)
    return set()


class _Concat(Func):
    """``a || b || c`` sur des tsvector."""

    arg_joiner = ' || '
    template = '(%(expressions)s)'
    output_field = SearchVectorField()


def vecteur_de_portee(portee):
    """
    (expression du vecteur interrogé, nom de l'index GIN qui le couvre).

    Trois cas :

    - aucun axe → ``search_titre``, qui porte son propre index ;
    - tous les axes → ``search_full``, idem ;
    - une combinaison intermédiaire → la concaténation des vecteurs concernés,
      qui n'a pas d'index : on filtre d'abord sur ``search_full`` (sur-ensemble
      indexé), puis on revérifie exactement sur la concaténation. Un index par
      combinaison (huit) coûterait des centaines de Mo pour le volume visé sans
      rien apporter de plus.
    """
    if not portee:
        return F('search_titre'), 'search_titre'
    if set(portee) >= set(PORTEES):
        return F('search_full'), 'search_full'
    vecteurs = [F('search_titre')] + [
        F(VECTEUR_PAR_PORTEE[axe]) for axe in PORTEES if axe in portee
    ]
    return _Concat(*vecteurs), 'search_full'


def _avec_mot_cle(queryset, mot_cle, portee, requete, info=None):
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
    vecteur, index = vecteur_de_portee(portee)
    exact = queryset.filter(**{index: requete})
    if not isinstance(vecteur, F):
        # Combinaison intermédiaire : l'index a donné les candidats, on
        # revérifie sur les seuls axes demandés.
        exact = exact.annotate(vecteur_portee=vecteur).filter(vecteur_portee=requete)

    # Décidé AVANT les facettes, volontairement : si le mot-clé correspond mais
    # qu'une facette exclut tout, la bonne réponse est « aucun résultat », pas
    # une liste de termes approchants que l'utilisateur n'a pas demandés.
    if exact.exists():
        if info is not None:
            info['approximatif'] = False
        return exact.annotate(pertinence=SearchRank(vecteur, requete))

    if info is not None:
        info['approximatif'] = True
    approchant = (
        Q(titre__trigram_word_similar=mot_cle)
        | Q(rattachements__trigram_word_similar=mot_cle)
    )
    if PORTEE_ENFANTS in portee:
        # Les libellés des enfants sont courts comme un titre : la similarité y
        # a un sens. Pas sur la description ni le contexte, blocs longs où elle
        # ne ferait que du bruit.
        approchant |= Q(enfants__trigram_word_similar=mot_cle)
    return queryset.filter(approchant).annotate(
        pertinence=SearchRank(vecteur, requete)
    )


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

    if mot_cle:
        requete = SearchQuery(mot_cle, config=SEARCH_CONFIG, search_type='websearch')
        queryset = _avec_mot_cle(queryset, mot_cle, portees(params), requete, info)

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

    # Ici l'index porte bien une colonne d'instance : on filtre dessus plutôt
    # que de raisonner sur l'identité de l'instance courante. Les deux reviennent
    # au même en local, mais celui-ci reste juste si l'index venait à contenir
    # des documents d'ailleurs.
    instances = liste(params, 'instances')
    if instances:
        queryset = queryset.filter(instance_id__in=instances)

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


#: Champs interrogés, dans l'ordre où on les présente à l'utilisateur. Les deux
#: premiers le sont toujours ; les autres selon la portée cochée.
CHAMPS_CORRESPONDANCE = ('titre', 'rattachements', 'description', 'contexte', 'enfants')

#: Champs dont on renvoie un extrait découpé autour de la correspondance. Le
#: titre n'en a pas besoin : il est affiché entier et surligné tel quel.
CHAMPS_EXTRAITS = ('rattachements', 'description', 'contexte', 'enfants')


def champs_interroges(portee):
    """Champs réellement interrogés pour une portée donnée."""
    return ('titre', 'rattachements') + tuple(
        CHAMP_PAR_PORTEE[axe] for axe in PORTEES if axe in portee
    )


def annoter_correspondances(queryset, params, approximatif=False):
    """
    Dit, pour chaque résultat, **quel champ a répondu** et **où** (#650, #681).

    « Pour "fleur" on ne sait pas si c'est lié au mot, ou bien si une des
    espèces est une fleur. » Le problème est réel et propre à cet index : les
    objets rattachés — espèces, habitats, protocoles —, la description, les
    libellés des parents et des enfants sont interrogés mais **pas affichés**
    sur la tuile. Un résultat dont le titre n'a aucun rapport visible avec la
    requête paraît donc arbitraire, alors qu'il est pertinent.

    On annote donc un booléen par champ interrogé, plus un extrait découpé par
    `ts_headline` autour de la correspondance pour chaque champ qui n'est pas
    le titre : c'est la seule façon d'isoler le passage qui a répondu, ces
    champs étant des blocs de texte sans séparateur. « Il ne doit pas y avoir
    de résultat dont on ne comprenne pas pourquoi il est ressorti » (#681).

    Les extraits sont renvoyés **sans balisage** : le surlignage est fait côté
    interface, sur des segments de texte, ce qui évite d'injecter du HTML venu
    de la base.

    Seuls les champs de la portée demandée sont annotés : annoncer une
    correspondance sur la description quand elle n'était pas interrogée serait
    un mensonge.

    À appeler **après** le calcul des compteurs d'onglets : ces annotations
    entreraient sinon dans le `GROUP BY` et fausseraient les totaux.
    """
    mot_cle = (params.get('q') or '').strip()
    if not mot_cle:
        return queryset

    champs = champs_interroges(portees(params))
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
        if champ in CHAMPS_EXTRAITS and not approximatif:
            # En repli, `ts_headline` ne trouverait rien : l'extrait est alors
            # construit côté sérialiseur autour du mot le plus proche.
            queryset = queryset.annotate(**{
                f'extrait_{champ}': SearchHeadline(
                    champ, requete, config=SEARCH_CONFIG,
                    start_sel='', stop_sel='', max_words=14, min_words=5,
                    highlight_all=False,
                )
            })

    return queryset


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

    if instance_exclue(params):
        return queryset.none()

    return queryset.distinct()


def trier_plans(queryset, params):
    """Tri des plans. Faute de score textuel, « pertinence » = alphabétique."""
    tri = params.get('tri') or TRI_PERTINENCE
    if tri == TRI_RECENT:
        return queryset.order_by(F('annee_debut').desc(nulls_last=True), 'nom')
    return queryset.order_by('nom')
