"""
Export Excel « Fiche de suivi » d'une action (#727) — prévu / réalisé d'UNE année.

Une fiche (onglet) par action. Depuis les exports du plan, on choisit l'année :
seules les actions dont le suivi est saisi cette année-là sont exportées. Depuis
la saisie du suivi, la fiche de l'action pour l'année ouverte (même vide).

Chaque fiche met en regard, colonne « Prévu » / colonne « Réalisé » :
identification (enjeu, OLT / OO), niveau de réalisation et mois, opérateurs et
financeurs, temps de travail par poste, budget par poste de dépense,
indicateurs de réponse (valeur cible / valeur saisie), emprise prévue et
réalisée sur une même carte, commentaires.

Réutilise le rédacteur, le cadre et la carte de la fiche action
(`services_export_fiche_action`) et les postes de dépense de l'export budget
suivi (`services_export_budget_rh`) : mêmes calculs, mêmes libellés.

Point d'entrée public : :func:`build_fiche_suivi_workbook`.
"""

from __future__ import annotations

import io
from collections import defaultdict
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from . import services_export_fiche_action as fa

_ZERO = Decimal(0)
_NCOLS = 5           # A:C libellé · D prévu · E réalisé
_SANS_OBJET = "/"    # prévu annuel d'une action programmée globalement (#749)
_MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
         "juil.", "août", "sept.", "oct.", "nov.", "déc."]


# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------

def _annee(op, annee):
    from .models_operations import OperationAnnee
    return (OperationAnnee.objects.filter(id_operation=op, annee=annee)
            .prefetch_related("organismes__realisation").first())


def _realisation(oa):
    try:
        return oa.realisation if oa is not None else None
    except Exception:   # RelatedObjectDoesNotExist
        return None


def _a_un_suivi(oa) -> bool:
    if oa is None:
        return False
    return _realisation(oa) is not None or any(
        getattr(o, "realisation", None) is not None for o in oa.organismes.all())


def actions_suivies(plan, annee, operation_ids=None):
    """Actions à exporter : celles dont le suivi est saisi en `annee`, ou les
    actions demandées (`operation_ids`, export depuis la saisie du suivi)."""
    ops, codes = fa.actions_a_exporter(plan, operation_ids)
    if operation_ids is None:
        ops = [op for op in ops if _a_un_suivi(_annee(op, annee))]
    return ops, codes


def _mois(flags) -> str:
    if not isinstance(flags, dict):
        return "—"
    mois = [_MOIS[int(m) - 1] for m, v in sorted(flags.items(), key=lambda kv: int(kv[0]))
            if v and str(m).isdigit() and 1 <= int(m) <= 12]
    return ", ".join(mois) or "—"


def _rh_lignes(op, oa, real):
    """{cible: (jours prévus, jours réalisés)}, dans l'ordre de rencontre."""
    from .services_export_budget_rh import _rh_cible

    out = defaultdict(lambda: [_ZERO, _ZERO])

    def cle(ligne):
        label = _rh_cible(ligne)
        return label if ligne.finance else f"{label} (bénévolat / partenariat)"

    if oa is not None:
        for l in oa.rh_lignes.select_related("id_poste", "id_organisme").order_by("pk"):
            out[cle(l)][0] += l.jours or _ZERO
    if real is not None:
        for l in real.rh_lignes.select_related("id_poste", "id_organisme").order_by("pk"):
            out[cle(l)][1] += l.jours or _ZERO
    return out


def _derniere_mesure(met, annee):
    from .models_indicateurs import Mesure
    return (Mesure.objects.filter(id_metrique=met, date_mesure__year=annee)
            .order_by("-date_mesure", "-date_ajout").first())


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------

