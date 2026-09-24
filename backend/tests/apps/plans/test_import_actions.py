"""
Tests du module 2 (actions) de l'import Excel (#478).

Couvre la construction du classeur d'actions (onglet de référence des
indicateurs + onglet Actions), la validation (dry-run) et l'exécution
(création des opérations + programmation annuelle).
"""

import io
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from apps.plans.models_operations import (
    Operation,
    OperationAnnee,
    OperationAnneeRH,
    Poste,
    PosteFonction,
    Fonction,
)
from apps.plans.services_import_actions import (
    build_actions_workbook,
    build_actions_example_workbook,
    parse_actions_workbook,
    validate_actions_import,
    execute_actions_import,
    _all_settings,
    _plan_indicateurs,
    _parse_flat_sheet,
    _resolve_settings,
    _MODE_LABELS,
    _RH_HEADERS,
)
from apps.plans.models import CorSitePg
from apps.users.models import CorOgSite

from tests.factories.users import (
    OrganismeFactory,
    RoleFactory,
    SiteFactory,
    SuperAdminFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.enjeux import (
    EnjeuFactory,
    ObjectifLongTermeFactory,
    NiveauExigenceFactory,
    IndicateurFactory,
    MetriqueFactory,
    OperationFactory,
    TypeNomenclatureFactory,
)
from tests.factories.core import NomenclatureFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plan_with_indicateur(user):
    """Plan minimal avec un indicateur (branche état)."""
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    enjeu = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
    ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
    ind = IndicateurFactory(id_ne=ne, id_utilisateur_ajout=user)
    return plan, ind


def _type_action(label="Chantier CS8"):
    type_nom = TypeNomenclatureFactory(mnemonique="TYPE_ACTION")
    return NomenclatureFactory(id_type=type_nom, mnemonique="CS8", label=label)


def _add_poste(plan, libelle="Garde"):
    """Crée un poste (avec une fonction) rattaché au plan."""
    fonction, _ = Fonction.objects.get_or_create(libelle=libelle)
    poste = Poste.objects.create(id_pg=plan, nombre=1)
    PosteFonction.objects.create(id_poste=poste, id_fonction=fonction)
    return poste


def _parsed(ind_code, ind_id, **overrides):
    """Un jeu « actions » minimal valide."""
    action = {
        "code": "A1",
        "indicateur": ind_code,
        "libelle": "Débroussaillage",
        "annee_min": 2024,
        "annee_max": 2026,
        "_row": 3,
    }
    action.update(overrides)
    return {"actions": [action], "indicateurs": {ind_code: ind_id}}


# ---------------------------------------------------------------------------
# Construction du classeur
# ---------------------------------------------------------------------------


def test_build_actions_workbook_lists_indicateurs():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan=plan)))
    assert wb.sheetnames == [
        "Lisez-moi",
        "Indicateurs",
        "Postes",
        "Organismes",
        "Listes",
        "Actions",
        "Budgets",
        "RH",
    ]
    assert wb["Listes"].sheet_state == "hidden"
    # L'indicateur du plan est listé, avec son id technique.
    assert wb["Indicateurs"].cell(row=3, column=1).value == "I1"
    assert wb["Indicateurs"].cell(row=3, column=4).value == ind.id_indicateur


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_reads_reference_and_actions():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan=plan)))
    wb["Actions"].cell(row=3, column=1, value="A1")
    wb["Actions"].cell(row=3, column=2, value="I1")
    wb["Actions"].cell(row=3, column=3, value="Action test")
    buf = io.BytesIO()
    wb.save(buf)
    parsed = parse_actions_workbook(buf.getvalue())
    assert parsed["indicateurs"] == {"I1": ind.id_indicateur}
    assert len(parsed["actions"]) == 1
    assert parsed["actions"][0]["libelle"] == "Action test"


def test_parse_rejects_non_xlsx():
    from apps.plans.services_import import ArborescenceImportError

    with pytest.raises(ArborescenceImportError):
        parse_actions_workbook(b"pas un classeur")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_ok():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    report = validate_actions_import(plan, _parsed("I1", ind.id_indicateur))
    assert report.can_import, report.errors
    assert report.summary["actions"] == 1


def test_validate_refuses_plan_without_indicateurs():
    user = RoleFactory()
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    report = validate_actions_import(plan, {"actions": [], "indicateurs": {}})
    assert not report.can_import
    assert any("arborescence" in i["message"] for i in report.errors)


def test_validate_refuses_plan_with_existing_actions():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    OperationFactory(id_indicateur=ind, id_utilisateur_ajout=user)
    report = validate_actions_import(plan, _parsed("I1", ind.id_indicateur))
    assert not report.can_import
    assert any("déjà des actions" in i["message"] for i in report.errors)


def test_actions_rattachees_par_metrique():
    """Une action rattachée à l'indicateur par sa seule métrique (#398) est
    exportée sous le code de cet indicateur et bloque un nouvel import."""
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    metrique = MetriqueFactory(id_indicateur=ind, id_utilisateur_ajout=user)
    op = OperationFactory(id_indicateur=None, id_utilisateur_ajout=user)
    op.metriques.add(metrique)

    parsed = parse_actions_workbook(build_actions_workbook(plan))
    assert [a["indicateur"] for a in parsed["actions"]] == ["I1"]
    report = validate_actions_import(plan, _parsed("I1", ind.id_indicateur))
    assert any("déjà des actions" in i["message"] for i in report.errors)


