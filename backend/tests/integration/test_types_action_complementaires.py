"""
#792 — plusieurs types d'action Gestref par action.

Décisions (Sophie, 13/11) :
- Q1 → b : un type **principal** (inchangé : Bilan, totaux, code d'affichage,
  exports par catégorie) et des types **complémentaires** facultatifs ;
- Q2 → c : le libellé est obligatoire dès que l'action a plusieurs types ;
- Q3 → a : l'action porte un suivi dès qu'un de ses types est CS ;
- Q4 → a : seulement dans la fiche action (un suivi garde un seul type).
"""
import csv
import io
import json

import pytest
from rest_framework import status

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans import referentiel_actions as ref
from apps.plans.models_operations import CorOperationTypeAction, Operation
from tests.integration.test_api_operations import operation_test_data  # noqa: F401

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _nom(code, label, actif=True, mnemo=ref.TYPE_ACTION):
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique=mnemo, defaults={"label": mnemo})
    n, _ = Nomenclature.objects.update_or_create(
        id_type=t, cd_nomenclature=code,
        defaults={"mnemonique": code, "label": label, "actif": actif})
    return n


@pytest.fixture
def d(operation_test_data):  # noqa: F811
    d = operation_test_data
    d["ip"] = _nom("IP.2", "Entretien d'habitats")
    d["pa"] = _nom("PA.1", "Animation")
    d["cs"] = _nom("CS.8.3", "Études de la végétation")
    return d


def _post(api_client, d, **extra):
    api_client.force_authenticate(user=d["referent"])
    return api_client.post("/api/plans/operations/", {
        "id_indicateur": d["indicateur1"].id_indicateur, "id_type_action": d["ip"].pk, **extra,
    }, format="json")


