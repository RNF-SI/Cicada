"""Export « Planification annuelle » d'une année (#794).

Plan complet du filet d'intégrité : l'action PC-01 est ajustée l'année qui suit
(stage 4 500 € pour l'organisme A, 14 j de garde à 250 €, avril-mai, 2 500 € de
l'Agence de l'eau) ; le plan de gestion y prévoit 4 000 + 2 000 € de stage et
12 j (9 000 €).
"""
import io
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.plans.services_export_planification_annuelle import build_planification_annuelle_workbook
from tests.factories.users import RoleFactory
from tests.integrite.socle import construire_plan_complet

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def pc():
    return construire_plan_complet(statut='valide')


def _classeur(pc, annee):
    return load_workbook(io.BytesIO(build_planification_annuelle_workbook(pc.plan, annee)))


def _ligne(ws, libelle):
    for row in ws.iter_rows(min_row=4, values_only=True):
        if row[3] == libelle:
            return row
    raise AssertionError(f'ligne « {libelle} » absente de {ws.title}')


def test_onglets(pc):
    wb = _classeur(pc, pc.annee + 1)
    annee = pc.annee + 1
    assert wb.sheetnames[:2] == [f'Budget {annee}', f'Budget {annee} — Organisme A']
    assert {'RH ' + str(annee), 'Financeurs', 'Calendrier'} <= set(wb.sheetnames)


def test_budget_plan_ajuste_ecart(pc):
    annee = pc.annee + 1
    ws = _classeur(pc, annee)[f'Budget {annee}']
    ligne = _ligne(ws, 'Action PC-01')
    assert ligne[4] == 'Planifiée'
    assert [Decimal(str(v)) for v in ligne[5:8]] == [Decimal('9000'), Decimal('8000'), Decimal('-1000')]
    # Action programmée globalement : le plan la prévoit sur la période.
    globale = _ligne(ws, 'Action PC-02')
    assert 'sur la période' in globale[5]


def test_budget_par_organisme(pc):
    annee = pc.annee + 1
    ws = _classeur(pc, annee)[f'Budget {annee} — Organisme A']
    ligne = _ligne(ws, 'Action PC-01')
    # Organisme A : 4 000 € de stage + 12 j au plan ; 4 500 € + 14 j ajustés.
    assert [Decimal(str(v)) for v in ligne[5:7]] == [Decimal('7000'), Decimal('8000')]


def test_rh_financeurs_calendrier(pc):
    annee = pc.annee + 1
    wb = _classeur(pc, annee)
    rh = _ligne(wb[f'RH {annee}'], 'Action PC-01')
    assert [Decimal(str(v)) for v in rh[5:8]] == [Decimal('12'), Decimal('14'), Decimal('2')]
    fin = _ligne(wb['Financeurs'], 'Action PC-01')
    assert fin[4] == 'Agence de l’eau'
    assert [Decimal(str(v)) for v in fin[5:7]] == [Decimal('6000'), Decimal('2500')]
    cal = _ligne(wb['Calendrier'], 'Action PC-01')
    assert cal[5:17] == (None, None, None, '●', '●', None, None, None, None, None, None, None)


def test_annee_sans_ajustement_reprend_le_plan(pc):
    ws = _classeur(pc, pc.annee)[f'Budget {pc.annee}']
    ligne = _ligne(ws, 'Action PC-01')
    assert Decimal(str(ligne[5])) == Decimal(str(ligne[6])) and Decimal(str(ligne[7])) == 0


def test_route_reservee_aux_referents(pc):
    url = f'/api/plans/plans/{pc.plan.pk}/export-planification-annuelle-xlsx/'
    referent = APIClient()
    referent.force_authenticate(pc.referent)
    reponse = referent.get(url, {'annee': pc.annee + 1})
    assert reponse.status_code == 200
    assert 'planification-annuelle' in reponse['Content-Disposition']
    assert referent.get(url, {'annee': pc.annee + 9}).status_code == 400
    etranger = APIClient()
    etranger.force_authenticate(RoleFactory())
    assert etranger.get(url, {'annee': pc.annee + 1}).status_code in (403, 404)


def test_suivi_budgetaire_colonne_prevu_ajuste(pc):
    """Les exports de suivi gagnent une colonne « Prévu ajusté » (#794)."""
    from apps.plans.services_export_budget_rh import build_budget_suivi_workbook
    ws = load_workbook(io.BytesIO(build_budget_suivi_workbook(pc.plan)))['TOTAL']
    annee = str(pc.annee + 1)
    hdr = next(r for r in range(1, 6) if any(ws.cell(r, c).value == annee
                                            for c in range(1, ws.max_column + 1)))
    col = next(c for c in range(1, ws.max_column + 1) if ws.cell(hdr, c).value == annee)
    assert [ws.cell(hdr + 1, col + j).value for j in range(3)] == ['Prévu PG', 'Prévu ajusté', 'Réalisé']
    ligne = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 4).value == 'Action PC-01')
    assert [ws.cell(ligne, col + j).value for j in range(3)] == ['9 000', '8 000', '0']


def test_fiche_de_suivi_trois_colonnes(pc):
    from apps.plans.services_export_fiche_suivi import build_fiche_suivi_workbook
    wb = load_workbook(io.BytesIO(build_fiche_suivi_workbook(
        pc.plan, pc.annee + 1, operation_ids=[pc.action.pk])))
    rows = [[c.value for c in row] for row in wb.worksheets[0].iter_rows()]
    total = next(r for r in rows if r[0] == 'Total budget')
    # Rien de réalisé : « / », convention des fiches.
    assert (total[3], total[5], total[7]) == ('9 000 €', '8 000 €', '/')
    planif = next(r for r in rows if r[0] == 'Planification ajustée')
    assert any(isinstance(v, str) and f'Planifiée en {pc.annee + 1}' in v for v in planif)


def _lignes_detail(ws, libelle):
    """(détail, plan de gestion, ajusté, écart) des lignes d'une action."""
    return [(row[4], *row[5:8]) for row in ws.iter_rows(min_row=4, values_only=True)
            if row[3] == libelle]


def test_detail_budget_par_type_de_cout(pc):
    """Retour 13/11 : le détail du coût de chaque action (déclinaison par
    type de coût), plan de gestion / ajusté / écart."""
    annee = pc.annee + 1
    lignes = _lignes_detail(_classeur(pc, annee)[f'Détail budget {annee}'], 'Action PC-01')
    valeurs = {d: tuple(Decimal(str(v)) for v in (p, a, e)) for d, p, a, e in lignes}
    # 12 j × 250 € au plan, 14 j ajustés ; stage 4 000 + 2 000 € au plan, 4 500 € ajustés.
    assert valeurs['Coût salarial — fonctionnement'] == (Decimal('3000'), Decimal('3500'), Decimal('500'))
    assert valeurs['Coût stage — fonctionnement'] == (Decimal('6000'), Decimal('4500'), Decimal('-1500'))
    assert valeurs['Total action'] == (Decimal('9000'), Decimal('8000'), Decimal('-1000'))


def test_detail_rh_par_type_de_poste(pc):
    annee = pc.annee + 1
    lignes = _lignes_detail(_classeur(pc, annee)[f'Détail RH {annee}'], 'Action PC-01')
    valeurs = {d: tuple(Decimal(str(v)) for v in (p, a, e)) for d, p, a, e in lignes}
    assert valeurs['Garde technicien'] == (Decimal('12'), Decimal('14'), Decimal('2'))
    assert valeurs['Total action'] == (Decimal('12'), Decimal('14'), Decimal('2'))