def _cmp(w, label, prevu, realise, *, total=False):
    """Ligne « libellé (A:C) | prévu (D) | réalisé (E) »."""
    ws = w.ws
    fill = fa._TOTAL_FILL if total else fa._SUBLABEL_FILL
    ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=3)
    lc = ws.cell(w.r, 1, label)
    lc.fill = PatternFill("solid", fgColor=fill)
    lc.font = fa._F_TOTAL if total else fa._F_SUBLABEL
    lc.alignment = fa._AL_L
    for col, v in ((4, prevu), (5, realise)):
        c = ws.cell(w.r, col, v if v not in (None, "") else "—")
        c.font = fa._F_TOTAL if total else fa._F_VALUE
        c.alignment = fa._AL_R if isinstance(v, str) and v[:1].isdigit() else fa._AL_L
        if total:
            c.fill = PatternFill("solid", fgColor=fa._TOTAL_FILL)
    for col in range(1, _NCOLS + 1):
        ws.cell(w.r, col).border = fa._B
    w.r += 1


def _cmp_header(w, label="", prevu="Prévu", realise="Réalisé"):
    ws = w.ws
    ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=3)
    lc = ws.cell(w.r, 1, label)
    lc.fill = PatternFill("solid", fgColor=fa._LABEL_FILL)
    lc.font = fa._F_LABEL
    lc.alignment = fa._AL_L
    for col, text in ((4, prevu), (5, realise)):
        c = ws.cell(w.r, col, text)
        c.fill = PatternFill("solid", fgColor=fa._YEARHDR_FILL)
        c.font = fa._F_YEAR
        c.alignment = fa._AL_C
    for col in range(1, _NCOLS + 1):
        ws.cell(w.r, col).border = fa._B
    w.r += 1


def _titre(w, texte, sous_titre):
    ws = w.ws
    for text, font, fill in ((texte, fa._F_TITLE, fa._PRIMARY), (sous_titre, fa._F_LABEL, None)):
        ws.merge_cells(start_row=w.r, start_column=1, end_row=w.r, end_column=_NCOLS)
        c = ws.cell(w.r, 1, text)
        c.font = font
        c.alignment = fa._AL_L
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
            ws.row_dimensions[w.r].height = 24
        w.r += 1
    w.blank()