def test_validate_missing_libelle():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    report = validate_actions_import(plan, _parsed("I1", ind.id_indicateur, libelle=""))
    assert not report.can_import
    assert any(i["column"] == "libelle" for i in report.errors)


def test_validate_unknown_indicateur_code():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = _parsed("I1", ind.id_indicateur)
    parsed["actions"][0]["indicateur"] = "I999"
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(i["column"] == "indicateur" for i in report.errors)


def test_validate_indicateur_not_in_plan():
    """Un id de référence qui n'appartient pas au plan est rejeté."""
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = _parsed("I1", ind.id_indicateur + 99999)
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any("n'appartient pas" in i["message"] for i in report.errors)


def test_validate_bad_year_order():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = _parsed("I1", ind.id_indicateur, annee_min=2028, annee_max=2024)
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(i["column"] == "annee_max" for i in report.errors)


def test_validate_unknown_type_action():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    _type_action()  # crée la nomenclature TYPE_ACTION (label « Chantier CS8 »)
    parsed = _parsed("I1", ind.id_indicateur, type_action="Type inexistant")
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(i["column"] == "type_action" for i in report.errors)


# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------


def test_execute_creates_operations_and_years():
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    type_action = _type_action()
    parsed = _parsed("I1", ind.id_indicateur, type_action=type_action.label)

    counts = execute_actions_import(plan, parsed, user)
    assert counts == {"actions": 1, "annees": 3, "budgets": 0, "rh": 0}

    op = Operation.objects.get(libelle="Débroussaillage")
    assert op.id_indicateur_id == ind.id_indicateur
    assert op.statut == "draft"
    assert op.id_type_action_id == type_action.id_nomenclature
    annees = set(
        OperationAnnee.objects.filter(id_operation=op).values_list("annee", flat=True)
    )
    assert annees == {2024, 2025, 2026}


def test_execute_refuses_when_invalid():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = _parsed("I1", ind.id_indicateur, libelle="")
    with pytest.raises(ValueError):
        execute_actions_import(plan, parsed, user)
    assert not Operation.objects.filter(id_indicateur=ind).exists()


# ---------------------------------------------------------------------------
# Budgets et RH (#560, #597, #600)
# ---------------------------------------------------------------------------


def _parsed_with_budget_rh(ind_code, ind_id, poste_code, poste_id):
    """Jeu actions + budgets + RH (parsé) valide, sans mode explicite."""
    return {
        "actions": [
            {
                "code": "A1",
                "indicateur": ind_code,
                "libelle": "Débroussaillage",
                "annee_min": 2024,
                "annee_max": 2026,
                "_row": 3,
            },
        ],
        "indicateurs": {ind_code: ind_id},
        "postes": {poste_code: poste_id},
        "budgets": [
            {
                "action": "A1",
                "annee": 2024,
                "budget_fonctionnement": "1000",
                "budget_investissement": "500",
                "_row": 3,
            },
        ],
        "rh": [
            {
                "action": "A1",
                "annee": 2024,
                "poste": poste_code,
                "jours": "10",
                "finance": "Oui",
                "_row": 3,
            },
        ],
    }


def _plan_with_organismes(user, n=2):
    """Plan avec un indicateur et un site géré par ``n`` organismes."""
    plan, ind = _plan_with_indicateur(user)
    site = SiteFactory()
    CorSitePg.objects.create(plan_de_gestion=plan, site=site)
    orgs = []
    for _ in range(n):
        org = OrganismeFactory()
        CorOgSite.objects.create(id_site=site, uuid_og=org)
        orgs.append(org)
    orgs.sort(key=lambda o: (o.nom_organisme or "").lower())
    return plan, ind, site, orgs


def _action(mode=None, **extra):
    row = {
        "code": "A1",
        "indicateur": "I1",
        "libelle": "Débroussaillage",
        "annee_min": 2024,
        "annee_max": 2025,
        "_row": 3,
    }
    if mode:
        row["mode_ventilation"] = _MODE_LABELS[mode]
    row.update(extra)
    return row


def _row(n, **values):
    return {"action": "A1", "annee": 2024, "_row": n, **values}


def test_build_actions_workbook_lists_postes():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    poste.cout_jour = Decimal("250")
    poste.save()
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan=plan)))
    assert {"Postes", "Organismes", "Budgets", "RH"} <= set(wb.sheetnames)
    ws = wb["Postes"]
    headers = [c.value for c in ws[2]]
    assert headers == [
        "code", "poste", "type de poste", "organisme", "coût jour (€)",
        "id (technique — ne pas modifier)",
    ]
    assert ws.cell(row=3, column=1).value == "Q1"
    assert ws.cell(row=3, column=2).value == "Garde"
    assert ws.cell(row=3, column=5).value == 250
    assert ws.cell(row=3, column=6).value == poste.id_poste
    assert parse_actions_workbook(build_actions_workbook(plan))["postes"] == {
        "Q1": poste.id_poste
    }


def test_postes_homonymes_numerotes_et_nom_local():
    """#611 / #632 — libellés de l'onglet Postes identiques à la fiche action."""
    user = RoleFactory()
    plan, _ind = _plan_with_indicateur(user)
    _add_poste(plan, "Garde")
    _add_poste(plan, "Garde")
    local = _add_poste(plan, "Garde")
    local.nom_local = "Garde du littoral"
    local.save()
    ws = load_workbook(io.BytesIO(build_actions_workbook(plan)))["Postes"]
    assert [ws.cell(row=r, column=2).value for r in (3, 4, 5)] == [
        "Garde 1", "Garde 2", "Garde du littoral",
    ]


