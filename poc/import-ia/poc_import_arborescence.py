"""
(module arborescence #478) POC — Import de l'arborescence d'un PG (JSON) vers la base.

⚠️ PROOF OF CONCEPT — non câblé dans l'application (cf. README). Pour exécuter :
    cp poc/import-ia/poc_import_arborescence.py \
       backend/apps/plans/management/commands/poc_import_arborescence.py
    docker compose exec web python manage.py poc_import_arborescence \
       /chemin/arborescence.json --plan <ID> [--user admin@test.fr] [--commit]
  (Sans --commit : DRY-RUN, rollback, rien écrit. C'est le défaut.)

Crée la hiérarchie Cicada à partir des seuls LIBELLÉS :
  Enjeu/FCR → (FacteurInfluence → Pression)
  Enjeu → OLT → NiveauExigence → Indicateur(ÉTAT) → Métrique
  Enjeu → ObjectifOperationnel → ResultatAttendu → Indicateur(PRESSION/RÉPONSE) → Métrique

Conformément à #478 :
  - Enjeux/FCR : infos requises absentes de la source (types écologiques, etc.)
    SIGNALÉES (`a_completer`) pour saisie humaine — l'enjeu est créé avec des
    valeurs par défaut prudentes.
  - Pressions : `type_pression_suggere` rapproché de la nomenclature TYPE_PRESSION
    (PressRef) ; à défaut, pression créée sans type et signalée.
  - Métriques : seul le libellé est importé ; aucune mesure → l'indicateur reste
    « indéterminé » naturellement (pas de score).

Ne crée PAS les actions/opérations (module séparé : poc_import_fiches.py).
"""

import json
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression, ObjectifLongTerme,
    NiveauExigence, ObjectifOperationnel, ResultatAttendu,
)
from apps.plans.models_indicateurs import Indicateur, Metrique
from apps.users.models import Role

ECO_FLAGS = {"habitat", "espece", "patrimoine_geologique", "fonctionnalite_ecosysteme"}


def _norm(s) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


