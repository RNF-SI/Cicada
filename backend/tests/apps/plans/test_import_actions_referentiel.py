"""
#786 (retour 09/11) — un classeur d'actions écrit avec un autre référentiel
des types d'action que celui de l'instance (Eden 62 exporté, Gestref en
service) doit s'importer : 32 lignes étaient refusées (« Valeur « Suivi des
végétations » non reconnue pour « type d'action » »), le résolveur ne
cherchant que parmi les types **actifs**.

Règles, les mêmes qu'un passage de référentiel (#751 / #776) :
- type de la version en service : repris tel quel ;
- type d'une ancienne version, correspondance sûre ou probable : remplacé par
  son équivalent, avec un avertissement ; le changement reste modifiable ;
- correspondance à arbitrer : l'ancien type est **gardé** et l'action est
  « à actualiser » (équivalents proposés), avec un avertissement ;
- type inconnu de l'instance : erreur qui le dit.

L'export écrit désormais le **code** avec le libellé (« CS.8.3 — … ») : le code
reste lisible d'une version à l'autre, le libellé non.
"""
import csv
import json

import pytest

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans import referentiel_actions as ref
from apps.plans.models_operations import Operation, SuiviInventaire
from apps.plans.models_referentiel import PassageReferentielObjet
from apps.plans.services_import_actions import (
    _plan_operations,
    build_actions_workbook,
    execute_actions_import,
    parse_actions_workbook,
    validate_actions_import,
)
from tests.factories.enjeux import (
    EnjeuFactory,
    IndicateurFactory,
    NiveauExigenceFactory,
    ObjectifLongTermeFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _nom(type_mnemo, code, label, actif=True):
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique=type_mnemo,
                                                  defaults={"label": type_mnemo})
    n, _ = Nomenclature.objects.update_or_create(
        id_type=t, cd_nomenclature=code,
        defaults={"mnemonique": code, "label": label, "actif": actif})
    return n


@pytest.fixture
def gestref(tmp_path, monkeypatch):
    """Instance passée d'Eden 62 à une version de test : anciens types désactivés."""
    monkeypatch.setattr(ref, "DOSSIER_REFERENTIELS", tmp_path)
    eden = {
        "cs3": _nom(ref.TYPE_ACTION, "CS3", "Suivi des végétations"),
        "cs14": _nom(ref.TYPE_ACTION, "CS14", "Suivi des facteurs abiotiques"),
    }
    d = tmp_path / "test_v1"
    d.mkdir()
    (d / "version.json").write_text(json.dumps(
        {"code": "TEST_V1", "libelle": "Test V1", "depuis": "EDEN62"}), encoding="utf-8")
    with open(d / "referentiel.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([
            ["code", "libelle"], ["CS", "Connaissance"], ["CS.1", "Études des eaux"],
            ["CS.2", "Études des milieux physiques"], ["CS.8.3", "Études de la végétation"]])
    with open(d / "correspondance.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([
            ["ancien_code", "nouveau_code", "confiance", "options", "note"],
            ["CS3", "CS.8.3", "sure", "", ""],
            ["CS14", "CS.1", "a_arbitrer", "CS.1|CS.2", "Eaux ou milieux physiques"]])
    ref.appliquer(ref.charger_version("test_v1"), envoyer_email=False)
    for n in eden.values():
        n.refresh_from_db()
        assert not n.actif
    return eden


def _type(code):
    return Nomenclature.objects.get(id_type__mnemonique=ref.TYPE_ACTION, cd_nomenclature=code)


@pytest.fixture
def plan():
    plan = PlanGestionFactory(statut="draft")
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=plan)))
    ind = IndicateurFactory(id_ne=ne, nom_indicateur="Surface de prairies")
    return plan, ind


def _parsed(ind, *types):
    return {
        "actions": [
            {"code": f"A{i}", "indicateur": "I1", "libelle": f"Action {i}", "_row": i + 2,
             "type_action": t}
            for i, t in enumerate(types, start=1)
        ],
        "indicateurs": {"I1": ind.id_indicateur},
    }