def test_build_actions_workbook_lists_organismes():
    user = RoleFactory()
    plan, _ind, _site, orgs = _plan_with_organismes(user)
    parsed = parse_actions_workbook(build_actions_workbook(plan))
    assert parsed["organismes"] == {
        "O1": orgs[0].id_organisme, "O2": orgs[1].id_organisme,
    }


def test_execute_creates_budgets_and_rh():
    """Sans mode explicite : un poste → « + type de poste » ; seules les
    enveloppes sont saisies → sans déclinaison par type de coût."""
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = _parsed_with_budget_rh("I1", ind.id_indicateur, "Q1", poste.id_poste)

    counts = execute_actions_import(plan, parsed, user)
    assert counts == {"actions": 1, "annees": 3, "budgets": 1, "rh": 1}

    op = Operation.objects.get(libelle="Débroussaillage")
    assert op.ventilation_mode == "by_type_poste"
    assert op.declinaison_par_poste is True
    assert op.declinaison_par_type_cout is False

    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    assert oa.budget_fonctionnement == Decimal("1000")
    assert oa.budget_investissement == Decimal("500")
    assert oa.budget == Decimal("1500")
    assert oa.etp == Decimal("10")
    assert oa.periodicite is True

    rh = OperationAnneeRH.objects.get(id_operation_annee=oa)
    assert rh.id_poste_id == poste.id_poste
    assert rh.id_organisme_id is None
    assert rh.jours == Decimal("10")
    assert rh.finance is True
    assert rh.categorie_depense == "fonctionnement"


def test_execute_mode_none():
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, budget_total="900")],
        "rh": [_row(3, jours="4")],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, user)
    op = Operation.objects.get()
    assert op.ventilation_mode == "none" and op.declinaison_par_poste is False
    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    assert oa.budget == Decimal("900")
    assert oa.budget_fonctionnement is None
    rh = OperationAnneeRH.objects.get()
    assert rh.id_poste_id is None and rh.id_organisme_id is None
    assert rh.categorie_depense == "fonctionnement"


def test_execute_mode_by_org_links_sites():
    user = SuperAdminFactory()
    plan, ind, site, orgs = _plan_with_organismes(user)
    parsed = {
        "actions": [_action("by_org")],
        "indicateurs": {"I1": ind.id_indicateur},
        "organismes": {"O1": orgs[0].id_organisme, "O2": orgs[1].id_organisme},
        "budgets": [
            _row(3, organisme="O1", budget_total="2000"),
            _row(4, organisme="O2", budget_total="1000"),
        ],
        "rh": [
            _row(3, organisme="O1", jours="8"),
            _row(4, organisme="O1", jours="2",
                 categorie_depense="Bénévolat partenariat"),
            _row(5, organisme="O2", jours="5"),
        ],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, user)

    op = Operation.objects.get()
    assert op.ventilation_mode == "by_org"
    assert list(op.sites.values_list("id_site", flat=True)) == [site.id_site]
    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    lines = {o.id_organisme_id: o for o in oa.organismes.all()}
    assert lines[orgs[0].id_organisme].budget_fonctionnement == Decimal("2000")
    assert lines[orgs[0].id_organisme].etp == Decimal("10")
    assert lines[orgs[1].id_organisme].budget_fonctionnement == Decimal("1000")
    assert oa.budget == Decimal("3000")
    assert oa.etp == Decimal("15")
    benevolat = OperationAnneeRH.objects.get(jours=Decimal("2"))
    assert benevolat.finance is False
    assert benevolat.id_organisme_id == orgs[0].id_organisme


def test_execute_mode_by_org_type_poste_detail():
    """Ventilation maximale : détail des coûts par organisme, temps par poste,
    coût salarial calculé (jours × coût jour) dans le total de l'année."""
    user = SuperAdminFactory()
    plan, ind, _site, orgs = _plan_with_organismes(user)
    poste = _add_poste(plan)
    poste.cout_jour = Decimal("300")
    poste.id_organisme = orgs[0]
    poste.save()
    parsed = {
        "actions": [_action("by_org_type_poste")],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "organismes": {"O1": orgs[0].id_organisme},
        "budgets": [
            _row(3, organisme="O1", cout_prestataire="1500", autre_cout="200",
                 autre_cout_commentaire="Location", cout_prestataire_invest="700"),
        ],
        "rh": [
            _row(3, poste="Q1", jours="10"),
            _row(4, poste="Q1", jours="2", categorie_depense="Investissement"),
        ],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, user)

    op = Operation.objects.get()
    assert op.ventilation_mode == "by_org_type_poste"
    assert op.declinaison_par_poste is True
    assert op.declinaison_par_type_cout is True
    assert op.cout_salarial_auto is True
    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    oao = oa.organismes.get()
    assert oao.cout_prestataire == Decimal("1500")
    assert oao.autre_cout_commentaire == "Location"
    assert oao.cout_prestataire_invest == Decimal("700")
    assert oao.budget_fonctionnement is None and oao.budget_investissement is None
    # 1500 + 200 + 700 + (10 + 2) j × 300 €
    assert oa.budget == Decimal("6000")
    invest = OperationAnneeRH.objects.get(jours=Decimal("2"))
    assert invest.categorie_depense == "investissement" and invest.finance is True


