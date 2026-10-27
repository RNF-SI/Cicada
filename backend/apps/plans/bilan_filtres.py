"""
Filtres et repères partagés par les trois endpoints du Bilan (#753).

`/bilan/`, `/bilan-indicateurs/` et `/bilan-series/` décrivent toujours la même
portée : mêmes enjeux / FCR, mêmes organismes, mêmes types d'indicateurs. Les
règles vivent donc ici, une seule fois.

- **Enjeux** : choix multiple (`?enjeu_id=1,2`). Un indicateur, et l'action qui
  le vise, se rattache à ses enjeux par les deux branches de l'arborescence —
  NE → OLT → enjeu (état) et RA → OO → enjeu / FCR (pression) ; la répartition
  « par enjeu » ne montre que les enjeux choisis.
- **Organismes** (`?organisme_id=`) : les actions ventilées à ces organismes ;
  leur budget et leur temps de travail ne comptent que la part de ces
  organismes, lue dans les mêmes cellules que les exports (`build_action_finance`).
- **Types d'indicateurs** (`?types=ETAT,PRESSION`) : par défaut les deux ; les
  indicateurs de réponse mesurent les actions, ils restent hors du Bilan.
- **Repères** : la liste stable des enjeux du plan, numérotés comme dans
  l'arborescence (« Enjeu 1 », « FCR 1 »), et celle des organismes — les
  options des filtres ne doivent pas dépendre du résultat filtré.
"""

from __future__ import annotations

from .services_export_fiche_action import oo_enjeux

TYPES_BILAN = ("ETAT", "PRESSION")


def ids_param(request, name) -> list[int]:
    """Identifiants d'un paramètre `?name=1,2` (ou répété), ignorés si invalides."""
    out = []
    for raw in request.query_params.getlist(name):
        for part in str(raw).split(","):
            part = part.strip()
            if part.isdigit() and int(part) not in out:
                out.append(int(part))
    return out


def types_param(request) -> tuple[str, ...]:
    raw = [t.strip().upper() for v in request.query_params.getlist("types")
           for t in str(v).split(",") if t.strip()]
    choisis = tuple(t for t in TYPES_BILAN if t in raw)
    return choisis or TYPES_BILAN


# ---------------------------------------------------------------------------
# Enjeux
# ---------------------------------------------------------------------------

def _is_fcr(enjeu) -> bool:
    cat = getattr(enjeu, "id_categorie", None)
    return bool(cat and (cat.mnemonique or "").upper() == "FCR")


def enjeux_du_plan(plan) -> list[dict]:
    """Enjeux puis FCR du plan, dans l'ordre de l'arborescence, avec leur code
    d'affichage (« Enjeu 1 », « FCR 2 » — numéros fixés compris, #442/#526)."""
    from .models_enjeux import Enjeu
    from .services_export_word import _manual_rank_map

    enjeux = list(Enjeu.objects.filter(id_pg=plan).select_related("id_categorie")
                  .order_by("ordre", "id_enjeu"))
    out = []
    for fcr, prefixe in ((False, "Enjeu"), (True, "FCR")):
        items = [e for e in enjeux if _is_fcr(e) == fcr]
        rangs = _manual_rank_map(items, lambda e: e.id_enjeu)
        out.extend({
            "enjeu_id": e.id_enjeu,
            "libelle": e.libelle or e.intitule_court or "",
            "categorie": "FCR" if fcr else "ENJEU",
            "code": f"{prefixe} {rangs[e.id_enjeu]}",
        } for e in items)
    return out


def enjeux_indicateur(ind) -> set[int]:
    """Enjeux d'un indicateur : NE → OLT → enjeu, RA → OO → enjeu(x)."""
    out = set()
    ne = getattr(ind, "id_ne", None)
    olt = getattr(ne, "id_olt", None) if ne else None
    if olt and olt.id_enjeu_id:
        out.add(olt.id_enjeu_id)
    ra = getattr(ind, "id_resultat_attendu", None)
    oo = getattr(ra, "id_oo", None) if ra else None
    if oo:
        out.update(e.id_enjeu for e in oo_enjeux(oo))
    return out


