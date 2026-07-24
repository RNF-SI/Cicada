"""
Export Excel « Fiche action » — une fiche (onglet) par opération d'un plan.

Calqué sur le modèle « Modèle_Export_CICADA_Fiche_action », qui distingue :

- **Action CS** (catégorie « Connaissance et suivi », `id_categorie_action_reserve`
  mnémonique ``CS``) : cadre indicateur d'état → niveau d'exigence → OLT → enjeu,
  avec détails du suivi / protocole ;
- **Action hors CS** (toutes les autres catégories) : cadre indicateur de pression
  → résultats attendus → OO → enjeu.

Les deux variantes partagent le volet administratif et financier (programmation
annuelle, blocs budgétaires par organisme gestionnaire, programmation mensuelle,
financeurs, indicateurs de réponse).

Point d'entrée public : :func:`build_fiche_action_workbook`.

Volet financier — note d'implémentation : le modèle de données ne stocke pas le
« coût salarial » ; on le recalcule (jours des postes × ``Poste.cout_jour``), comme
le front. La ventilation fonctionnement / investissement des jours suit
``OperationAnneeRH.categorie_depense`` ; prestataire / autres coûts / budgets
proviennent de ``OperationAnneeOrganisme`` (ou de ``OperationAnnee`` en mode sans
ventilation par organisme).
"""

from __future__ import annotations

import io
from collections import defaultdict
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .services_export_finance import build_action_finance, poste_entry_factory

# ---------------------------------------------------------------------------
# Styles (palette CICADA)
# ---------------------------------------------------------------------------

_PRIMARY = "FF025359"
_TERRA = "FFB74D5D"
_GREEN = "FF04854B"
_BEIGE = "FFF3EFEA"
_SECTION = "FF025359"
_LABEL_FILL = "FFDCE6E7"
_SUBLABEL_FILL = "FFEDF4F4"
_TOTAL_FILL = "FFC0E3CF"
_YEARHDR_FILL = "FFFEC180"
_WHITE = "FFFFFFFF"

_F_TITLE = Font(name="Calibri", bold=True, size=13, color=_WHITE)
_F_SECTION = Font(name="Calibri", bold=True, size=11, color=_WHITE)
_F_LABEL = Font(name="Calibri", bold=True, size=10, color=_PRIMARY)
_F_SUBLABEL = Font(name="Calibri", size=10, color="FF343433")
_F_VALUE = Font(name="Calibri", size=10, color="FF343433")
_F_TOTAL = Font(name="Calibri", bold=True, size=10, color=_PRIMARY)
_F_PRIO = Font(name="Calibri", bold=True, size=12, color=_WHITE)
_F_YEAR = Font(name="Calibri", bold=True, size=9, color=_PRIMARY)
_F_X = Font(name="Calibri", bold=True, size=11, color=_GREEN)

_thin = Side(style="thin", color="FFBFC9C9")
_med = Side(style="medium", color="FF9DB3B4")
_B = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_BM = Border(left=_med, right=_med, top=_med, bottom=_med)

_AL_L = Alignment(horizontal="left", vertical="center", wrap_text=True)
_AL_LT = Alignment(horizontal="left", vertical="top", wrap_text=True)
_AL_C = Alignment(horizontal="center", vertical="center", wrap_text=True)
_AL_R = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _n(value) -> Decimal:
    if value in (None, ""):
        return Decimal(0)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(0)


def _txt(value) -> str:
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value)


def _euro(value) -> str:
    d = _n(value)
    if d == 0:
        return "/"
    return f"{d:,.0f} €".replace(",", " ")


def _jours(value) -> str:
    d = _n(value)
    if d == 0:
        return "/"
    return f"{d:g}"


def _sanitize_title(title: str, used: set) -> str:
    for ch in '[]:*?/\\':
        title = title.replace(ch, " ")
    title = (title.strip() or "Action")[:31]
    base, i = title, 2
    while title.lower() in used:
        sfx = f" ({i})"
        title = base[: 31 - len(sfx)] + sfx
        i += 1
    used.add(title.lower())
    return title


# ---------------------------------------------------------------------------
# Cadre de l'action (état ou pression)
# ---------------------------------------------------------------------------