def test_execute_mode_by_type_poste_salaire_saisi():
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = {
        "actions": [_action("by_type_poste", cout_salarial_auto="Non")],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "budgets": [_row(3, cout_salarial="3000", cout_stage="400")],
        "rh": [_row(3, poste="Q1", jours="10")],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, user)
    op = Operation.objects.get()
    assert op.cout_salarial_auto is False
    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    assert oa.cout_salarial == Decimal("3000") and oa.cout_stage == Decimal("400")
    assert oa.budget == Decimal("3400")


def test_mode_by_type_detail_stocke_le_salaire_saisi():
    """« Par type de budget » avec détail : rien à calculer, le coût salarial
    est saisi (``salaryIsComputed`` → False), comme dans la fiche action."""
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("by_type")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, cout_salarial="1200", autre_cout="100")],
    }
    execute_actions_import(plan, parsed, user)
    op = Operation.objects.get()
    assert op.declinaison_par_type_cout is True
    assert op.cout_salarial_auto is False
    oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
    assert oa.cout_salarial == Decimal("1200") and oa.budget == Decimal("1300")


def test_poste_non_finance_par_defaut():
    """Catégorie vide : déduite du caractère financé du poste (bénévole)."""
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    fonction, _ = Fonction.objects.get_or_create(
        libelle="Bénévole (test import)", defaults={"finance_par_defaut": False}
    )
    poste = Poste.objects.create(id_pg=plan, nombre=1)
    PosteFonction.objects.create(id_poste=poste, id_fonction=fonction)
    parsed = {
        "actions": [_action()],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "rh": [_row(3, poste="Q1", jours="6")],
    }
    execute_actions_import(plan, parsed, user)
    rh = OperationAnneeRH.objects.get()
    assert rh.categorie_depense == "benevolat_partenariat" and rh.finance is False


@pytest.mark.parametrize(
    "mode, budget, message",
    [
        ("none", {"budget_fonctionnement": "10"}, "budget fonctionnement"),
        ("by_type", {"budget_total": "10"}, "budget total"),
        ("by_type_poste", {"cout_salarial": "10"}, "coût salarial"),
    ],
)
def test_validate_colonne_hors_mode(mode, budget, message):
    """Un montant hors des colonnes du mode serait invisible : erreur. (Coût
    salarial saisi alors que la saisie automatique est demandée.)"""
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action(mode, cout_salarial_auto="Oui")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, **budget)],
    }
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(
        i["sheet"] == "Budgets" and message in i["message"] for i in report.errors
    )


def test_validate_cibles_selon_le_mode():
    user = RoleFactory()
    plan, ind, _site, orgs = _plan_with_organismes(user)
    poste = _add_poste(plan)
    parsed = {
        "actions": [_action("by_org_type")],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "organismes": {"O1": orgs[0].id_organisme},
        "budgets": [_row(3, budget_fonctionnement="10")],  # organisme manquant
        "rh": [_row(3, poste="Q1", jours="2")],  # poste inattendu, org manquant
    }
    report = validate_actions_import(plan, parsed)
    cols = {(i["sheet"], i["column"]) for i in report.errors}
    assert ("Budgets", "organisme") in cols
    assert ("RH", "poste") in cols
    assert ("RH", "organisme") in cols


def test_validate_organisme_hors_plan():
    user = RoleFactory()
    plan, ind, _site, _orgs = _plan_with_organismes(user)
    etranger = OrganismeFactory()
    parsed = {
        "actions": [_action("by_org")],
        "indicateurs": {"I1": ind.id_indicateur},
        "organismes": {"O9": etranger.id_organisme},
        "budgets": [_row(3, organisme="O9", budget_total="10")],
    }
    report = validate_actions_import(plan, parsed)
    assert any("n'appartient pas" in i["message"] for i in report.errors)


def test_validate_investissement_sans_type_de_budget():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none")],
        "indicateurs": {"I1": ind.id_indicateur},
        "rh": [_row(3, jours="2", categorie_depense="Investissement")],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import  # conservée, comme dans la fiche action
    assert any(
        i["column"] == "categorie_depense" and i["level"] == "warning"
        for i in report.issues
    )


def test_validate_mode_et_categorie_inconnus():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action(mode_ventilation="Au hasard",
                            declinaison_par_type_cout="Peut-être")],
        "indicateurs": {"I1": ind.id_indicateur},
        "rh": [_row(3, jours="2", categorie_depense="Divers")],
    }
    report = validate_actions_import(plan, parsed)
    cols = {i["column"] for i in report.errors}
    assert {"mode_ventilation", "declinaison_par_type_cout", "categorie_depense"} <= cols


def test_validate_budget_en_double():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, budget_total="10"), _row(4, budget_total="20")],
    }
    report = validate_actions_import(plan, parsed)
    assert any("double" in i["message"] for i in report.errors)


