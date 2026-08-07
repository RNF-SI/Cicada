"""
Assemblage de la fiche publique d'un plan de gestion.

L'arborescence est reconstruite en Python à partir d'une poignée de requêtes
plutôt que par navigation paresseuse : un plan bien rempli compte plusieurs
centaines d'objets, et laisser l'ORM les découvrir au fil de la sérialisation
produirait des milliers de requêtes.

Les collections sont posées sur les instances sous des noms suffixés ``_pub``.
Ce n'est pas de la coquetterie : Django interdit d'écraser un manager de
relation inverse (``enjeu.objectifs_long_terme = [...]`` lève une exception).
Les sérialiseurs les remappent vers des noms de sortie propres.
"""

from django.db.models import Prefetch, Q

from apps.plans.access import OPERATION_TO_PG_PATHS
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, ObjectifLongTerme, ObjectifOperationnel,
)
from apps.plans.models_operations import Operation


def _indicateurs_prefetch(chemin):
    """Prefetch des indicateurs d'un niveau d'exigence ou d'un résultat attendu."""
    from apps.plans.models_indicateurs import Indicateur, Metrique

    return Prefetch(
        chemin,
        queryset=(
            Indicateur.objects
            .select_related('type_indicateur')
            .prefetch_related(
                # La grille de lecture publiée (#634) se calcule à partir du
                # type, du format et des blocs ET/OU de chaque métrique : sans
                # ces trois-là, une fiche bien remplie coûte des centaines de
                # requêtes.
                Prefetch(
                    'metriques',
                    queryset=(
                        Metrique.objects
                        .select_related('type_metrique', 'format_metrique')
                        .prefetch_related('score_blocks')
                        .order_by('nom_metrique')
                    ),
                ),
            )
            .order_by('nom_indicateur')
        ),
        to_attr='indicateurs_pub',
    )


def _charger_enjeux(plan):
    enjeux = list(
        Enjeu.objects.filter(id_pg=plan)
        .select_related('id_categorie')
        .prefetch_related('taxons', 'habitats')
        # Priorité 1 d'abord ; les enjeux sans priorité (FCR) en dernier.
        .order_by('rang', 'libelle')
    )
    for enjeu in enjeux:
        enjeu.facteurs_pub = []
        enjeu.olt_pub = []
        enjeu.oo_pub = []
    return enjeux


def _rattacher_facteurs(plan, enjeux_par_id):
    """Un facteur peut être partagé entre plusieurs enjeux (#552) : il apparaît sous chacun."""
    from apps.plans.models_enjeux import Pression

    facteurs = (
        FacteurInfluence.objects.filter(enjeux__id_pg=plan)
        .distinct()
        .prefetch_related(
            'enjeux',
            Prefetch(
                'pressions',
                queryset=Pression.objects.select_related('id_type_pression')
                .order_by('libelle'),
                to_attr='pressions_pub',
            ),
        )
        .order_by('libelle')
    )
    for facteur in facteurs:
        for enjeu in facteur.enjeux.all():
            cible = enjeux_par_id.get(enjeu.pk)
            if cible is not None:
                cible.facteurs_pub.append(facteur)


def _rattacher_objectifs_long_terme(plan, enjeux_par_id):
    from apps.plans.models_enjeux import NiveauExigence

    objectifs = (
        ObjectifLongTerme.objects.filter(id_enjeu__id_pg=plan)
        .prefetch_related(
            Prefetch(
                'niveaux_exigence',
                queryset=NiveauExigence.objects.prefetch_related(
                    _indicateurs_prefetch('indicateurs')
                ).order_by('libelle'),
                to_attr='niveaux_pub',
            )
        )
        .order_by('libelle')
    )
    for objectif in objectifs:
        cible = enjeux_par_id.get(objectif.id_enjeu_id)
        if cible is not None:
            cible.olt_pub.append(objectif)