def type_indicateur(ind) -> str | None:
    """ETAT / PRESSION / REPONSE ; à défaut de type saisi, déduit de la branche."""
    t = getattr(ind, "type_indicateur", None)
    mnemo = (getattr(t, "mnemonique", "") or "").upper()
    if mnemo:
        return mnemo
    if getattr(ind, "id_ne_id", None):
        return "ETAT"
    if getattr(ind, "id_resultat_attendu_id", None):
        return "PRESSION"
    return None


def enjeux_operation(op) -> set[int]:
    """Enjeux d'une action, par les indicateurs d'état / de pression qu'elle vise."""
    inds = [m.id_indicateur for m in op.metriques.all() if m.id_indicateur_id]
    if op.id_indicateur_id:
        inds.append(op.id_indicateur)
    out = set()
    for ind in inds:
        if type_indicateur(ind) != "REPONSE":
            out |= enjeux_indicateur(ind)
    return out


OPERATION_PREFETCH = (
    "metriques__id_indicateur__type_indicateur",
    "metriques__id_indicateur__id_ne__id_olt",
    "metriques__id_indicateur__id_resultat_attendu__id_oo__pressions"
    "__id_facteur_influence__enjeux",
)


def indicateurs_du_plan(plan, types=TYPES_BILAN, enjeu_ids=()):
    """[(indicateur, enjeux)] des indicateurs du plan retenus par le Bilan."""
    from .access import INDICATEUR_TO_PG_PATHS
    from .models_indicateurs import Indicateur

    ids = set()
    for path in INDICATEUR_TO_PG_PATHS:
        ids.update(Indicateur.objects.filter(**{path: plan}).values_list("pk", flat=True))
    qs = (Indicateur.objects.filter(pk__in=ids)
          .select_related("type_indicateur", "id_ne__id_olt", "id_resultat_attendu__id_oo")
          .prefetch_related("id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux",
                            "metriques__mesures", "metriques__score_blocks")
          .order_by("pk"))
    plan_enjeux = {e["enjeu_id"] for e in enjeux_du_plan(plan)}
    out = []
    for ind in qs:
        if type_indicateur(ind) not in types:
            continue
        enjeux = enjeux_indicateur(ind) & plan_enjeux
        if enjeu_ids:
            enjeux &= set(enjeu_ids)
            if not enjeux:
                continue
        out.append((ind, enjeux))
    return out


# ---------------------------------------------------------------------------
# Actions et organismes
# ---------------------------------------------------------------------------

def organismes_actions(op_ids) -> dict[int, set[int]]:
    """{id_operation: {organismes auxquels l'action est ventilée}} — par sa
    ventilation budgétaire ou par son temps de travail (organisme de la ligne,
    ou du poste), comme les onglets par organisme des exports."""
    from .models_operations import (
        OperationAnneeOrganisme, OperationAnneeRH, RealisationOperationAnneeRH,
    )

    out = {}
    op = "id_operation_annee__id_operation"
    real_op = "id_realisation_operation_annee__id_operation_annee__id_operation"
    sources = (
        (OperationAnneeOrganisme, op, ("id_organisme",)),
        (OperationAnneeRH, op, ("id_organisme", "id_poste__id_organisme")),
        (RealisationOperationAnneeRH, real_op, ("id_organisme", "id_poste__id_organisme")),
    )
    for model, chemin, champs in sources:
        for champ in champs:
            rows = (model.objects.filter(**{f"{chemin}__in": op_ids, f"{champ}__isnull": False})
                    .values_list(chemin, champ))
            for op_id, org_id in rows:
                out.setdefault(op_id, set()).add(org_id)
    return out


def organismes_du_plan(plan) -> list[dict]:
    """Organismes auxquels au moins une action du plan est ventilée."""
    from apps.users.models import BibOrganismes

    from .access import plan_operation_ids

    org_ids = set().union(set(), *organismes_actions(plan_operation_ids(plan)).values())
    return [{"id_organisme": o.pk, "nom": o.nom_organisme or f"Organisme {o.pk}"}
            for o in BibOrganismes.objects.filter(pk__in=org_ids).order_by("nom_organisme")]


