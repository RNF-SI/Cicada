"""
#770 — import des actions : appariement du référentiel des types d'action de
la structure vers Gestref.

Décisions (Sophie 13/11, mainteneur) :
- le type de la structure arrive par une colonne du classeur ;
- l'appariement se saisit à l'import ;
- il est gardé par organisme (gestionnaire du plan) et réutilisé ;
- la colonne Gestref l'emporte quand elle est remplie.
"""
import io
import json

import pytest
from rest_framework import status

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans import referentiel_actions as ref
from apps.plans.models_referentiel import AppariementTypeAction
from apps.plans.services_import_actions import (
    _plan_operations,
    execute_actions_import,
    validate_actions_import,
)
from tests.factories.enjeux import (
    EnjeuFactory,
    IndicateurFactory,
    NiveauExigenceFactory,
    ObjectifLongTermeFactory,
)
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import (
    CorOgSiteFactory,
    OrganismeFactory,
    SiteFactory,
    SuperAdminFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _type(code, label):
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique=ref.TYPE_ACTION,
                                                  defaults={"label": ref.TYPE_ACTION})
    n, _ = Nomenclature.objects.update_or_create(
        id_type=t, cd_nomenclature=code, defaults={"mnemonique": code, "label": label, "actif": True})
    return n


def _plan(organisme):
    plan = PlanGestionFactory(statut="draft")
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=plan)))
    return plan, IndicateurFactory(id_ne=ne)


def _parsed(ind, *lignes):
    """``lignes`` : (type Gestref, type de la structure)."""
    return {
        "actions": [
            {"code": f"A{i}", "indicateur": "I1", "libelle": f"Action {i}", "_row": i + 1,
             "type_action": g, "type_action_structure": s}
            for i, (g, s) in enumerate(lignes, start=1)
        ],
        "indicateurs": {"I1": ind.id_indicateur},
    }


@pytest.fixture
def d():
    org = OrganismeFactory()
    plan, ind = _plan(org)
    return {"org": org, "plan": plan, "ind": ind, "user": SuperAdminFactory(),
            "fauche": _type("IP.2", "Entretien d'habitats"),
            "suivi": _type("CS.8.3", "Études de la végétation")}


def test_type_de_la_structure_sans_appariement_bloque_et_est_liste(d):
    parsed = _parsed(d["ind"], ("", "FAU-01"), ("", "fau-01 "), ("", "SUIVI VEG"))
    report = validate_actions_import(d["plan"], parsed, user=d["user"])
    assert not report.can_import
    erreurs = [e for e in report.errors if e["column"] == "type_action_structure"]
    assert [e["row"] for e in erreurs] == [2, 3, 4]
    corresp = report.as_dict()["appariements"]
    # Une ligne par valeur (casse et espaces ignorés), avec ses lignes.
    assert [(a["valeur"], a["lignes"], a["id_type_action"]) for a in corresp] == [
        ("FAU-01", [2, 3], None), ("SUIVI VEG", [4], None)]
    assert report.as_dict()["organisme_appariement"]["id"] == d["org"].pk


def test_appariement_saisi_puis_garde_pour_l_organisme(d):
    parsed = _parsed(d["ind"], ("", "FAU-01"), ("", "SUIVI VEG"))
    choix = {"FAU-01": d["fauche"].pk, "SUIVI VEG": d["suivi"].pk}
    assert validate_actions_import(d["plan"], parsed, choix, d["user"]).can_import

    counts = execute_actions_import(d["plan"], parsed, d["user"], choix)
    assert counts["appariements"] == 2
    ops = {op.code_operation: op for op in _plan_operations(d["plan"])}
    assert ops["A1"].id_type_action == d["fauche"]
    assert ops["A2"].id_type_action == d["suivi"]
    assert set(AppariementTypeAction.objects.filter(organisme=d["org"])
               .values_list("valeur", "id_type_action")) == {
        ("FAU-01", d["fauche"].pk), ("SUIVI VEG", d["suivi"].pk)}

    # Import suivant du même organisme : rien à ressaisir.
    plan2, ind2 = _plan(d["org"])
    report = validate_actions_import(plan2, _parsed(ind2, ("", "fau-01")), user=d["user"])
    assert report.can_import, report.errors
    assert report.as_dict()["appariements"][0]["origine"] == "enregistre"
    execute_actions_import(plan2, _parsed(ind2, ("", "fau-01")), d["user"])
    assert _plan_operations(plan2).get().id_type_action == d["fauche"]


def test_un_autre_organisme_ne_voit_pas_ces_appariements(d):
    AppariementTypeAction.objects.create(organisme=d["org"], valeur="FAU-01", cle="fau-01",
                                         id_type_action=d["fauche"])
    plan2, ind2 = _plan(OrganismeFactory())
    report = validate_actions_import(plan2, _parsed(ind2, ("", "FAU-01")), user=d["user"])
    assert not report.can_import


def test_choix_de_l_import_l_emporte_sur_l_appariement_garde(d):
    AppariementTypeAction.objects.create(organisme=d["org"], valeur="FAU-01", cle="fau-01",
                                         id_type_action=d["fauche"])
    parsed = _parsed(d["ind"], ("", "FAU-01"))
    execute_actions_import(d["plan"], parsed, d["user"], {"FAU-01": d["suivi"].pk})
    assert _plan_operations(d["plan"]).get().id_type_action == d["suivi"]
    assert AppariementTypeAction.objects.get(organisme=d["org"]).id_type_action == d["suivi"]


def test_la_colonne_gestref_l_emporte(d):
    """Type Gestref rempli : le type de la structure est ignoré, rien à apparier."""
    parsed = _parsed(d["ind"], ("IP.2 — Entretien d'habitats", "SUIVI VEG"))
    report = validate_actions_import(d["plan"], parsed, user=d["user"])
    assert report.can_import, report.errors
    assert report.as_dict()["appariements"] == []
    execute_actions_import(d["plan"], parsed, d["user"])
    assert _plan_operations(d["plan"]).get().id_type_action == d["fauche"]
    assert not AppariementTypeAction.objects.exists()


def test_api_champ_appariements(api_client, d):
    from apps.plans.services_import_actions import build_actions_workbook, parse_actions_workbook
    from openpyxl import load_workbook

    # Classeur réel : une action, type Gestref vide, type de la structure rempli.
    wb = load_workbook(io.BytesIO(build_actions_workbook(d["plan"])))
    ws = wb["Actions"]
    ligne_entete = next(r for r in ws.iter_rows() if r[0].value == "code")
    entetes = [c.value for c in ligne_entete]
    ligne = {e: None for e in entetes}
    ligne.update({"code": "A1", "indicateur": next(iter(parse_actions_workbook(
        build_actions_workbook(d["plan"]))["indicateurs"])), "libellé": "Fauche",
        "type d'action (référentiel de la structure)": "FAU-01"})
    ws.append([ligne[e] for e in entetes])
    buf = io.BytesIO()
    wb.save(buf)

    api_client.force_authenticate(user=d["user"])
    url = f"/api/plans/plans/{d['plan'].pk}/import-actions/validate/"
    buf.seek(0)
    resp = api_client.post(url, {"file": buf}, format="multipart")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["can_import"] is False
    assert resp.data["appariements"][0]["valeur"] == "FAU-01"

    buf.seek(0)
    resp = api_client.post(url, {"file": buf, "appariements": json.dumps({"FAU-01": d["fauche"].pk})},
                           format="multipart")
    assert resp.data["can_import"] is True, resp.data["issues"]