@pytest.mark.parametrize(
    "budgets, rh, expected",
    [
        ([], [], ("none", True)),
        ([{"budget_total": "1"}], [], ("none", True)),
        ([{"organisme": "O1", "budget_total": "1"}], [], ("by_org", True)),
        ([{"budget_fonctionnement": "1"}], [], ("by_type", False)),
        ([{"cout_stage": "1"}], [], ("by_type", True)),
        ([{"organisme": "O1", "budget_investissement": "1"}], [],
         ("by_org_type", False)),
        ([], [{"poste": "Q1"}], ("by_type_poste", True)),
        ([{"organisme": "O1", "cout_prestataire": "1"}], [{"poste": "Q1"}],
         ("by_org_type_poste", True)),
        ([], [{"categorie_depense": "Investissement"}], ("by_type", True)),
    ],
)
def test_deduction_du_mode(budgets, rh, expected):
    settings = _resolve_settings(_action(), budgets, rh)
    assert (settings["mode"], settings["detail"]) == expected


def test_roundtrip_budget_rh_via_workbook():
    """Injection dans le classeur généré puis import de bout en bout."""
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    _add_poste(plan)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan=plan)))
    ind_code = wb["Indicateurs"].cell(row=3, column=1).value
    poste_code = wb["Postes"].cell(row=3, column=1).value
    _fill(wb["Actions"], code="A1", indicateur=ind_code, **{
        "libellé": "Action", "année début": 2024, "année fin": 2024,
        "mode de ventilation": _MODE_LABELS["by_type_poste"],
        "déclinaison par type de coût": "Non",
    })
    _fill(wb["Budgets"], action="A1", **{
        "année": 2024, "budget fonctionnement (€)": 800,
    })
    _fill(wb["RH"], action="A1", poste=poste_code, jours=5, **{
        "année": 2024, "catégorie de dépense": "Bénévolat partenariat",
    })
    buf = io.BytesIO()
    wb.save(buf)

    parsed = parse_actions_workbook(buf.getvalue())
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    counts = execute_actions_import(plan, parsed, user)
    assert counts["budgets"] == 1 and counts["rh"] == 1

    rh_line = OperationAnneeRH.objects.get()
    assert rh_line.finance is False and rh_line.jours == Decimal("5")
    assert rh_line.categorie_depense == "benevolat_partenariat"


def test_export_puis_reimport_conserve_le_parametrage():
    """Le classeur exporté d'un plan se réimporte à l'identique dans un autre
    plan (mêmes postes / organismes → mêmes codes)."""
    user = SuperAdminFactory()
    plan, ind, _site, orgs = _plan_with_organismes(user)
    poste = _add_poste(plan)
    poste.cout_jour = Decimal("100")
    poste.save()
    parsed = {
        "actions": [_action("by_org_type_poste", cout_salarial_auto="Non")],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "organismes": {"O1": orgs[0].id_organisme, "O2": orgs[1].id_organisme},
        "budgets": [
            _row(3, organisme="O1", cout_salarial="500", cout_stage="50"),
            _row(4, organisme="O2", autre_cout_invest="70",
                 autre_cout_invest_commentaire="Clôture"),
        ],
        "rh": [_row(3, poste="Q1", jours="3", categorie_depense="Investissement")],
    }
    execute_actions_import(plan, parsed, user)

    exported = parse_actions_workbook(build_actions_workbook(plan))
    action = exported["actions"][0]
    assert action["mode_ventilation"] == _MODE_LABELS["by_org_type_poste"]
    assert action["declinaison_par_type_cout"] == "Oui"
    assert action["cout_salarial_auto"] == "Non"
    budgets = {b["organisme"]: b for b in exported["budgets"]}
    assert Decimal(str(budgets["O1"]["cout_salarial"])) == Decimal("500")
    assert budgets["O2"]["autre_cout_invest_commentaire"] == "Clôture"
    assert exported["rh"][0]["categorie_depense"] == "Investissement"
    assert exported["rh"][0]["poste"] == "Q1"
    # Le classeur exporté est lui-même valide (hors refus « plan déjà rempli »).
    report = validate_actions_import(plan, exported)
    assert [i for i in report.errors if i["sheet"]] == []


def _fill(ws, **values):
    """Écrit une ligne (ligne 3, à la place de la ligne exemple) en ciblant les
    colonnes par leur en-tête."""
    headers = {c.value: c.column for c in ws[2]}
    for col in headers.values():
        ws.cell(row=3, column=col).value = None
    for header, value in values.items():
        ws.cell(row=3, column=headers[header], value=value)


def test_classeur_ancien_format_financé():
    """Un classeur antérieur à #597 (colonne « financé ? ») reste lisible."""
    from openpyxl import Workbook

    ws = Workbook().active
    for c, h in enumerate(["action", "année", "poste", "jours", "financé ?"], 1):
        ws.cell(row=2, column=c, value=h)
    for c, v in enumerate(["A1", 2024, "Q1", 4, "Non"], 1):
        ws.cell(row=3, column=c, value=v)
    rows = _parse_flat_sheet(ws, _RH_HEADERS)
    assert rows[0]["finance"] == "Non" and rows[0]["poste"] == "Q1"


def test_validate_rh_unknown_poste():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = _parsed_with_budget_rh("I1", ind.id_indicateur, "Q1", poste.id_poste)
    parsed["rh"][0]["poste"] = "Q999"  # code de poste inexistant
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(i["sheet"] == "RH" and i["column"] == "poste" for i in report.errors)


def test_validate_budget_negative():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = _parsed_with_budget_rh("I1", ind.id_indicateur, "Q1", poste.id_poste)
    parsed["budgets"][0]["budget_fonctionnement"] = "-100"
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(
        i["sheet"] == "Budgets" and "négatif" in i["message"] for i in report.errors
    )


