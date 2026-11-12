"""
Export Excel « Planification annuelle » d'un plan pour une année (#794).

Calqué sur les budget et RH prévisionnels, réduit à l'année choisie : pour
chaque action, la programmation du plan de gestion (la référence), la
programmation ajustée de l'année et l'écart.

- ``Budget`` : une ligne par action (puis un onglet par organisme gestionnaire
  quand une action ventile son budget par organisme) — plan de gestion, ajusté,
  écart, et la part fonctionnement / investissement de l'ajusté quand une
  action distingue les types de budget ;
- ``RH`` : temps de travail des agents (jours), même découpage, et le temps
  bénévole ou partenaire à part ;
- ``Financeurs`` : montant prévu par le plan (global sur l'action, #790) et
  montant de l'année ajustée ;
- ``Calendrier`` : statut de l'année et mois de réalisation, ajustés (●) et du
  plan (○).

Mêmes calculs que la page « Ajustement planification annuelle » et que les
exports budget / RH : ``build_action_finance`` (avec et sans les
ajustements), ``Planification`` pour le statut, les mois et les reports.

Point d'entrée public : :func:`build_planification_annuelle_workbook`.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from . import services_export_budget_rh as br
from .services_export_finance import (
    GLOBAL_YEAR, build_action_finance, build_plan_finance, poste_entry_factory,
)

_ZERO = Decimal(0)
_EURO = '#,##0 "€"'
_JOURS = '0.0'
_MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.",
         "Nov.", "Déc."]
_IDENT = ["Enjeu / FCR", "Code simplifié", "Code action PG", "Libellé de l'action", "Statut"]

STATUTS = {
    "planifiee": "Planifiée",
    "non_prevue": "Non prévue",
    "reportee": "Reportée en {annee}",
    "reportee_partiel": "Reste reporté en {annee}",
}


def statut_libelle(resume) -> str:
    """Libellé du statut ajusté de l'année (comme la page de l'ajustement)."""
    cle = resume["statut"]
    if cle == "planifiee" and resume.get("annee_report"):
        cle = "reportee_partiel"
    return STATUTS[cle].format(annee=resume.get("annee_report"))


class _Feuille:
    """Une feuille : titre, en-tête, lignes d'action, total."""

    def __init__(self, wb, used, nom, plan, sous_titre, colonnes):
        self.ws = wb.create_sheet(br._title(nom, used))
        self.colonnes = colonnes
        n = len(_IDENT) + len(colonnes)
        widths = {1: 18, 2: 12, 3: 14, 4: 44, 5: 18}
        for c in range(1, n + 1):
            self.ws.column_dimensions[get_column_letter(c)].width = widths.get(c, 14)
        self.ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
        br._set(self.ws, 1, 1, br._plan_title(plan), font=br._F_TITLE, align=br._AL_L)
        self.ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n)
        br._set(self.ws, 2, 1, sous_titre, font=br._F_SUB, align=br._AL_L)
        for c, titre in enumerate(_IDENT + [t for t, _f in colonnes], start=1):
            br._set(self.ws, 3, c, titre, fill=br._HDR_FILL, font=br._F_HDR, align=br._AL_C)
        self.r = 4
        self.totaux = [_ZERO] * len(colonnes)
        self.ws.freeze_panes = self.ws.cell(4, len(_IDENT) + 1).coordinate
        self.ws.sheet_view.showGridLines = False

    def ligne(self, ident, valeurs):
        for c, v in enumerate(ident, start=1):
            br._set(self.ws, self.r, c, v, align=br._AL_C if c in (2, 3) else br._AL_L)
        for i, (v, (_t, fmt)) in enumerate(zip(valeurs, self.colonnes)):
            cell = br._set(self.ws, self.r, len(_IDENT) + 1 + i, v)
            if isinstance(v, Decimal):
                cell.number_format = fmt
                self.totaux[i] += v
        self.r += 1

    def total(self, libelle="TOTAL"):
        self.ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=len(_IDENT))
        br._set(self.ws, self.r, 1, libelle, fill=br._TOTAL_FILL, font=br._F_TOTAL, align=br._AL_L)
        for i, (v, (_t, fmt)) in enumerate(zip(self.totaux, self.colonnes)):
            cell = br._set(self.ws, self.r, len(_IDENT) + 1 + i, v,
                           fill=br._TOTAL_FILL, font=br._F_TOTAL)
            cell.number_format = fmt


