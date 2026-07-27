"""
Tests des exports Excel/Word d'un plan de gestion.

Couvre :
- la logique financière partagée (``services_export_finance``) : coût salarial
  recalculé, ventilation fonctionnement/investissement, prestataire fonct+invest,
  bénévoles, réalisé, modes avec/sans ventilation par organisme ;
- la génération des classeurs (fiche action, budget/RH prév. et suivi) et de la
  fiche Word : validité du fichier, onglets attendus, quelques valeurs clés.
"""

import io

import pytest
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans.models_operations import (
    Fonction, Operation, OperationAnnee, OperationAnneeOrganisme,
    OperationAnneeRH, Poste, PosteFonction, RealisationOperationAnnee,
    RealisationOperationAnneeRH,
)
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory, SuperAdminFactory


def _nomenclature(type_mnemo, mnemo, label):
    t, _ = TypeNomenclature.objects.get_or_create(
        mnemonique=type_mnemo, defaults={'label': type_mnemo})
    n, _ = Nomenclature.objects.get_or_create(
        id_type=t, mnemonique=mnemo,
        defaults={'cd_nomenclature': mnemo[:10], 'label': label})
    return n


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def plan_finance():
    """Plan 2024-2026 avec une action CS ventilée par organisme + RH + coûts.

    Valeurs contrôlées (année 2024) :
      - RH : 10 jours fonctionnement @ 300 €/j → salarial fonct = 3000 €
      - RH : 2 jours bénévolat
      - Organisme : prestataire fonct 500 €, prestataire invest 200 €,
        autre_cout 100 €, autre_cout_invest 50 €
    """
    plan = PlanGestionFactory(annee_debut=2024, annee_fin=2026)
    org = OrganismeFactory(nom_organisme="Org Alpha")

    enjeu = EnjeuFactory(id_pg=plan)
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    ind = IndicateurFactory(id_ne=ne)
    met = MetriqueFactory(id_indicateur=ind)

    cs = _nomenclature('CATEGORIE_ACTION_RESERVE', 'CS', 'Connaissance et suivi')
    op = OperationFactory(
        metriques=[met], id_categorie_action_reserve=cs,
        ventilation_mode='by_org_type', declinaison_par_poste=True,
        code_operation='CS01', annee_min=2024, annee_max=2026,
    )

    fonction, _ = Fonction.objects.get_or_create(
        libelle='Conservateur (export test)', defaults={'type_poste': 'salarie'})
    poste = Poste.objects.create(id_pg=plan, id_organisme=org, nombre=1, cout_jour=300)
    PosteFonction.objects.create(id_poste=poste, id_fonction=fonction, pourcentage=100)

    oa = OperationAnnee.objects.create(id_operation=op, annee=2024, periodicite=True)
    OperationAnneeRH.objects.create(
        id_operation_annee=oa, id_poste=poste, id_organisme=org,
        jours=10, categorie_depense='fonctionnement')
    OperationAnneeRH.objects.create(
        id_operation_annee=oa, id_poste=poste, id_organisme=org,
        jours=2, categorie_depense='benevolat_partenariat')
    OperationAnneeOrganisme.objects.create(
        id_operation_annee=oa, id_organisme=org,
        cout_prestataire=500, cout_prestataire_invest=200,
        autre_cout=100, autre_cout_invest=50)

    # Réalisé (pour les exports « suivi »)
    real = RealisationOperationAnnee.objects.create(
        id_operation_annee=oa, periodicite_realisee=True)
    RealisationOperationAnneeRH.objects.create(
        id_realisation_operation_annee=real, id_poste=poste, id_organisme=org,
        jours=8, categorie_depense='fonctionnement')

    return {'plan': plan, 'org': org, 'op': op, 'poste': poste}