def test_validate_budget_unknown_action():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = _parsed_with_budget_rh("I1", ind.id_indicateur, "Q1", 1)
    parsed["budgets"][0]["action"] = "A999"
    report = validate_actions_import(plan, parsed)
    assert not report.can_import
    assert any(
        i["sheet"] == "Budgets" and i["column"] == "action" for i in report.errors
    )


def test_validate_budget_year_outside_span_is_warning():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = _parsed_with_budget_rh("I1", ind.id_indicateur, "Q1", poste.id_poste)
    parsed["budgets"][0]["annee"] = 2099  # hors [2024, 2026]
    report = validate_actions_import(plan, parsed)
    assert report.can_import  # avertissement, pas erreur
    assert any(
        i["level"] == "warning" and i["sheet"] == "Budgets" for i in report.issues
    )


# ---------------------------------------------------------------------------
# Listes déroulantes inter-onglets, ligne exemple, classeur exemple
# ---------------------------------------------------------------------------


def test_budgets_rh_have_action_dropdown():
    """Les onglets Budgets et RH proposent la liste des codes d'actions."""
    user = SuperAdminFactory()
    plan, _ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan)))

    def _formulas(sheet):
        return [dv.formula1 for dv in wb[sheet].data_validations.dataValidation]

    # La colonne « action » de Budgets et de RH pointe vers l'onglet Actions.
    assert any("Actions" in f for f in _formulas("Budgets"))
    assert any("Actions" in f for f in _formulas("RH"))


def test_actions_hint_rows_ignored_on_parse():
    """La ligne exemple des onglets Actions/Budgets/RH n'est pas importée."""
    user = SuperAdminFactory()
    plan, _ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan)))
    # Une ligne exemple grisée est présente en L3.
    assert wb["Actions"].cell(row=3, column=1).value == "(exemple)"
    assert wb["Budgets"].cell(row=3, column=1).value == "(exemple)"
    assert wb["RH"].cell(row=3, column=1).value == "(exemple)"
    # …mais le parse d'un modèle vide ne renvoie aucune donnée.
    parsed = parse_actions_workbook(build_actions_workbook(plan))
    assert parsed["actions"] == []
    assert parsed["budgets"] == []
    assert parsed["rh"] == []


def test_actions_example_workbook_full_structure():
    """L'exemple d'actions téléchargeable est complet et cohérent."""
    parsed = parse_actions_workbook(build_actions_example_workbook())
    assert len(parsed["actions"]) == 3
    assert len(parsed["budgets"]) == 5
    assert len(parsed["rh"]) == 6
    assert set(parsed["postes"]) == {"Q1", "Q2", "Q3"}
    assert set(parsed["organismes"]) == {"O1", "O2"}
    # Le paramétrage déclaré de chaque action est cohérent avec ses lignes :
    # aucune erreur de mode ne doit apparaître dans l'exemple.
    settings = _all_settings(parsed)
    assert {c: s["mode"] for c, s in settings.items()} == {
        "A1": "by_type_poste", "A2": "by_type", "A3": "by_org",
    }
    # Indicateurs de référence disponibles pour le rattachement des actions.
    assert len(parsed["indicateurs"]) == 3
    # Chaque action référence un indicateur listé en référence.
    for action in parsed["actions"]:
        assert action["indicateur"] in parsed["indicateurs"]


# ---------------------------------------------------------------------------
# Aller-retour export → import, un cas par mode de ventilation (#600)
# ---------------------------------------------------------------------------


def _snapshot(plan):
    """Tout ce que l'import écrit, indépendamment des identifiants."""
    from apps.plans.services_import_actions import _plan_operations

    snap = {}
    for op in _plan_operations(plan):
        years = {}
        for oa in op.operation_annees.all():
            orgs = sorted(
                (
                    o.id_organisme_id, o.budget_fonctionnement,
                    o.budget_investissement, o.cout_salarial, o.cout_salarial_invest,
                    o.cout_stage, o.cout_prestataire, o.autre_cout,
                    o.autre_cout_commentaire, o.cout_prestataire_invest,
                    o.autre_cout_invest, o.autre_cout_invest_commentaire, o.etp,
                )
                for o in oa.organismes.all()
            )
            rh = sorted(
                (str(r.id_poste_id), str(r.id_organisme_id), r.jours,
                 r.categorie_depense, r.finance)
                for r in oa.rh_lignes.all()
            )
            years[oa.annee] = (
                oa.budget, oa.etp, oa.periodicite, oa.budget_fonctionnement,
                oa.budget_investissement, oa.cout_salarial, oa.cout_salarial_invest,
                oa.cout_stage, oa.cout_prestataire, oa.autre_cout,
                oa.autre_cout_commentaire, oa.cout_prestataire_invest,
                oa.autre_cout_invest, oa.autre_cout_invest_commentaire, orgs, rh,
            )
        snap[op.code_operation] = (
            op.ventilation_mode, op.declinaison_par_poste,
            op.declinaison_par_type_cout, op.cout_salarial_auto,
            sorted(op.sites.values_list("id_site", flat=True)), years,
        )
    return snap


