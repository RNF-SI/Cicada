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


@pytest.fixture
def plan_arbo():
    """Plan avec une arborescence complète (branche NE + branche OO/RA).

    - branche état : OLT → NE → indicateur d'état → métrique multi-blocs (#619)
      → action (sans `code_operation`, pour vérifier le code local du plan) ;
    - branche pression : facteur → pression → OO → RA → indicateur de pression
      → métrique.
    """
    from apps.plans.models_indicateurs import MetriqueScoreBlock
    from tests.factories.enjeux import (
        FacteurInfluenceFactory, IndicateurPressionFactory,
        ObjectifOperationnelFactory, PressionFactory, ResultatAttenduFactory,
    )

    plan = PlanGestionFactory(annee_debut=2024, annee_fin=2026)
    t_etat = _nomenclature('TYPE_INDICATEUR', 'ETAT', 'État')
    t_pression = _nomenclature('TYPE_INDICATEUR', 'PRESSION', 'Pression')
    cs = _nomenclature('CATEGORIE_ACTION_RESERVE', 'CS', 'Connaissance et suivi')

    enjeu = EnjeuFactory(id_pg=plan, etat_enjeu="État actuel de l'enjeu")

    # -- branche « vision à long terme »
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    ind = IndicateurFactory(id_ne=ne, type_indicateur=t_etat)
    met = MetriqueFactory(
        id_indicateur=ind, nom_metrique='Recouvrement', unite='%',
        bloc_intitule='Surface', sens_variation='CROISSANT',
        score_1_inf=0, score_1_sup=10, score_5_inf=90, score_5_sup=100,
    )
    bloc2 = MetriqueScoreBlock.objects.create(
        id_metrique=met, position=1, intitule='Hauteur', unite='cm',
        logical_op='AND', score_1_inf=0, score_1_sup=5,
        score_5_inf=50, score_5_sup=100,
    )
    op = OperationFactory(
        metriques=[met], id_categorie_action_reserve=cs,
        code_operation=None, numero_manuel=None,
    )

    # -- branche « stratégie d'action »
    facteur = FacteurInfluenceFactory(id_enjeu=enjeu, libelle='Fréquentation')
    pression = PressionFactory(id_facteur_influence=facteur, libelle='Piétinement')
    oo = ObjectifOperationnelFactory(pressions=[pression])
    ra = ResultatAttenduFactory(id_oo=oo)
    ind_p = IndicateurPressionFactory(id_resultat_attendu=ra, type_indicateur=t_pression)
    met_p = MetriqueFactory(id_indicateur=ind_p, nom_metrique='Sentiers', unite='m')

    return {
        'plan': plan, 'enjeu': enjeu, 'met': met, 'bloc2': bloc2,
        'op': op, 'met_pression': met_p,
    }


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
        assert 'CS01' in data_row

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
# Export arborescence « de présentation » (#619 / #620)
# ---------------------------------------------------------------------------

def _find_row(ws, label, col=1):
    """Numéro de la première ligne dont la cellule `col` vaut `label`."""
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, col).value == label:
            return r
    return None


def _row_values(ws, row):
    return [ws.cell(row, c).value for c in range(1, ws.max_column + 1)]


def _fill(ws, row, col):
    return ws.cell(row, col).fill.fgColor.rgb


