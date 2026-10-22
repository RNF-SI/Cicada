"""
Exports Excel **Budget** et **RH**, en **prévisionnel** et en **suivi**.

Quatre classeurs calqués sur les modèles CICADA :

- ``build_rh_previsionnel_workbook`` — jours prévisionnels par organisme
  gestionnaire (1 onglet / OG), TOTAL, et synthèse par type de poste ;
- ``build_rh_suivi_workbook`` — idem avec colonnes Prévu / Réalisé par année ;
- ``build_budget_previsionnel_workbook`` — budget prévisionnel par OG
  (sections Fonctionnement / Investissement), TOTAL, synthèse par poste de dépense ;
- ``build_budget_suivi_workbook`` — idem avec colonnes Prévu / Réalisé.

Toute la logique de coûts provient du module partagé
:mod:`apps.plans.services_export_finance`.
"""

from __future__ import annotations

import io
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import export_theme
from .services_export_finance import build_plan_finance, year_label

_ZERO = Decimal(0)

# --- styles ---
_PRIMARY = "FF025359"
_WHITE = "FFFFFFFF"
_HDR_FILL = "FF025359"
_YEAR_FILL = "FFFEC180"
_SECTION_FILL = "FFDCE6E7"
_TOTAL_FILL = "FFC0E3CF"

_F_TITLE = Font(name="Calibri", bold=True, size=13, color=_PRIMARY)
_F_SUB = Font(name="Calibri", bold=True, size=10, color="FF746F6E")
_F_HDR = Font(name="Calibri", bold=True, size=9, color=_WHITE)
_F_YEAR = Font(name="Calibri", bold=True, size=9, color=_PRIMARY)
_F_CELL = Font(name="Calibri", size=9, color="FF343433")
_F_SECTION = Font(name="Calibri", bold=True, size=10, color=_PRIMARY)
_F_TOTAL = Font(name="Calibri", bold=True, size=9, color=_PRIMARY)


def _appliquer_couleur_instance():
    """Réaligne les styles sur la couleur d'export de l'instance (#601)."""
    global _PRIMARY, _HDR_FILL, _F_TITLE, _F_YEAR, _F_SECTION, _F_TOTAL

    couleur = export_theme.argb()
    if couleur == _PRIMARY:
        return
    _PRIMARY = _HDR_FILL = couleur
    _F_TITLE = Font(name="Calibri", bold=True, size=13, color=couleur)
    _F_YEAR = Font(name="Calibri", bold=True, size=9, color=couleur)
    _F_SECTION = Font(name="Calibri", bold=True, size=10, color=couleur)
    _F_TOTAL = Font(name="Calibri", bold=True, size=9, color=couleur)

_thin = Side(style="thin", color="FFBFC9C9")
_B = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_AL_L = Alignment(horizontal="left", vertical="center", wrap_text=True)
_AL_C = Alignment(horizontal="center", vertical="center", wrap_text=True)
_AL_R = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _fmt_jours(v) -> str:
    v = v or _ZERO
    if v == 0:
        return "0"
    return f"{v:g}"


def _fmt_euro(v) -> str:
    v = v or _ZERO
    return f"{v:,.0f}".replace(",", " ")


def _title(name: str, used: set) -> str:
    for ch in '[]:*?/\\':
        name = name.replace(ch, " ")
    name = (name.strip() or "Feuille")[:31]
    base, i = name, 2
    while name.lower() in used:
        sfx = f" ({i})"
        name = base[: 31 - len(sfx)] + sfx
        i += 1
    used.add(name.lower())
    return name


def _plan_title(plan) -> str:
    nom = (plan.nom or "").strip() or f"Plan {plan.id_pg}"
    return f"PLAN DE GESTION {plan.annee_debut}-{plan.annee_fin_effective} — {nom}".upper()


def _set(ws, r, c, value, *, fill=None, font=_F_CELL, align=_AL_R):
    cell = ws.cell(r, c, value)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = font
    cell.alignment = align
    cell.border = _B
    return cell