def _ident(af, statut):
    return [af.enjeu_label, af.categorie, af.code, af.libelle, statut]


def build_planification_annuelle_workbook(plan, annee) -> bytes:
    from .planification_annuelle import Planification, ajustements_par_annee

    br._appliquer_couleur_instance()
    pf = build_plan_finance(plan)
    operations = [af.op for af in pf.actions]
    ajustements = ajustements_par_annee([op.pk for op in operations])
    org_names = dict(pf.org_names)
    ajustees = {
        af.op.pk: build_action_finance(af.op, org_names, defaultdict(poste_entry_factory),
                                       ajustements=ajustements)
        for af in pf.actions}
    planif = Planification(plan, operations)

    statuts, resumes = {}, {}
    for af in pf.actions:
        op_id = af.op.pk
        resume = planif.resume(op_id, planif.effectif(op_id, annee))
        resumes[op_id] = resume
        entrants = planif.reports_entrants(op_id, annee)
        statut = statut_libelle(resume)
        if entrants:
            statut += " ; " + ", ".join(
                f"{'reste' if e['partiel'] else 'report'} de {e['annee']}" for e in entrants)
        statuts[op_id] = statut

    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    _feuilles_budget(wb, used, plan, pf, ajustees, statuts, annee, org_names)
    _feuille_rh(wb, used, plan, pf, ajustees, statuts, annee)
    _feuille_financeurs(wb, used, plan, pf, planif, annee)
    _feuille_calendrier(wb, used, plan, pf, planif, statuts, annee)
    return br._save(wb)


def _prevu_pg(af, cellule, attr):
    """Prévu du plan pour l'année ; programmation globale : « … sur la période »."""
    if af.is_global:
        periode = getattr(af.year_total(GLOBAL_YEAR), attr)
        return f"{br._fmt_euro(periode) if attr != 'jours' else br._fmt_jours(periode)} sur la période"
    return getattr(cellule, attr)


def _ecart(pg, ajuste):
    return ajuste - pg if isinstance(pg, Decimal) else None


def _feuilles_budget(wb, used, plan, pf, ajustees, statuts, annee, org_names):
    colonnes = [("Plan de gestion", _EURO), (f"Ajusté {annee}", _EURO), ("Écart", _EURO)]
    if pf.has_type_budget:
        colonnes += [("dont fonctionnement (ajusté)", _EURO), ("dont investissement (ajusté)", _EURO)]

    def remplir(feuille, cellule_de):
        for af in pf.actions:
            pg, aj = cellule_de(af, af), cellule_de(af, ajustees[af.op.pk])
            prevu = _prevu_pg(af, pg, "tot")
            if not aj.tot and not (pg.tot if not af.is_global else 0):
                continue
            valeurs = [prevu, aj.tot, _ecart(prevu, aj.tot)]
            if pf.has_type_budget:
                valeurs += [aj.tot_fonct, aj.tot_invest]
            feuille.ligne(_ident(af, statuts[af.op.pk]), valeurs)
        feuille.total()

    total = _Feuille(wb, used, f"Budget {annee}", plan,
                     f"BUDGET {annee} (€) — plan de gestion et planification ajustée — tous organismes",
                     colonnes)
    remplir(total, lambda af, source: source.year_total(annee))
    if pf.is_org_ventilated:
        for oid in sorted({oid for a in ajustees.values() for (oid, _y) in a.cells} | set(pf.org_ids()),
                          key=lambda i: (i == 0, org_names.get(i, ""))):
            nom = org_names.get(oid, "Non ventilé")
            feuille = _Feuille(wb, used, f"Budget {annee} — {nom}", plan,
                               f"BUDGET {annee} (€) — {nom}", colonnes)
            remplir(feuille, lambda af, source, oid=oid: source.cell(oid, annee))


