"""
#790 — Montants par financeur (facultatifs) : financeurs du plan, montant
prévu global par action, montant réalisé par année (financeur non prévu
accepté), bilan prévu / réalisé et alerte d'écart avec le budget prévu.
"""
from decimal import Decimal

import pytest
from rest_framework import status

from apps.plans.models_operations import (
    FinanceOperation,
    Financeur,
    Operation,
    OperationAnnee,
    RealisationFinanceur,
)
from tests.factories.core import NomenclatureFactory
from tests.factories.enjeux import TypeNomenclatureFactory
from tests.integration.test_api_operations import operation_test_data  # noqa: F401

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _cat(label="Agence de l'eau"):
    type_nom = TypeNomenclatureFactory(mnemonique="CATEGORIE_FINANCE")
    return NomenclatureFactory(id_type=type_nom, mnemonique=label[:20], label=label)


@pytest.fixture
def donnees(operation_test_data):  # noqa: F811
    d = operation_test_data
    d["cat"] = _cat()
    d["agence"] = Financeur.objects.create(id_pg=d["plan"], nom="Agence RMC", id_categorie=d["cat"])
    d["region"] = Financeur.objects.create(id_pg=d["plan"], nom="Région",
                                           categorie_libre="Fonds régional spécial")
    return d


class TestFinanceursDuPlan:
    def test_liste_et_creation_avec_categorie_libre(self, api_client, donnees):
        api_client.force_authenticate(user=donnees["referent"])
        plan = donnees["plan"]
        r = api_client.get(f"/api/plans/financeurs/by-plan/{plan.id_pg}/")
        assert r.status_code == 200
        assert {f["nom"] for f in r.data} == {"Agence RMC", "Région"}
        region = next(f for f in r.data if f["nom"] == "Région")
        assert region["categorie_affichage"] == "Fonds régional spécial"

        r = api_client.post("/api/plans/financeurs/", {
            "id_pg": plan.id_pg, "nom": "Commune", "categorie_libre": "Mécénat local"},
            format="json")
        assert r.status_code == status.HTTP_201_CREATED, r.data
        # La catégorie libre reste propre au plan : aucune nomenclature créée.
        assert not type(donnees["cat"]).objects.filter(label="Mécénat local").exists()

    def test_meme_nom_meme_categorie_refuse(self, api_client, donnees):
        api_client.force_authenticate(user=donnees["referent"])
        r = api_client.post("/api/plans/financeurs/", {
            "id_pg": donnees["plan"].id_pg, "nom": "agence rmc",
            "id_categorie": donnees["cat"].id_nomenclature}, format="json")
        assert r.status_code == 400

    def test_meme_nom_autre_categorie_accepte(self, api_client, donnees):
        api_client.force_authenticate(user=donnees["referent"])
        r = api_client.post("/api/plans/financeurs/", {
            "id_pg": donnees["plan"].id_pg, "nom": "Agence RMC",
            "categorie_libre": "Autre"}, format="json")
        assert r.status_code == 201

    def test_utilisateur_hors_plan_ne_cree_pas(self, api_client, donnees):
        api_client.force_authenticate(user=donnees["user"])
        r = api_client.post("/api/plans/financeurs/", {
            "id_pg": donnees["plan"].id_pg, "nom": "Intrus"}, format="json")
        assert r.status_code in (403, 400)


