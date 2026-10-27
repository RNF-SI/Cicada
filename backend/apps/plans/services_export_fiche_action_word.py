"""
Export Word (.docx) des fiches action (#662).

Même contenu que la fiche Excel (`services_export_fiche_action`, modèle
« Modèle_Export_CICADA_Fiche_action ») — validé par Sophie en #607 — mis en
page comme un document : titres, tableaux libellé / valeur, tableaux par année.
Une fiche par page, en paysage pour que les années tiennent en largeur.

  <intitulé de l'action>  –  <priorité>
  Code action (local) / Code action (référentiel Gestref)
  1) Cadre de l'action         métriques, indicateur, NE/RA, OLT/OO, enjeu
  2) Détails de l'opération    détails (protocoles pour une action CS),
                               opérateurs, partenaires, localisation, emprise
  3) Volet administratif et financier (prévisionnel seul, #607)
                               programmation annuelle, budgets (par organisme
                               si le mode le prévoit), bénévoles, programmation
                               mensuelle, financeurs
  4) Indicateurs de réponse    liste + grilles de lecture

Les données (actions, cadre, finances, grilles) viennent des fonctions de la
fiche Excel : seuls la mise en forme et ce module diffèrent.

Point d'entrée public : :func:`build_fiche_action_docx`.
"""

from __future__ import annotations

import io
from collections import defaultdict

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from . import export_theme
from . import services_export_fiche_action as fiche
from .services_export_finance import (
    GLOBAL_YEAR, build_action_finance, poste_entry_factory, year_label,
)

_txt = fiche._txt
_euro = fiche._euro
_jours = fiche._jours

_MOIS = ["Janv", "Fév", "Mars", "Avril", "Mai", "Juin",
         "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

# Trames reprises de la fiche Excel (ARGB → RGB hexadécimal).
_LABEL = fiche._LABEL_FILL[2:]
_SUBLABEL = fiche._SUBLABEL_FILL[2:]
_TOTAL = fiche._TOTAL_FILL[2:]
_YEARHDR = fiche._YEARHDR_FILL[2:]
_TERRA = RGBColor(0xB7, 0x4D, 0x5D)
_BLACK = RGBColor(0x34, 0x34, 0x33)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_GREEN = RGBColor(0x04, 0x85, 0x4B)
# Largeur utile d'une page A4 paysage avec des marges de 1,5 cm.
_LARGEUR = Cm(26.7)


class _Doc:
    """Document en cours, avec la couleur d'instance résolue (#601)."""

    def __init__(self):
        rgb = export_theme.rgb()
        self.primary = RGBColor(*rgb)
        self.primary_hex = "%02X%02X%02X" % tuple(rgb)
        self.doc = Document()
        style = self.doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(9.5)
        section = self.doc.sections[0]
        # Paysage : un plan de 10-12 ans reste lisible dans les tableaux par année.
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(section, side, Cm(1.5))

    # -- Briques -----------------------------------------------------------

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def title(self, libelle, priorite):
        p = self.doc.add_paragraph()
        run = p.add_run(libelle or "Action sans intitulé")
        run.bold = True
        run.font.size = Pt(15)
        run.font.color.rgb = self.primary
        sep = p.add_run("  –  ")
        sep.font.color.rgb = _BLACK
        pr = p.add_run(priorite or "Priorité —")
        pr.bold = True
        pr.font.size = Pt(12)
        pr.font.color.rgb = _TERRA
        return p

    def section(self, text):
        """Bandeau de partie, comme les lignes de section de la fiche Excel."""
        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _widths(table, [_LARGEUR])
        cell = table.rows[0].cells[0]
        _shade(cell, self.primary_hex)
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = _WHITE
        self._space()

    def kv(self, rows):
        """Tableau libellé / valeur (une ligne par couple)."""
        table = self.doc.add_table(rows=0, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for label, value in rows:
            cells = table.add_row().cells
            _shade(cells[0], _LABEL)
            lab = cells[0].paragraphs[0].add_run(label)
            lab.bold = True
            lab.font.color.rgb = self.primary
            _write_multiline(cells[1], value)
        _widths(table, [Cm(6.5), _LARGEUR - Cm(6.5)])
        self._space()
        return table

    def picture(self, label, png):
        table = self.doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cells = table.rows[0].cells
        _shade(cells[0], _LABEL)
        lab = cells[0].paragraphs[0].add_run(label)
        lab.bold = True
        lab.font.color.rgb = self.primary
        cells[1].paragraphs[0].add_run().add_picture(io.BytesIO(png), width=Cm(9))
        _widths(table, [Cm(6.5), _LARGEUR - Cm(6.5)])
        self._space()

    def grid(self, header, rows, *, header_fill=None, first_width=Cm(7)):
        """Tableau à colonnes : `header` = libellés de colonnes (le 1er vide ou
        un titre), `rows` = [(libellé, [valeurs], style)] avec style ∈
        {None, 'sub', 'total', 'banner'}."""
        ncols = 1 + len(header) - 1
        table = self.doc.add_table(rows=1, cols=ncols)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = table.rows[0].cells
        for i, text in enumerate(header):
            _shade(hdr[i], header_fill or _YEARHDR if i else _LABEL)
            run = hdr[i].paragraphs[0].add_run(str(text))
            run.bold = True
            run.font.color.rgb = self.primary
            if i:
                hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for label, values, style in rows:
            cells = table.add_row().cells
            if style == "banner":
                merged = cells[0].merge(cells[-1])
                _shade(merged, self.primary_hex)
                run = merged.paragraphs[0].add_run(label)
                run.bold = True
                run.font.color.rgb = _WHITE
                continue
            fill = {"total": _TOTAL, "sub": _SUBLABEL}.get(style)
            if fill:
                for c in cells:
                    _shade(c, fill)
            lab = cells[0].paragraphs[0].add_run(label)
            lab.bold = style == "total"
            if style == "total":
                lab.font.color.rgb = self.primary
            for i, value in enumerate(values, start=1):
                para = cells[i].paragraphs[0]
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run(value)
                run.bold = style == "total"
                if value == "x":
                    run.bold = True
                    run.font.color.rgb = _GREEN
        rest = _LARGEUR - first_width
        _widths(table, [first_width] + [int(rest / max(len(header) - 1, 1))] * (len(header) - 1))
        self._space()
        return table

    def _space(self):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)

    def body(self, text):
        p = self.doc.add_paragraph()
        run = p.add_run(text)
        run.italic = True
        return p

    def to_bytes(self):
        buf = io.BytesIO()
        self.doc.save(buf)
        return buf.getvalue()


def _shade(cell, hex_rgb):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_rgb)
    tc_pr.append(shd)