def _feuille_rh(wb, used, plan, pf, ajustees, statuts, annee):
    colonnes = [("Plan de gestion (j)", _JOURS), (f"Ajusté {annee} (j)", _JOURS), ("Écart (j)", _JOURS),
                ("Bénévolat / partenariat ajusté (j)", _JOURS)]
    feuille = _Feuille(wb, used, f"RH {annee}", plan,
                       f"RESSOURCES HUMAINES {annee} (jours d'agents) — plan de gestion et "
                       "planification ajustée", colonnes)
    for af in pf.actions:
        pg, aj = af.year_total(annee), ajustees[af.op.pk].year_total(annee)
        prevu = _prevu_pg(af, pg, "jours")
        if not (aj.jours or aj.j_benevole) and not (pg.jours if not af.is_global else 0):
            continue
        feuille.ligne(_ident(af, statuts[af.op.pk]),
                      [prevu, aj.jours, _ecart(prevu, aj.jours), aj.j_benevole])
    feuille.total()


def _feuille_financeurs(wb, used, plan, pf, planif, annee):
    from .models_operations import FinanceOperation, Financeur

    colonnes = [("Plan de gestion (sur l'action)", _EURO), (f"Prévu {annee} (ajusté)", _EURO)]
    feuille = _Feuille(wb, used, "Financeurs", plan,
                       f"FINANCEURS — montants prévus {annee} par action", colonnes)
    br._set(feuille.ws, 3, 5, "Financeur", fill=br._HDR_FILL, font=br._F_HDR, align=br._AL_C)
    noms = dict(Financeur.objects.filter(id_pg=plan).values_list("pk", "nom"))
    for af in pf.actions:
        pg = dict(FinanceOperation.objects.filter(id_operation=af.op, id_financeur__isnull=False)
                  .values_list("id_financeur", "montant"))
        ajuste = {f["id_financeur"]: f["montant"]
                  for f in planif.effectif(af.op.pk, annee)["financeurs"]}
        for fid in sorted(set(pg) | set(ajuste), key=lambda i: noms.get(i, "")):
            montant_pg, montant = pg.get(fid), ajuste.get(fid)
            feuille.ligne(_ident(af, noms.get(fid, "")),
                          [Decimal(montant_pg) if montant_pg is not None else "—",
                           Decimal(montant) if montant is not None else "—"])
    feuille.total()


def _feuille_calendrier(wb, used, plan, pf, planif, statuts, annee):
    colonnes = [(m, "@") for m in _MOIS]
    feuille = _Feuille(wb, used, "Calendrier", plan,
                       f"CALENDRIER {annee} — ● mois de la planification ajustée, "
                       "○ mois du plan de gestion seul", colonnes)
    for c in range(len(_IDENT) + 1, len(_IDENT) + 13):
        feuille.ws.column_dimensions[get_column_letter(c)].width = 6
    for af in pf.actions:
        op_id = af.op.pk
        ajustes = set(planif.resume(op_id, planif.effectif(op_id, annee))["mois"])
        du_plan = set(planif.resume(op_id, planif.pg(op_id, annee))["mois"])
        if not ajustes and not du_plan:
            continue
        valeurs = ["●" if m in ajustes else "○" if m in du_plan else "" for m in range(1, 13)]
        feuille.ligne(_ident(af, statuts[op_id]), valeurs)
    for row in feuille.ws.iter_rows(min_row=4, min_col=len(_IDENT) + 1):
        for cell in row:
            cell.alignment = br._AL_C