def operations_retenues(plan, enjeu_ids=(), organisme_ids=()) -> set[int] | None:
    """Actions du plan retenues par les filtres ; None = aucun filtre."""
    if not enjeu_ids and not organisme_ids:
        return None
    from .access import plan_operation_ids
    from .models_operations import Operation

    op_ids = plan_operation_ids(plan)
    if enjeu_ids:
        wanted = set(enjeu_ids)
        ops = Operation.objects.filter(pk__in=op_ids).select_related(
            "id_indicateur__type_indicateur", "id_indicateur__id_ne__id_olt",
            "id_indicateur__id_resultat_attendu__id_oo",
        ).prefetch_related(*OPERATION_PREFETCH)
        op_ids = {op.pk for op in ops if enjeux_operation(op) & wanted}
    if organisme_ids:
        wanted = set(organisme_ids)
        orgs = organismes_actions(op_ids)
        op_ids = {i for i in op_ids if orgs.get(i, set()) & wanted}
    return op_ids


def budget_rh_organismes(annees_suivies, organisme_ids, *, avec_globale):
    """Budget et temps de travail de la seule part des organismes choisis.

    Mêmes cellules que les exports budget / RH (`build_action_finance`).
    `annees_suivies` : {(id_operation, année)} ayant un suivi dans la portée —
    comme le bilan non filtré, le prévu ne compte que pour ces années ;
    `avec_globale` ajoute la programmation globale de ces actions (#735, hors
    vue annuelle). Retourne un dict de Decimal :
    prev_fonct, prev_invest, real_fonct, real_invest, prev_fin, prev_non_fin,
    real_fin, real_non_fin.
    """
    from collections import defaultdict
    from decimal import Decimal

    from .models_operations import Operation
    from .services_export_finance import (
        GLOBAL_YEAR, build_action_finance, poste_entry_factory,
    )

    tot = defaultdict(lambda: Decimal(0))
    wanted = set(organisme_ids)
    op_ids = {op_id for op_id, _a in annees_suivies}
    for op in Operation.objects.filter(pk__in=op_ids):
        af = build_action_finance(op, {}, defaultdict(poste_entry_factory))
        for (org_id, annee), c in af.cells.items():
            if org_id not in wanted:
                continue
            if annee is GLOBAL_YEAR:
                if not avec_globale:
                    continue
            elif (op.pk, annee) not in annees_suivies:
                continue
            tot["prev_fonct"] += c.tot_fonct
            tot["prev_invest"] += c.tot_invest
            tot["real_fonct"] += c.rtot_fonct
            tot["real_invest"] += c.rtot_invest
            tot["prev_fin"] += c.j_fonct + c.j_invest
            tot["prev_non_fin"] += c.j_benevole
            tot["real_fin"] += c.rj_fonct + c.rj_invest
            tot["real_non_fin"] += c.rj_benevole
    return tot


def rh_organismes_par_annee(annees_suivies, organisme_ids) -> dict:
    """{année: (jours prévus, jours réalisés)} de la part des organismes choisis,
    sur les {(id_operation, année)} suivies (programmation globale exclue :
    elle n'a pas d'année)."""
    from collections import defaultdict
    from decimal import Decimal

    from .models_operations import Operation
    from .services_export_finance import build_action_finance, poste_entry_factory

    out = defaultdict(lambda: [Decimal(0), Decimal(0)])
    wanted = set(organisme_ids)
    op_ids = {op_id for op_id, _a in annees_suivies}
    for op in Operation.objects.filter(pk__in=op_ids):
        af = build_action_finance(op, {}, defaultdict(poste_entry_factory))
        for (org_id, annee), c in af.cells.items():
            if org_id in wanted and (op.pk, annee) in annees_suivies:
                out[annee][0] += c.jours + c.j_benevole
                out[annee][1] += c.rjours + c.rj_benevole
    return out