# ---------------------------------------------------------------------------
# Logique financière partagée
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportFinance:
    def test_cout_salarial_recalcule(self, plan_finance):
        from apps.plans.services_export_finance import build_plan_finance
        pf = build_plan_finance(plan_finance['plan'])
        assert pf.years == [2024, 2025, 2026]
        assert len(pf.actions) == 1
        af = pf.actions[0]
        assert af.is_cs is True
        assert af.categorie == 'CS'
        assert af.is_org_ventilated is True
        oid = plan_finance['org'].id_organisme
        c = af.cell(oid, 2024)
        # 10 jours × 300 €/j
        assert c.sal_fonct == 3000
        assert c.j_fonct == 10
        assert c.j_benevole == 2

    def test_ventilation_fonct_invest_prestataire(self, plan_finance):
        from apps.plans.services_export_finance import build_plan_finance
        af = build_plan_finance(plan_finance['plan']).actions[0]
        c = af.cell(plan_finance['org'].id_organisme, 2024)
        # prestataire présent dans les DEUX blocs (#607 Q2)
        assert c.prest_fonct == 500
        assert c.prest_invest == 200
        assert c.autre_fonct == 100
        assert c.autre_invest == 50
        # totaux
        assert c.tot_fonct == 3000 + 500 + 100     # salarial + presta + autres
        assert c.tot_invest == 0 + 200 + 50
        assert c.tot == c.tot_fonct + c.tot_invest

    def test_realise(self, plan_finance):
        from apps.plans.services_export_finance import build_plan_finance
        af = build_plan_finance(plan_finance['plan']).actions[0]
        c = af.cell(plan_finance['org'].id_organisme, 2024)
        assert c.rj_fonct == 8
        assert c.rsal_fonct == 8 * 300

    def test_code_action_pg_est_le_code_affichage(self, plan_finance):
        """#618 — la colonne « Code action PG » porte le code calculé (CS1…)."""
        from apps.plans.services_export_finance import build_plan_finance
        af = build_plan_finance(plan_finance['plan']).actions[0]
        assert af.code == 'CS1'

    def test_mode_none_non_ventile(self, plan_finance):
        """Une action en mode 'none' n'est pas ventilée par organisme (#607 Q3)."""
        from apps.plans.services_export_finance import build_action_finance, poste_entry_factory
        from collections import defaultdict
        op = plan_finance['op']
        op.ventilation_mode = 'none'
        op.save(update_fields=['ventilation_mode'])
        af = build_action_finance(op, {}, defaultdict(poste_entry_factory))
        assert af.is_org_ventilated is False