class TestSaisie:
    def test_creation_lecture_et_ordre(self, api_client, d):
        resp = _post(api_client, d, libelle="Fauche et animation",
                     types_action_complementaires_ids=[d["pa"].pk])
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert [t["code"] for t in resp.data["types_action_complementaires"]] == ["PA.1"]
        op = Operation.objects.get(pk=resp.data["id_operation"])
        assert op.complementaires() == [d["pa"]]
        assert op.id_type_action == d["ip"]  # le principal ne bouge pas

    def test_libelle_obligatoire_des_plusieurs_types(self, api_client, d):
        """Q2 → c."""
        resp = _post(api_client, d, libelle="  ", types_action_complementaires_ids=[d["pa"].pk])
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "libelle" in resp.data

    def test_principal_et_doublons_ignores_autre_nomenclature_refusee(self, api_client, d):
        resp = _post(api_client, d, libelle="X",
                     types_action_complementaires_ids=[d["ip"].pk, d["pa"].pk, d["pa"].pk])
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert [t["code"] for t in resp.data["types_action_complementaires"]] == ["PA.1"]
        autre = _nom("P1", "Priorité", mnemo="PRIORITE_OPERATION")
        resp = _post(api_client, d, libelle="Y", types_action_complementaires_ids=[autre.pk])
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "types_action_complementaires_ids" in resp.data

    def test_modification_remplace_et_patch_sans_le_champ_garde(self, api_client, d):
        op_id = _post(api_client, d, libelle="X",
                      types_action_complementaires_ids=[d["pa"].pk]).data["id_operation"]
        url = f"/api/plans/operations/{op_id}/"
        assert api_client.patch(url, {"description": "z"}, format="json").status_code == 200
        assert Operation.objects.get(pk=op_id).complementaires() == [d["pa"]]
        resp = api_client.patch(url, {"types_action_complementaires_ids": []}, format="json")
        assert resp.status_code == 200, resp.data
        assert Operation.objects.get(pk=op_id).complementaires() == []

    def test_patch_qui_vide_le_libelle_avec_plusieurs_types_refuse(self, api_client, d):
        op_id = _post(api_client, d, libelle="X",
                      types_action_complementaires_ids=[d["pa"].pk]).data["id_operation"]
        resp = api_client.patch(f"/api/plans/operations/{op_id}/", {"libelle": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestSuivi:
    """Q3 → a — un type CS parmi les complémentaires suffit."""

    def test_complementaire_cs_porte_un_suivi_de_ce_type(self, api_client, d):
        resp = _post(api_client, d, libelle="Fauche et suivi",
                     types_action_complementaires_ids=[d["cs"].pk],
                     suivi_inventaire={"intitule": "Suivi de la fauche"})
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        op = Operation.objects.get(pk=resp.data["id_operation"])
        assert op.id_suivi is not None
        assert op.id_suivi.id_type_action == d["cs"]
        assert op.type_de_suivi() == d["cs"]

    def test_retirer_le_type_cs_detache_le_suivi(self, api_client, d):
        op_id = _post(api_client, d, libelle="Fauche et suivi",
                      types_action_complementaires_ids=[d["cs"].pk],
                      suivi_inventaire={"intitule": "Suivi"}).data["id_operation"]
        resp = api_client.patch(f"/api/plans/operations/{op_id}/",
                                {"types_action_complementaires_ids": [d["pa"].pk]}, format="json")
        assert resp.status_code == 200, resp.data
        assert Operation.objects.get(pk=op_id).id_suivi is None


def _op(d, *compl, libelle="Fauche et animation"):
    op = Operation.objects.create(id_indicateur=d["indicateur1"], libelle=libelle,
                                  id_type_action=d["ip"], id_utilisateur_ajout=d["referent"])
    for i, t in enumerate(compl):
        CorOperationTypeAction.objects.create(id_operation=op, id_type_action=t, ordre=i)
    return op


def test_nouvelle_version_du_plan_copie_les_types(d):
    from apps.plans.services import PlanDuplicationService
    op = _op(d, d["pa"])
    copie = PlanDuplicationService.build_version_plan(d["plan"], d["super_admin"],
                                                      nom="Copie", version="2")
    copie.save()
    PlanDuplicationService.copy_content(d["plan"], copie, d["super_admin"])
    nouvelle = Operation.objects.exclude(pk=op.pk).get(libelle=op.libelle)
    assert nouvelle.complementaires() == [d["pa"]]


def test_fiches_action_excel_et_word(d):
    from docx import Document
    from openpyxl import load_workbook

    from apps.plans.services_export_fiche_action import build_fiche_action_workbook
    from apps.plans.services_export_fiche_action_word import build_fiche_action_docx
    op = _op(d, d["pa"], d["cs"])
    wb = load_workbook(io.BytesIO(build_fiche_action_workbook(d["plan"], [op.pk])))
    texte = " | ".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value)
    assert "Types d'action complémentaires" in texte
    assert "PA.1 — Animation ; CS.8.3 — Études de la végétation" in texte
    doc = Document(io.BytesIO(build_fiche_action_docx(d["plan"], [op.pk])))
    cellules = " ".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert "PA.1 — Animation ; CS.8.3 — Études de la végétation" in cellules


def test_classeur_des_actions_aller_retour(d):
    from apps.plans.services_import_actions import (
        _plan_operations, build_actions_workbook, execute_actions_import,
        parse_actions_workbook, validate_actions_import)
    op = _op(d, d["pa"], d["cs"])
    parsed = parse_actions_workbook(build_actions_workbook(d["plan"]))
    ligne = next(a for a in parsed["actions"] if a["libelle"] == op.libelle)
    assert ligne["types_action_complementaires"] == \
        "PA.1 — Animation ; CS.8.3 — Études de la végétation"
    for o in _plan_operations(d["plan"]):
        o.delete()
    report = validate_actions_import(d["plan"], parsed)
    assert report.can_import, report.errors
    execute_actions_import(d["plan"], parsed, d["super_admin"])
    nouvelle = _plan_operations(d["plan"]).get(libelle="Fauche et animation")
    assert nouvelle.complementaires() == [d["pa"], d["cs"]]


def test_classeur_type_complementaire_inconnu(d):
    from apps.plans.services_import_actions import (
        build_actions_workbook, parse_actions_workbook, validate_actions_import)
    _op(d, d["pa"])
    parsed = parse_actions_workbook(build_actions_workbook(d["plan"]))
    parsed["actions"][0]["types_action_complementaires"] = "PA.1 ; Type qui n'existe pas"
    Operation.objects.all().delete()
    report = validate_actions_import(d["plan"], parsed)
    erreurs = [e for e in report.errors if e["column"] == "types_action_complementaires"]
    assert len(erreurs) == 1 and "Type qui n'existe pas" in erreurs[0]["message"]


def test_exploration_trouve_les_types_complementaires(d):
    from apps.search.indexing import construire_documents
    from apps.search.models import ContenuIndexe
    op = _op(d, d["pa"])
    doc = next(x for x in construire_documents(d["plan"])
               if x.type_contenu == ContenuIndexe.TYPE_ACTION and x.id_objet == op.pk)
    assert doc.codes_referentiel == ["TYPE_ACTION:IP.2", "TYPE_ACTION:PA.1"]


@pytest.fixture
def version(tmp_path, monkeypatch, d):
    """Instance qui passe à une version de test : PA1 → PA.1 sûre, CS14 à arbitrer."""
    monkeypatch.setattr(ref, "DOSSIER_REFERENTIELS", tmp_path)
    anciens = {"pa1": _nom("PA1", "Animation (Eden)"), "cs14": _nom("CS14", "Facteurs abiotiques")}
    for n in (d["ip"], d["pa"], d["cs"]):
        n.delete()
    v = tmp_path / "test_v1"
    v.mkdir()
    (v / "version.json").write_text(json.dumps(
        {"code": "TEST_V1", "libelle": "Test V1", "depuis": "EDEN62"}), encoding="utf-8")
    with open(v / "referentiel.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["code", "libelle"], ["PA", "Animation"], ["PA.1", "Animer"],
                                 ["CS", "Connaissance"], ["CS.1", "Eaux"], ["CS.2", "Milieux"]])
    with open(v / "correspondance.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["ancien_code", "nouveau_code", "confiance", "options", "note"],
                                 ["PA1", "PA.1", "sure", "", ""],
                                 ["CS14", "CS.1", "a_arbitrer", "CS.1|CS.2", ""]])
    return anciens


