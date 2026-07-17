"""
Tests HTTP des endpoints d'import / export Excel (#478).

Couvre la couche API (`PlanGestionViewSet`) que les tests service ne touchent
pas :
- export du classeur (GET, tout statut) et bon type MIME ;
- validation (dry-run) via multipart → rapport JSON ;
- import réel dans un brouillon (201 + décomptes) ;
- **verrou brouillon** : import refusé (403) sur un plan validé — la permission
  `CanModifyOnlyDraftPlan` s'applique aux endpoints d'écriture ;
- authentification requise ;
- fichier manquant → 400.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.plans.models import PlanGestion
from apps.plans.services_import import build_arborescence_workbook

from tests.factories.users import SuperAdminFactory
from tests.factories.plans import PlanGestionFactory, PlanGestionValideFactory

# Réutilise les helpers de construction d'un plan source riche.
from tests.apps.plans.test_import_arborescence import (
    _base_nomenclatures,
    _build_source_plan,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _upload_from_plan(plan):
    """Construit un fichier .xlsx d'arborescence à partir d'un plan source."""
    content = build_arborescence_workbook(plan=plan)
    return SimpleUploadedFile("arborescence.xlsx", content, content_type=XLSX_MIME)


def _url(plan, suffix):
    return f"/api/plans/plans/{plan.pk}/{suffix}"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_arborescence_requires_auth():
    plan = PlanGestionFactory()
    resp = APIClient().get(_url(plan, "export-arborescence-xlsx/"))
    assert resp.status_code in (401, 403)


def test_export_arborescence_ok_on_draft():
    user = SuperAdminFactory()
    _base_nomenclatures()
    plan = _build_source_plan(user)
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get(_url(plan, "export-arborescence-xlsx/"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == XLSX_MIME
    assert b"PK" == resp.content[:2]  # signature d'un .xlsx (zip)


def test_export_arborescence_ok_on_validated_plan():
    """L'export (lecture) fonctionne quel que soit le statut du plan."""
    user = SuperAdminFactory()
    plan = PlanGestionValideFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get(_url(plan, "export-arborescence-xlsx/?empty=1"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == XLSX_MIME


def test_export_actions_ok():
    user = SuperAdminFactory()
    _base_nomenclatures()
    plan = _build_source_plan(user)
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get(_url(plan, "export-actions-xlsx/"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == XLSX_MIME


# ---------------------------------------------------------------------------
# Validation (dry-run)
# ---------------------------------------------------------------------------


def test_validate_endpoint_returns_report():
    user = SuperAdminFactory()
    _base_nomenclatures()
    source = _build_source_plan(user)
    target = PlanGestionFactory(id_utilisateur_ajout=user)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        _url(target, "import-arborescence/validate/"),
        {"file": _upload_from_plan(source)},
        format="multipart",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["can_import"] is True
    assert body["summary"]["enjeux"] == source.enjeux.count()
    # Rien n'a été écrit (dry-run).
    assert target.enjeux.count() == 0


def test_import_missing_file_returns_400():
    user = SuperAdminFactory()
    target = PlanGestionFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(_url(target, "import-arborescence/"), {}, format="multipart")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Import réel + verrou brouillon
# ---------------------------------------------------------------------------


def test_import_creates_arborescence_on_draft():
    user = SuperAdminFactory()
    _base_nomenclatures()
    source = _build_source_plan(user)
    target = PlanGestionFactory(id_utilisateur_ajout=user)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        _url(target, "import-arborescence/"),
        {"file": _upload_from_plan(source)},
        format="multipart",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["created"]["enjeux"] == source.enjeux.count()
    assert target.enjeux.count() == source.enjeux.count()


def test_import_refused_on_validated_plan():
    """Verrou #248 : import bloqué (403) hors brouillon, même pour un super admin."""
    user = SuperAdminFactory()
    _base_nomenclatures()
    source = _build_source_plan(user)
    target = PlanGestionValideFactory(id_utilisateur_ajout=user)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        _url(target, "import-arborescence/"),
        {"file": _upload_from_plan(source)},
        format="multipart",
    )
    assert resp.status_code == 403
    # Aucune écriture sur le plan validé.
    assert target.enjeux.count() == 0


# ---------------------------------------------------------------------------
# Exemples téléchargeables (indépendants d'un plan)
# ---------------------------------------------------------------------------


def test_example_arborescence_endpoint_ok():
    user = SuperAdminFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/plans/plans/example-arborescence-xlsx/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == XLSX_MIME
    assert resp.content[:2] == b"PK"


def test_example_actions_endpoint_ok():
    user = SuperAdminFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/plans/plans/example-actions-xlsx/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == XLSX_MIME


def test_example_endpoints_require_auth():
    assert APIClient().get(
        "/api/plans/plans/example-arborescence-xlsx/"
    ).status_code in (401, 403)
    assert APIClient().get("/api/plans/plans/example-actions-xlsx/").status_code in (
        401,
        403,
    )


# ---------------------------------------------------------------------------
# Édition assistée (#9) : schéma, validate-data, import-data, read-xlsx (#10)
# ---------------------------------------------------------------------------


def test_import_schema_endpoint():
    client = APIClient()
    client.force_authenticate(user=SuperAdminFactory())
    resp = client.get("/api/plans/plans/import-arborescence-schema/")
    assert resp.status_code == 200
    sheets = resp.json()["sheets"]
    assert any(s["key"] == "enjeux" for s in sheets)
    enjeux = next(s for s in sheets if s["key"] == "enjeux")
    assert any(c["key"] == "code" and c["required"] for c in enjeux["columns"])


def test_validate_data_roundtrip():
    user = SuperAdminFactory()
    _base_nomenclatures()
    target = PlanGestionFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    body = {
        "data": {
            "enjeux": [
                {"code": "E1", "categorie": "ENJEU", "libelle": "Qualité des eaux"}
            ]
        }
    }
    resp = client.post(
        f"/api/plans/plans/{target.pk}/import-arborescence/validate-data/",
        body,
        format="json",
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["can_import"] is True
    assert len(j["data"]["enjeux"]) == 1
    assert target.enjeux.count() == 0  # dry-run


def test_import_data_creates_arborescence():
    user = SuperAdminFactory()
    _base_nomenclatures()
    target = PlanGestionFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    body = {
        "data": {
            "enjeux": [
                {"code": "E1", "categorie": "ENJEU", "libelle": "Qualité des eaux"}
            ]
        }
    }
    resp = client.post(
        f"/api/plans/plans/{target.pk}/import-arborescence/import-data/",
        body,
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert target.enjeux.count() == 1


def test_import_data_refused_on_validated_plan():
    user = SuperAdminFactory()
    _base_nomenclatures()
    target = PlanGestionValideFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        f"/api/plans/plans/{target.pk}/import-arborescence/import-data/",
        {"data": {"enjeux": [{"code": "E1", "categorie": "ENJEU", "libelle": "X"}]}},
        format="json",
    )
    assert resp.status_code == 403


def test_read_xlsx_endpoint():
    user = SuperAdminFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    content = build_arborescence_workbook(plan=None)
    upload = SimpleUploadedFile("foreign.xlsx", content, content_type=XLSX_MIME)
    resp = client.post(
        "/api/plans/plans/read-xlsx/", {"file": upload}, format="multipart"
    )
    assert resp.status_code == 200
    sheets = resp.json()["sheets"]
    assert any(s["name"] == "Enjeux" for s in sheets)


# ---------------------------------------------------------------------------
# Modes d'import : add / replace + résumé du contenu existant
# ---------------------------------------------------------------------------


def test_existing_summary_endpoint():
    from tests.factories.enjeux import EnjeuFactory

    user = SuperAdminFactory()
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(
        f"/api/plans/plans/{plan.pk}/import-arborescence/existing-summary/"
    )
    assert resp.status_code == 200
    assert resp.json()["enjeux"] == 1


def test_import_data_add_mode_appends():
    from tests.factories.enjeux import EnjeuFactory

    user = SuperAdminFactory()
    _base_nomenclatures()
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user, libelle="Existant")
    client = APIClient()
    client.force_authenticate(user=user)
    body = {
        "mode": "add",
        "data": {
            "enjeux": [{"code": "E1", "categorie": "ENJEU", "libelle": "Nouveau"}]
        },
    }
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-arborescence/import-data/",
        body,
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert plan.enjeux.count() == 2


def test_import_data_create_mode_refuses_non_empty():
    from tests.factories.enjeux import EnjeuFactory

    user = SuperAdminFactory()
    _base_nomenclatures()
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-arborescence/import-data/",
        {"data": {"enjeux": [{"code": "E1", "categorie": "ENJEU", "libelle": "X"}]}},
        format="json",
    )
    assert resp.status_code == 400  # création seule refuse un plan non vide


# ---------------------------------------------------------------------------
# Actions — couture JSON (schéma, validate-data, import-data) : socle de l'IA
# ---------------------------------------------------------------------------


def test_actions_import_schema_endpoint():
    """Le schéma actions expose les onglets de saisie + les indicateurs de
    référence du plan (codes de rattachement pour la grille / l'extraction IA)."""
    from tests.apps.plans.test_import_actions import _plan_with_indicateur

    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get(f"/api/plans/plans/{plan.pk}/import-actions-schema/")
    assert resp.status_code == 200
    body = resp.json()
    assert {s["key"] for s in body["sheets"]} == {"actions", "budgets", "rh"}
    actions = next(s for s in body["sheets"] if s["key"] == "actions")
    indic_col = next(c for c in actions["columns"] if c["key"] == "indicateur")
    assert indic_col["required"] and indic_col["ref"] == "indicateurs"
    refs = body["references"]["indicateurs"]
    assert len(refs) == 1
    assert refs[0]["id"] == ind.id_indicateur
    assert refs[0]["code"]  # code de rattachement non vide (ex : I1)


def test_actions_validate_data_roundtrip():
    from apps.plans.models_operations import Operation
    from tests.apps.plans.test_import_actions import _plan_with_indicateur, _type_action

    user = SuperAdminFactory()
    _type_action()
    plan, ind = _plan_with_indicateur(user)
    client = APIClient()
    client.force_authenticate(user=user)

    schema = client.get(f"/api/plans/plans/{plan.pk}/import-actions-schema/").json()
    code = schema["references"]["indicateurs"][0]["code"]

    body = {
        "data": {
            "actions": [
                {"code": "A1", "indicateur": code, "libelle": "Débroussaillage"}
            ]
        }
    }
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-actions/validate-data/",
        body,
        format="json",
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["can_import"] is True
    assert len(j["data"]["actions"]) == 1
    assert Operation.objects.filter(id_indicateur=ind).count() == 0  # dry-run


def test_actions_import_data_creates_operations():
    from apps.plans.models_operations import Operation
    from tests.apps.plans.test_import_actions import _plan_with_indicateur

    user = SuperAdminFactory()
    plan, ind = _plan_with_indicateur(user)
    client = APIClient()
    client.force_authenticate(user=user)

    schema = client.get(f"/api/plans/plans/{plan.pk}/import-actions-schema/").json()
    code = schema["references"]["indicateurs"][0]["code"]

    body = {
        "data": {
            "actions": [
                {
                    "code": "A1",
                    "indicateur": code,
                    "libelle": "Débroussaillage",
                    "annee_min": 2024,
                    "annee_max": 2026,
                }
            ]
        }
    }
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-actions/import-data/",
        body,
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["created"]["actions"] == 1
    assert Operation.objects.filter(id_indicateur=ind).count() == 1


def test_actions_import_data_refused_on_validated_plan():
    """Verrou #248 : import JSON d'actions bloqué (403) hors brouillon."""
    from tests.factories.plans import PlanGestionValideFactory

    user = SuperAdminFactory()
    plan = PlanGestionValideFactory(id_utilisateur_ajout=user)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-actions/import-data/",
        {"data": {"actions": [{"code": "A1", "indicateur": "I1", "libelle": "X"}]}},
        format="json",
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Contrat « format IA » : un payload tel que produit par tools/import-ia
# (colonnes complètes, valeurs vides = chaîne vide, nomenclatures par LIBELLÉ)
# doit s'importer par la couture JSON. Garantit que l'extracteur IA vise le
# bon format sans dépendre du classeur Excel.
# ---------------------------------------------------------------------------


def test_import_data_ai_shaped_payload_imports():
    from apps.core.models import Nomenclature

    user = SuperAdminFactory()
    _base_nomenclatures()
    plan = PlanGestionFactory(id_utilisateur_ajout=user)

    # Libellés réels (l'IA émet les libellés autorisés, pas les mnémoniques).
    lbl_enjeu = Nomenclature.objects.get(mnemonique="ENJEU").label
    lbl_etat = Nomenclature.objects.get(mnemonique="ETAT").label
    lbl_num = Nomenclature.objects.get(mnemonique="NUMERIQUE").label

    def row(**vals):
        # Toutes les colonnes présentes, non renseignées = "" (comme to_payload).
        return vals

    data = {
        "enjeux": [
            row(
                code="E1",
                categorie=lbl_enjeu,
                libelle="Qualité des eaux",
                categorie_fcr="",
                importance="",
                rang="",
                intitule_court="",
                categorie_ecologique="",
                types_ecologiques="",
                types_socioeco="",
                etat_enjeu="",
                description="",
            )
        ],
        "olt": [
            row(
                code="O1",
                enjeu="E1",
                libelle="Maintenir le bon état",
                numero_manuel="",
                description="",
            )
        ],
        "ne": [row(code="N1", olt="O1", libelle="Seuil 18 ha", description="")],
        "indicateurs": [
            row(
                code="I1",
                parent="N1",
                type=lbl_etat,
                nom_indicateur="Surface",
                description="",
            )
        ],
        "metriques": [
            row(
                code="M1",
                indicateur="I1",
                nom_metrique="Surface (ha)",
                type_metrique=lbl_num,
                unite="ha",
                description="",
            )
        ],
    }

    client = APIClient()
    client.force_authenticate(user=user)

    # Dry-run : le rapport doit être importable (libellés résolus).
    val = client.post(
        f"/api/plans/plans/{plan.pk}/import-arborescence/validate-data/",
        {"data": data},
        format="json",
    )
    assert val.status_code == 200
    assert val.json()["can_import"] is True, val.json()["issues"]

    # Import réel.
    resp = client.post(
        f"/api/plans/plans/{plan.pk}/import-arborescence/import-data/",
        {"data": data},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    created = resp.json()["created"]
    assert created["enjeux"] == 1
    assert created["indicateurs"] == 1
    assert created["metriques"] == 1
    assert plan.enjeux.count() == 1