# ---------------------------------------------------------------------------
# Génération des classeurs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportWorkbooks:
    def _load(self, content):
        return load_workbook(io.BytesIO(content))

    def test_fiche_action(self, plan_finance):
        from apps.plans.services_export_fiche_action import build_fiche_action_workbook
        wb = self._load(build_fiche_action_workbook(plan_finance['plan']))
        assert 'CS01' in wb.sheetnames
        ws = wb['CS01']
        labels = [ws.cell(r, 1).value for r in range(1, ws.max_row + 1)]
        # variante CS
        assert any(l == "Indicateur d'état" for l in labels)
        # prévisionnel uniquement (#607 Q4) : pas de ligne « réalisée »
        assert not any('réalisée' in (l or '').lower() for l in labels)
        # prestataire dans les deux blocs (#607 Q2)
        assert any('prestataire — investissement' in (l or '').lower() for l in labels)

    def test_budget_previsionnel(self, plan_finance):
        from apps.plans.services_export_budget_rh import build_budget_previsionnel_workbook
        wb = self._load(build_budget_previsionnel_workbook(plan_finance['plan']))
        assert any('TOTAL par poste de dépense' == s for s in wb.sheetnames)
        # une feuille par organisme gestionnaire
        assert any('Org Alpha' in s for s in wb.sheetnames)

    def test_budget_suivi_a_colonnes_prevu_realise(self, plan_finance):
        from apps.plans.services_export_budget_rh import build_budget_suivi_workbook
        wb = self._load(build_budget_suivi_workbook(plan_finance['plan']))
        ws = next(wb[s] for s in wb.sheetnames if 'Org Alpha' in s)
        row4 = [ws.cell(4, c).value for c in range(1, ws.max_column + 1)]
        assert 'Prévu' in row4 and 'Réalisé' in row4

    def test_rh_previsionnel(self, plan_finance):
        from apps.plans.services_export_budget_rh import build_rh_previsionnel_workbook
        wb = self._load(build_rh_previsionnel_workbook(plan_finance['plan']))
        assert 'RH par type de poste' in wb.sheetnames
        # 10 jours prévus en 2024 pour l'action, colonne TOTAL = 10
        ws = next(wb[s] for s in wb.sheetnames if 'Org Alpha' in s)
        data_row = [ws.cell(4, c).value for c in range(1, ws.max_column + 1)]
        # #618 — colonne « Code action PG » = code local du plan (et non le
        # champ libre `code_operation`)
        assert 'CS1' in data_row

    def test_budget_suivi_totaux_fonct_invest(self, plan_finance):
        """#618 — sous-totaux Fonctionnement / Investissement sur la feuille TOTAL."""
        from apps.plans.services_export_budget_rh import build_budget_suivi_workbook
        wb = self._load(build_budget_suivi_workbook(plan_finance['plan']))
        ws = wb['Total par type de dépense']
        labels = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)}
        assert 'TOTAL Fonctionnement' in labels
        assert 'TOTAL Investissement' in labels
        # colonnes TOTAL (prévu / réalisé) en fin de feuille
        c_prev, c_real = ws.max_column - 1, ws.max_column
        # fonctionnement 2024 : 3000 (salarial) + 500 (presta) + 100 (autres)
        assert ws.cell(labels['TOTAL Fonctionnement'], c_prev).value == '3 600'
        # réalisé : 8 jours × 300 €/j
        assert ws.cell(labels['TOTAL Fonctionnement'], c_real).value == '2 400'
        # investissement 2024 : 200 (presta) + 50 (autres)
        assert ws.cell(labels['TOTAL Investissement'], c_prev).value == '250'
        assert ws.cell(labels['TOTAL Investissement'], c_real).value == '0'
        # cohérence avec le TOTAL général
        assert ws.cell(labels['TOTAL'], c_prev).value == '3 850'

    def test_rh_suivi(self, plan_finance):
        from apps.plans.services_export_budget_rh import build_rh_suivi_workbook
        wb = self._load(build_rh_suivi_workbook(plan_finance['plan']))
        assert 'Total par poste' in wb.sheetnames

    def test_word_et_arborescence(self, plan_finance):
        from apps.plans.services_export_word import build_plan_docx
        from apps.plans.services_export_arbo import build_presentation_workbook
        docx = build_plan_docx(plan_finance['plan'])
        assert docx[:2] == b'PK'      # conteneur zip Office
        wb = self._load(build_presentation_workbook(plan_finance['plan']))
        assert len(wb.sheetnames) >= 1


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportEndpoints:
    ENDPOINTS = [
        'export-arborescence-presentation-xlsx',
        'export-fiches-actions-xlsx',
        'export-plan-docx',
        'export-rh-previsionnel-xlsx',
        'export-rh-suivi-xlsx',
        'export-budget-previsionnel-xlsx',
        'export-budget-suivi-xlsx',
    ]

    def test_endpoints_return_file(self, api_client, plan_finance):
        api_client.force_authenticate(user=SuperAdminFactory())
        plan = plan_finance['plan']
        for ep in self.ENDPOINTS:
            resp = api_client.get(f'/api/plans/plans/{plan.id_pg}/{ep}/')
            assert resp.status_code == 200, ep
            assert resp['Content-Type'].startswith('application/vnd.openxmlformats'), ep
            content = b''.join(resp.streaming_content) if resp.streaming else resp.content
            assert content[:2] == b'PK', ep

    def test_endpoints_require_auth(self, api_client, plan_finance):
        plan = plan_finance['plan']
        resp = api_client.get(f'/api/plans/plans/{plan.id_pg}/export-budget-previsionnel-xlsx/')
        assert resp.status_code in (401, 403)
