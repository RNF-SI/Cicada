"""
#763 — Règles communes aux seeders qui créent des actions.

Une donnée seedée qui ne respecte plus les règles de saisie rend la recette
illisible : on ne sait plus si un défaut vient d'un bug ou d'une donnée
ancienne. Ces helpers appliquent aux actions seedées ce que le formulaire et
le serveur imposent à une action saisie. Le test
``tests/apps/core/test_seed_coherence_ventilation.py`` les vérifie sur le jeu
d'essai complet.
"""
from decimal import Decimal


def couts_detailles(budget) -> dict:
    """
    Composants de coût d'une enveloppe annuelle, pour une action dont les
    coûts sont détaillés (#600 / #624) : les enveloppes fonctionnement /
    investissement se recalculent depuis eux et ne sont donc pas stockées.
    Le coût salarial, calculé, vient des lignes de temps par poste.
    """
    budget = Decimal(str(budget or 0))

    def part(ratio):
        return (budget * Decimal(ratio)).quantize(Decimal('0.01'))

    return {
        'budget_fonctionnement': None,
        'budget_investissement': None,
        'cout_prestataire': part('0.30'),
        'autre_cout': part('0.20'),
        'autre_cout_commentaire': 'Frais divers (seed)',
        'cout_prestataire_invest': part('0.15'),
        'autre_cout_invest': part('0.05'),
        'autre_cout_invest_commentaire': 'Matériel (seed)',
    }


# Montants d'une année ou d'un organisme : remis à zéro avant d'écrire ceux du
# mode, sinon un passage précédent (autre mode, autre règle) laisse des champs
# que la vue additionne.
MONTANTS_VIDES = {
    'budget_fonctionnement': None,
    'budget_investissement': None,
    'cout_salarial': None,
    'cout_salarial_invest': None,
    'cout_stage': None,
    'cout_prestataire': None,
    'autre_cout': None,
    'autre_cout_commentaire': '',
    'cout_prestataire_invest': None,
    'autre_cout_invest': None,
    'autre_cout_invest_commentaire': '',
}


def _est_cs(type_action) -> bool:
    """Même règle que le serveur (`_accepte_un_suivi`, #715)."""
    if type_action is None:
        return True
    return (type_action.cd_nomenclature or type_action.mnemonique or '').startswith('CS')


def aligner_suivis_sur_actions(operations, seeder=None) -> int:
    """
    #715 — un suivi n'est porté que par une action CS, et l'action et son suivi
    partagent le même type d'action.

    - Action qui n'est pas CS : elle se détache de son suivi, qui reste dans le
      module Inventaires (comme à l'enregistrement de l'action).
    - Action CS : elle prend le type de son suivi, plus précis dans le jeu
      d'essai (« Suivi des oiseaux » plutôt que « Inventaire de la faune ») ;
      un suivi sans type prend celui de l'action.

    Renvoie le nombre d'actions corrigées.
    """
    corrigees = 0
    for op in operations.select_related('id_type_action', 'id_suivi__id_type_action'):
        suivi = op.id_suivi
        if not _est_cs(op.id_type_action):
            op.id_suivi = None
            op.est_suivi_existant = False
            op.save(update_fields=['id_suivi', 'est_suivi_existant'])
            corrigees += 1
            if seeder is not None:
                seeder.log_item('détaché', f'suivi « {suivi.intitule[:40]} » de {op.code_operation} (non CS)')
            continue
        if suivi.id_type_action_id == op.id_type_action_id:
            continue
        if suivi.id_type_action_id and _est_cs(suivi.id_type_action):
            op.id_type_action_id = suivi.id_type_action_id
            op.save(update_fields=['id_type_action'])
        else:
            suivi.id_type_action_id = op.id_type_action_id
            suivi.save(update_fields=['id_type_action'])
        corrigees += 1
    return corrigees