class Command(BaseCommand):
    help = "POC #478 : importe l'arborescence (JSON) d'un PG (enjeux → ... → métriques)."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)
        parser.add_argument("--plan", type=int, required=True)
        parser.add_argument("--user", type=str)
        parser.add_argument("--commit", action="store_true", help="Écrit en base (sinon dry-run).")

    def handle(self, *args, **opts):
        data = json.loads(Path(opts["json_path"]).read_text(encoding="utf-8"))
        enjeux = data.get("enjeux", [])
        if not enjeux:
            raise CommandError("Aucun enjeu dans le JSON.")

        plan = PlanGestion.objects.filter(pk=opts["plan"]).first()
        if not plan:
            raise CommandError(f"Plan {opts['plan']} introuvable.")
        if plan.statut != "draft":
            self.stdout.write(self.style.WARNING(
                f"⚠ Plan {plan.pk} non brouillon (statut={plan.statut}) — l'import de contenu suppose un plan éditable (#248)."))

        user = (Role.objects.filter(email=opts["user"]).first() if opts.get("user")
                else Role.objects.filter(is_superuser=True).order_by("pk").first())
        if not user:
            raise CommandError("Aucun utilisateur créateur (--user ou superuser).")

        self.user = user
        self.cat_enjeu = self._nom_by_mnemo("CATEGORIE_ENJEU")
        self.type_indic = self._nom_by_mnemo("TYPE_INDICATEUR")
        self.type_pression = list(Nomenclature.objects.filter(id_type__mnemonique="TYPE_PRESSION"))

        self.counts = {k: 0 for k in
                       ("enjeux", "facteurs", "pressions", "olts", "nes", "oos", "ras", "indicateurs", "metriques")}
        self.todo = {"enjeux_a_completer": [], "pressions_sans_type": []}

        # Dry-run robuste : tout le travail dans un atomic() ; sans --commit on lève
        # une exception pour forcer le rollback. (transaction.savepoint() est un no-op
        # hors atomic, en mode autocommit — il ne protège PAS un dry-run.)
        class _DryRun(Exception):
            pass
        try:
            with transaction.atomic():
                for e in enjeux:
                    self._import_enjeu(plan, e)
                if not opts["commit"]:
                    raise _DryRun()
        except _DryRun:
            pass
        if opts["commit"]:
            self.stdout.write(self.style.SUCCESS("✓ COMMIT — écrit en base."))
        else:
            self.stdout.write(self.style.WARNING("DRY-RUN — rollback (rien écrit). Ajoute --commit pour persister."))

        self.stdout.write("\nRésumé : " + ", ".join(f"{v} {k}" for k, v in self.counts.items()))
        if self.todo["enjeux_a_completer"]:
            self.stdout.write(self.style.WARNING("\nÀ compléter à l'import (#478) :"))
            for lib, champs in self.todo["enjeux_a_completer"]:
                self.stdout.write(f"  • Enjeu « {lib} » : {', '.join(champs)}")
        if self.todo["pressions_sans_type"]:
            self.stdout.write(self.style.WARNING("\nPressions sans type PressRef (à choisir) :"))
            for lib in self.todo["pressions_sans_type"]:
                self.stdout.write(f"  • {lib}")

    # ------------------------------------------------------------------ helpers
    def _nom_by_mnemo(self, type_mnemo):
        return {n.mnemonique: n for n in Nomenclature.objects.filter(id_type__mnemonique=type_mnemo)}

    @transaction.atomic
    def _import_enjeu(self, plan, e):
        cat = self.cat_enjeu.get(e.get("categorie"))
        if cat is None:
            raise CommandError(f"Nomenclature CATEGORIE_ENJEU '{e.get('categorie')}' absente — importer les nomenclatures d'abord.")

        types = set(e.get("types_ecologiques") or [])
        enjeu = Enjeu(
            id_pg=plan,
            id_categorie=cat,
            libelle=(e.get("libelle") or "")[:500],
            rang=e.get("priorite"),
            categorie_ecologique=e.get("categorie_ecologique") if e.get("categorie_ecologique") is not None else True,
            habitat="habitat" in types,
            espece="espece" in types,
            patrimoine_geologique="patrimoine_geologique" in types,
            fonctionnalite_ecosysteme="fonctionnalite_ecosysteme" in types,
            id_utilisateur_ajout=self.user,
        )
        enjeu.save()
        self.counts["enjeux"] += 1
        self.stdout.write(f"+ Enjeu « {enjeu.libelle[:50]} » [{e.get('categorie')}]")

        champs = list(e.get("a_completer") or [])
        if not types and e.get("categorie_ecologique") is not False \
                and not any("types_ecologiques" in c for c in champs):
            champs.append("types_ecologiques")
        if champs:
            self.todo["enjeux_a_completer"].append((enjeu.libelle, champs))

        # Facteurs → Pressions
        for f in e.get("facteurs") or []:
            facteur = FacteurInfluence.objects.create(
                id_enjeu=enjeu, libelle=(f.get("libelle") or "")[:500], id_utilisateur_ajout=self.user)
            self.counts["facteurs"] += 1
            for p in f.get("pressions") or []:
                tp = self._match_type_pression(p.get("type_pression_suggere"))
                Pression.objects.create(
                    id_facteur_influence=facteur, libelle=(p.get("libelle") or "")[:500],
                    id_type_pression=tp, id_utilisateur_ajout=self.user)
                self.counts["pressions"] += 1
                if tp is None:
                    self.todo["pressions_sans_type"].append(p.get("libelle"))

        # OLT → NE → Indicateur(ÉTAT) → Métrique
        for olt_d in e.get("olts") or []:
            olt = ObjectifLongTerme.objects.create(
                id_enjeu=enjeu, libelle=(olt_d.get("libelle") or "")[:500], id_utilisateur_ajout=self.user)
            self.counts["olts"] += 1
            for ne_d in olt_d.get("niveaux_exigence") or []:
                ne = NiveauExigence.objects.create(
                    id_olt=olt, libelle=(ne_d.get("libelle") or "")[:500], id_utilisateur_ajout=self.user)
                self.counts["nes"] += 1
                for ind_d in ne_d.get("indicateurs") or []:
                    self._create_indicateur(ind_d, id_ne=ne)

        # OO → RA → Indicateur(PRESSION/RÉPONSE) → Métrique
        for oo_d in e.get("objectifs_operationnels") or []:
            oo = ObjectifOperationnel.objects.create(
                id_enjeu=enjeu, libelle=(oo_d.get("libelle") or "")[:500], id_utilisateur_ajout=self.user)
            self.counts["oos"] += 1
            for ra_d in oo_d.get("resultats_attendus") or []:
                ra = ResultatAttendu.objects.create(
                    id_oo=oo, libelle=(ra_d.get("libelle") or "")[:500], id_utilisateur_ajout=self.user)
                self.counts["ras"] += 1
                for ind_d in ra_d.get("indicateurs") or []:
                    self._create_indicateur(ind_d, id_resultat_attendu=ra)

    def _create_indicateur(self, ind_d, id_ne=None, id_resultat_attendu=None):
        indic = Indicateur.objects.create(
            id_ne=id_ne, id_resultat_attendu=id_resultat_attendu,
            nom_indicateur=(ind_d.get("nom") or "")[:500],
            type_indicateur=self.type_indic.get(ind_d.get("type")),
            id_utilisateur_ajout=self.user)
        self.counts["indicateurs"] += 1
        for m in ind_d.get("metriques") or []:
            Metrique.objects.create(
                id_indicateur=indic,
                nom_metrique=(m.get("nom") or "")[:500],
                description=m.get("valeur_cible") or None,  # « valeur idéale à atteindre »
                unite=m.get("unite") or None,
                id_utilisateur_ajout=self.user)
            self.counts["metriques"] += 1

    def _match_type_pression(self, suggestion):
        """Best-effort : rapproche la suggestion d'une nomenclature TYPE_PRESSION."""
        s = _norm(suggestion)
        if not s:
            return None
        for n in self.type_pression:
            if s == _norm(n.mnemonique) or s == _norm(n.label) or s in _norm(n.label):
                return n
        return None