@pytest.mark.django_db
class TestExportArborescencePresentation:
    """#619 / #620 — mise en forme et contenu du classeur d'arborescence."""

    def _sheet(self, plan):
        from apps.plans.services_export_arbo import build_presentation_workbook
        wb = load_workbook(io.BytesIO(build_presentation_workbook(plan)))
        return wb[wb.sheetnames[0]]

    # ---- #620 : colonnes et couleurs --------------------------------------

    def test_pas_de_colonne_niveau_exigence_en_face_des_facteurs(self, plan_arbo):
        """Le bloc bas commence par « Facteurs d'influence » (#620)."""
        ws = self._sheet(plan_arbo['plan'])
        b_h2 = _find_row(ws, "Facteurs d'influence")
        assert b_h2 is not None, "en-tête « Facteurs d'influence » absent"
        assert ws.cell(b_h2, 1).value == "Facteurs d'influence"
        assert ws.cell(b_h2, 2).value == "Pressions à gérer"
        # « Niveau d'exigence » ne subsiste que dans le bloc haut
        niveaux = [
            (r, c)
            for r in range(1, ws.max_row + 1)
            for c in range(1, 12)
            if (ws.cell(r, c).value or '') == "Niveau d'exigence"
        ]
        assert niveaux == [], f"colonne « Niveau d'exigence » résiduelle : {niveaux}"

    def test_couleurs_du_modele(self, plan_arbo):
        """Bandeaux bleu foncé, données « stratégie » en orange (#620)."""
        from apps.plans.services_export_arbo import (
            _C_ENJEU, _C_ETAT_DATA, _C_INFLU, _C_STRAT_DATA,
        )
        ws = self._sheet(plan_arbo['plan'])
        # bandeau « Influences sur l'enjeu » = même bleu foncé que « Enjeu »
        r_enjeu = _find_row(ws, "Enjeu")
        r_influ = _find_row(ws, "Influences sur l'enjeu")
        assert _fill(ws, r_enjeu, 1) == _C_ENJEU == _C_INFLU
        assert _fill(ws, r_influ, 1) == _C_INFLU
        # données facteur / pression : bleu clair (bloc « influences »), pas orange
        b_data = _find_row(ws, "Facteurs d'influence") + 1
        assert _fill(ws, b_data, 1) == _C_ETAT_DATA
        assert _fill(ws, b_data, 2) == _C_ETAT_DATA   # ancre de la fusion B:C
        # données « stratégie d'action » (objectifs opérationnels et suivantes) :
        # orange du modèle, plus rouge/rose
        assert _fill(ws, b_data, 4) == _C_STRAT_DATA
        assert _C_STRAT_DATA == 'FFFCD5B5', _C_STRAT_DATA

    # ---- #619 : grille de lecture et code action --------------------------

    def test_grille_a_une_colonne_unite(self, plan_arbo):
        """La grille de lecture porte une colonne « Unité » (#619)."""
        from apps.plans.services_export_arbo import GR_MET, GR_UNITE
        ws = self._sheet(plan_arbo['plan'])
        r = _find_row(ws, "Métriques", col=GR_MET)
        assert r is not None, "sous-en-tête « Métriques » de la grille absent"
        assert ws.cell(r, GR_UNITE).value == "Unité"
        # l'unité de la métrique apparaît en face de sa ligne
        unites = [ws.cell(rr, GR_UNITE).value
                  for rr in range(r + 1, r + 4)]
        assert '%' in unites, unites

    def test_grille_exporte_tous_les_blocs(self, plan_arbo):
        """Une métrique multi-blocs sort une ligne PAR bloc (#619).

        Auparavant seul le bloc principal était écrit.
        """
        from apps.plans.services_export_arbo import GR_MET, GR_UNITE
        ws = self._sheet(plan_arbo['plan'])
        r = _find_row(ws, "Métriques", col=GR_MET)
        libelles = [ws.cell(rr, GR_MET).value or '' for rr in range(r + 1, r + 5)]
        unites = [ws.cell(rr, GR_UNITE).value or '' for rr in range(r + 1, r + 5)]
        # bloc principal : nom de la métrique + intitulé du bloc, unité « % »
        assert any('Recouvrement' in v and 'Surface' in v for v in libelles), libelles
        # bloc complémentaire : intitulé + opérateur logique, unité « cm »
        assert any('Hauteur' in v and 'ET' in v for v in libelles), libelles
        assert '%' in unites and 'cm' in unites, unites

    def test_grille_haute_ne_recouvre_pas_le_bloc_bas(self, plan_arbo):
        """Une grille plus haute que ses données décale le bloc bas (#619)."""
        from apps.plans.models_indicateurs import MetriqueScoreBlock
        from apps.plans.services_export_arbo import GR_MET
        met = plan_arbo['met']
        for pos in range(2, 6):   # 4 blocs de plus → grille de 6 lignes
            MetriqueScoreBlock.objects.create(
                id_metrique=met, position=pos, intitule=f'Bloc {pos}',
                logical_op='OR', score_1_inf=0, score_1_sup=pos)
        ws = self._sheet(plan_arbo['plan'])
        r_influ = _find_row(ws, "Influences sur l'enjeu")
        r_grille_top = _find_row(ws, "Métriques", col=GR_MET) + 1
        # les 6 lignes de grille du bloc haut tiennent avant le bandeau bas
        assert r_influ >= r_grille_top + 6, (r_influ, r_grille_top)
        assert ws.cell(r_influ, GR_MET).value != 'Bloc 5'

    def test_code_action_est_le_code_local_du_plan(self, plan_arbo):
        """La colonne « Code » porte le code calculé du plan (CS1…) — #619.

        L'action de la fixture n'a ni `code_operation` ni `numero_manuel` :
        la colonne restait vide.
        """
        ws = self._sheet(plan_arbo['plan'])
        h2 = _find_row(ws, "Code", col=8)
        codes = [ws.cell(r, 8).value for r in range(h2 + 1, h2 + 4)]
        assert 'CS1' in codes, codes



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