class TestMontantsPrevus:
    def _creer(self, api_client, donnees, finances, budget="1000.00"):
        api_client.force_authenticate(user=donnees["referent"])
        r = api_client.post("/api/plans/operations/", {
            "libelle": "Restauration avec financeurs",
            "metrique_ids": [donnees["metrique1"].id_metrique],
            "operation_annees": [{"annee": 2024, "periodicite": True, "budget": budget}],
            "finances": finances,
        }, format="json")
        assert r.status_code == status.HTTP_201_CREATED, r.data
        return Operation.objects.get(libelle="Restauration avec financeurs")

    def test_montant_global_par_financeur(self, api_client, donnees):
        op = self._creer(api_client, donnees, [
            {"id_financeur": donnees["agence"].id_financeur, "montant": "600.00"},
            {"id_financeur": donnees["region"].id_financeur},  # montant facultatif
        ])
        lignes = {f.id_financeur.nom: f for f in op.finances.all()}
        assert lignes["Agence RMC"].montant == Decimal("600.00")
        assert lignes["Région"].montant is None
        # Copie du financeur, lue par les exports et l'exploration.
        assert lignes["Agence RMC"].libelle == "Agence RMC"
        assert lignes["Agence RMC"].id_categorie_id == donnees["cat"].id_nomenclature

    def test_financeur_saisi_par_son_nom_rejoint_celui_du_plan(self, api_client, donnees):
        op = self._creer(api_client, donnees, [
            {"libelle": "agence rmc", "id_categorie": donnees["cat"].id_nomenclature,
             "montant": "100"},
            {"libelle": "Département", "categorie_libre": "Conseil départemental"},
        ])
        agence = op.finances.get(libelle__iexact="agence rmc")
        assert agence.id_financeur_id == donnees["agence"].id_financeur
        dep = op.finances.get(libelle="Département")
        assert dep.id_financeur.categorie_libre == "Conseil départemental"
        assert dep.id_financeur.id_pg_id == donnees["plan"].id_pg

    def test_bilan_et_alerte_d_ecart(self, api_client, donnees):
        op = self._creer(api_client, donnees, [
            {"id_financeur": donnees["agence"].id_financeur, "montant": "600.00"},
        ])
        r = api_client.get(f"/api/plans/operations/{op.id_operation}/")
        bilan = r.data["financeurs_bilan"]
        assert bilan["total_prevu"] == "600.00"
        assert bilan["budget_prevu"] == "1000.00"
        # Q3 — alerte, jamais bloquante.
        assert bilan["ecart_budget"] is True


class TestMontantsRealises:
    def test_upsert_montants_annuels_et_financeur_non_prevu(self, api_client, donnees):
        op = donnees["op1"]
        FinanceOperation.objects.create(id_operation=op, id_financeur=donnees["agence"],
                                        libelle="Agence RMC", montant=Decimal("900"))
        oa = OperationAnnee.objects.create(id_operation=op, annee=2024, periodicite=True)
        api_client.force_authenticate(user=donnees["referent"])
        r = api_client.post("/api/plans/realisations/upsert/", {
            "id_operation_annee": oa.id_operation_annee,
            "financeurs": [
                {"id_financeur": donnees["agence"].id_financeur, "montant": "400.00"},
                # Non prévu par l'action : accepté, comme un poste non prévu.
                {"id_financeur": donnees["region"].id_financeur, "montant": "50.00"},
            ],
        }, format="json")
        assert r.status_code == 200, r.data
        assert {(f["id_financeur"], f["montant"]) for f in r.data["financeurs"]} == {
            (donnees["agence"].id_financeur, "400.00"), (donnees["region"].id_financeur, "50.00")}

        r = api_client.get(f"/api/plans/operations/{op.id_operation}/")
        par_nom = {l["nom"]: l for l in r.data["financeurs_bilan"]["lignes"]}
        assert par_nom["Agence RMC"]["prevu"] == "900.00"
        assert par_nom["Agence RMC"]["realise"] == "400.00"
        assert par_nom["Région"]["prevu"] is None and par_nom["Région"]["prevu_par_action"] is False
        assert par_nom["Région"]["realise_par_annee"] == {"2024": "50.00"}

    def test_financeur_d_un_autre_plan_refuse(self, api_client, donnees):
        from tests.factories.plans import PlanGestionFactory
        autre = Financeur.objects.create(id_pg=PlanGestionFactory(), nom="Ailleurs")
        oa = OperationAnnee.objects.create(id_operation=donnees["op1"], annee=2024)
        api_client.force_authenticate(user=donnees["referent"])
        r = api_client.post("/api/plans/realisations/upsert/", {
            "id_operation_annee": oa.id_operation_annee,
            "financeurs": [{"id_financeur": autre.id_financeur, "montant": "1"}],
        }, format="json")
        assert r.status_code == 400
        assert not RealisationFinanceur.objects.exists()

    def test_effacer_le_suivi_efface_les_montants(self, api_client, donnees):
        oa = OperationAnnee.objects.create(id_operation=donnees["op1"], annee=2024)
        api_client.force_authenticate(user=donnees["referent"])
        api_client.post("/api/plans/realisations/upsert/", {
            "id_operation_annee": oa.id_operation_annee,
            "financeurs": [{"id_financeur": donnees["agence"].id_financeur, "montant": "1"}],
        }, format="json")
        api_client.post("/api/plans/realisations/effacer/",
                        {"id_operation_annee": oa.id_operation_annee}, format="json")
        assert not RealisationFinanceur.objects.exists()


