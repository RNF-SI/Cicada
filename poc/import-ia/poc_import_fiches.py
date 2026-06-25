"""
(c) POC — Import des fiches actions extraites (JSON schéma Cicada) vers la base.

⚠️ PROOF OF CONCEPT — volontairement NON câblé dans l'application.
   Ce fichier est une *commande de gestion Django* isolée. Pour l'exécuter :
       cp poc/import-ia/poc_import_fiches.py \
          backend/apps/plans/management/commands/poc_import_fiches.py
       docker compose exec web python manage.py poc_import_fiches \
          /chemin/extraction.json --plan <ID> [--user admin@test.fr] [--commit]
   (Sans --commit : DRY-RUN, aucune écriture en base. C'est le défaut.)

Ce que fait l'import, par fiche :
  - crée une Operation en statut 'draft' (libellé, code, description, priorité,
    type d'action, opérateurs/partenaires/financeurs, années min/max,
    programmation_annuelle JSON) ;
  - crée les OperationAnnee programmées (periodicite=True, budget/etp best-effort) ;
  - RATTACHEMENT : tente de relier l'Operation à un Indicateur EXISTANT du plan
    en faisant correspondre `cadre.indicateur` à `Indicateur.nom_indicateur`
    (comparaison normalisée). Si aucun match -> Operation laissée non rattachée
    (id_indicateur=NULL) et SIGNALÉE dans le rapport pour rattachement manuel.

L'import ne crée JAMAIS d'enjeu/OLT/NE/indicateur : il se branche sur l'arborescence
déjà saisie dans Cicada. La création de l'arborescence est hors périmètre de ce POC
(c'est la décision « on importe les fiches actions, pas les métriques »).
"""

import json
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion
from apps.plans.models_indicateurs import Indicateur
from apps.plans.models_operations import Operation, OperationAnnee
from apps.users.models import Role


def _norm(s) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