def _widths(table, widths):
    """Largeurs de colonnes. Word lit celles des cellules, LibreOffice la grille
    du tableau (`w:gridCol`) : on renseigne les deux."""
    table.autofit = False
    for column, width in zip(table.columns, widths):
        column.width = width
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width


def _write_multiline(cell, value):
    """Valeur multi-lignes : un paragraphe par ligne (les « \\n » de la fiche
    Excel), pour qu'un protocole ou une description restent lisibles."""
    lines = (_txt(value) or "").split("\n")
    first = True
    for line in lines:
        para = cell.paragraphs[0] if first else cell.add_paragraph()
        para.add_run(line)
        first = False


# ---------------------------------------------------------------------------
# Une fiche
# ---------------------------------------------------------------------------

def _render_action(d: _Doc, op, years, *, is_cs, code_local=""):
    # #735 — une action programmée globalement n'a pas de colonne « période »
    # dans la programmation annuelle : son volet financier a la sienne.
    years = [y for y in years if y is not GLOBAL_YEAR]
    prio = op.id_priorite.label if op.id_priorite_id else ""
    d.title(_txt(op.libelle), prio)

    code = code_local or _txt(op.code_operation) or (
        f"n° {op.numero_manuel}" if op.numero_manuel else "")
    d.kv([
        ("Code action (local)", code),
        ("Code action (référentiel Gestref)", fiche.code_referentiel(op)),
    ])

    # ---- 1) Cadre de l'action ----
    d.section("1) Cadre de l'action")
    cadre = fiche._cadre(op)
    l_ind, l_exig, l_obj = fiche.cadre_labels(cadre, is_cs)
    d.kv([
        ("Métriques", " ; ".join(cadre["metriques"])),
        (l_ind, " ; ".join(cadre["indicateurs"])),
        (l_exig, " ; ".join(cadre["exigences"])),
        (l_obj, " ; ".join(cadre["objectifs"])),
        ("Enjeu", " ; ".join(cadre["enjeux"])),
    ])

    # ---- 2) Détails de l'opération ----
    d.section("2) Détails de l'opération")
    details = _txt(op.description)
    rows = []
    if is_cs:
        blocs = [details] if details else []
        suivi = getattr(op, "id_suivi", None)
        for pr in (suivi.protocoles.all() if suivi else []):
            standardise = bool(pr.protocole_dans_campanule)
            nom = _txt(pr.protocole_campanule_nom) if standardise else _txt(pr.nom_protocole)
            nom = nom or _txt(pr.nom_protocole) or _txt(pr.protocole_campanule_nom)
            libelle = "Protocole standardisé" if standardise else "Protocole non standardisé"
            lignes = [f"{libelle} : {nom}" if nom else libelle]
            if _txt(pr.description_protocole):
                lignes.append(f"Descriptif du protocole : {_txt(pr.description_protocole)}")
            if _txt(pr.objectif_protocole):
                lignes.append(f"Objectifs du protocole : {_txt(pr.objectif_protocole)}")
            blocs.append("\n".join(lignes))
        rows.append(("Détails du suivi", "\n\n".join(blocs)))
    else:
        rows.append(("Détails de l'action", details))
    rows += [
        ("Opérateurs", _txt(op.operateurs)),
        ("Partenaires", _txt(op.partenaires)),
        ("Localisation (site(s))", " ; ".join(_txt(s.nom_site) for s in op.sites.all())),
    ]
    try:
        png = fiche._geom_png(fiche._operation_geom(op))
    except Exception:        # une géométrie exotique ne doit pas casser l'export
        png = None
    if not png:
        rows.append(("Emprise de l'action", "Non renseignée"))
    d.kv(rows)
    if png:
        d.picture("Emprise de l'action", png)

    # ---- 3) Volet administratif et financier (prévisionnel, #607) ----
    d.section("3) Détail du volet administratif et financier de l'opération")
    from .models_operations import OperationAnnee
    annees = {oa.annee: oa for oa in OperationAnnee.objects.filter(id_operation=op)}
    header = ["Programmation annuelle"] + [str(year_label(y)) for y in years]
    d.grid(header, [(
        "Périodicité",
        ["x" if getattr(annees.get(y), "periodicite", False) else "" for y in years],
        "sub",
    )])

    org_names: dict = {}
    af = build_action_finance(op, org_names, defaultdict(poste_entry_factory))

    # #735 — mêmes lignes que la fiche Excel (`fiche.finance_rows`), selon le
    # paramétrage de l'action ; une seule colonne « Période … » en global.
    cols, col_labels = fiche.finance_columns(af, years, annees)
    fmt = {"jours": _jours, "total_jours": _jours, "euro": _euro, "total": _euro}
    finance = []
    for label, values, style in fiche.finance_rows(af, org_names, cols):
        if style == "banner":
            finance.append((label, [], "banner"))
            continue
        finance.append((label, [fmt[style](v) for v in values],
                        "total" if style.startswith("total") else None))
    titre = "Budget et temps de travail prévus" if af.is_global else "Budget prévisionnel"
    d.grid([titre] + [str(c) for c in col_labels], finance, first_width=Cm(8))

    # Programmation mensuelle (mois programmé sur au moins une année)
    month_flags = fiche._monthly_flags(op, annees)
    d.grid(["Programmation mensuelle"] + _MOIS, [(
        "Périodicité", ["x" if month_flags.get(m) else "" for m in range(1, 13)], "sub",
    )])

    financeurs = []
    for f in op.finances.all():
        lbl = _txt(f.libelle)
        cat = _txt(getattr(getattr(f, "id_categorie", None), "label", ""))
        financeurs.append(" — ".join(x for x in (lbl, cat) if x))
    if _txt(op.financeurs):
        financeurs.append(_txt(op.financeurs))
    d.kv([("Financeurs et types de financement", " ; ".join(financeurs))])

    # ---- 4) Indicateurs de réponse ----
    d.section("4) Indicateurs de réponse")
    simples, grilles = [], []
    for ind in fiche._reponse_indicateurs(op):
        nom = _txt(ind.nom_indicateur)
        metriques = list(ind.metriques.all())
        if not metriques:
            simples.append(nom)
            continue
        for met in metriques:
            libelle = _txt(met.nom_metrique)
            if fiche._is_grille(met):
                grilles.append((nom, met))
            else:
                simples.append(f"{nom} ({libelle})" if libelle else nom)
    d.kv([("Indicateurs de réponse", " ; ".join(dict.fromkeys(simples)))])
    for nom, met in grilles:
        libelle = _txt(met.nom_metrique)
        unite = _txt(met.unite)
        titre = f"{nom} — {libelle}" if libelle else nom
        if unite:
            titre += f" ({unite})"
        table = d.grid(
            [titre] + [fiche._SCORE_LABELS[level] for level in range(1, 6)],
            [("Grille de lecture",
              [fiche._grid_cell(met, level) for level in range(1, 6)], None)],
        )
        # Paliers de score aux couleurs du design system (texte noir).
        for level in range(1, 6):
            _shade(table.rows[0].cells[level], fiche._SCORE_FILLS[level][2:])


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def build_fiche_action_docx(plan, operation_ids=None) -> bytes:
    """Document Word des fiches action du plan, une par page.

    `operation_ids` restreint l'export à certaines actions (export d'UNE fiche
    depuis sa page, comme pour l'Excel #642).
    """
    years = plan.annees_plan() or [""]   # #672 — prolongation comprise
    operations, codes = fiche.actions_a_exporter(plan, operation_ids)

    d = _Doc()
    if not operations:
        d.body("Ce plan ne contient pas encore d'action.")
    for index, op in enumerate(operations):
        if index:
            d.page_break()
        code_local = codes.get(op.id_operation) or _txt(op.code_operation)
        _render_action(d, op, years, is_cs=fiche._is_cs(op), code_local=code_local)
    return d.to_bytes()