def test_passage_de_referentiel_convertit_chaque_type(d, version):
    op = Operation.objects.create(id_indicateur=d["indicateur1"], libelle="Action",
                                  id_utilisateur_ajout=d["referent"])
    CorOperationTypeAction.objects.create(id_operation=op, id_type_action=version["pa1"], ordre=0)
    CorOperationTypeAction.objects.create(id_operation=op, id_type_action=version["cs14"], ordre=1)
    definition = ref.charger_version("test_v1")
    ref.appliquer(definition, envoyer_email=False)
    codes = [t.cd_nomenclature for t in Operation.objects.get(pk=op.pk).complementaires()]
    # Sûre : remplacé ; à arbitrer : gardé, à remplacer dans la fiche action.
    assert codes == ["PA.1", "CS14"]
    ref.annuler(definition)
    codes = [t.cd_nomenclature for t in Operation.objects.get(pk=op.pk).complementaires()]
    assert codes == ["PA1", "CS14"]


def test_actualiser_le_type_principal_garde_le_suivi_d_un_complementaire_cs(d):
    """Q3 → a — le principal quitte CS, un complémentaire CS garde le suivi."""
    from apps.plans.models_operations import SuiviInventaire
    cs2 = _nom("CS.2", "Milieux physiques")
    suivi = SuiviInventaire.objects.create(intitule="Suivi", id_type_action=d["cs"],
                                           id_pg=d["plan"], id_utilisateur_ajout=d["referent"])
    op = _op(d, cs2)
    op.id_type_action = d["cs"]
    op.id_suivi = suivi
    op.save()
    ref.actualiser_type(op, d["pa"], d["referent"], type_attendu_id=d["cs"].pk)
    op.refresh_from_db()
    assert op.id_type_action == d["pa"]
    assert op.id_suivi == suivi
