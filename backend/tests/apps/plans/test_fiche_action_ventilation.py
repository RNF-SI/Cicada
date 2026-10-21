"""
#735 (retour 21/10) — la fiche action exportée (Excel et Word) suit le
paramétrage de l'action :

- sans ventilation par type de budget, AUCUNE distinction fonctionnement /
  investissement (ni budget ni temps de travail) ;
- sans déclinaison par type de coût, pas de lignes de types de coût ;
- programmation globale : une seule colonne « Période … » pour le budget et le
  temps de travail, pas une colonne vide par année.
"""

import io
from decimal import Decimal

import pytest
from docx import Document
from openpyxl import load_workbook

from apps.plans.models_operations import (
    OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
)
from apps.plans.services_export_fiche_action import build_fiche_action_workbook
from apps.plans.services_export_fiche_action_word import build_fiche_action_docx
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory

ANNEES = (2028, 2029)


def _action(mode, *, detail, globale=False):
    """Action 2028-2029 : 1 000 € de stage, 500 € de prestataire, 200 € d'autres
    coûts et 10 j par ligne porteuse (ou un total de 1 700 € sans détail)."""
    plan = PlanGestionFactory(annee_debut=2027, annee_fin=2030, statut='draft')
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=plan)))
    op = OperationFactory(
        code_operation='ACT1', ventilation_mode=mode, declinaison_par_type_cout=detail,
        cout_salarial_auto=False, programmation_globale=globale,
        annee_min=2028, annee_max=2029,
    )
    op.metriques.add(MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=ne)))
    porteuses = []
    for annee in ANNEES:
        oa = OperationAnnee.objects.create(id_operation=op, annee=annee, periodicite=True)
        if not globale:
            porteuses.append(oa)
    if globale:
        porteuses.append(OperationAnnee.objects.create(id_operation=op, annee=None))

    org = OrganismeFactory(nom_organisme='Org Alpha') if mode in ('by_org', 'by_org_type') else None
    for oa in porteuses:
        montants = (
            dict(cout_salarial=Decimal('300'), cout_stage=Decimal('1000'),
                 cout_prestataire=Decimal('500'), autre_cout=Decimal('200'))
            if detail else
            (dict(budget_fonctionnement=Decimal('1200'), budget_investissement=Decimal('500'))
             if mode in ('by_type', 'by_org_type') else {})
        )
        if org:
            OperationAnneeOrganisme.objects.create(
                id_operation_annee=oa, id_organisme=org,
                **(montants or {'budget_fonctionnement': Decimal('1700')}))
        else:
            for k, v in (montants or {'budget': Decimal('1700')}).items():
                setattr(oa, k, v)
            oa.save()
        OperationAnneeRH.objects.create(
            id_operation_annee=oa, jours=10, categorie_depense='fonctionnement',
            id_organisme=org)
    return plan


def _xlsx(plan):
    """Lignes du volet financier : {libellé: [valeurs de la zone de données]}."""
    ws = load_workbook(io.BytesIO(build_fiche_action_workbook(plan)))['ACT1']
    debut = next(r for r in range(1, ws.max_row + 1)
                 if ws.cell(r, 1).value == 'Programmation annuelle')
    fin = next(r for r in range(debut, ws.max_row + 1)
               if ws.cell(r, 1).value == 'Programmation mensuelle')
    lignes = {}
    for r in range(debut, fin):
        label = ws.cell(r, 1).value
        if label:
            lignes[label] = [ws.cell(r, c).value for c in range(4, ws.max_column + 1)]
    return ws, lignes


def _docx_labels(plan):
    doc = Document(io.BytesIO(build_fiche_action_docx(plan)))
    table = next(t for t in doc.tables
                 if t.rows[0].cells[0].text in ('Budget prévisionnel',
                                                'Budget et temps de travail prévus'))
    return table, [row.cells[0].text for row in table.rows[1:]]


def _sans_distinction(labels):
    texte = ' '.join(labels).lower()
    return 'fonctionnement' not in texte and 'investissement' not in texte