class Command(BaseCommand):
    help = "POC : importe des fiches actions (JSON) comme Operations brouillon dans un plan."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Fichier JSON {'fiches': [...]}")
        parser.add_argument("--plan", type=int, required=True, help="id_pg du plan cible")
        parser.add_argument("--user", type=str, help="Email du Role créateur (défaut: 1er superuser)")
        parser.add_argument("--commit", action="store_true",
                            help="Écrit en base. Sans ce flag : dry-run.")

    def handle(self, *args, **opts):
        data = json.loads(Path(opts["json_path"]).read_text(encoding="utf-8"))
        fiches = data.get("fiches", [])
        if not fiches:
            raise CommandError("Aucune fiche dans le JSON.")

        plan = PlanGestion.objects.filter(pk=opts["plan"]).first()
        if not plan:
            raise CommandError(f"Plan {opts['plan']} introuvable.")
        if plan.statut != "draft":
            self.stdout.write(self.style.WARNING(
                f"⚠ Le plan {plan.pk} n'est pas en brouillon (statut={plan.statut}). "
                "L'import de contenu suppose un plan éditable (#248)."))

        user = (Role.objects.filter(email=opts["user"]).first() if opts.get("user")
                else Role.objects.filter(is_superuser=True).order_by("pk").first())
        if not user:
            raise CommandError("Aucun utilisateur créateur (--user ou superuser).")

        # Index des indicateurs du plan pour le rattachement (normalisé -> indicateur).
        plan_indics = [i for i in Indicateur.objects.all()
                       if getattr(i.get_plan_de_gestion(), "pk", None) == plan.pk]
        index = {_norm(i.nom_indicateur): i for i in plan_indics}
        self.stdout.write(f"Plan {plan.pk} : {len(plan_indics)} indicateur(s) candidats au rattachement.")

        prio_nom = self._nomenclature_index("PRIORITE_OPERATION")
        type_nom = self._nomenclature_index("TYPE_ACTION")

        report = {"crees": 0, "rattaches": 0, "non_rattaches": []}
        # Dry-run robuste : atomic() + exception pour forcer le rollback. (savepoint()
        # est un no-op hors atomic, en mode autocommit — il ne protège PAS un dry-run.)
        class _DryRun(Exception):
            pass
        try:
            with transaction.atomic():
                for fiche in fiches:
                    self._import_fiche(fiche, user, index, prio_nom, type_nom, report)
                if not opts["commit"]:
                    raise _DryRun()
        except _DryRun:
            pass
        if opts["commit"]:
            self.stdout.write(self.style.SUCCESS("✓ COMMIT — écrit en base."))
        else:
            self.stdout.write(self.style.WARNING("DRY-RUN — rollback (rien écrit). Ajoute --commit pour persister."))

        self.stdout.write(
            f"\nRésumé : {report['crees']} opérations, "
            f"{report['rattaches']} rattachées à un indicateur, "
            f"{len(report['non_rattaches'])} à rattacher manuellement.")
        for code, indic in report["non_rattaches"]:
            self.stdout.write(f"  ⚠ {code:8} : indicateur \"{indic}\" non trouvé dans le plan")

    # ------------------------------------------------------------------ helpers
    def _nomenclature_index(self, mnemonique):
        qs = Nomenclature.objects.filter(id_type__mnemonique=mnemonique)
        return {_norm(n.cd_nomenclature): n for n in qs}

    @transaction.atomic
    def _import_fiche(self, fiche, user, index, prio_nom, type_nom, report):
        cadre = fiche.get("cadre", {})
        op_data = fiche.get("operation", {})
        prog = fiche.get("programmation", {})

        # Rattachement à un indicateur existant (best-effort, sans inventer).
        indic_label = _norm(cadre.get("indicateur"))
        indicateur = index.get(indic_label)
        if not indicateur and indic_label:
            # tolérance : la 1re partie avant un séparateur (indicateurs multiples)
            first = _norm(str(cadre.get("indicateur")).split(";")[0])
            indicateur = index.get(first)

        annees = [e["annee"] for e in (prog.get("calendrier_annuel") or []) if e.get("programme")]
        details = op_data.get("details") or ""
        if op_data.get("nom_protocole"):
            details = f"{details}\n\nProtocole : {op_data['nom_protocole']}".strip()

        op = Operation(
            libelle=(fiche.get("intitule") or "")[:500],
            code_operation=(fiche.get("code_action") or "")[:100] or None,
            description=details or None,
            id_priorite=prio_nom.get(_norm(fiche.get("priorite"))),
            id_type_action=self._match_type_action(fiche, type_nom),
            id_indicateur=indicateur,
            operateurs=self._join((op_data.get("operateurs_internes") or [])
                                  + (op_data.get("operateurs_externes") or [])) or None,
            partenaires=self._join(op_data.get("partenaires")) or None,
            financeurs=self._join(f.get("organisme_ou_financeur")
                                  for f in (prog.get("financements") or [])) or None,
            annee_min=min(annees) if annees else None,
            annee_max=max(annees) if annees else None,
            programmation_annuelle={str(a): True for a in annees},
            statut=Operation.STATUT_DRAFT,
            id_utilisateur_ajout=user,
        )
        op.save()

        for a in annees:
            OperationAnnee.objects.create(id_operation=op, annee=a, periodicite=True)

        report["crees"] += 1
        if indicateur:
            report["rattaches"] += 1
        else:
            report["non_rattaches"].append((fiche.get("code_action") or "?", cadre.get("indicateur")))
        self.stdout.write(
            f"  + {fiche.get('code_action',''):8} {op.libelle[:42]:42} "
            f"{'→ ' + indicateur.nom_indicateur[:30] if indicateur else '(non rattachée)'}")

    def _match_type_action(self, fiche, type_nom):
        """Best-effort : code exact (CS 1.1) puis préfixe nature (CS…)."""
        code = _norm(fiche.get("code_action"))
        if code in type_nom:
            return type_nom[code]
        nature = _norm(fiche.get("code_nature"))
        for key, nom in type_nom.items():
            if nature and key.startswith(nature):
                return nom
        return None

    @staticmethod
    def _join(values):
        return " ; ".join(str(v) for v in (values or []) if v)
