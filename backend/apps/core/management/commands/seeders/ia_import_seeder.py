"""Seeder des plans pré-remplis par IA (module d'import IA).

Rejoue les extractions IA réelles (Val Suzon, Jura, Pibeste) conservées sous
``data/ia_plans/*.json``. Chaque fixture contient les métadonnées du plan, son
arborescence et ses actions au **format plat d'import** — on les réinjecte via
le pipeline existant (``execute_import`` + ``execute_actions_import``), puis on
marque le plan ``import_ia_en_attente=True`` pour qu'il apparaisse dans le
module de relecture (``/plans/import-ia``).

Ré-exporter les fixtures après modification en base :

    from dataclasses import asdict
    from apps.plans.services_import import _extract_plan
    from apps.plans.services_import_actions import _actions_reference, _extract_actions
    arbo = asdict(_extract_plan(plan))
    _, ind_map, _, _ = _actions_reference(plan)
    actions = _extract_actions(plan, ind_map)
"""
import json
from pathlib import Path
from typing import List

from django.utils import timezone

from apps.core.models import Nomenclature
from apps.plans.models import CorRolePlan, PlanGestion
from apps.plans.services_import import execute_import, sanitize_parsed
from apps.plans.services_import_actions import (
    execute_actions_import,
    sanitize_actions_parsed,
)

from .base import BaseSeeder

DATA_DIR = Path(__file__).resolve().parent / "data" / "ia_plans"


class IaImportSeeder(BaseSeeder):
    """Recrée les plans importés par IA, en attente de relecture."""

    name = "ia_import"
    dependencies = ["users"]

    def _fixtures(self):
        return sorted(DATA_DIR.glob("*.json"))

    def _noms(self) -> List[str]:
        noms = []
        for path in self._fixtures():
            with open(path, encoding="utf-8") as fh:
                noms.append(json.load(fh)["meta"]["nom"])
        return noms

    def seed(self) -> List[PlanGestion]:
        self.log_header("Plans importés par IA (relecture)")
        users = self.context.require("users")
        admin = next((u for u in users if u.email == "admin@test.fr"), users[0])

        created: List[PlanGestion] = []
        for path in self._fixtures():
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = payload["meta"]

            # Idempotence : on repart d'un plan vide.
            PlanGestion.objects.filter(nom=meta["nom"]).delete()

            doc_type = Nomenclature.objects.filter(
                mnemonique=meta.get("type_document") or "PLAN_INITIAL"
            ).first()
            plan = PlanGestion.objects.create(
                nom=meta["nom"],
                statut="draft",
                version="1",
                rang=meta.get("rang") or 1,
                id_type_document=doc_type,
                annee_debut=meta.get("annee_debut"),
                annee_fin=meta.get("annee_fin"),
                id_utilisateur_ajout=admin,
                id_utilisateur_maj=admin,
            )

            # Référents (au minimum l'admin, pour pouvoir gérer le cycle de vie).
            ref_emails = meta.get("referents") or ["admin@test.fr"]
            for email in ref_emails:
                ref = next((u for u in users if u.email == email), None) or admin
                CorRolePlan.objects.update_or_create(
                    id_role=ref, plan_de_gestion=plan, defaults={"referent": True}
                )
                plan.referents.add(ref)

            # Arborescence puis actions, via le pipeline d'import (codes I{n}
            # déterministes → les actions se rattachent aux bons indicateurs).
            arbo = sanitize_parsed(payload.get("arborescence") or {})
            execute_import(plan, arbo, admin, mode="create")
            actions = payload.get("actions") or []
            if actions:
                parsed = sanitize_actions_parsed(plan, {"actions": actions})
                execute_actions_import(plan, parsed, admin)

            plan.import_ia_en_attente = True
            plan.import_ia_date = timezone.now()
            plan.save(update_fields=["import_ia_en_attente", "import_ia_date"])

            created.append(plan)
            self.log_item(
                "OK",
                f"{plan.nom} — {plan.enjeux.count()} enjeux, {len(actions)} actions",
            )

        self.log_summary(len(created), "plan IA")
        return created

    def reset(self) -> int:
        deleted = PlanGestion.objects.filter(nom__in=self._noms()).delete()[0]
        return deleted

    def get_dry_run_summary(self) -> List[str]:
        return [
            f"{len(self._fixtures())} plans pré-remplis par IA "
            "(Val Suzon, Jura, Pibeste) → en attente de relecture"
        ]