def _linked_indicateurs(op):
    inds = {}
    for met in op.metriques.all():
        if met.id_indicateur_id:
            inds[met.id_indicateur_id] = met.id_indicateur
    if op.id_indicateur_id:
        inds[op.id_indicateur_id] = op.id_indicateur
    return list(inds.values())


def _cadre(op):
    """Renvoie les libellés du cadre (métriques, indicateur, NE/RA, OLT/OO, enjeu)."""
    metriques = [_txt(m.nom_metrique) for m in op.metriques.all()]
    inds = _linked_indicateurs(op)
    indicateurs, exigences, objectifs, enjeux = [], [], [], []
    for ind in inds:
        indicateurs.append(_txt(ind.nom_indicateur))
        ne = getattr(ind, "id_ne", None)
        ra = getattr(ind, "id_resultat_attendu", None)
        if ne:
            exigences.append(_txt(ne.libelle))
            olt = getattr(ne, "id_olt", None)
            if olt:
                objectifs.append(_txt(olt.libelle))
                enj = getattr(olt, "id_enjeu", None)
                if enj:
                    enjeux.append(_txt(enj.libelle) or _txt(enj.intitule_court))
        if ra:
            exigences.append(_txt(ra.libelle))
            oo = getattr(ra, "id_oo", None)
            if oo:
                objectifs.append(_txt(oo.libelle))
                enj = getattr(oo, "id_enjeu", None)
                if enj:
                    enjeux.append(_txt(enj.libelle) or _txt(enj.intitule_court))

    def uniq(seq):
        out = []
        for s in seq:
            if s and s not in out:
                out.append(s)
        return out

    return {
        "metriques": uniq(metriques),
        "indicateurs": uniq(indicateurs),
        "exigences": uniq(exigences),
        "objectifs": uniq(objectifs),
        "enjeux": uniq(enjeux),
    }


# ---------------------------------------------------------------------------
# Volet financier
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Rendu d'une fiche
# ---------------------------------------------------------------------------

class _Writer:
    def __init__(self, ws, ncols):
        self.ws = ws
        self.ncols = ncols          # nb total de colonnes (3 + nb années)
        self.r = 1

    def section(self, text):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=self.ncols)
        c = ws.cell(self.r, 1, text)
        c.fill = PatternFill("solid", fgColor=_SECTION)
        c.font = _F_SECTION
        c.alignment = _AL_L
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _BM
        ws.row_dimensions[self.r].height = 20
        self.r += 1

    def kv(self, label, value, *, fill=_LABEL_FILL, font_label=_F_LABEL):
        """Ligne « label (A:C) | valeur (D:fin) »."""
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=3)
        lc = ws.cell(self.r, 1, label)
        lc.fill = PatternFill("solid", fgColor=fill)
        lc.font = font_label
        lc.alignment = _AL_LT
        ws.merge_cells(start_row=self.r, start_column=4, end_row=self.r, end_column=self.ncols)
        vc = ws.cell(self.r, 4, value)
        vc.font = _F_VALUE
        vc.alignment = _AL_LT
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _B
        self.r += 1

    def year_header(self, label, years):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=3)
        lc = ws.cell(self.r, 1, label)
        lc.fill = PatternFill("solid", fgColor=_LABEL_FILL)
        lc.font = _F_LABEL
        lc.alignment = _AL_L
        for i, y in enumerate(years):
            c = ws.cell(self.r, 4 + i, y)
            c.fill = PatternFill("solid", fgColor=_YEARHDR_FILL)
            c.font = _F_YEAR
            c.alignment = _AL_C
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _B
        self.r += 1

    def marks_row(self, label, flags, years):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=3)
        lc = ws.cell(self.r, 1, label)
        lc.fill = PatternFill("solid", fgColor=_SUBLABEL_FILL)
        lc.font = _F_SUBLABEL
        lc.alignment = _AL_L
        for i, y in enumerate(years):
            v = "x" if flags.get(y) else ""
            c = ws.cell(self.r, 4 + i, v)
            c.font = _F_X
            c.alignment = _AL_C
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _B
        self.r += 1

    def cost_row(self, label, values_by_year, years, *, fmt=_euro, fill=_SUBLABEL_FILL,
                 font=_F_SUBLABEL, label_font=None):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=3)
        lc = ws.cell(self.r, 1, label)
        lc.fill = PatternFill("solid", fgColor=fill)
        lc.font = label_font or _F_SUBLABEL
        lc.alignment = _AL_L
        for i, y in enumerate(years):
            c = ws.cell(self.r, 4 + i, fmt(values_by_year.get(y, 0)))
            c.font = font
            c.alignment = _AL_R
            c.fill = PatternFill("solid", fgColor=fill) if fill == _TOTAL_FILL else PatternFill()
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _B
        self.r += 1

    def org_banner(self, text):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=self.ncols)
        c = ws.cell(self.r, 1, text)
        c.fill = PatternFill("solid", fgColor=_PRIMARY)
        c.font = Font(name="Calibri", bold=True, size=10, color=_WHITE)
        c.alignment = _AL_L
        for col in range(1, self.ncols + 1):
            ws.cell(self.r, col).border = _B
        self.r += 1

    def blank(self):
        self.r += 1