# (action, budgets, rh) — codes O1/O2 = organismes, Q1/Q2 = postes.
_MODE_CASES = {
    "none": (
        {},
        [_row(3, budget_total="900"), _row(4, annee=2025, budget_total="0")],
        [_row(3, jours="4")],
    ),
    "by_org": (
        {},
        [_row(3, organisme="O1", budget_total="2000")],
        [_row(3, organisme="O1", jours="8"), _row(4, organisme="O2", jours="3",
                                                    categorie_depense="Bénévolat partenariat")],
    ),
    "by_type": (
        {"declinaison_par_type_cout": "Non"},
        [_row(3, budget_fonctionnement="800", budget_investissement="1200")],
        [_row(3, jours="5", categorie_depense="Investissement")],
    ),
    "by_org_type": (
        {},
        [_row(3, organisme="O1", cout_salarial="1000", autre_cout="50",
              autre_cout_commentaire="Carburant"),
         _row(4, organisme="O2", cout_prestataire_invest="400")],
        [_row(3, organisme="O2", jours="2")],
    ),
    "by_type_poste": (
        {},
        [_row(3, cout_stage="300", cout_prestataire="1500")],
        [_row(3, poste="Q1", jours="6"), _row(4, poste="Q2", jours="10")],
    ),
    "by_org_type_poste": (
        {"cout_salarial_auto": "Non"},
        [_row(3, organisme="O1", cout_salarial="1800", cout_salarial_invest="200"),
         _row(4, organisme="O2", autre_cout_invest="70",
              autre_cout_invest_commentaire="Clôture")],
        [_row(3, poste="Q1", jours="6", categorie_depense="Investissement")],
    ),
}


@pytest.mark.parametrize("mode", list(_MODE_CASES))
def test_aller_retour_par_mode(mode):
    """Un classeur exporté puis réimporté restitue exactement les mêmes
    données, pour chacun des 6 modes de ventilation."""
    user = SuperAdminFactory()
    plan, ind, _site, orgs = _plan_with_organismes(user)
    salarie = _add_poste(plan, "Garde")
    salarie.cout_jour, salarie.id_organisme = Decimal("300"), orgs[0]
    salarie.save()
    fonction, _ = Fonction.objects.get_or_create(
        libelle="Bénévole (test import)", defaults={"finance_par_defaut": False}
    )
    benevole = Poste.objects.create(id_pg=plan, nombre=4, cout_jour=Decimal("0"))
    PosteFonction.objects.create(id_poste=benevole, id_fonction=fonction)

    extra, budgets, rh = _MODE_CASES[mode]
    parsed = {
        "actions": [_action(mode, **extra)],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": salarie.id_poste, "Q2": benevole.id_poste},
        "organismes": {"O1": orgs[0].id_organisme, "O2": orgs[1].id_organisme},
        "budgets": budgets,
        "rh": rh,
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    assert [i for i in report.issues if i["level"] == "warning"] == []
    execute_actions_import(plan, parsed, user)
    before = _snapshot(plan)
    assert before["A1"][0] == mode

    content = build_actions_workbook(plan)
    Operation.objects.filter(id_indicateur__in=[ind]).delete()
    reparsed = parse_actions_workbook(content)
    report = validate_actions_import(plan, reparsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, reparsed, user)

    assert _snapshot(plan) == before


# ---------------------------------------------------------------------------
# Règles partagées avec la fiche action (operation-budget.ts)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode, detail, auto, computed, layout",
    [
        # Sans type de budget : rien à détailler, valeur historique « calculé ».
        ("none", True, False, True, "total"),
        ("by_org", True, False, True, "total"),
        # Type de budget sans poste : détail → coût salarial toujours saisi.
        ("by_type", True, True, False, "detail"),
        ("by_org_type", True, True, False, "detail"),
        ("by_type", False, False, True, "enveloppes"),
        # « + type de poste » : le choix du gestionnaire.
        ("by_type_poste", True, True, True, "detail"),
        ("by_type_poste", True, False, False, "detail"),
        ("by_org_type_poste", True, False, False, "detail"),
        ("by_org_type_poste", False, False, True, "enveloppes"),
    ],
)
def test_regles_cout_salarial_et_disposition(mode, detail, auto, computed, layout):
    """Miroir de ``salaryIsComputed`` / ``budgetMode()`` côté front."""
    from apps.plans.services_import_actions import _budget_layout, _salary_is_computed

    assert _salary_is_computed(mode, detail, auto) is computed
    assert _budget_layout(mode, detail) == layout


# ---------------------------------------------------------------------------
# Détails d'exécution et de validation
# ---------------------------------------------------------------------------


def test_annee_sans_montant_non_programmee():
    """Seule une année qui porte un montant est cochée « programmée »."""
    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, budget_total="100"), _row(4, annee=2025, budget_total="0")],
    }
    execute_actions_import(plan, parsed, user)
    years = {oa.annee: oa.periodicite for oa in OperationAnnee.objects.all()}
    assert years == {2024: True, 2025: False}


def test_organisme_avec_temps_sans_budget():
    """Du temps saisi pour un organisme sans budget crée sa ligne de
    ventilation (jours cumulés), comme dans la fiche."""
    user = SuperAdminFactory()
    plan, ind, _site, orgs = _plan_with_organismes(user)
    parsed = {
        "actions": [_action("by_org")],
        "indicateurs": {"I1": ind.id_indicateur},
        "organismes": {"O2": orgs[1].id_organisme},
        "rh": [_row(3, organisme="O2", jours="3"), _row(4, organisme="O2", jours="4")],
    }
    execute_actions_import(plan, parsed, user)
    oao = OperationAnnee.objects.get(annee=2024).organismes.get()
    assert oao.id_organisme_id == orgs[1].id_organisme
    assert oao.etp == Decimal("7") and oao.budget_fonctionnement is None