# ---------------------------------------------------------------------------
# Matrice « actions » (A-D + colonnes années) avec sections
# ---------------------------------------------------------------------------

class _ActionMatrix:
    """Feuille : Enjeu/FCR | Code simplifié | Code action PG | Libellé | années | TOTAL."""

    HEADERS = ["Enjeu / FCR", "Code simplifié", "Code action PG", "Libellé de l'action"]

    def __init__(self, ws, years, *, suivi, fmt):
        self.ws = ws
        self.years = years
        self.suivi = suivi
        self.fmt = fmt
        self.ncols = 4 + (2 * len(years) + 2 if suivi else len(years) + 1)
        self.r = 1
        widths = {1: 18, 2: 13, 3: 15, 4: 44}
        for c in range(5, self.ncols + 1):
            widths[c] = 10
        for c, w in widths.items():
            ws.column_dimensions[get_column_letter(c)].width = w

    # --- positions colonnes ---
    def _yc(self, i, real=False):
        if self.suivi:
            return 5 + 2 * i + (1 if real else 0)
        return 5 + i

    def _tc(self, real=False):
        if self.suivi:
            return 5 + 2 * len(self.years) + (1 if real else 0)
        return 5 + len(self.years)

    def head(self, title, subtitle):
        ws = self.ws
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=self.ncols)
        c = ws.cell(1, 1, title); c.font = _F_TITLE; c.alignment = _AL_L
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=self.ncols)
        c = ws.cell(2, 1, subtitle); c.font = _F_SUB; c.alignment = _AL_L
        self.r = 3
        hr = self.r
        # colonnes A-D (fusion sur 2 lignes en mode suivi)
        for i, h in enumerate(self.HEADERS):
            col = i + 1
            if self.suivi:
                ws.merge_cells(start_row=hr, start_column=col, end_row=hr + 1, end_column=col)
            _set(ws, hr, col, h, fill=_HDR_FILL, font=_F_HDR, align=_AL_C)
        # années
        for i, y in enumerate(self.years):
            if self.suivi:
                ws.merge_cells(start_row=hr, start_column=self._yc(i), end_row=hr, end_column=self._yc(i, True))
            _set(ws, hr, self._yc(i), str(year_label(y)), fill=_YEAR_FILL, font=_F_YEAR, align=_AL_C)
        if self.suivi:
            ws.merge_cells(start_row=hr, start_column=self._tc(), end_row=hr, end_column=self._tc(True))
        _set(ws, hr, self._tc(), "TOTAL", fill=_YEAR_FILL, font=_F_YEAR, align=_AL_C)
        if self.suivi:
            # sous-en-tête Prévu / Réalisé
            for i in range(len(self.years)):
                _set(ws, hr + 1, self._yc(i), "Prévu", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
                _set(ws, hr + 1, self._yc(i, True), "Réalisé", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            _set(ws, hr + 1, self._tc(), "Prévu", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            _set(ws, hr + 1, self._tc(True), "Réalisé", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            self.r = hr + 2
        else:
            self.r = hr + 1

    def section(self, label):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=self.ncols)
        _set(ws, self.r, 1, f"► {label}", fill=_SECTION_FILL, font=_F_SECTION, align=_AL_L)
        self.r += 1

    def row(self, enjeu, cat, code, libelle, prev, real=None):
        ws = self.ws
        _set(ws, self.r, 1, enjeu, font=_F_CELL, align=_AL_L)
        _set(ws, self.r, 2, cat, font=_F_CELL, align=_AL_C)
        _set(ws, self.r, 3, code, font=_F_CELL, align=_AL_C)
        _set(ws, self.r, 4, libelle, font=_F_CELL, align=_AL_L)
        tp = _ZERO
        tr = _ZERO
        for i, y in enumerate(self.years):
            pv = prev.get(y, _ZERO)
            tp += pv
            _set(ws, self.r, self._yc(i), self.fmt(pv))
            if self.suivi:
                rv = (real or {}).get(y, _ZERO)
                tr += rv
                _set(ws, self.r, self._yc(i, True), self.fmt(rv))
        _set(ws, self.r, self._tc(), self.fmt(tp), fill=_TOTAL_FILL, font=_F_TOTAL)
        if self.suivi:
            _set(ws, self.r, self._tc(True), self.fmt(tr), fill=_TOTAL_FILL, font=_F_TOTAL)
        self.r += 1

    def total(self, label, prev, real=None):
        ws = self.ws
        ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=4)
        _set(ws, self.r, 1, label, fill=_TOTAL_FILL, font=_F_TOTAL, align=_AL_L)
        tp = tr = _ZERO
        for i, y in enumerate(self.years):
            pv = prev.get(y, _ZERO); tp += pv
            _set(ws, self.r, self._yc(i), self.fmt(pv), fill=_TOTAL_FILL, font=_F_TOTAL)
            if self.suivi:
                rv = (real or {}).get(y, _ZERO); tr += rv
                _set(ws, self.r, self._yc(i, True), self.fmt(rv), fill=_TOTAL_FILL, font=_F_TOTAL)
        _set(ws, self.r, self._tc(), self.fmt(tp), fill=_TOTAL_FILL, font=_F_TOTAL)
        if self.suivi:
            _set(ws, self.r, self._tc(True), self.fmt(tr), fill=_TOTAL_FILL, font=_F_TOTAL)
        self.r += 1

    def freeze(self):
        self.ws.freeze_panes = self.ws.cell(4 if not self.suivi else 5, 5).coordinate
        self.ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# Matrice « synthèse » (libellé [+ coût/jour] + colonnes années)
# ---------------------------------------------------------------------------

class _LabelMatrix:
    def __init__(self, ws, years, *, suivi, fmt, label_header="Type de poste", cout_col=False):
        self.ws = ws
        self.years = years
        self.suivi = suivi
        self.fmt = fmt
        self.cout_col = cout_col
        self.base = 2 + (1 if cout_col else 0)   # 1ère colonne année
        self.ncols = (self.base - 1) + (2 * len(years) + 2 if suivi else len(years) + 1)
        self.r = 1
        ws.column_dimensions["A"].width = 32
        if cout_col:
            ws.column_dimensions["B"].width = 11
        for c in range(self.base, self.ncols + 1):
            ws.column_dimensions[get_column_letter(c)].width = 10
        self.label_header = label_header

    def _yc(self, i, real=False):
        if self.suivi:
            return self.base + 2 * i + (1 if real else 0)
        return self.base + i

    def _tc(self, real=False):
        if self.suivi:
            return self.base + 2 * len(self.years) + (1 if real else 0)
        return self.base + len(self.years)

    def head(self, title, subtitle):
        ws = self.ws
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=self.ncols)
        c = ws.cell(1, 1, title); c.font = _F_TITLE; c.alignment = _AL_L
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=self.ncols)
        c = ws.cell(2, 1, subtitle); c.font = _F_SUB; c.alignment = _AL_L
        hr = 3
        if self.suivi:
            ws.merge_cells(start_row=hr, start_column=1, end_row=hr + 1, end_column=1)
        _set(ws, hr, 1, self.label_header, fill=_HDR_FILL, font=_F_HDR, align=_AL_C)
        if self.cout_col:
            if self.suivi:
                ws.merge_cells(start_row=hr, start_column=2, end_row=hr + 1, end_column=2)
            _set(ws, hr, 2, "Coût/jour", fill=_HDR_FILL, font=_F_HDR, align=_AL_C)
        for i, y in enumerate(self.years):
            if self.suivi:
                ws.merge_cells(start_row=hr, start_column=self._yc(i), end_row=hr, end_column=self._yc(i, True))
            _set(ws, hr, self._yc(i), str(year_label(y)), fill=_YEAR_FILL, font=_F_YEAR, align=_AL_C)
        if self.suivi:
            ws.merge_cells(start_row=hr, start_column=self._tc(), end_row=hr, end_column=self._tc(True))
        _set(ws, hr, self._tc(), "TOTAL", fill=_YEAR_FILL, font=_F_YEAR, align=_AL_C)
        if self.suivi:
            for i in range(len(self.years)):
                _set(ws, hr + 1, self._yc(i), "Prévu", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
                _set(ws, hr + 1, self._yc(i, True), "Réalisé", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            _set(ws, hr + 1, self._tc(), "Prévu", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            _set(ws, hr + 1, self._tc(True), "Réalisé", fill=_SECTION_FILL, font=_F_TOTAL, align=_AL_C)
            self.r = hr + 2
        else:
            self.r = hr + 1

    def section(self, label, prev=None, real=None):
        ws = self.ws
        if prev is None:
            # En-tête simple, sans valeur : on fusionne toute la ligne.
            ws.merge_cells(start_row=self.r, start_column=1, end_row=self.r, end_column=self.ncols)
            _set(ws, self.r, 1, f"► {label}", fill=_SECTION_FILL, font=_F_SECTION, align=_AL_L)
            self.r += 1
            return
        # #618 — en-tête AVEC sous-total par année (total du poste de dépense).
        _set(ws, self.r, 1, f"► {label}", fill=_SECTION_FILL, font=_F_SECTION, align=_AL_L)
        if self.cout_col:
            _set(ws, self.r, 2, "", fill=_SECTION_FILL, font=_F_SECTION, align=_AL_C)
        tp = tr = _ZERO
        for i, y in enumerate(self.years):
            pv = prev.get(y, _ZERO); tp += pv
            _set(ws, self.r, self._yc(i), self.fmt(pv), fill=_SECTION_FILL, font=_F_SECTION)
            if self.suivi:
                rv = (real or {}).get(y, _ZERO); tr += rv
                _set(ws, self.r, self._yc(i, True), self.fmt(rv), fill=_SECTION_FILL, font=_F_SECTION)
        _set(ws, self.r, self._tc(), self.fmt(tp), fill=_SECTION_FILL, font=_F_SECTION)
        if self.suivi:
            _set(ws, self.r, self._tc(True), self.fmt(tr), fill=_SECTION_FILL, font=_F_SECTION)
        self.r += 1

    def row(self, label, prev, real=None, *, cout=None, total_style=False):
        ws = self.ws
        fill = _TOTAL_FILL if total_style else None
        font = _F_TOTAL if total_style else _F_CELL
        _set(ws, self.r, 1, label, fill=fill, font=font, align=_AL_L)
        if self.cout_col:
            _set(ws, self.r, 2, ("" if cout in (None, "") else self.fmt(cout) if False else cout), fill=fill, font=font, align=_AL_C)
        tp = tr = _ZERO
        for i, y in enumerate(self.years):
            pv = prev.get(y, _ZERO); tp += pv
            _set(ws, self.r, self._yc(i), self.fmt(pv), fill=fill, font=font)
            if self.suivi:
                rv = (real or {}).get(y, _ZERO); tr += rv
                _set(ws, self.r, self._yc(i, True), self.fmt(rv), fill=fill, font=font)
        _set(ws, self.r, self._tc(), self.fmt(tp), fill=_TOTAL_FILL, font=_F_TOTAL)
        if self.suivi:
            _set(ws, self.r, self._tc(True), self.fmt(tr), fill=_TOTAL_FILL, font=_F_TOTAL)
        self.r += 1

    def freeze(self):
        self.ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# Agrégations plan
# ---------------------------------------------------------------------------

def _sum_years(seq_of_dicts, years):
    out = {y: _ZERO for y in years}
    for d in seq_of_dicts:
        for y in years:
            out[y] += d.get(y, _ZERO)
    return out


def _poste_labels(pf, benevole_last=True):
    """Libellés de poste distincts (agrégés tous organismes), bénévoles/partenaires en fin."""
    labels = []
    for (oid, label, y) in pf.poste_jours:
        if label not in labels:
            labels.append(label)
    specials = ["Bénévoles", "Partenaires"]
    normals = [l for l in labels if l not in specials]
    normals.sort(key=lambda s: s.lower())
    ordered = normals + [s for s in specials if s in labels]
    return ordered


def _poste_year(pf, label, key):
    """{année: valeur} agrégé tous organismes pour un type de poste et une clé."""
    out = {y: _ZERO for y in pf.years}
    for (oid, lab, y), v in pf.poste_jours.items():
        if lab == label and y in out:
            out[y] += v.get(key, _ZERO)
    return out


def _poste_cout_jour(pf, label):
    for (oid, lab, y), v in pf.poste_jours.items():
        if lab == label and v.get("cout_jour"):
            return v["cout_jour"]
    return None


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _org_sheets(pf):
    """Organismes ayant leur onglet, dans un ordre stable.

    #735 — seulement si au moins une action ventile par organisme : sinon le
    seul onglet TOTAL dit tout (un onglet « Non ventilé » ou par organisme du
    poste n'apporterait rien que le gestionnaire ait saisi)."""
    return pf.org_ids() if pf.is_org_ventilated else []


def _total_sheet_name(pf, name="TOTAL"):
    return name if pf.is_org_ventilated else "TOTAL"


def _total_subtitle(pf):
    return "TOTAL (tous organismes)" if pf.is_org_ventilated else "TOTAL"


def build_rh_previsionnel_workbook(plan) -> bytes:
    _appliquer_couleur_instance()
    pf = build_plan_finance(plan)
    wb = Workbook(); wb.remove(wb.active); used = set()
    title = _plan_title(plan)

    def org_rows(oid):
        rows = []
        for af in pf.actions:
            prev = {y: af.cell(oid, y).jours for y in pf.years}
            if sum(prev.values()) != 0:
                rows.append((af, prev))
        return rows

    for oid in _org_sheets(pf):
        rows = org_rows(oid)
        if not rows:
            continue
        name = pf.org_names.get(oid, "Non ventilé")
        m = _ActionMatrix(wb.create_sheet(_title(f"RH Prév. — {name}", used)), pf.years, suivi=False, fmt=_fmt_jours)
        m.head(title, f"RESSOURCES HUMAINES — PRÉVISIONNEL (jours) — {name}")
        for af, prev in rows:
            m.row(af.enjeu_label, af.categorie, af.code, af.libelle, prev)
        m.total(f"TOTAL jours prévus — {name}", _sum_years([p for _, p in rows], pf.years))
        m.freeze()

    # TOTAL tous organismes
    m = _ActionMatrix(wb.create_sheet(_title("TOTAL", used)), pf.years, suivi=False, fmt=_fmt_jours)
    m.head(title, f"RESSOURCES HUMAINES — PRÉVISIONNEL (jours) — {_total_subtitle(pf)}")
    all_rows = []
    for af in pf.actions:
        prev = {y: af.year_total(y).jours for y in pf.years}
        if sum(prev.values()) != 0:
            m.row(af.enjeu_label, af.categorie, af.code, af.libelle, prev)
            all_rows.append(prev)
    m.total("TOTAL jours prévus", _sum_years(all_rows, pf.years))
    m.freeze()

    # Par type de poste — #735 : seulement si une action décline son temps par poste.
    if pf.par_poste:
        _rh_par_poste_sheet(wb, pf, used, suivi=False)

    return _save(wb)


def build_rh_suivi_workbook(plan) -> bytes:
    _appliquer_couleur_instance()
    pf = build_plan_finance(plan)
    wb = Workbook(); wb.remove(wb.active); used = set()
    title = _plan_title(plan)

    for oid in _org_sheets(pf):
        rows = []
        for af in pf.actions:
            prev = {y: af.cell(oid, y).jours for y in pf.years}
            real = {y: af.cell(oid, y).rjours for y in pf.years}
            if sum(prev.values()) != 0 or sum(real.values()) != 0:
                rows.append((af, prev, real))
        if not rows:
            continue
        name = pf.org_names.get(oid, "Non ventilé")
        m = _ActionMatrix(wb.create_sheet(_title(f"RH Suivi — {name}", used)), pf.years, suivi=True, fmt=_fmt_jours)
        m.head(title, f"RESSOURCES HUMAINES — SUIVI (jours) — {name}")
        for af, prev, real in rows:
            m.row(af.enjeu_label, af.categorie, af.code, af.libelle, prev, real)
        m.total(f"TOTAL — {name}", _sum_years([p for _, p, _ in rows], pf.years), _sum_years([r for _, _, r in rows], pf.years))
        m.freeze()

    m = _ActionMatrix(wb.create_sheet(_title("TOTAL", used)), pf.years, suivi=True, fmt=_fmt_jours)
    m.head(title, f"RESSOURCES HUMAINES — SUIVI (jours) — {_total_subtitle(pf)}")
    pr, rr = [], []
    for af in pf.actions:
        prev = {y: af.year_total(y).jours for y in pf.years}
        real = {y: af.year_total(y).rjours for y in pf.years}
        if sum(prev.values()) != 0 or sum(real.values()) != 0:
            m.row(af.enjeu_label, af.categorie, af.code, af.libelle, prev, real)
            pr.append(prev); rr.append(real)
    m.total("TOTAL", _sum_years(pr, pf.years), _sum_years(rr, pf.years))
    m.freeze()

    if pf.par_poste_suivi:
        _rh_par_poste_sheet(wb, pf, used, suivi=True)
    return _save(wb)


def _rh_par_poste_sheet(wb, pf, used, *, suivi):
    label = "Total par poste" if suivi else "RH par type de poste"
    m = _LabelMatrix(wb.create_sheet(_title(label, used)), pf.years, suivi=suivi, fmt=_fmt_jours)
    m.head(_plan_title(pf.plan), f"RESSOURCES HUMAINES — {'SUIVI' if suivi else 'PRÉVISIONNEL'} (jours) — {_total_subtitle(pf)}")
    for lab in _poste_labels(pf):
        prev = _poste_year(pf, lab, "prev")
        real = _poste_year(pf, lab, "real") if suivi else None
        if sum(prev.values()) == 0 and (not real or sum(real.values()) == 0):
            continue
        m.row(lab, prev, real)
    m.freeze()


def _budget_sections(pf):
    """Sections d'une matrice budget : (libellé, attr. prévu, attr. réalisé).

    #735 — fonctionnement / investissement seulement si une action du plan
    ventile par type de budget ; sinon une seule section « Budget »."""
    if pf.has_type_budget:
        return [("Fonctionnement", "tot_fonct", "rtot_fonct"),
                ("Investissement", "tot_invest", "rtot_invest")]
    return [("Budget", "tot", "rtot")]


def _budget_matrix(m, pf, cell_for, name, *, suivi):
    """Remplit une matrice budget (un organisme ou le total) ; False si vide."""
    blocks = []
    for label, a_prev, a_real in _budget_sections(pf):
        rows = []
        for af in pf.actions:
            prev = {y: getattr(cell_for(af, y), a_prev) for y in pf.years}
            real = {y: getattr(cell_for(af, y), a_real) for y in pf.years} if suivi else None
            if sum(prev.values()) or (real and sum(real.values())):
                rows.append((af, prev, real))
        blocks.append((label, rows))
    if not any(rows for _, rows in blocks):
        return False
    for label, rows in blocks:
        m.section(label)
        for af, prev, real in rows:
            m.row(af.enjeu_label, af.categorie, af.code, af.libelle, prev, real)
        suffix = f" {name}" if name else ""
        m.total(f"TOTAL — {label}{suffix}",
                _sum_years([p for _, p, _ in rows], pf.years),
                _sum_years([r for _, _, r in rows], pf.years) if suivi else None)
    return True


def _build_budget_workbook(plan, *, suivi) -> bytes:
    _appliquer_couleur_instance()
    pf = build_plan_finance(plan)
    wb = Workbook(); wb.remove(wb.active); used = set()
    title = _plan_title(plan)
    kind = "SUIVI" if suivi else "PRÉVISIONNEL"
    prefix = "Budget Suivi" if suivi else "Budget Prév."

    for oid in _org_sheets(pf):
        name = pf.org_names.get(oid, "Non ventilé")
        ws = wb.create_sheet(_title(f"{prefix} — {name}", used))
        m = _ActionMatrix(ws, pf.years, suivi=suivi, fmt=_fmt_euro)
        m.head(title, f"BUDGET {kind} (€) — {name}")
        if _budget_matrix(m, pf, lambda af, y, oid=oid: af.cell(oid, y), name, suivi=suivi):
            m.freeze()
        else:
            wb.remove(ws)
            used.discard(ws.title.lower())

    total_name = _total_sheet_name(pf, "TOTAL" if suivi else "TOTAL OG")
    m = _ActionMatrix(wb.create_sheet(_title(total_name, used)), pf.years, suivi=suivi, fmt=_fmt_euro)
    m.head(title, f"BUDGET {kind} (€) — {_total_subtitle(pf)}")
    _budget_matrix(m, pf, lambda af, y: af.year_total(y), "", suivi=suivi)
    m.freeze()

    # #735 — synthèse par poste de dépense : seulement si une action détaille
    # ses types de coût (sinon elle ne ferait que répéter le TOTAL).
    if pf.has_cost_detail:
        _budget_par_poste_sheet(wb, pf, used, suivi=suivi)
    return _save(wb)


def build_budget_previsionnel_workbook(plan) -> bytes:
    return _build_budget_workbook(plan, suivi=False)


def build_budget_suivi_workbook(plan) -> bytes:
    return _build_budget_workbook(plan, suivi=True)


def _plan_cost_by_year(pf, attr):
    """{année: Σ sur actions/organismes d'un composant de coût}."""
    out = {y: _ZERO for y in pf.years}
    for af in pf.actions:
        for y in pf.years:
            out[y] += getattr(af.year_total(y), attr)
    return out


def _plan_cost_by_year_sum(pf, *attrs):
    """{année: Σ sur actions/organismes de plusieurs composants de coût} (#618)."""
    out = {y: _ZERO for y in pf.years}
    for af in pf.actions:
        for y in pf.years:
            yt = af.year_total(y)
            out[y] += sum(getattr(yt, a) for a in attrs)
    return out


def _plan_cost_by_year_diff(pf, attr, minus):
    """{année: Σ attr − Σ minus} (« autres coûts » hors stage, #735)."""
    a = _plan_cost_by_year(pf, attr)
    b = _plan_cost_by_year(pf, minus)
    return {y: a[y] - b[y] for y in pf.years}


def _budget_par_poste_sheet(wb, pf, used, *, suivi):
    name = "Total par type de dépense" if suivi else "TOTAL par poste de dépense"
    m = _LabelMatrix(wb.create_sheet(_title(name, used)), pf.years, suivi=suivi,
                     fmt=_fmt_euro, label_header="Poste", cout_col=True)
    m.head(_plan_title(pf.plan), f"BUDGET {'SUIVI' if suivi else 'PRÉVISIONNEL'} (€) — par poste de dépense")
    salaried = [l for l in _poste_labels(pf) if l not in ("Bénévoles", "Partenaires")]

    def cost(*attrs):
        return _plan_cost_by_year_sum(pf, *attrs)

    def poste_rows(keys_prev, keys_real):
        """Coût salarial par type de poste (seulement si temps par poste)."""
        if not (pf.par_poste_suivi if suivi else pf.par_poste):
            return
        for lab in salaried:
            prev = _sum_years([_poste_year(pf, lab, k) for k in keys_prev], pf.years)
            real = (_sum_years([_poste_year(pf, lab, k) for k in keys_real], pf.years)
                    if suivi else None)
            if sum(prev.values()) != 0 or (real and sum(real.values()) != 0):
                m.row(lab, prev, real, cout=_poste_cout_jour(pf, lab))

    if pf.has_type_budget:
        # Fonctionnement - salarial
        m.section("Fonctionnement — Coût salarial",
                  cost("sal_fonct"), cost("rsal_fonct") if suivi else None)
        poste_rows(["salf_prev"], ["salf_real"])
        # Fonctionnement - autres (#735 : le stage y est détaillé)
        m.section("Fonctionnement — autres coûts",
                  cost("prest_fonct", "autre_fonct"),
                  cost("rprest_fonct", "rautre_fonct") if suivi else None)
        m.row("Prestataire", cost("prest_fonct"),
              cost("rprest_fonct") if suivi else None, cout="/")
        m.row("Coût stage", cost("stage_fonct"),
              cost("rstage_fonct") if suivi else None, cout="/")
        m.row("Autres coûts de fonctionnement",
              _plan_cost_by_year_diff(pf, "autre_fonct", "stage_fonct"),
              _plan_cost_by_year_diff(pf, "rautre_fonct", "rstage_fonct") if suivi else None,
              cout="/")
        # #618 — sous-total du bloc fonctionnement (salarial + autres coûts)
        m.row("TOTAL Fonctionnement", cost("tot_fonct"),
              cost("rtot_fonct") if suivi else None, cout="", total_style=True)
        # Investissement - salarial
        m.section("Investissement — Coût salarial",
                  cost("sal_invest"), cost("rsal_invest") if suivi else None)
        poste_rows(["sali_prev"], ["sali_real"])
        # Investissement - autres
        m.section("Investissement — autres coûts",
                  cost("prest_invest", "autre_invest"),
                  cost("rprest_invest", "rautre_invest") if suivi else None)
        m.row("Prestataire", cost("prest_invest"),
              cost("rprest_invest") if suivi else None, cout="/")
        m.row("Autres coûts d'investissement", cost("autre_invest"),
              cost("rautre_invest") if suivi else None, cout="/")
        # #618 — sous-total du bloc investissement (salarial + autres coûts)
        m.row("TOTAL Investissement", cost("tot_invest"),
              cost("rtot_invest") if suivi else None, cout="", total_style=True)
    else:
        # #735 — sans type de budget : types de coût seuls, sans
        # fonctionnement / investissement.
        m.section("Coût salarial", cost("sal_fonct", "sal_invest"),
                  cost("rsal_fonct", "rsal_invest") if suivi else None)
        poste_rows(["salf_prev", "sali_prev"], ["salf_real", "sali_real"])
        m.section("Autres coûts",
                  cost("prest_fonct", "prest_invest", "autre_fonct", "autre_invest"),
                  cost("rprest_fonct", "rprest_invest", "rautre_fonct", "rautre_invest")
                  if suivi else None)
        m.row("Coût stage", cost("stage_fonct"),
              cost("rstage_fonct") if suivi else None, cout="/")
        m.row("Prestataire", cost("prest_fonct", "prest_invest"),
              cost("rprest_fonct", "rprest_invest") if suivi else None, cout="/")
        autres = _plan_cost_by_year_diff(pf, "autre_fonct", "stage_fonct")
        autres = {y: autres[y] + v for y, v in cost("autre_invest").items()}
        rautres = None
        if suivi:
            rautres = _plan_cost_by_year_diff(pf, "rautre_fonct", "rstage_fonct")
            rautres = {y: rautres[y] + v for y, v in cost("rautre_invest").items()}
        m.row("Autres coûts", autres, rautres, cout="/")
    # TOTAL
    m.row("TOTAL", cost("tot"), cost("rtot") if suivi else None, cout="", total_style=True)
    m.freeze()


def _plan_cost_by_year_real(pf, attr):
    out = {y: _ZERO for y in pf.years}
    for af in pf.actions:
        for y in pf.years:
            out[y] += getattr(af.year_total(y), attr)
    return out


def _save(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