def _render(ws, plan, op, annee, code):
    from .services_export_budget_rh import _budget_postes
    from .services_export_finance import build_action_finance, poste_entry_factory

    for col, width in ((1, 14), (2, 14), (3, 14), (4, 34), (5, 34)):
        ws.column_dimensions[get_column_letter(col)].width = width
    w = fa._Writer(ws, _NCOLS)
    oa = _annee(op, annee)
    real = _realisation(oa)
    globale = bool(getattr(op, "programmation_globale", False))
    cadre = fa._cadre(op)

    _titre(w, f"FICHE DE SUIVI — {code} {fa._txt(op.libelle)} — {annee}".replace("  ", " "),
           f"Plan de gestion : {fa._txt(plan.nom)}")

    # --- Identification ---
    w.section("Identification de l'action")
    w.kv("Code action", code or "—")
    w.kv("Enjeu / FCR", " ; ".join(cadre["enjeux"]) or "—")
    w.kv("OLT / OO", " ; ".join(cadre["objectifs"]) or "—")
    priorite = getattr(op, "id_priorite", None)
    w.kv("Priorité", fa._txt(getattr(priorite, "label", "")) or "—")
    if globale:
        prog = "Programmée globalement sur la période de l'action"
    elif oa is not None and oa.periodicite:
        prog = f"Programmée en {annee}"
    else:
        prog = f"Non programmée en {annee} (réalisée non prévue)"
    w.kv("Programmation", prog)

    # --- Réalisation ---
    w.section(f"Réalisation {annee}")
    niveau = getattr(real, "id_niveau_realisation", None) if real else None
    w.kv("Niveau de réalisation", fa._txt(getattr(niveau, "label", "")) or "Non saisi")
    _cmp_header(w)
    _cmp(w, "Mois de réalisation",
         _mois(getattr(oa, "periodicite_mensuelle", None)) if oa else "—",
         _mois(getattr(real, "periodicite_mensuelle_realisee", None)) if real else "—")
    _cmp(w, "Opérateurs", fa._txt(op.operateurs), fa._txt(getattr(real, "operateurs_realises", "")))
    _cmp(w, "Financeurs", fa._txt(op.financeurs), fa._txt(getattr(real, "financeurs_realises", "")))

    # --- Temps de travail ---
    w.section("Temps de travail (jours)")
    _cmp_header(w, "Poste / temps de travail")
    lignes = _rh_lignes(op, oa, real)
    tp = tr = _ZERO
    for label, (p, r) in lignes.items():
        _cmp(w, label, _SANS_OBJET if globale else fa._jours(p), fa._jours(r))
        tp += p; tr += r
    if not lignes:
        _cmp(w, "Aucun temps de travail", "—", "—")
    _cmp(w, "Total temps de travail", _SANS_OBJET if globale else fa._jours(tp),
         fa._jours(tr), total=True)

    # --- Budget ---
    w.section("Budget (€)")
    _cmp_header(w, "Poste de dépense")
    af = build_action_finance(op, {}, defaultdict(poste_entry_factory))
    cell = af.year_total(annee)
    for label, prev_of, real_of in _budget_postes(af):
        p, r = prev_of(cell), real_of(cell)
        if p or r:
            _cmp(w, label, _SANS_OBJET if globale else fa._euro(p), fa._euro(r))
    _cmp(w, "Total budget", _SANS_OBJET if globale else fa._euro(cell.tot),
         fa._euro(cell.rtot), total=True)

    # --- Indicateurs de réponse ---
    w.section("Indicateurs de réponse")
    metriques = [(ind, met) for ind in fa._reponse_indicateurs(op) for met in ind.metriques.all()]
    if metriques:
        _cmp_header(w, "Métrique (indicateur)", "Valeur cible", f"Valeur {annee}")
        for ind, met in metriques:
            unite = f" {fa._txt(met.unite)}" if fa._txt(getattr(met, "unite", "")) else ""
            mesure = _derniere_mesure(met, annee)
            cible = fa._txt(met.etat_reference)
            _cmp(w, f"{fa._txt(met.nom_metrique)} ({fa._txt(ind.nom_indicateur)})",
                 f"{cible}{unite}" if cible else "—",
                 f"{fa._txt(mesure.valeur)}{unite}" if mesure and fa._txt(mesure.valeur) else "—")
    else:
        w.kv("Indicateurs de réponse", "Aucun indicateur de réponse rattaché à l'action")

    # --- Emprise ---
    w.section("Emprise")
    prevue = fa._operation_geom(op)
    realisee = getattr(real, "geom_realisee", None) if real else None
    png = fa._geom_png(prevue, realise=realisee) if (prevue or realisee) else None
    if png:
        w.picture_row("Emprise prévue (bleu-vert)\net réalisée (terra cotta)", png)
    else:
        w.kv("Emprise", "Aucune emprise prévue ni réalisée")

    # --- Commentaires ---
    w.section("Commentaires du suivi")
    w.kv("Commentaires", fa._txt(getattr(real, "commentaires", "")) or "—")
    ws.sheet_view.showGridLines = False


def build_fiche_suivi_workbook(plan, annee, operation_ids=None) -> bytes:
    """Classeur des fiches de suivi de l'année `annee` (un onglet par action)."""
    fa._appliquer_couleur_instance()
    annee = int(annee)
    ops, codes = actions_suivies(plan, annee, operation_ids)

    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    if not ops:
        ws = wb.create_sheet(fa._sanitize_title(f"Suivi {annee}", used))
        ws["A1"] = f"Aucun suivi saisi en {annee} pour ce plan."
        ws["A1"].font = Font(bold=True, size=12, color=fa._PRIMARY)
    for op in ops:
        code = codes.get(op.id_operation) or fa._txt(op.code_operation)
        # Code court (CS1…) d'abord : l'année doit rester lisible dans les
        # 31 caractères d'un nom d'onglet.
        titre = code or fa._txt(op.code_operation) or f"Action {op.id_operation}"
        ws = wb.create_sheet(fa._sanitize_title(f"{titre} {annee}"[-31:] if len(titre) > 25
                                                else f"{titre} {annee}", used))
        _render(ws, plan, op, annee, code)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