def test_sites_rattaches_une_seule_fois():
    """Deux organismes gérant le même site → un seul rattachement de site ;
    un site du plan qu'aucun organisme utilisé ne gère n'est pas rattaché."""
    user = SuperAdminFactory()
    plan, ind, site, orgs = _plan_with_organismes(user)
    autre_site = SiteFactory()
    CorSitePg.objects.create(plan_de_gestion=plan, site=autre_site)
    CorOgSite.objects.create(id_site=autre_site, uuid_og=OrganismeFactory())
    parsed = {
        "actions": [_action("by_org")],
        "indicateurs": {"I1": ind.id_indicateur},
        "organismes": {"O1": orgs[0].id_organisme, "O2": orgs[1].id_organisme},
        "budgets": [_row(3, organisme="O1", budget_total="1"),
                    _row(4, organisme="O2", budget_total="1")],
    }
    execute_actions_import(plan, parsed, user)
    assert list(Operation.objects.get().sites.values_list("id_site", flat=True)) == [
        site.id_site
    ]


def test_mode_sans_organisme_ne_rattache_pas_de_site():
    user = SuperAdminFactory()
    plan, ind, _site, _orgs = _plan_with_organismes(user)
    parsed = {
        "actions": [_action("by_type", declinaison_par_type_cout="Non")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, budget_fonctionnement="10")],
    }
    execute_actions_import(plan, parsed, user)
    assert Operation.objects.get().sites.count() == 0


def test_mode_explicite_prime_sur_la_deduction():
    """Un poste en RH avec un mode explicite sans poste → erreur de cible,
    pas de bascule silencieuse vers « + type de poste »."""
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    poste = _add_poste(plan)
    parsed = {
        "actions": [_action("by_type")],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "rh": [_row(3, poste="Q1", jours="2")],
    }
    report = validate_actions_import(plan, parsed)
    assert any(
        i["column"] == "poste" and "inattendu" in i["message"] for i in report.errors
    )


def test_reglages_sans_effet_avertissent():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none", declinaison_par_type_cout="Non",
                            cout_salarial_auto="Non")],
        "indicateurs": {"I1": ind.id_indicateur},
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import
    warned = {i["column"] for i in report.issues if i["level"] == "warning"}
    assert {"declinaison_par_type_cout", "cout_salarial_auto"} <= warned


def test_message_colonne_hors_mode_liste_les_colonnes_attendues():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("by_type", declinaison_par_type_cout="Non")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, cout_stage="10")],
    }
    [error] = validate_actions_import(plan, parsed).errors
    assert error["column"] == "cout_stage"
    assert "sans déclinaison par type de coût" in error["message"]
    assert "« budget fonctionnement (€) »" in error["message"]


def test_rapport_resume_compte_les_lignes():
    user = RoleFactory()
    plan, ind = _plan_with_indicateur(user)
    parsed = {
        "actions": [_action("none")],
        "indicateurs": {"I1": ind.id_indicateur},
        "budgets": [_row(3, budget_total="1")],
        "rh": [_row(3, jours="1"), _row(4, jours="2")],
    }
    assert validate_actions_import(plan, parsed).summary == {
        "actions": 1, "budgets": 1, "rh": 2,
    }


# ---------------------------------------------------------------------------
# Structure du classeur
# ---------------------------------------------------------------------------


def test_classeur_listes_deroulantes_parametrage():
    """Mode, réglages Oui/Non, organisme et catégorie proposent une liste."""
    user = SuperAdminFactory()
    plan, _ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan)))

    def _validations(sheet):
        out = {}
        for dv in wb[sheet].data_validations.dataValidation:
            col = str(dv.sqref).split(":")[0].rstrip("0123456789")
            out[wb[sheet][f"{col}2"].value] = dv.formula1
        return out

    actions = _validations("Actions")
    assert "Listes" in actions["mode de ventilation"]
    assert actions["déclinaison par type de coût"] == '"Oui,Non"'
    assert actions["saisie automatique du coût salarial"] == '"Oui,Non"'
    assert "Organismes" in _validations("Budgets")["organisme"]
    rh = _validations("RH")
    assert "Organismes" in rh["organisme"] and "Postes" in rh["poste"]
    assert "Listes" in rh["catégorie de dépense"]
    listes = [c.value for c in wb["Listes"]["A"] + wb["Listes"]["B"]
              + wb["Listes"]["C"] + wb["Listes"]["D"]]
    assert _MODE_LABELS["by_org_type_poste"] in listes
    assert "Bénévolat partenariat" in listes


def test_onglets_de_reference_proteges():
    user = SuperAdminFactory()
    plan, _ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan)))
    for name in ("Indicateurs", "Postes", "Organismes", "Listes"):
        assert wb[name].protection.sheet, name
    for name in ("Actions", "Budgets", "RH"):
        assert not wb[name].protection.sheet, name


def test_lisez_moi_decrit_les_six_modes():
    user = SuperAdminFactory()
    plan, _ind = _plan_with_indicateur(user)
    wb = load_workbook(io.BytesIO(build_actions_workbook(plan)))
    text = "\n".join(str(c.value) for c in wb["Lisez-moi"]["B"] if c.value)
    for label in _MODE_LABELS.values():
        assert label in text
    assert "Catégorie de dépense" in text
