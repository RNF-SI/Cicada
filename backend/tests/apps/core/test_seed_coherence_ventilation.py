"""
#763 — Jeu d'essai : des plans et des actions conformes aux règles actuelles.

Une donnée seedée qui ne respecte plus les règles de saisie rend la recette
illisible : on ne sait plus si un défaut est un bug ou une donnée ancienne. Ce
test relance le jeu d'essai complet (deux fois : il doit rester idempotent) et
passe chaque action au crible des règles de la programmation et du suivi :

- « aucune ventilation » : un seul temps de travail total (#759) ;
- temps décliné par poste si et seulement si la programmation l'est (#735) ;
- pas d'investissement sans type de budget (#735, retour 21/10) ;
- coûts détaillés ↔ composants stockés, enveloppes sinon (#600 / #735) ;
- coût salarial stocké seulement quand il est saisi (#600 / #722 / #741) ;
- temps réalisé par poste selon la déclinaison du suivi (#760) ;
- programmation globale : une ligne de période, des années sans montant (#735) ;
- suivis : rattachés à une action CS, du même type d'action, avec protocole (#715).

Il vérifie aussi que les plans composites couvrent les combinaisons attendues.
"""
from datetime import date

import pytest
from django.core.management import call_command

from apps.plans.models import PlanGestion
from apps.plans.models_operations import (
    Operation, OperationAnnee, OperationAnneeOrganisme, RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme,
)
from apps.plans.rh_total import est_temps_total_unique
from apps.plans.serializers_operations import OperationCreateSerializer

pytestmark = [pytest.mark.django_db]

ORG_MODES = ('by_org', 'by_org_type', 'by_org_type_poste')
TYPE_MODES = ('by_type', 'by_org_type', 'by_type_poste', 'by_org_type_poste')
ENVELOPPES = ('budget_fonctionnement', 'budget_investissement')
COMPOSANTS = ('cout_salarial', 'cout_salarial_invest', 'cout_stage', 'cout_prestataire',
              'autre_cout', 'cout_prestataire_invest', 'autre_cout_invest')
INVEST = ('budget_investissement', 'cout_salarial_invest', 'cout_prestataire_invest',
          'autre_cout_invest')
SALARIAL = ('cout_salarial', 'cout_salarial_invest')

PLAN_COMPOSITE_PROG = 'Ventilation composite — programmation'
PLAN_COMPOSITE_SUIVI = 'Ventilation composite — suivi'


def _seed():
    call_command('import_nomenclatures', verbosity=0)
    call_command('seed_testdata', verbosity=0)


def _actions(plan):
    return [o for o in Operation.objects.all() if o.get_plan_de_gestion() == plan]


def _rempli(obj, champ):
    return getattr(obj, champ, None) not in (None, 0)


def incoherences(operations):
    """Écarts aux règles actuelles, une ligne lisible par écart."""
    ecarts = []
    for op in operations:
        plan = op.get_plan_de_gestion()
        nom = f"{plan.nom if plan else '—'} / {op.code_operation or op.libelle}"
        mode = op.ventilation_mode or 'none'

        def ecart(regle):
            ecarts.append(f"{regle} : {nom}")

        annees = list(OperationAnnee.tous.filter(id_operation=op))
        globales = [a for a in annees if a.annee is None]
        if bool(globales) != op.programmation_globale:
            ecart("programmation globale sans sa ligne de période (ou l'inverse)")
        par_poste = op.temps_par_poste()
        for a in annees:
            orgs = list(OperationAnneeOrganisme.objects.filter(id_operation_annee=a))
            porteurs = [a, *orgs]
            rh = list(a.rh_lignes.all())
            if op.programmation_globale and a.annee is not None and (
                    rh or any(_rempli(x, c) for x in porteurs for c in ('budget', *ENVELOPPES, *COMPOSANTS))):
                ecart("programmation globale avec des montants annuels")
            if est_temps_total_unique(op) and (
                    len(rh) > 1 or any(ligne.id_poste_id or ligne.id_organisme_id for ligne in rh)):
                ecart("« aucune ventilation » : plusieurs lignes de temps (#759)")
            if par_poste and any(ligne.id_poste_id is None for ligne in rh):
                ecart("temps décliné par poste avec une ligne sans poste")
            if not par_poste and any(ligne.id_poste_id for ligne in rh):
                ecart("temps saisi par poste sans déclinaison par poste")
            if mode not in TYPE_MODES and (
                    any(_rempli(x, c) for x in porteurs for c in INVEST)
                    or any(ligne.categorie_depense == 'investissement' for ligne in rh)):
                ecart("investissement sans type de budget")
            if mode not in ORG_MODES and any(
                    _rempli(o, c) for o in orgs for c in (*ENVELOPPES, *COMPOSANTS)):
                ecart("montants par organisme hors mode par organisme")
            if op.declinaison_par_type_cout and any(_rempli(x, c) for x in porteurs for c in ENVELOPPES):
                ecart("coûts détaillés mais enveloppes stockées")
            if not op.declinaison_par_type_cout and any(_rempli(x, c) for x in porteurs for c in COMPOSANTS):
                ecart("composants de coût stockés sans déclinaison par type de coût")
            if op.cout_salarial_auto and any(_rempli(x, c) for x in porteurs for c in SALARIAL):
                ecart("coût salarial stocké alors qu'il est calculé")

            realisation = RealisationOperationAnnee.objects.filter(id_operation_annee=a).first()
            if realisation is None:
                continue
            reel = list(realisation.rh_lignes.all())
            poste_reel = op.get_declinaison_par_poste_realise()
            if poste_reel and any(ligne.id_poste_id is None for ligne in reel):
                ecart("temps réalisé par poste avec une ligne sans poste (#760)")
            if not poste_reel and any(ligne.id_poste_id for ligne in reel):
                ecart("temps réalisé par poste sans déclinaison au suivi (#760)")
            if not poste_reel and est_temps_total_unique(op) and len(reel) > 1:
                ecart("« aucune ventilation » : plusieurs lignes de temps réalisé (#759)")
            if mode not in TYPE_MODES and any(ligne.categorie_depense == 'investissement' for ligne in reel):
                ecart("temps réalisé en investissement sans type de budget")
            if op.get_cout_salarial_auto_realise() and any(
                    _rempli(realisation, f'{c}_realise') for c in SALARIAL):
                ecart("coût salarial réalisé stocké alors qu'il est calculé (#722)")

        suivi = op.id_suivi
        if suivi is not None:
            # Même règle que le serveur : le type d'action fait foi.
            if not OperationCreateSerializer._accepte_un_suivi(op.id_type_action):
                ecart("suivi rattaché à une action qui n'est pas CS (#715)")
            if suivi.id_type_action_id != op.id_type_action_id:
                ecart("suivi d'un autre type d'action que son action (#715)")
            if not suivi.protocoles.exists():
                ecart("suivi sans protocole")
    return ecarts