@pytest.mark.django_db
class TestFicheActionSansTypeDeBudget:
    def test_aucune_ventilation_avec_declinaison(self):
        plan = _action('none', detail=True)
        _, lignes = _xlsx(plan)
        assert _sans_distinction(lignes)
        for label in ('Travail prévisionnel (jours)', 'Coût salarial', 'Coût stage',
                      'Coût prestataire', 'Autres coûts', 'Budget total (€)'):
            assert label in lignes, label
        assert lignes['Coût stage'][1:3] == ['1 000 €', '1 000 €']
        assert lignes['Autres coûts'][1:3] == ['200 €', '200 €']
        assert lignes['Budget total (€)'][1:3] == ['2 000 €', '2 000 €']
        _, labels = _docx_labels(plan)
        assert _sans_distinction(labels)
        assert 'Coût stage' in labels

    def test_aucune_ventilation_sans_declinaison(self):
        plan = _action('none', detail=False)
        _, lignes = _xlsx(plan)
        assert _sans_distinction(lignes)
        assert 'Coût salarial' not in lignes
        assert lignes['Budget total (€)'][1:3] == ['1 700 €', '1 700 €']
        assert lignes['Travail prévisionnel (jours)'][1:3] == ['10', '10']

    def test_par_organisme_avec_declinaison(self):
        plan = _action('by_org', detail=True)
        _, lignes = _xlsx(plan)
        assert _sans_distinction(lignes)
        assert any('Org Alpha' in label for label in lignes)
        assert lignes['Coût salarial'][1:3] == ['300 €', '300 €']
        _, labels = _docx_labels(plan)
        assert _sans_distinction(labels)

    def test_benevoles_absents_sans_jours(self):
        _, lignes = _xlsx(_action('none', detail=True))
        assert 'Jours bénévoles / partenaires' not in lignes


@pytest.mark.django_db
class TestFicheActionAvecTypeDeBudget:
    def test_avec_declinaison_detaille_le_stage(self):
        _, lignes = _xlsx(_action('by_type', detail=True))
        assert 'Coût stage — fonctionnement' in lignes
        assert lignes['Coût stage — fonctionnement'][1:3] == ['1 000 €', '1 000 €']
        # Le stage n'est plus compté dans les autres coûts.
        assert lignes['Autres coûts de fonctionnement'][1:3] == ['200 €', '200 €']
        assert 'Total Budget d\'investissement (€)' in lignes

    def test_sans_declinaison_enveloppes_seules(self):
        _, lignes = _xlsx(_action('by_type', detail=False))
        assert 'Coût salarial — fonctionnement' not in lignes
        assert 'Coût prestataire — investissement' not in lignes
        assert lignes['Total Budget de fonctionnement (€)'][1:3] == ['1 200 €', '1 200 €']
        assert lignes['Total Budget d\'investissement (€)'][1:3] == ['500 €', '500 €']
        assert lignes['Budget total (€)'][1:3] == ['1 700 €', '1 700 €']


@pytest.mark.django_db
class TestFicheActionGlobale:
    def test_une_seule_case_periode(self):
        plan = _action('by_org', detail=True, globale=True)
        ws, lignes = _xlsx(plan)
        assert _sans_distinction(lignes)
        # L'en-tête annuel ne porte que les années (périodicité par année).
        assert lignes['Programmation annuelle'][:4] == [2027, 2028, 2029, 2030]
        assert lignes['Budget et temps de travail prévus'][0] == 'Période 2028–2029'
        # Une seule valeur, fusionnée sur toute la zone de données.
        assert lignes['Budget total (€)'][0] == '2 000 €'
        assert all(v is None for v in lignes['Budget total (€)'][1:])
        r = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == 'Budget total (€)')
        assert any(m.min_row == r and m.min_col == 4 and m.max_col == ws.max_column
                   for m in ws.merged_cells.ranges)
        table, labels = _docx_labels(plan)
        assert [c.text for c in table.rows[0].cells] == [
            'Budget et temps de travail prévus', 'Période 2028–2029']
        assert _sans_distinction(labels)