def test_ancien_libelle_eden_converti_ou_garde_a_actualiser(gestref, plan):
    """Le cas du retour : un classeur exporté en Eden 62 (libellés nus) importé
    sur une instance passée à la nouvelle version."""
    plan, ind = plan
    parsed = _parsed(ind, "Suivi des végétations", "Suivi des facteurs abiotiques",
                     "Études des eaux")
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    msgs = [w["message"] for w in report.warnings if w["column"] == "type_action"]
    assert any("CS.8.3" in m and "remplacé" in m for m in msgs), msgs
    assert any("CS14" in m and "à actualiser" in m for m in msgs), msgs

    execute_actions_import(plan, parsed, SuperAdminFactory())
    ops = {op.code_operation: op for op in _plan_operations(plan)}
    assert ops["A1"].id_type_action == _type("CS.8.3")
    assert ops["A2"].id_type_action == gestref["cs14"]  # cohabitation (#776)
    assert ops["A3"].id_type_action == _type("CS.1")

    # Le changement automatique est consigné (modifiable) ; l'action à
    # arbitrer apparaît dans « Actions à actualiser », équivalents proposés.
    assert ref.objet_du_passage(ops["A1"]).statut == PassageReferentielObjet.STATUT_APPLIQUE
    attente = ref.objet_en_attente(ops["A2"])
    assert attente is not None
    assert attente.options == ["CS.1", "CS.2"]
    assert attente.plan == plan
    assert ref.objet_du_passage(ops["A3"]) is None


def test_code_prefixe_et_type_inconnu(gestref, plan):
    plan, ind = plan
    parsed = _parsed(ind, "CS3 — Suivi des végétations", "CS.2 — Études des milieux physiques",
                     "Type qui n'existe nulle part")
    report = validate_actions_import(plan, parsed)
    erreurs = [e for e in report.errors if e["column"] == "type_action"]
    assert [e["row"] for e in erreurs] == [5]
    assert "Test V1" in erreurs[0]["message"]

    parsed["actions"].pop()
    execute_actions_import(plan, parsed, SuperAdminFactory())
    ops = {op.code_operation: op for op in _plan_operations(plan)}
    assert ops["A1"].id_type_action == _type("CS.8.3")
    assert ops["A2"].id_type_action == _type("CS.2")


def test_suivi_d_une_action_cs_converti(gestref, plan):
    """L'onglet « Suivis » porte aussi un type d'action."""
    plan, ind = plan
    parsed = _parsed(ind, "Suivi des végétations")
    parsed["actions"][0]["suivi"] = "S1"
    parsed["suivis"] = [{"code": "S1", "_row": 3, "intitule": "Suivi de la végétation",
                         "id_type_action": "Suivi des végétations"}]
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, SuperAdminFactory())
    suivi = SuiviInventaire.objects.get(intitule="Suivi de la végétation")
    assert suivi.id_type_action == _type("CS.8.3")


def test_export_ecrit_le_code_et_se_reimporte(gestref, plan):
    plan, ind = plan
    execute_actions_import(plan, _parsed(ind, "CS.8.3", "CS14"), SuperAdminFactory())

    parsed = parse_actions_workbook(build_actions_workbook(plan))
    types = {a["code"]: a["type_action"] for a in parsed["actions"]}
    assert types["A1"] == "CS.8.3 — Études de la végétation"
    assert types["A2"] == "CS14 — Suivi des facteurs abiotiques"

    for op in _plan_operations(plan):
        op.delete()
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, SuperAdminFactory())
    ops = {op.code_operation: op for op in _plan_operations(plan)}
    assert ops["A1"].id_type_action == _type("CS.8.3")
    assert ops["A2"].id_type_action == gestref["cs14"]
    assert Operation.objects.filter(pk=ops["A2"].pk).exists()
    assert ref.objet_en_attente(ops["A2"]) is not None


def test_instance_sans_passage_libelle_et_code(plan):
    """Instance encore à sa version d'origine : rien ne change pour elle."""
    plan, ind = plan
    cs3 = _nom(ref.TYPE_ACTION, "CS3", "Suivi des végétations")
    parsed = _parsed(ind, "Suivi des végétations", "CS3 — Suivi des végétations")
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    assert not [w for w in report.warnings if w["column"] == "type_action"]
    execute_actions_import(plan, parsed, SuperAdminFactory())
    assert {op.id_type_action for op in _plan_operations(plan)} == {cs3}
