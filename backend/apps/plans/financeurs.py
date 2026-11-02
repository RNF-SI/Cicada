"""
#790 — Montants par financeur : source unique du bilan prévu / réalisé d'une
action, lue par la fiche action (API) et par les exports (fiches action Excel
et Word, fiche de suivi, onglets « Par financeur » des budgets).

- Prévu : ``FinanceOperation.montant``, **global sur l'action** (facultatif).
- Réalisé : ``RealisationFinanceur.montant``, **par année** ; un financeur non
  prévu par l'action peut y figurer. On compare le **total réalisé** au prévu,
  comme pour la programmation globale (#735).
- Écart : la somme des montants prévus ≠ budget prévu de l'action → alerte,
  jamais bloquante (Q3).
"""
from __future__ import annotations

from decimal import Decimal


def _txt(d):
    return None if d is None else f"{Decimal(d):.2f}"


def budget_prevu(op) -> Decimal:
    """Budget prévu total de l'action, calculé comme les exports (#600)."""
    from collections import defaultdict

    from .services_export_finance import build_action_finance, poste_entry_factory

    af = build_action_finance(op, {}, defaultdict(poste_entry_factory))
    return sum((c.tot for c in af.cells.values()), Decimal(0))


def bilan_financeurs(op) -> dict:
    """Bilan des coûts par financeur d'une action (nombres ``Decimal``)."""
    from .models_operations import RealisationFinanceur

    lignes: dict[int, dict] = {}

    def ligne(f):
        return lignes.setdefault(f.id_financeur, {
            "id_financeur": f.id_financeur, "nom": f.nom,
            "categorie": f.categorie_affichage, "prevu": None,
            "prevu_par_action": False, "realise": None, "realise_par_annee": {},
        })

    for fin in op.finances.select_related("id_financeur__id_categorie").all():
        if fin.id_financeur_id is None:
            continue
        lg = ligne(fin.id_financeur)
        lg["prevu_par_action"] = True
        if fin.montant is not None:
            lg["prevu"] = (lg["prevu"] or Decimal(0)) + fin.montant
    for r in (RealisationFinanceur.objects
              .filter(id_realisation_operation_annee__id_operation_annee__id_operation=op)
              .select_related("id_financeur__id_categorie",
                              "id_realisation_operation_annee__id_operation_annee")):
        lg = ligne(r.id_financeur)
        if r.montant is None:
            continue
        annee = r.id_realisation_operation_annee.id_operation_annee.annee
        lg["realise"] = (lg["realise"] or Decimal(0)) + r.montant
        lg["realise_par_annee"][annee] = lg["realise_par_annee"].get(annee, Decimal(0)) + r.montant

    rows = sorted(lignes.values(), key=lambda l: (not l["prevu_par_action"], l["nom"].lower()))
    total_prevu = sum((l["prevu"] for l in rows if l["prevu"] is not None), Decimal(0))
    total_realise = sum((l["realise"] for l in rows if l["realise"] is not None), Decimal(0))
    a_des_montants = any(l["prevu"] is not None for l in rows)
    budget = budget_prevu(op) if a_des_montants else None
    return {
        "lignes": rows,
        "total_prevu": total_prevu if a_des_montants else None,
        "total_realise": total_realise if any(l["realise"] is not None for l in rows) else None,
        "budget_prevu": budget,
        "ecart_budget": bool(a_des_montants and budget is not None and total_prevu != budget),
    }


def bilan_financeurs_json(op) -> dict:
    """Le bilan, montants en chaînes (format DRF des décimaux)."""
    b = bilan_financeurs(op)
    return {
        "lignes": [{
            **l, "prevu": _txt(l["prevu"]), "realise": _txt(l["realise"]),
            "realise_par_annee": {str(a): _txt(m) for a, m in sorted(
                l["realise_par_annee"].items(), key=lambda kv: (kv[0] is None, kv[0] or 0))},
        } for l in b["lignes"]],
        "total_prevu": _txt(b["total_prevu"]),
        "total_realise": _txt(b["total_realise"]),
        "budget_prevu": _txt(b["budget_prevu"]),
        "ecart_budget": b["ecart_budget"],
    }