def _render_action(ws, op, years, *, is_cs):
    ncols = 3 + len(years)
    w = _Writer(ws, ncols)
    # largeurs
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 16
    for i in range(len(years)):
        ws.column_dimensions[get_column_letter(4 + i)].width = 11

    # ---- En-tête : code / intitulé / priorité ----
    ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=ncols - 2)
    hc = ws.cell(w.r, 1, _txt(op.libelle))
    hc.fill = PatternFill("solid", fgColor=_PRIMARY)
    hc.font = _F_TITLE
    hc.alignment = _AL_L
    ws.merge_cells(start_row=w.r, start_column=ncols - 1, end_row=w.r, end_column=ncols)
    prio = op.id_priorite.label if op.id_priorite_id else ""
    pc = ws.cell(w.r, ncols - 1, prio or "Priorité —")
    pc.fill = PatternFill("solid", fgColor=_TERRA)
    pc.font = _F_PRIO
    pc.alignment = _AL_C
    for col in range(1, ncols + 1):
        ws.cell(w.r, col).border = _BM
    ws.row_dimensions[w.r].height = 22
    w.r += 1
    code = _txt(op.code_operation) or (f"n° {op.numero_manuel}" if op.numero_manuel else "")
    w.kv("Code action", code)

    # ---- 1) Cadre de l'action ----
    w.section("1) Cadre de l'action")
    cadre = _cadre(op)
    w.kv("Métriques", " ; ".join(cadre["metriques"]))
    w.kv("Indicateur d'état" if is_cs else "Indicateur de pression", " ; ".join(cadre["indicateurs"]))
    w.kv("Niveau d'exigence" if is_cs else "Résultats attendus", " ; ".join(cadre["exigences"]))
    w.kv("OLT" if is_cs else "Objectif opérationnel", " ; ".join(cadre["objectifs"]))
    w.kv("Enjeu", " ; ".join(cadre["enjeux"]))

    # ---- 2) Détails de l'opération ----
    w.section("2) Détails de l'opération")
    details = _txt(op.description)
    if is_cs:
        protos = []
        suivi = getattr(op, "id_suivi", None)
        if suivi:
            for pr in suivi.protocoles.all():
                nom = _txt(getattr(pr, "protocole_campanule_nom", "")) or _txt(getattr(pr, "nom_protocole", ""))
                if nom:
                    protos.append(nom)
        if protos:
            details = (details + "\n" if details else "") + "Protocole(s) : " + " ; ".join(protos)
        w.kv("Détails du suivi", details)
    else:
        w.kv("Détails de l'action", details)
    w.kv("Opérateurs", _txt(op.operateurs))
    w.kv("Partenaires", _txt(op.partenaires))

    # ---- 3) Volet administratif et financier ----
    w.section("3) Détail du volet administratif et financier de l'opération")

    # #607 Q4 : la fiche action est **prévisionnelle** (actions saisies, pas le suivi).
    from .models_operations import OperationAnnee
    annees = {oa.annee: oa for oa in OperationAnnee.objects.filter(id_operation=op)}
    prev_flags = {y: bool(getattr(oa, "periodicite", False)) for y, oa in annees.items()}
    w.year_header("Programmation annuelle", years)
    w.marks_row("Périodicité", prev_flags, years)

    org_names: dict = {}
    af = build_action_finance(op, org_names, defaultdict(poste_entry_factory))

    def cost_block(title, cell_for, *, org_ventilated):
        """Rend un bloc fonctionnement/investissement/total pour un organisme
        (ou pour l'opération entière si non ventilée)."""
        w.org_banner(title)
        # Fonctionnement
        w.cost_row("Travail prévisionnel (jours) — fonctionnement", {y: cell_for(y).j_fonct for y in years}, years, fmt=_jours)
        w.cost_row("Coût salarial — fonctionnement", {y: cell_for(y).sal_fonct for y in years}, years)
        w.cost_row("Coût prestataire — fonctionnement", {y: cell_for(y).prest_fonct for y in years}, years)
        w.cost_row("Autres coûts de fonctionnement", {y: cell_for(y).autre_fonct for y in years}, years)
        w.cost_row("Total Budget de fonctionnement (€)", {y: cell_for(y).tot_fonct for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
        # Investissement
        w.cost_row("Travail prévisionnel (jours) — investissement", {y: cell_for(y).j_invest for y in years}, years, fmt=_jours)
        w.cost_row("Coût salarial — investissement", {y: cell_for(y).sal_invest for y in years}, years)
        w.cost_row("Coût prestataire — investissement", {y: cell_for(y).prest_invest for y in years}, years)
        w.cost_row("Autres coûts d'investissement", {y: cell_for(y).autre_invest for y in years}, years)
        w.cost_row("Total Budget d'investissement (€)", {y: cell_for(y).tot_invest for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
        w.cost_row("Budget total (€)", {y: cell_for(y).tot for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)

    # #607 Q3 : ventilation par organisme uniquement si le mode le prévoit.
    if af.is_org_ventilated:
        real_orgs = [oid for oid in af.org_ids() if oid != 0]
        for idx, oid in enumerate(real_orgs, 1):
            cost_block(
                f"Organisme gestionnaire {idx} — {org_names.get(oid, '')}",
                lambda y, oid=oid: af.cell(oid, y),
                org_ventilated=True,
            )
        # TOTAL tous organismes
        if len(real_orgs) > 1:
            w.org_banner("TOTAL")
            w.cost_row("Travail prévisionnel (jours)", {y: af.year_total(y).jours for y in years}, years, fmt=_jours, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
            w.cost_row("Budget de fonctionnement (€)", {y: af.year_total(y).tot_fonct for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
            w.cost_row("Budget d'investissement (€)", {y: af.year_total(y).tot_invest for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
            w.cost_row("Budget total (€)", {y: af.year_total(y).tot for y in years}, years, fill=_TOTAL_FILL, font=_F_TOTAL, label_font=_F_TOTAL)
    else:
        cost_block("Budget de l'opération", lambda y: af.year_total(y), org_ventilated=False)

    w.cost_row("Jours bénévoles / partenaires", {y: af.year_total(y).j_benevole for y in years}, years, fmt=_jours)

    # Programmation mensuelle (agrégée : mois programmé sur au moins une année)
    w.blank()
    months = ["Janv", "Fév", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
    month_flags = _monthly_flags(op, annees)
    _render_monthly(w, months, month_flags)

    # Financeurs
    financeurs = []
    for f in op.finances.all():
        lbl = _txt(f.libelle)
        cat = _txt(getattr(getattr(f, "id_categorie", None), "label", ""))
        financeurs.append(" — ".join(x for x in (lbl, cat) if x))
    if _txt(op.financeurs):
        financeurs.append(_txt(op.financeurs))
    w.kv("Financeurs et types de financement", " ; ".join(financeurs), fill=_LABEL_FILL)

    # Indicateurs de réponse
    reponses = []
    for ind in _linked_indicateurs(op):
        t = getattr(ind, "type_indicateur", None)
        if t and (t.mnemonique or "").upper() == "REPONSE":
            reponses.append(_txt(ind.nom_indicateur))
    # + indicateurs réponse partageant le même NE/RA que l'action
    reponses += _sibling_reponse_indicateurs(op)
    reponses = list(dict.fromkeys([r for r in reponses if r]))
    w.kv("Indicateurs de réponse", " ; ".join(reponses), fill=_LABEL_FILL)

    ws.sheet_view.showGridLines = False


def _monthly_flags(op, annees):
    flags = {m: False for m in range(1, 13)}
    default = op.programmation_mensuelle_defaut or {}
    for m, v in (default.items() if isinstance(default, dict) else []):
        if v:
            flags[int(m)] = True
    for oa in annees.values():
        pm = getattr(oa, "periodicite_mensuelle", None) or {}
        if isinstance(pm, dict):
            for m, v in pm.items():
                if v:
                    flags[int(m)] = True
    return flags


def _render_monthly(w, months, month_flags):
    ws = w.ws
    ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=3)
    lc = ws.cell(w.r, 1, "Programmation mensuelle")
    lc.fill = PatternFill("solid", fgColor=_LABEL_FILL)
    lc.font = _F_LABEL
    lc.alignment = _AL_L
    # 12 mois répartis sur les colonnes disponibles à partir de D
    for i, name in enumerate(months):
        col = 4 + i
        if col > w.ncols:
            break
        c = ws.cell(w.r, col, name)
        c.fill = PatternFill("solid", fgColor=_YEARHDR_FILL)
        c.font = _F_YEAR
        c.alignment = _AL_C
    for col in range(1, w.ncols + 1):
        ws.cell(w.r, col).border = _B
    w.r += 1
    ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=3)
    lc = ws.cell(w.r, 1, "Périodicité")
    lc.fill = PatternFill("solid", fgColor=_SUBLABEL_FILL)
    lc.font = _F_SUBLABEL
    lc.alignment = _AL_L
    for i in range(12):
        col = 4 + i
        if col > w.ncols:
            break
        c = ws.cell(w.r, col, "x" if month_flags.get(i + 1) else "")
        c.font = _F_X
        c.alignment = _AL_C
    for col in range(1, w.ncols + 1):
        ws.cell(w.r, col).border = _B
    w.r += 1


def _sibling_reponse_indicateurs(op):
    """Indicateurs de type Réponse partageant le NE ou RA de l'action."""
    out = []
    for ind in _linked_indicateurs(op):
        ne = getattr(ind, "id_ne", None)
        ra = getattr(ind, "id_resultat_attendu", None)
        if ne:
            for sib in ne.indicateurs.all():
                t = getattr(sib, "type_indicateur", None)
                if t and (t.mnemonique or "").upper() == "REPONSE":
                    out.append(_txt(sib.nom_indicateur))
        if ra:
            for sib in ra.indicateurs.all():
                t = getattr(sib, "type_indicateur", None)
                if t and (t.mnemonique or "").upper() == "REPONSE":
                    out.append(_txt(sib.nom_indicateur))
    return out


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def _is_cs(op) -> bool:
    cat = getattr(op, "id_categorie_action_reserve", None)
    return bool(cat and (cat.mnemonique or "").upper() == "CS")


def build_fiche_action_workbook(plan) -> bytes:
    """Construit le classeur des fiches action (un onglet par opération)."""
    from .models_operations import Operation

    y0 = plan.annee_debut or 0
    y1 = plan.annee_fin or y0
    years = list(range(y0, y1 + 1)) if y0 else []
    if not years:
        years = [""]

    ops = (
        Operation.objects
        .filter(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
        .select_related("id_priorite", "id_categorie_action_reserve", "id_indicateur",
                        "id_suivi")
        .prefetch_related(
            "metriques__id_indicateur__id_ne__id_olt__id_enjeu",
            "metriques__id_indicateur__id_resultat_attendu__id_oo",
            "finances__id_categorie", "id_suivi__protocoles",
        )
        .distinct()
    )
    # + opérations rattachées directement à un indicateur (#367)
    ops_direct = (
        Operation.objects
        .filter(id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
        .exclude(id_operation__in=[o.id_operation for o in ops])
        .distinct()
    )
    all_ops = list(ops) + list(ops_direct)
    all_ops.sort(key=lambda o: (_txt(o.code_operation), o.id_operation))

    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    if not all_ops:
        ws = wb.create_sheet(_sanitize_title("Actions", used))
        ws["A1"] = "Ce plan ne contient pas encore d'action."
        ws["A1"].font = Font(bold=True, size=12, color=_PRIMARY)
    for op in all_ops:
        is_cs = _is_cs(op)
        code = _txt(op.code_operation) or f"Action {op.id_operation}"
        ws = wb.create_sheet(_sanitize_title(code, used))
        _render_action(ws, op, years, is_cs=is_cs)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