def _rattacher_objectifs_operationnels(plan, enjeux_par_id):
    """
    Un OO pend soit directement d'un enjeu (cas FCR, #337), soit de ses
    pressions — donc de leur facteur, donc des enjeux de ce facteur.
    """
    from apps.plans.models_enjeux import ResultatAttendu

    objectifs = (
        ObjectifOperationnel.objects.filter(
            Q(id_enjeu__id_pg=plan)
            | Q(pressions__id_facteur_influence__enjeux__id_pg=plan)
        )
        .distinct()
        .prefetch_related(
            'pressions__id_facteur_influence__enjeux',
            Prefetch(
                'resultats_attendus',
                queryset=ResultatAttendu.objects.prefetch_related(
                    _indicateurs_prefetch('indicateurs')
                ).order_by('libelle'),
                to_attr='resultats_pub',
            ),
        )
        .order_by('libelle')
    )

    for objectif in objectifs:
        cibles = set()
        if objectif.id_enjeu_id:
            cibles.add(objectif.id_enjeu_id)
        for pression in objectif.pressions.all():
            facteur = pression.id_facteur_influence
            if facteur:
                cibles.update(enjeu.pk for enjeu in facteur.enjeux.all())

        for id_enjeu in cibles:
            cible = enjeux_par_id.get(id_enjeu)
            if cible is not None:
                cible.oo_pub.append(objectif)


#: Nomenclatures dont les suivis et protocoles ne stockent que le mnémonique.
#: Elles sont résolues en une requête pour toute la fiche : les résoudre champ
#: par champ, comme le fait le sérialiseur interne des suivis, coûterait une
#: requête par action et par champ.
TYPES_NOMENCLATURE_SUIVI = (
    'OBJECTIF_SUIVI', 'CIBLE_SUIVI', 'OUTIL_SAISIE',
    'BANCARISATION_STOCKAGE', 'PERIODE_SUIVI',
)


def _libelles_nomenclature():
    """`{(type, mnémonique): libellé}` pour tout ce qu'affiche un suivi."""
    from apps.core.models import Nomenclature

    return {
        (type_mnemonique, mnemonique): label
        for type_mnemonique, mnemonique, label in (
            Nomenclature.objects
            .filter(id_type__mnemonique__in=TYPES_NOMENCLATURE_SUIVI)
            .values_list('id_type__mnemonique', 'mnemonique', 'label')
        )
    }


def _charger_actions(plan):
    from apps.plans.models_indicateurs import Metrique

    scope = Q()
    for chemin in OPERATION_TO_PG_PATHS:
        scope |= Q(**{chemin: plan})

    # Les métriques portent leur indicateur — c'est par elles qu'une action
    # atteint ses indicateurs de réponse (#626), en plus du lien direct.
    metriques = Metrique.objects.select_related(
        'id_indicateur__type_indicateur',
        'type_metrique', 'format_metrique',
    ).prefetch_related('score_blocks')

    actions = list(
        Operation.objects.filter(scope)
        .distinct()
        .select_related(
            'id_categorie_action_reserve', 'id_type_action', 'id_priorite',
            'id_indicateur', 'id_indicateur__type_indicateur',
            'id_suivi', 'id_suivi__id_statut',
        )
        .prefetch_related(
            'sites',
            'id_suivi__protocoles',
            Prefetch('metriques', queryset=metriques),
            # Métriques et grille des indicateurs de réponse, atteints par les
            # deux chemins possibles : le lien direct et les métriques.
            Prefetch('id_indicateur__metriques', queryset=metriques),
            Prefetch('metriques__id_indicateur__metriques', queryset=metriques),
        )
        .order_by('code_operation', 'libelle')
    )

    suivis = [action.id_suivi for action in actions if action.id_suivi_id]
    if not suivis:
        return actions

    libelles = _libelles_nomenclature()
    for suivi in suivis:
        suivi.libelles_pub = libelles
        for protocole in suivi.protocoles.all():
            protocole.libelles_pub = libelles

    return actions


def construire_fiche(plan):
    """
    Complète ``plan`` avec son arborescence publique et retourne l'instance.

    Les collections attachées sont celles que lit
    :class:`apps.search.serializers_fiche.FichePubliqueSerializer`.
    """
    enjeux = _charger_enjeux(plan)
    enjeux_par_id = {enjeu.pk: enjeu for enjeu in enjeux}

    _rattacher_facteurs(plan, enjeux_par_id)
    _rattacher_objectifs_long_terme(plan, enjeux_par_id)
    _rattacher_objectifs_operationnels(plan, enjeux_par_id)

    plan.enjeux_pub = enjeux
    plan.actions_pub = _charger_actions(plan)
    return plan