class TestExports:
    """#790 — fiches action (Excel / Word), fiche de suivi et budgets."""

    @pytest.fixture
    def op(self, donnees):
        op = donnees["op1"]
        self.annee = donnees["plan"].annee_debut
        oa = OperationAnnee.objects.create(id_operation=op, annee=self.annee, periodicite=True,
                                           budget=Decimal("1000"))
        FinanceOperation.objects.create(id_operation=op, id_financeur=donnees["agence"],
                                        libelle="Agence RMC", id_categorie=donnees["cat"],
                                        montant=Decimal("700"))
        from apps.plans.models_operations import RealisationOperationAnnee
        real = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationFinanceur.objects.create(id_realisation_operation_annee=real,
                                            id_financeur=donnees["agence"], montant=Decimal("450"))
        RealisationFinanceur.objects.create(id_realisation_operation_annee=real,
                                            id_financeur=donnees["region"], montant=Decimal("30"))
        return op

    @staticmethod
    def _textes(content):
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content))
        return wb, {ws.title: " | ".join(str(c.value) for row in ws.iter_rows() for c in row
                                         if c.value is not None) for ws in wb}

    def test_fiche_action_excel_et_word(self, donnees, op):
        from apps.plans.services_export_fiche_action import build_fiche_action_workbook
        from apps.plans.services_export_fiche_action_word import build_fiche_action_docx
        _wb, textes = self._textes(build_fiche_action_workbook(donnees["plan"], [op.id_operation]))
        texte = " ".join(textes.values())
        assert "Agence RMC — Agence de l'eau" in texte and "700" in texte
        # Q3 — écart avec le budget prévu (1 000 €) signalé.
        assert "diffère du budget prévu" in texte
        import io
        from docx import Document
        doc = Document(io.BytesIO(build_fiche_action_docx(donnees["plan"], [op.id_operation])))
        cellules = " ".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
        assert "Agence RMC" in cellules and "700" in cellules

    def test_fiche_de_suivi(self, donnees, op):
        from apps.plans.services_export_fiche_suivi import build_fiche_suivi_workbook
        _wb, textes = self._textes(build_fiche_suivi_workbook(donnees["plan"], self.annee))
        texte = " ".join(textes.values())
        assert "Financement par financeur" in texte
        assert "Région — Fonds régional spécial (non prévu)" in texte
        assert "450" in texte

    def test_onglet_par_financeur_des_budgets(self, donnees, op):
        from apps.plans.services_export_budget_rh import (
            build_budget_previsionnel_workbook, build_budget_suivi_workbook)
        wb, textes = self._textes(build_budget_previsionnel_workbook(donnees["plan"]))
        assert "Par financeur" in wb.sheetnames
        assert "Agence RMC" in textes["Par financeur"] and "Région" not in textes["Par financeur"]
        wb, textes = self._textes(build_budget_suivi_workbook(donnees["plan"]))
        assert f"Réalisé {self.annee}" in textes["Par financeur"]
        assert "450" in textes["Par financeur"]
        assert "Région (non prévu)" in textes["Par financeur"]


def test_nouvelle_version_rattachee_a_ses_propres_financeurs(donnees):
    """Une copie du plan (nouvelle version) garde les financements, rattachés
    aux financeurs de la copie — jamais à ceux du plan d'origine."""
    from apps.plans.services import PlanDuplicationService
    from tests.factories.plans import PlanGestionFactory
    FinanceOperation.objects.create(id_operation=donnees["op1"], id_financeur=donnees["agence"],
                                    libelle="Agence RMC", id_categorie=donnees["cat"],
                                    montant=Decimal("250"))
    copie = PlanGestionFactory()
    PlanDuplicationService.copy_content(donnees["plan"], copie, donnees["super_admin"])
    fin = FinanceOperation.objects.exclude(id_operation=donnees["op1"]).get(libelle="Agence RMC")
    assert fin.id_financeur.id_pg_id == copie.id_pg
    assert fin.montant == Decimal("250")
    assert fin.id_financeur.id_categorie_id == donnees["cat"].id_nomenclature