def test_jeu_d_essai_coherent_et_idempotent():
    _seed()
    nb_operations = Operation.objects.count()
    _seed()
    assert Operation.objects.count() == nb_operations

    assert incoherences(Operation.objects.all()) == []

    # Composite de programmation : toutes les variantes dans un même plan.
    prog = PlanGestion.objects.get(nom=PLAN_COMPOSITE_PROG)
    assert prog.statut == 'draft'
    ops = _actions(prog)
    assert {o.ventilation_mode for o in ops} == {
        'none', 'by_org', 'by_type', 'by_org_type', 'by_type_poste', 'by_org_type_poste'}
    assert {o.declinaison_par_type_cout for o in ops} == {True, False}
    assert {o.cout_salarial_auto for o in ops if o.declinaison_par_type_cout} == {True, False}
    assert {o.programmation_globale for o in ops} == {True, False}
    assert {o.temps_par_poste() for o in ops} == {True, False}

    # Composite de suivi : plan validé, réglages du suivi ≠ programmation.
    suivi = PlanGestion.objects.get(nom=PLAN_COMPOSITE_SUIVI)
    assert suivi.statut == 'valide'
    ops = _actions(suivi)
    assert any(not o.temps_par_poste() and o.get_declinaison_par_poste_realise() for o in ops)
    assert any(not o.declinaison_par_type_cout and o.get_declinaison_par_type_cout_realise() for o in ops)
    assert any(
        o.declinaison_par_type_cout and not o.get_cout_salarial_auto_realise() and (
            RealisationOperationAnnee.objects.filter(
                id_operation_annee__id_operation=o, cout_salarial_realise__gt=0).exists()
            or RealisationOperationAnneeOrganisme.objects.filter(
                id_operation_annee_organisme__id_operation_annee__id_operation=o,
                cout_salarial_realise__gt=0).exists())
        for o in ops)
    # #761 — une action sans réglage ni suivi, qui se verra proposer ceux du plan.
    assert any(not o.reglages_suivi_definis() and not RealisationOperationAnnee.objects.filter(
        id_operation_annee__id_operation=o).exists() for o in ops)
    # Années saisies, partielles et non saisies.
    annee = date.today().year
    saisies = {
        y: {o.pk for o in ops if RealisationOperationAnnee.objects.filter(
            id_operation_annee__id_operation=o, id_operation_annee__annee=y).exists()}
        for y in range(annee - 2, annee + 1)
    }
    programmees = {
        y: {o.pk for o in ops if OperationAnnee.objects.filter(id_operation=o, annee=y).exists()}
        for y in saisies
    }
    assert any(saisies[y] and saisies[y] == programmees[y] for y in saisies)
    assert any(saisies[y] and saisies[y] < programmees[y] for y in saisies)
