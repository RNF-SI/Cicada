"""
Import / export Excel des **actions** (opérations) d'un plan de gestion — module 2
du dispositif d'import (#478). Fait suite au module « arborescence »
(``services_import.py``).

Une action s'importe dans un plan qui possède **déjà son arborescence**. Comme
les codes logiques de l'arborescence (I1, I2…) ne sont pas persistés en base, le
classeur d'actions est **généré depuis le plan** : il embarque un onglet de
référence ``Indicateurs`` listant les indicateurs existants (code lisible + nom
+ enjeu + identifiant technique). L'onglet ``Actions`` référence l'indicateur
parent par ce code (liste déroulante). À l'import, on relit les deux onglets
pour rattacher chaque action au bon indicateur du plan.

Périmètre : libellé, type d'action, priorité, années (``annee_min`` /
``annee_max`` → ``OperationAnnee``), opérateurs / financeurs (texte libre), et
le **paramétrage budgétaire** de la fiche action (#600) : mode de ventilation,
« déclinaison par type de coût », « saisie automatique du coût salarial ».
Deux onglets facultatifs complètent la saisie, et s'enregistrent exactement
comme le ferait la fiche action pour le mode choisi :

- ``Budgets`` : montants par (action, année[, organisme]). Selon le mode, un
  budget total, des enveloppes fonctionnement / investissement, ou le détail
  des coûts (salarial, stage, prestataire, autres) ;
- ``RH`` : temps de travail en jours par (action, année), décliné par poste
  (modes « + type de poste »), par organisme (modes « par organisme » sans
  poste) ou global, avec sa catégorie de dépense (#597).

Les postes du plan et les organismes gestionnaires de ses sites sont listés
dans des onglets de référence (``Postes``, ``Organismes``). Les actions sont
créées en statut ``draft``.
"""

from __future__ import annotations

import io
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from apps.core.models import Nomenclature

from .models_indicateurs import Indicateur
from .models_operations import (
    CategorieDepense,
    CorOperationSite,
    Operation,
    OperationAnnee,
    OperationAnneeOrganisme,
    OperationAnneeRH,
    Poste,
)
from .services_export_finance import ORG_VENTILATION_MODES, TYPE_VENTILATION_MODES
from .services_import import (
    ERROR,
    FORMAT_VERSION,
    WARNING,
    ArborescenceImportError,
    ImportReport,
    _NomenclatureResolver,
    _as_int,
    _cell_str,
    _is_example_row,
    _norm,
    _parse_bool,
    _BORDER,
    _EXAMPLE_MARKER,
    _HEADER_FILL,
    _HEADER_FONT,
    _HINT_FILL,
    _HINT_FONT,
    _PRIMARY,
    _REQUIRED_FILL,
    _TITLE_FONT,
    _WRAP_TOP,
)


def _as_decimal(value):
    """Convertit une cellule en Decimal (ou None si vide/invalide)."""
    text = _cell_str(value)
    if not text:
        return None
    try:
        return Decimal(text.replace(",", ".").replace(" ", ""))
    except (InvalidOperation, ValueError):
        return None


_HEADER_ROW = 2
_FIRST_DATA_ROW = 3
_BLANK_ROWS = 200

# Types de nomenclature utilisés par les actions.
_TYPE_ACTION = "TYPE_ACTION"
_PRIORITE = "PRIORITE_OPERATION"


# ---------------------------------------------------------------------------
# Traversée des indicateurs d'un plan (référence stable code → indicateur)
# ---------------------------------------------------------------------------


def _plan_indicateurs(plan) -> list[tuple[Indicateur, str]]:
    """Retourne les indicateurs du plan avec le libellé de leur enjeu, dans un
    ordre déterministe (branche état puis branche opérationnelle)."""
    result: list[tuple[Indicateur, str]] = []
    seen: set[int] = set()

    def _add(ind, enjeu_libelle):
        if ind.id_indicateur not in seen:
            seen.add(ind.id_indicateur)
            result.append((ind, enjeu_libelle))

    enjeux = list(plan.enjeux.all().order_by("ordre", "id_enjeu"))

    # Branche état : Enjeu → OLT → NE → Indicateur
    for enjeu in enjeux:
        for olt in enjeu.objectifs_long_terme.all().order_by("ordre", "id_olt"):
            for ne in olt.niveaux_exigence.all().order_by("ordre", "id_ne"):
                for ind in ne.indicateurs.all().order_by("ordre", "id_indicateur"):
                    _add(ind, enjeu.libelle)

    # Branche opérationnelle : Enjeu → Facteur → Pression → OO → RA → Indicateur
    for enjeu in enjeux:
        for cor in enjeu.cor_facteurs.all().order_by("ordre", "id"):
            facteur = cor.id_facteur_influence
            for pr in facteur.pressions.all().order_by("ordre", "id_pression"):
                for oo in pr.objectifs_operationnels.all().order_by("ordre", "id_oo"):
                    for ra in oo.resultats_attendus.all().order_by("ordre", "id_ra"):
                        for ind in ra.indicateurs.all().order_by(
                            "ordre", "id_indicateur"
                        ):
                            _add(ind, enjeu.libelle)
        # OO rattachés directement au FCR (#337)
        for oo in enjeu.objectifs_operationnels_directs.all().order_by(
            "ordre", "id_oo"
        ):
            for ra in oo.resultats_attendus.all().order_by("ordre", "id_ra"):
                for ind in ra.indicateurs.all().order_by("ordre", "id_indicateur"):
                    _add(ind, enjeu.libelle)

    return result


def _plan_postes(plan) -> list[Poste]:
    """Postes du plan (référence pour le temps de travail, #560)."""
    return list(
        plan.postes.all()
        .select_related("id_organisme")
        .prefetch_related("fonctions__id_fonction__id_type_poste")
        .order_by("id_poste")
    )


def _poste_labels(postes) -> dict[int, str]:
    """Libellé affiché de chaque poste, numéroté quand plusieurs postes du plan
    portent le même (#611) — même règle que ``posteDisplayLabel`` côté front.
    Le libellé est le nom local s'il est saisi (#632), sinon les fonctions."""
    base = {p.id_poste: (p.libelle or "") for p in postes}
    labels: dict[int, str] = {}
    for p in postes:
        same = [q for q in postes if base[q.id_poste] == base[p.id_poste]]
        label = base[p.id_poste] or f"Poste {p.id_poste}"
        if len(same) > 1 and base[p.id_poste]:
            label = f"{label} {same.index(p) + 1}"
        labels[p.id_poste] = label
    return labels


def _poste_ref_rows(postes, poste_code_by_id) -> list[dict]:
    """Lignes de l'onglet de référence « Postes »."""
    labels = _poste_labels(postes)
    rows = []
    for p in postes:
        types: list[str] = []
        for pf in p.fonctions.all():
            label = pf.id_fonction.type_poste_display
            if label and label not in types:
                types.append(label)
        rows.append(
            {
                "code": poste_code_by_id[p.id_poste],
                "poste": labels[p.id_poste],
                "type": " · ".join(types),
                "organisme": p.organisme_affichage or "",
                "cout_jour": p.cout_jour if p.cout_jour is not None else "",
                "id": p.id_poste,
            }
        )
    return rows


def _plan_organismes(plan) -> list[tuple[object, list[int]]]:
    """Organismes gestionnaires des sites du plan, avec les sites qu'ils gèrent.

    Ce sont les organismes que la fiche action propose pour la ventilation
    « par organisme » (gestionnaires des sites de l'action).
    """
    from apps.users.models import CorOgSite

    site_ids = list(plan.sites.values_list("site_id", flat=True))
    by_org: dict[int, tuple[object, list[int]]] = {}
    for cor in (
        CorOgSite.objects.filter(id_site_id__in=site_ids)
        .select_related("uuid_og")
        .order_by("uuid_og__nom_organisme", "id_site_id")
    ):
        org = cor.uuid_og
        entry = by_org.setdefault(org.id_organisme, (org, []))
        entry[1].append(cor.id_site_id)
    return sorted(by_org.values(), key=lambda e: (e[0].nom_organisme or "").lower())


def _organisme_ref_rows(organismes, org_code_by_id) -> list[dict]:
    """Lignes de l'onglet de référence « Organismes »."""
    return [
        {
            "code": org_code_by_id[org.id_organisme],
            "organisme": org.nom_organisme or "",
            "id": org.id_organisme,
        }
        for org, _sites in organismes
    ]


# ---------------------------------------------------------------------------
# Paramétrage budgétaire d'une action (#600) — miroir de la fiche action
# ---------------------------------------------------------------------------

# Libellés des modes de ventilation, repris de la fiche action.
_MODE_LABELS = {
    "none": "Pas de ventilation",
    "by_org": "Par organisme",
    "by_type": "Par type de budget",
    "by_org_type": "Par organisme + type de budget",
    "by_type_poste": "Par type de budget + type de poste",
    "by_org_type_poste": "Par organisme + type de budget + type de poste",
}
_MODE_BY_TEXT = {
    **{_norm(label): key for key, label in _MODE_LABELS.items()},
    **{_norm(key): key for key in _MODE_LABELS},
}
_POSTE_MODES = set(Operation.VENTILATION_POSTE_MODES)
# Modes dont le temps de travail se saisit par organisme (sans poste).
_RH_ORG_MODES = {"by_org", "by_org_type"}

_CATEGORIE_LABELS = {
    CategorieDepense.FONCTIONNEMENT: "Fonctionnement",
    CategorieDepense.INVESTISSEMENT: "Investissement",
    CategorieDepense.BENEVOLAT_PARTENARIAT: "Bénévolat partenariat",
}
_CATEGORIE_BY_TEXT = {
    **{_norm(label): key for key, label in _CATEGORIE_LABELS.items()},
    **{_norm(key): key for key in _CATEGORIE_LABELS},
}


def _parse_mode(value):
    return _MODE_BY_TEXT.get(_norm(value))


def _parse_categorie(value):
    return _CATEGORIE_BY_TEXT.get(_norm(value))


def _salary_option_available(mode, detail) -> bool:
    """La case « saisie automatique du coût salarial » n'existe que dans les
    modes « + type de poste » avec détail des coûts (``salaryOptionAvailable``)."""
    return mode in _POSTE_MODES and detail


def _salary_is_computed(mode, detail, auto) -> bool:
    """Coût salarial calculé (jours × coût jour) plutôt que saisi — même règle
    que ``salaryIsComputed`` (``shared/utils/operation-budget.ts``) : c'est la
    valeur que la fiche action enregistre dans ``cout_salarial_auto``."""
    if _salary_option_available(mode, detail):
        return auto
    return not (mode in TYPE_VENTILATION_MODES and detail)


def _budget_layout(mode, detail) -> str:
    """Famille de montants que le mode enregistre (``budgetMode()`` du front) :
    ``total`` (sans type de budget), ``enveloppes`` (fonctionnement /
    investissement saisis) ou ``detail`` (types de coût)."""
    if mode not in TYPE_VENTILATION_MODES:
        return "total"
    return "detail" if detail else "enveloppes"


def _rh_target(mode) -> str:
    """Cible des lignes de temps de travail (``rhMode()`` du front)."""
    if mode in _POSTE_MODES:
        return "poste"
    if mode in _RH_ORG_MODES:
        return "organisme"
    return "global"


# ---------------------------------------------------------------------------
# Colonnes de l'onglet « Actions »
# ---------------------------------------------------------------------------

# (key, header, required, help, nomenclature_type, width)
_ACTION_COLUMNS = [
    (
        "code",
        "code",
        True,
        "Identifiant libre et unique de l'action (ex : A1).",
        None,
        10,
    ),
    (
        "indicateur",
        "indicateur",
        True,
        "Code de l'indicateur auquel l'action se rattache (voir l'onglet "
        "« Indicateurs »).",
        None,
        14,
    ),
    ("libelle", "libellé", True, "Intitulé de l'action.", None, 45),
    (
        "type_action",
        "type d'action",
        False,
        "Type d'action (codification Eden 62).",
        _TYPE_ACTION,
        26,
    ),
    ("priorite", "priorité", False, "Priorité de l'action.", _PRIORITE, 18),
    ("annee_min", "année début", False, "Première année (ex : 2024).", None, 14),
    ("annee_max", "année fin", False, "Dernière année (ex : 2028).", None, 14),
    (
        "mode_ventilation",
        "mode de ventilation",
        False,
        "Comme dans la fiche action : il fixe les colonnes à remplir dans "
        "« Budgets » et la cible du temps de travail dans « RH ». Laissé vide, "
        "il est déduit de ce que vous saisissez dans ces deux onglets.",
        None,
        34,
    ),
    (
        "declinaison_par_type_cout",
        "déclinaison par type de coût",
        False,
        "Modes « par type de budget » uniquement. Oui : budget détaillé en coût "
        "salarial, stage, prestataire et autres coûts. Non : seuls les budgets "
        "de fonctionnement et d'investissement sont saisis. Laissé vide : "
        "déduit des colonnes remplies dans « Budgets ».",
        None,
        18,
    ),
    (
        "cout_salarial_auto",
        "saisie automatique du coût salarial",
        False,
        "Modes « + type de poste » avec déclinaison par type de coût "
        "uniquement. Oui : coût salarial calculé (jours × coût jour du poste). "
        "Non : coût salarial saisi dans « Budgets ». Laissé vide : Oui, sauf si "
        "un coût salarial est saisi.",
        None,
        18,
    ),
    ("operateurs", "opérateurs", False, "Texte libre.", None, 30),
    ("financeurs", "financeurs", False, "Texte libre.", None, 30),
    ("description", "description", False, "", None, 40),
]

# Colonnes de l'onglet de référence « Indicateurs » (lecture seule à la saisie).
_REF_COLUMNS = [
    ("code", "code", 10),
    ("indicateur", "indicateur", 45),
    ("enjeu", "enjeu", 35),
    ("id", "id (technique — ne pas modifier)", 26),
]

# Colonnes de l'onglet de référence « Postes » (lecture seule à la saisie).
_POSTE_REF_COLUMNS = [
    ("code", "code", 10),
    ("poste", "poste", 40),
    ("type", "type de poste", 20),
    ("organisme", "organisme", 30),
    ("cout_jour", "coût jour (€)", 14),
    ("id", "id (technique — ne pas modifier)", 26),
]

# Colonnes de l'onglet de référence « Organismes » (lecture seule à la saisie).
_ORGANISME_REF_COLUMNS = [
    ("code", "code", 10),
    ("organisme", "organisme", 45),
    ("id", "id (technique — ne pas modifier)", 26),
]

# Onglet « Budgets » : montants par (action, année[, organisme]). Seules les
# colonnes du mode de l'action sont lues (cf. ``_budget_layout``).
# (key, header, required, help, width)
_BUDGET_COLUMNS = [
    ("action", "action", True, "Code de l'action (onglet « Actions »).", 12),
    ("annee", "année", True, "Année concernée (ex : 2024).", 10),
    (
        "organisme",
        "organisme",
        False,
        "Code de l'organisme (onglet « Organismes »). Obligatoire dans les "
        "modes « par organisme », à laisser vide sinon.",
        12,
    ),
    (
        "budget_total",
        "budget total (€)",
        False,
        "Modes « Pas de ventilation » et « Par organisme ».",
        16,
    ),
    (
        "budget_fonctionnement",
        "budget fonctionnement (€)",
        False,
        "Modes « par type de budget » SANS déclinaison par type de coût.",
        18,
    ),
    (
        "budget_investissement",
        "budget investissement (€)",
        False,
        "Modes « par type de budget » SANS déclinaison par type de coût.",
        18,
    ),
    (
        "cout_salarial",
        "coût salarial fonctionnement (€)",
        False,
        "Déclinaison par type de coût, coût salarial saisi (pas en saisie "
        "automatique).",
        18,
    ),
    (
        "cout_stage",
        "coût stage (€)",
        False,
        "Déclinaison par type de coût (fonctionnement).",
        14,
    ),
    (
        "cout_prestataire",
        "coût prestataire fonctionnement (€)",
        False,
        "Déclinaison par type de coût.",
        18,
    ),
    (
        "autre_cout",
        "autres coûts fonctionnement (€)",
        False,
        "Déclinaison par type de coût.",
        18,
    ),
    (
        "autre_cout_commentaire",
        "commentaire autres coûts fonctionnement",
        False,
        "Déclinaison par type de coût : nature des autres coûts.",
        26,
    ),
    (
        "cout_salarial_invest",
        "coût salarial investissement (€)",
        False,
        "Déclinaison par type de coût, coût salarial saisi (pas en saisie "
        "automatique).",
        18,
    ),
    (
        "cout_prestataire_invest",
        "coût prestataire investissement (€)",
        False,
        "Déclinaison par type de coût.",
        18,
    ),
    (
        "autre_cout_invest",
        "autres coûts investissement (€)",
        False,
        "Déclinaison par type de coût.",
        18,
    ),
    (
        "autre_cout_invest_commentaire",
        "commentaire autres coûts investissement",
        False,
        "Déclinaison par type de coût : nature des autres coûts.",
        26,
    ),
]

# Familles de colonnes de montants, par disposition du tableau budgétaire.
_BUDGET_TOTAL_COLS = ("budget_total",)
_BUDGET_ENVELOPE_COLS = ("budget_fonctionnement", "budget_investissement")
_BUDGET_SALARY_COLS = ("cout_salarial", "cout_salarial_invest")
_BUDGET_DETAIL_COLS = (
    "cout_stage",
    "cout_prestataire",
    "autre_cout",
    "autre_cout_commentaire",
    "cout_prestataire_invest",
    "autre_cout_invest",
    "autre_cout_invest_commentaire",
)
_BUDGET_VALUE_COLS = (
    _BUDGET_TOTAL_COLS + _BUDGET_ENVELOPE_COLS + _BUDGET_SALARY_COLS + _BUDGET_DETAIL_COLS
)
_BUDGET_TEXT_COLS = ("autre_cout_commentaire", "autre_cout_invest_commentaire")
_BUDGET_HEADER_BY_KEY = {c[0]: c[1] for c in _BUDGET_COLUMNS}


def _allowed_budget_cols(mode, detail, salary_computed) -> tuple[str, ...]:
    layout = _budget_layout(mode, detail)
    if layout == "total":
        return _BUDGET_TOTAL_COLS
    if layout == "enveloppes":
        return _BUDGET_ENVELOPE_COLS
    if salary_computed:
        return _BUDGET_DETAIL_COLS
    return _BUDGET_SALARY_COLS + _BUDGET_DETAIL_COLS


# Onglet « RH » : temps de travail par (action, année[, poste | organisme]),
# en jours (#560), avec sa catégorie de dépense (#597).
_RH_COLUMNS = [
    ("action", "action", True, "Code de l'action (onglet « Actions »).", 12),
    ("annee", "année", True, "Année concernée (ex : 2024).", 10),
    (
        "poste",
        "poste",
        False,
        "Code du poste (onglet « Postes »). Obligatoire dans les modes « + type "
        "de poste », à laisser vide sinon.",
        12,
    ),
    (
        "organisme",
        "organisme",
        False,
        "Code de l'organisme (onglet « Organismes »). Obligatoire dans les modes "
        "« Par organisme » et « Par organisme + type de budget », à laisser "
        "vide sinon.",
        12,
    ),
    ("jours", "jours", False, "Nombre de jours travaillés.", 10),
    (
        "categorie_depense",
        "catégorie de dépense",
        False,
        "Fonctionnement, Investissement (modes « par type de budget » "
        "uniquement) ou Bénévolat partenariat (temps valorisé en jours, sans "
        "coût). Laissée vide : Bénévolat partenariat pour un poste non financé "
        "(bénévole…), Fonctionnement sinon.",
        24,
    ),
]

# En-têtes normalisés → clé de colonne, pour le parsing des onglets à plat.
_BUDGET_HEADERS = {_norm(c[1]): c[0] for c in _BUDGET_COLUMNS}
_RH_HEADERS = {
    **{_norm(c[1]): c[0] for c in _RH_COLUMNS},
    # Classeurs antérieurs à #597 : colonne « financé ? » (Oui / Non).
    _norm("financé ?"): "finance",
}


# ---------------------------------------------------------------------------
# Construction du classeur
# ---------------------------------------------------------------------------


def _nomenclature_values() -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for type_mnemo in (_TYPE_ACTION, _PRIORITE):
        labels = list(
            Nomenclature.objects.filter(id_type__mnemonique=type_mnemo, actif=True)
            .order_by("id_nomenclature")
            .values_list("label", flat=True)
        )
        values[type_mnemo] = [lbl for lbl in labels if lbl]
    return values


def _actions_code_range(n_action_rows: int) -> str:
    """Plage de la colonne « code » de l'onglet Actions (source des dropdowns
    « action » des onglets Budgets et RH)."""
    last = _HEADER_ROW + max(n_action_rows, 0) + _BLANK_ROWS
    return f"'Actions'!$A${_FIRST_DATA_ROW}:$A${last}"


def _render_actions_workbook(
    indicateurs,
    code_by_id,
    poste_rows,
    organisme_rows,
    action_rows,
    budget_rows,
    rh_rows,
    plan=None,
    with_hints=False,
    example_name=None,
) -> bytes:
    """Assemble le classeur des actions à partir de données déjà préparées."""
    wb = Workbook()
    wb.remove(wb.active)

    # Codes de rattachement pour les dropdowns.
    first_ind_code = next(iter(code_by_id.values()), "I1")
    first_poste_code = poste_rows[0]["code"] if poste_rows else "Q1"
    actions_range = _actions_code_range(len(action_rows) + (1 if with_hints else 0))

    hints = _actions_hint_rows(first_ind_code, first_poste_code) if with_hints else {}

    _write_lisez_moi(wb, plan, example_name=example_name, with_hints=with_hints)
    ref_code_range = _write_indicateurs_ref(wb, indicateurs, code_by_id)
    poste_code_range = _write_ref_sheet(
        wb,
        "Postes",
        "Postes existants du plan (référence RH). Ne modifiez pas la colonne "
        "« id ». Créez vos postes via la page « Postes / RH » du plan.",
        _POSTE_REF_COLUMNS,
        poste_rows,
    )
    org_code_range = _write_ref_sheet(
        wb,
        "Organismes",
        "Organismes gestionnaires des sites du plan (ventilation par "
        "organisme). Ne modifiez pas la colonne « id ».",
        _ORGANISME_REF_COLUMNS,
        organisme_rows,
    )
    list_ranges = _write_listes(wb)
    _write_actions(
        wb,
        action_rows,
        ref_code_range,
        list_ranges,
        hint_row=hints.get("actions"),
    )
    _write_budgets(
        wb, budget_rows, actions_range, org_code_range, hint_row=hints.get("budgets")
    )
    _write_rh(
        wb,
        rh_rows,
        poste_code_range,
        org_code_range,
        actions_range,
        list_ranges,
        hint_row=hints.get("rh"),
    )

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_actions_workbook(plan) -> bytes:
    """Construit le classeur d'import des actions pour un plan donné.

    L'onglet ``Indicateurs`` est pré-rempli avec les indicateurs existants du
    plan ; l'onglet ``Actions`` est vierge (avec une ligne exemple) ou
    pré-rempli si des actions existent déjà (export/sauvegarde).
    """
    indicateurs = _plan_indicateurs(plan)
    code_by_id = {
        ind.id_indicateur: f"I{i}" for i, (ind, _) in enumerate(indicateurs, start=1)
    }
    postes = _plan_postes(plan)
    poste_code_by_id = {p.id_poste: f"Q{i}" for i, p in enumerate(postes, start=1)}
    organismes = _plan_organismes(plan)
    org_code_by_id = {
        org.id_organisme: f"O{i}" for i, (org, _s) in enumerate(organismes, start=1)
    }

    action_rows = _extract_actions(plan, code_by_id)
    budget_rows = _extract_budgets(plan, org_code_by_id)
    rh_rows = _extract_rh(plan, poste_code_by_id, org_code_by_id)

    return _render_actions_workbook(
        indicateurs,
        code_by_id,
        _poste_ref_rows(postes, poste_code_by_id),
        _organisme_ref_rows(organismes, org_code_by_id),
        action_rows,
        budget_rows,
        rh_rows,
        plan=plan,
        with_hints=not action_rows,
    )


ACTIONS_EXAMPLE_NAME = "Réserve naturelle d'une zone humide (exemple)"


def _actions_hint_rows(first_ind_code: str, first_poste_code: str) -> dict[str, dict]:
    """Une ligne « exemple » par onglet de saisie (Actions, Budgets, RH).

    La 1re colonne porte le marqueur ``(exemple)`` (ignoré à l'import) ; les
    colonnes de rattachement montrent des codes réels (indicateur, poste) pour
    illustrer les liens.
    """
    return {
        "actions": {
            "code": _EXAMPLE_MARKER,
            "indicateur": first_ind_code,
            "libelle": "Faucher tardivement les prairies humides",
            "annee_min": 2024,
            "annee_max": 2028,
            "mode_ventilation": _MODE_LABELS["by_type_poste"],
            "declinaison_par_type_cout": "Oui",
            "cout_salarial_auto": "Oui",
            "operateurs": "Équipe technique de la réserve",
            "financeurs": "Agence de l'eau",
            "description": "Fauche annuelle avec exportation, après le 15 juillet.",
        },
        "budgets": {
            "action": _EXAMPLE_MARKER,
            "annee": 2024,
            "cout_prestataire": 1500,
            "autre_cout": 300,
            "autre_cout_commentaire": "Location de matériel",
        },
        "rh": {
            "action": _EXAMPLE_MARKER,
            "annee": 2024,
            "poste": first_poste_code,
            "jours": 6,
            "categorie_depense": _CATEGORIE_LABELS[CategorieDepense.FONCTIONNEMENT],
        },
    }


def _actions_example_data():
    """Données fictives (indicateurs/postes/organismes/actions/budgets/RH) pour
    l'exemple. Trois actions illustrent trois modes de ventilation."""
    from types import SimpleNamespace

    indicateurs = [
        (
            SimpleNamespace(
                id_indicateur=9001,
                nom_indicateur="État de conservation des habitats tourbeux",
            ),
            "Habitats tourbeux",
        ),
        (
            SimpleNamespace(
                id_indicateur=9002,
                nom_indicateur="Richesse en passereaux paludicoles nicheurs",
            ),
            "Avifaune paludicole",
        ),
        (
            SimpleNamespace(
                id_indicateur=9003,
                nom_indicateur="Surface colonisée par la Jussie",
            ),
            "Habitats tourbeux",
        ),
    ]
    code_by_id = {9001: "I1", 9002: "I2", 9003: "I3"}
    poste_rows = [
        {
            "code": "Q1",
            "poste": "Chargé·e de mission",
            "type": "Salarié",
            "organisme": "Association gestionnaire (exemple)",
            "cout_jour": 350,
            "id": 8001,
        },
        {
            "code": "Q2",
            "poste": "Garde technicien·ne",
            "type": "Salarié",
            "organisme": "Association gestionnaire (exemple)",
            "cout_jour": 280,
            "id": 8002,
        },
        {
            "code": "Q3",
            "poste": "Bénévoles",
            "type": "Bénévole",
            "organisme": "Association gestionnaire (exemple)",
            "cout_jour": 0,
            "id": 8003,
        },
    ]
    organisme_rows = [
        {"code": "O1", "organisme": "Association gestionnaire (exemple)", "id": 7001},
        {"code": "O2", "organisme": "Commune co-gestionnaire (exemple)", "id": 7002},
    ]

    # Valeurs de nomenclature réelles (si disponibles) pour un rendu réaliste.
    noms = _nomenclature_values()
    type_action = (noms.get(_TYPE_ACTION) or [""])[0]
    priorite = (noms.get(_PRIORITE) or [""])[0]
    fonct = _CATEGORIE_LABELS[CategorieDepense.FONCTIONNEMENT]
    invest = _CATEGORIE_LABELS[CategorieDepense.INVESTISSEMENT]
    benevolat = _CATEGORIE_LABELS[CategorieDepense.BENEVOLAT_PARTENARIAT]

    action_rows = [
        {
            "code": "A1",
            "indicateur": "I1",
            "libelle": "Faucher tardivement les prairies humides",
            "type_action": type_action,
            "priorite": priorite,
            "annee_min": 2024,
            "annee_max": 2028,
            "mode_ventilation": _MODE_LABELS["by_type_poste"],
            "declinaison_par_type_cout": "Oui",
            "cout_salarial_auto": "Oui",
            "operateurs": "Équipe technique de la réserve",
            "financeurs": "Agence de l'eau",
            "description": "Fauche annuelle avec exportation, après le 15 juillet.",
        },
        {
            "code": "A2",
            "indicateur": "I2",
            "libelle": "Poser des panneaux de mise en défens des roselières",
            "type_action": type_action,
            "priorite": priorite,
            "annee_min": 2024,
            "annee_max": 2025,
            "mode_ventilation": _MODE_LABELS["by_type"],
            "declinaison_par_type_cout": "Non",
            "operateurs": "Garde technicien·ne",
            "financeurs": "Région",
            "description": "Balisage des zones de quiétude au printemps.",
        },
        {
            "code": "A3",
            "indicateur": "I3",
            "libelle": "Arrachage manuel de la Jussie",
            "type_action": type_action,
            "priorite": priorite,
            "annee_min": 2024,
            "annee_max": 2029,
            "mode_ventilation": _MODE_LABELS["by_org"],
            "operateurs": "Chantier bénévole",
            "financeurs": "Agence de l'eau",
            "description": "Campagnes d'arrachage estivales répétées.",
        },
    ]
    budget_rows = [
        # A1 — détail des coûts, coût salarial calculé depuis l'onglet RH.
        {
            "action": "A1",
            "annee": 2024,
            "cout_prestataire": 1500,
            "autre_cout": 300,
            "autre_cout_commentaire": "Location de matériel",
        },
        {"action": "A1", "annee": 2025, "cout_prestataire": 1500},
        # A2 — enveloppes fonctionnement / investissement.
        {
            "action": "A2",
            "annee": 2024,
            "budget_fonctionnement": 800,
            "budget_investissement": 1200,
        },
        # A3 — un budget total par organisme.
        {"action": "A3", "annee": 2024, "organisme": "O1", "budget_total": 2000},
        {"action": "A3", "annee": 2024, "organisme": "O2", "budget_total": 1000},
    ]
    rh_rows = [
        # A1 — temps décliné par poste.
        {"action": "A1", "annee": 2024, "poste": "Q1", "jours": 6,
         "categorie_depense": fonct},
        {"action": "A1", "annee": 2024, "poste": "Q2", "jours": 4,
         "categorie_depense": fonct},
        {"action": "A1", "annee": 2024, "poste": "Q3", "jours": 10,
         "categorie_depense": benevolat},
        # A2 — temps global, ventilé par catégorie de dépense.
        {"action": "A2", "annee": 2024, "jours": 3, "categorie_depense": invest},
        # A3 — temps par organisme.
        {"action": "A3", "annee": 2024, "organisme": "O1", "jours": 8,
         "categorie_depense": fonct},
        {"action": "A3", "annee": 2024, "organisme": "O2", "jours": 12,
         "categorie_depense": benevolat},
    ]
    return (
        indicateurs,
        code_by_id,
        poste_rows,
        organisme_rows,
        action_rows,
        budget_rows,
        rh_rows,
    )


def build_actions_example_workbook() -> bytes:
    """Classeur **exemple** des actions, entièrement rempli (indépendant d'un plan).

    Reprend le thème de l'exemple d'arborescence : montre des actions rattachées
    à des indicateurs (onglet de référence), avec budgets et RH renseignés dans
    trois modes de ventilation, et illustre les liens entre onglets. Fictif : à
    consulter, pas à importer tel quel (les indicateurs de référence n'existent
    dans aucun plan réel).
    """
    return _render_actions_workbook(
        *_actions_example_data(),
        with_hints=False,
        example_name=ACTIONS_EXAMPLE_NAME,
    )


# Correspondance mode → saisie attendue, affichée dans le « Lisez-moi ».
_LISEZ_MOI_MODES = [
    (
        "none",
        "Budgets : « budget total ». RH : temps global (sans poste ni organisme).",
    ),
    (
        "by_org",
        "Budgets : une ligne par organisme avec son « budget total ». "
        "RH : une ligne par organisme.",
    ),
    (
        "by_type",
        "Budgets : « budget fonctionnement » / « budget investissement », ou le "
        "détail des coûts si « déclinaison par type de coût » = Oui (coût "
        "salarial alors saisi). RH : temps global.",
    ),
    (
        "by_org_type",
        "Budgets : comme « Par type de budget », une ligne par organisme. "
        "RH : une ligne par organisme.",
    ),
    (
        "by_type_poste",
        "Budgets : détail des coûts (coût stage, prestataire, autres coûts…), ou "
        "les deux enveloppes si « déclinaison par type de coût » = Non. "
        "RH : une ligne par poste.",
    ),
    (
        "by_org_type_poste",
        "Budgets : comme « Par type de budget + type de poste », une ligne par "
        "organisme. RH : une ligne par poste.",
    ),
]


def _write_lisez_moi(wb: Workbook, plan, example_name=None, with_hints=False) -> None:
    ws = wb.create_sheet("Lisez-moi", 0)
    ws.sheet_properties.tabColor = _PRIMARY
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    lines = [
        ("Import des actions d'un plan de gestion", _TITLE_FONT),
        (f"Format version {FORMAT_VERSION}", Font(italic=True, color="746F6E")),
        ("", None),
        ("• Remplissez l'onglet « Actions » : une action par ligne.", None),
        (
            "• Rattachez chaque action à un indicateur en reportant son code "
            "(colonne « indicateur ») depuis l'onglet « Indicateurs ».",
            None,
        ),
        (
            "• L'onglet « Indicateurs » liste les indicateurs existants du plan. "
            "Ne modifiez pas la colonne « id (technique) ».",
            None,
        ),
        (
            "• Les colonnes type d'action, priorité et mode de ventilation "
            "proposent une liste déroulante.",
            None,
        ),
        ("• Les actions importées sont créées en brouillon.", None),
        ("", None),
        (
            "Budgets et temps de travail (facultatif)",
            Font(bold=True, color=_PRIMARY),
        ),
        (
            "• Chaque action a un mode de ventilation, comme dans sa fiche : il "
            "fixe les colonnes à remplir dans « Budgets » et la cible du temps de "
            "travail dans « RH ». Laissé vide, il est déduit de ce que vous "
            "saisissez (un poste dans « RH » → mode « + type de poste », un "
            "organisme → mode « par organisme »…).",
            None,
        ),
    ]
    lines += [
        (f"   – {_MODE_LABELS[mode]} : {text}", None)
        for mode, text in _LISEZ_MOI_MODES
    ]
    lines += [
        (
            "• Coût salarial : dans les modes « + type de poste », il est calculé "
            "(jours × coût jour du poste) quand « saisie automatique du coût "
            "salarial » = Oui ; sinon, et dans les autres modes détaillés, "
            "saisissez-le dans les colonnes « coût salarial ».",
            None,
        ),
        (
            "• Catégorie de dépense (onglet « RH ») : Fonctionnement, "
            "Investissement (modes « par type de budget » seulement) ou "
            "Bénévolat partenariat (temps valorisé en jours, sans coût).",
            None,
        ),
        (
            "• Une colonne qui ne correspond pas au mode de l'action est "
            "signalée en erreur : elle serait invisible dans la fiche action.",
            None,
        ),
        (
            "• Les postes du plan sont listés dans l'onglet « Postes » (créez-les "
            "d'abord via la page « Postes / RH » du plan) ; les organismes "
            "gestionnaires des sites du plan dans l'onglet « Organismes ».",
            None,
        ),
        (
            "• Les onglets Budgets et RH proposent une liste déroulante « action » "
            "avec les codes que vous saisissez dans l'onglet « Actions ».",
            None,
        ),
    ]
    if with_hints:
        lines += [
            ("", None),
            (
                "• La première ligne grisée des onglets Actions, Budgets et RH est "
                "un EXEMPLE (commence par « (exemple) ») : elle montre quoi écrire "
                "et n'est jamais importée. Saisissez vos données sur les lignes "
                "suivantes.",
                Font(italic=True, color="9A8F86"),
            ),
        ]
    if example_name is not None:
        lines += [
            ("", None),
            (
                f"⚠ EXEMPLE PÉDAGOGIQUE FICTIF — {example_name}. Illustre le format "
                "et les liens entre onglets ; remplacez son contenu par le vôtre.",
                Font(bold=True, italic=True, color="B74D5D"),
            ),
        ]
    if plan is not None:
        lines += [("", None), (f"Plan : {plan.nom}", Font(italic=True, color="746F6E"))]
    for i, (text, font) in enumerate(lines, start=1):
        cell = ws.cell(row=i, column=2, value=text)
        if font:
            cell.font = font
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.sheet_view.showGridLines = False


def _write_indicateurs_ref(wb, indicateurs, code_by_id) -> str:
    ws = wb.create_sheet("Indicateurs")
    desc = ws.cell(
        row=1,
        column=1,
        value="Indicateurs existants du plan (référence). "
        "Ne modifiez pas la colonne « id ».",
    )
    desc.font = Font(italic=True, color="746F6E", size=10)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(_REF_COLUMNS))
    for c, (key, header, width) in enumerate(_REF_COLUMNS, start=1):
        cell = ws.cell(row=_HEADER_ROW, column=c, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = width
    for r, (ind, enjeu_libelle) in enumerate(indicateurs, start=_FIRST_DATA_ROW):
        ws.cell(row=r, column=1, value=code_by_id[ind.id_indicateur])
        ws.cell(row=r, column=2, value=ind.nom_indicateur)
        ws.cell(row=r, column=3, value=enjeu_libelle)
        ws.cell(row=r, column=4, value=ind.id_indicateur)
        for c in range(1, len(_REF_COLUMNS) + 1):
            ws.cell(row=r, column=c).border = _BORDER
            ws.cell(row=r, column=c).alignment = _WRAP_TOP
    ws.freeze_panes = f"A{_FIRST_DATA_ROW}"
    ws.sheet_view.showGridLines = False
    ws.protection.sheet = True  # onglet de référence : non modifiable
    last = max(len(indicateurs) + _HEADER_ROW, _HEADER_ROW + 1)
    return f"'Indicateurs'!$A${_FIRST_DATA_ROW}:$A${last}"


# Listes hors nomenclature (onglet masqué « Listes »).
_MODE_LIST = "MODE_VENTILATION"
_CATEGORIE_LIST = "CATEGORIE_DEPENSE"


def _write_listes(wb) -> dict[str, str]:
    ws = wb.create_sheet("Listes")
    ranges: dict[str, str] = {}
    lists = {
        **_nomenclature_values(),
        _MODE_LIST: list(_MODE_LABELS.values()),
        _CATEGORIE_LIST: list(_CATEGORIE_LABELS.values()),
    }
    for col_idx, (type_mnemo, labels) in enumerate(lists.items(), start=1):
        letter = get_column_letter(col_idx)
        ws.cell(row=1, column=col_idx, value=type_mnemo).font = Font(bold=True)
        for r, label in enumerate(labels, start=2):
            ws.cell(row=r, column=col_idx, value=label)
        if labels:
            ranges[type_mnemo] = f"'Listes'!${letter}$2:${letter}${len(labels) + 1}"
        ws.column_dimensions[letter].width = 28
    ws.sheet_state = "hidden"
    ws.protection.sheet = True  # onglet de référence : non modifiable
    return ranges


def _write_actions(wb, rows, ref_code_range, list_ranges, hint_row=None) -> None:
    ws = wb.create_sheet("Actions")
    desc = ws.cell(
        row=1,
        column=1,
        value="Une action par ligne, rattachée à un " "indicateur par son code.",
    )
    desc.font = Font(italic=True, color="746F6E", size=10)
    ws.merge_cells(
        start_row=1, start_column=1, end_row=1, end_column=len(_ACTION_COLUMNS)
    )

    for c, (key, header, required, help_text, nomencl, width) in enumerate(
        _ACTION_COLUMNS, start=1
    ):
        cell = ws.cell(row=_HEADER_ROW, column=c, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _REQUIRED_FILL if required else _HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = _BORDER
        if help_text:
            cell.comment = Comment(
                help_text + (" (obligatoire)" if required else ""), "CICADA"
            )
        ws.column_dimensions[get_column_letter(c)].width = width

    r = _FIRST_DATA_ROW
    n_hint = 0
    if hint_row and not rows:
        for c, (key, *_rest) in enumerate(_ACTION_COLUMNS, start=1):
            cell = ws.cell(row=r, column=c, value=hint_row.get(key, ""))
            cell.alignment = _WRAP_TOP
            cell.border = _BORDER
            cell.font = _HINT_FONT
            cell.fill = _HINT_FILL
        r += 1
        n_hint = 1
    for row in rows:
        for c, (key, *_rest) in enumerate(_ACTION_COLUMNS, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(key, ""))
            cell.alignment = _WRAP_TOP
            cell.border = _BORDER
        r += 1

    last_row = _HEADER_ROW + n_hint + max(len(rows), 0) + _BLANK_ROWS
    for c, (key, header, required, help_text, nomencl, width) in enumerate(
        _ACTION_COLUMNS, start=1
    ):
        letter = get_column_letter(c)
        dv = None
        if key == "indicateur":
            dv = DataValidation(type="list", formula1=ref_code_range, allow_blank=True)
        elif key == "mode_ventilation" and list_ranges.get(_MODE_LIST):
            dv = DataValidation(
                type="list", formula1=list_ranges[_MODE_LIST], allow_blank=True
            )
        elif key in ("declinaison_par_type_cout", "cout_salarial_auto"):
            dv = DataValidation(type="list", formula1='"Oui,Non"', allow_blank=True)
        elif nomencl and list_ranges.get(nomencl):
            dv = DataValidation(
                type="list", formula1=list_ranges[nomencl], allow_blank=True
            )
        if dv is not None:
            dv.error = "Choisissez une valeur dans la liste proposée."
            dv.errorTitle = "Valeur non autorisée"
            ws.add_data_validation(dv)
            dv.add(f"{letter}{_FIRST_DATA_ROW}:{letter}{last_row}")

    ws.freeze_panes = f"A{_FIRST_DATA_ROW}"
    ws.auto_filter.ref = (
        f"A{_HEADER_ROW}:{get_column_letter(len(_ACTION_COLUMNS))}{_HEADER_ROW}"
    )
    ws.sheet_view.showGridLines = False


def _oui_non(value: bool) -> str:
    return "Oui" if value else "Non"


def _extract_actions(plan, code_by_id) -> list[dict]:
    """Actions existantes du plan, pour le pré-remplissage (export/sauvegarde)."""
    if not code_by_id:
        return []
    rows = []
    ops = _plan_operations(plan).select_related("id_type_action", "id_priorite")
    for op in ops:
        mode = op.ventilation_mode or "none"
        detail = op.declinaison_par_type_cout
        rows.append(
            {
                "code": _op_code(op),
                "indicateur": code_by_id.get(_op_indicateur_id(op, code_by_id), ""),
                "libelle": op.libelle,
                "type_action": op.id_type_action.label if op.id_type_action else "",
                "priorite": op.id_priorite.label if op.id_priorite else "",
                "annee_min": op.annee_min if op.annee_min is not None else "",
                "annee_max": op.annee_max if op.annee_max is not None else "",
                "mode_ventilation": _MODE_LABELS.get(mode, ""),
                # Réglages exportés seulement là où la fiche les propose.
                "declinaison_par_type_cout": _oui_non(detail)
                if mode in TYPE_VENTILATION_MODES
                else "",
                "cout_salarial_auto": _oui_non(op.cout_salarial_auto)
                if _salary_option_available(mode, detail)
                else "",
                "operateurs": op.operateurs or "",
                "financeurs": op.financeurs or "",
                "description": op.description or "",
            }
        )
    return rows


def _write_ref_sheet(wb, name, description, columns, rows) -> str:
    """Écrit un onglet de référence non modifiable (Postes, Organismes) et
    renvoie la plage de sa colonne « code » (source des listes déroulantes)."""
    ws = wb.create_sheet(name)
    desc = ws.cell(row=1, column=1, value=description)
    desc.font = Font(italic=True, color="746F6E", size=10)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    for c, (key, header, width) in enumerate(columns, start=1):
        cell = ws.cell(row=_HEADER_ROW, column=c, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(c)].width = width
    for r, row in enumerate(rows, start=_FIRST_DATA_ROW):
        for c, (key, _header, _width) in enumerate(columns, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(key, ""))
            cell.border = _BORDER
            cell.alignment = _WRAP_TOP
    ws.freeze_panes = f"A{_FIRST_DATA_ROW}"
    ws.sheet_view.showGridLines = False
    ws.protection.sheet = True  # onglet de référence : non modifiable
    last = max(len(rows) + _HEADER_ROW, _HEADER_ROW + 1)
    return f"'{name}'!$A${_FIRST_DATA_ROW}:$A${last}"


def _write_simple_sheet(
    wb, name, description, columns, rows, dropdowns=None, hint_row=None
) -> None:
    """Écrit un onglet de saisie « à plat » (Budgets, RH).

    ``columns`` : liste de (key, header, required, help, width).
    ``dropdowns`` : {key: (type_or_range)} — 'oui_non' ou une référence de plage.
    ``hint_row`` : ligne exemple (grisée, jamais importée) si l'onglet est vide.
    """
    dropdowns = dropdowns or {}
    ws = wb.create_sheet(name)
    desc = ws.cell(row=1, column=1, value=description)
    desc.font = Font(italic=True, color="746F6E", size=10)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))

    for c, (key, header, required, help_text, width) in enumerate(columns, start=1):
        cell = ws.cell(row=_HEADER_ROW, column=c, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _REQUIRED_FILL if required else _HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = _BORDER
        if help_text:
            cell.comment = Comment(
                help_text + (" (obligatoire)" if required else ""), "CICADA"
            )
        ws.column_dimensions[get_column_letter(c)].width = width

    r = _FIRST_DATA_ROW
    n_hint = 0
    if hint_row and not rows:
        for c, (key, *_rest) in enumerate(columns, start=1):
            cell = ws.cell(row=r, column=c, value=hint_row.get(key, ""))
            cell.alignment = _WRAP_TOP
            cell.border = _BORDER
            cell.font = _HINT_FONT
            cell.fill = _HINT_FILL
        r += 1
        n_hint = 1
    for row in rows:
        for c, (key, *_rest) in enumerate(columns, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(key, ""))
            cell.alignment = _WRAP_TOP
            cell.border = _BORDER
        r += 1

    last_row = _HEADER_ROW + n_hint + max(len(rows), 0) + _BLANK_ROWS
    for c, (key, *_rest) in enumerate(columns, start=1):
        spec = dropdowns.get(key)
        if not spec:
            continue
        formula = '"Oui,Non"' if spec == "oui_non" else spec
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        dv.error = "Choisissez une valeur dans la liste proposée."
        dv.errorTitle = "Valeur non autorisée"
        ws.add_data_validation(dv)
        letter = get_column_letter(c)
        dv.add(f"{letter}{_FIRST_DATA_ROW}:{letter}{last_row}")

    ws.freeze_panes = f"A{_FIRST_DATA_ROW}"
    ws.auto_filter.ref = (
        f"A{_HEADER_ROW}:{get_column_letter(len(columns))}{_HEADER_ROW}"
    )
    ws.sheet_view.showGridLines = False


def _write_budgets(wb, rows, actions_range, org_code_range, hint_row=None) -> None:
    _write_simple_sheet(
        wb,
        "Budgets",
        "Montants par action et par année (et par organisme dans les modes "
        "« par organisme »). Ne remplissez que les colonnes du mode de "
        "ventilation de l'action (voir « Lisez-moi »).",
        _BUDGET_COLUMNS,
        rows,
        dropdowns={"action": actions_range, "organisme": org_code_range},
        hint_row=hint_row,
    )


def _write_rh(
    wb, rows, poste_code_range, org_code_range, actions_range, list_ranges,
    hint_row=None,
) -> None:
    dropdowns = {
        "action": actions_range,
        "poste": poste_code_range,
        "organisme": org_code_range,
    }
    if list_ranges.get(_CATEGORIE_LIST):
        dropdowns["categorie_depense"] = list_ranges[_CATEGORIE_LIST]
    _write_simple_sheet(
        wb,
        "RH",
        "Temps de travail en jours par action et par année : par poste, par "
        "organisme ou global selon le mode de ventilation de l'action.",
        _RH_COLUMNS,
        rows,
        dropdowns=dropdowns,
        hint_row=hint_row,
    )


def _plan_operations(plan):
    """Opérations rattachées aux indicateurs du plan — directement ou par une
    de leurs métriques (actions antérieures au rattachement direct #398)."""
    ids = [ind.id_indicateur for ind, _ in _plan_indicateurs(plan)]
    if not ids:
        return Operation.objects.none()
    return (
        Operation.objects.filter(
            Q(id_indicateur_id__in=ids) | Q(metriques__id_indicateur_id__in=ids)
        )
        .distinct()
        .order_by("ordre", "id_operation")
    )


def _op_indicateur_id(op, code_by_id):
    """Indicateur de rattachement d'une action : le direct, sinon celui de sa
    première métrique appartenant au plan."""
    if op.id_indicateur_id in code_by_id:
        return op.id_indicateur_id
    for ind_id in op.metriques.values_list("id_indicateur_id", flat=True):
        if ind_id in code_by_id:
            return ind_id
    return None


def _op_code(op) -> str:
    return op.code_operation or f"A{op.id_operation}"


def _cell_value(value):
    return "" if value is None else value


def _extract_budgets(plan, org_code_by_id) -> list[dict]:
    """Montants existants, dans les colonnes du mode de chaque action."""
    rows = []
    for op in _plan_operations(plan).prefetch_related("operation_annees__organismes"):
        mode = op.ventilation_mode or "none"
        cols = _allowed_budget_cols(
            mode, op.declinaison_par_type_cout, op.cout_salarial_auto
        )
        for oa in op.operation_annees.all():
            if mode in ORG_VENTILATION_MODES:
                sources = [
                    (org_code_by_id.get(oao.id_organisme_id, ""), oao)
                    for oao in oa.organismes.all()
                ]
            else:
                sources = [("", oa)]
            for org_code, src in sources:
                row = {"action": _op_code(op), "annee": oa.annee, "organisme": org_code}
                for col in cols:
                    if col == "budget_total":
                        # Par organisme, le total est rangé côté fonctionnement.
                        value = (
                            src.budget_fonctionnement if mode == "by_org" else src.budget
                        )
                    else:
                        value = getattr(src, col)
                    row[col] = _cell_value(value)
                if any(_cell_str(row.get(col)) for col in cols):
                    rows.append(row)
    return rows


def _extract_rh(plan, poste_code_by_id, org_code_by_id) -> list[dict]:
    rows = []
    for op in _plan_operations(plan):
        for oa in op.operation_annees.all().order_by("annee"):
            for rh in oa.rh_lignes.all().order_by("id_operation_annee_rh"):
                categorie, _finance = CategorieDepense.resolve(
                    rh.categorie_depense, rh.finance
                )
                rows.append(
                    {
                        "action": _op_code(op),
                        "annee": oa.annee if oa.annee is not None else "",
                        "poste": poste_code_by_id.get(rh.id_poste_id, ""),
                        "organisme": ""
                        if rh.id_poste_id
                        else org_code_by_id.get(rh.id_organisme_id, ""),
                        "jours": _cell_value(rh.jours),
                        "categorie_depense": _CATEGORIE_LABELS.get(categorie, ""),
                    }
                )
    return rows


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_actions_workbook(source) -> dict:
    """Lit le classeur d'actions : renvoie ``{"actions": [...], "indicateurs":
    {code: id_indicateur}}``. Lève ``ArborescenceImportError`` si illisible."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    elif hasattr(source, "read"):
        source = io.BytesIO(source.read())
    try:
        wb = load_workbook(source, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ArborescenceImportError(
            "Le fichier n'a pas pu être lu. Vérifiez qu'il s'agit bien d'un "
            "classeur Excel (.xlsx) issu du modèle d'import des actions."
        ) from exc

    ws_by_name = {_norm(name): wb[name] for name in wb.sheetnames}

    ref = ws_by_name.get(_norm("Indicateurs"))
    actions_ws = ws_by_name.get(_norm("Actions"))
    if ref is None or actions_ws is None:
        raise ArborescenceImportError(
            "Onglets « Indicateurs » et « Actions » attendus dans le fichier."
        )

    # Référence code → id_indicateur (colonne 1 = code, colonne 4 = id).
    ref_map: dict[str, int] = {}
    for values in ref.iter_rows(min_row=_FIRST_DATA_ROW, values_only=True):
        code = _cell_str(values[0] if len(values) > 0 else None)
        ident = _as_int(values[3] if len(values) > 3 else None)
        if code and ident is not None:
            ref_map[code] = ident

    # Actions.
    header_to_key = {_norm(header): key for key, header, *_ in _ACTION_COLUMNS}
    col_index_to_key: dict[int, str] = {}
    header_cells = next(
        actions_ws.iter_rows(
            min_row=_HEADER_ROW, max_row=_HEADER_ROW, values_only=True
        ),
        (),
    )
    for idx, cell in enumerate(header_cells):
        key = header_to_key.get(_norm(cell))
        if key:
            col_index_to_key[idx] = key
    for key, header, required, *_ in _ACTION_COLUMNS:
        if required and key not in col_index_to_key.values():
            raise ArborescenceImportError(
                f"Colonne obligatoire « {header} » absente de l'onglet « Actions »."
            )

    actions = []
    for r, values in enumerate(
        actions_ws.iter_rows(min_row=_FIRST_DATA_ROW, values_only=True),
        start=_FIRST_DATA_ROW,
    ):
        record, has_value = {}, False
        for idx, key in col_index_to_key.items():
            value = values[idx] if idx < len(values) else None
            if _cell_str(value):
                has_value = True
            record[key] = value
        if not has_value:
            continue
        if _is_example_row(record.get("code")):  # ligne exemple du modèle
            continue
        record["_row"] = r
        actions.append(record)

    budgets = _parse_flat_sheet(ws_by_name.get(_norm("Budgets")), _BUDGET_HEADERS)
    rh = _parse_flat_sheet(ws_by_name.get(_norm("RH")), _RH_HEADERS)

    return {
        "actions": actions,
        "indicateurs": ref_map,
        "postes": _parse_ref_codes(ws_by_name.get(_norm("Postes"))),
        "organismes": _parse_ref_codes(ws_by_name.get(_norm("Organismes"))),
        "budgets": budgets,
        "rh": rh,
    }


def _parse_ref_codes(ws) -> dict[str, int]:
    """Onglet de référence (Postes, Organismes) → ``{code: id}``.

    La colonne de l'identifiant est retrouvée par son en-tête (« id … ») : sa
    position a changé d'une version du modèle à l'autre."""
    if ws is None:
        return {}
    header = next(
        ws.iter_rows(min_row=_HEADER_ROW, max_row=_HEADER_ROW, values_only=True), ()
    )
    id_idx = next(
        (i for i, h in enumerate(header) if _norm(h).startswith("id")), None
    )
    if id_idx is None:
        return {}
    codes: dict[str, int] = {}
    for values in ws.iter_rows(min_row=_FIRST_DATA_ROW, values_only=True):
        code = _cell_str(values[0] if values else None)
        ident = _as_int(values[id_idx] if id_idx < len(values) else None)
        if code and ident is not None:
            codes[code] = ident
    return codes


def _parse_flat_sheet(ws, headers_map) -> list[dict]:
    """Lit un onglet à plat (en-tête ligne 2, données dès la ligne 3) en
    rapprochant les en-têtes de ``headers_map`` (``{en-tête normalisé: clé}``)."""
    if ws is None:
        return []
    col_index_to_key: dict[int, str] = {}
    header_cells = next(
        ws.iter_rows(min_row=_HEADER_ROW, max_row=_HEADER_ROW, values_only=True), ()
    )
    for idx, cell in enumerate(header_cells):
        key = headers_map.get(_norm(cell))
        if key:
            col_index_to_key[idx] = key

    rows = []
    for r, values in enumerate(
        ws.iter_rows(min_row=_FIRST_DATA_ROW, values_only=True), start=_FIRST_DATA_ROW
    ):
        record, has_value = {}, False
        for idx, key in col_index_to_key.items():
            value = values[idx] if idx < len(values) else None
            if _cell_str(value):
                has_value = True
            record[key] = value
        if not has_value:
            continue
        if _is_example_row(record.get("action")):  # ligne exemple du modèle
            continue
        record["_row"] = r
        rows.append(record)
    return rows


# ---------------------------------------------------------------------------
# Paramétrage budgétaire de chaque action : explicite ou déduit
# ---------------------------------------------------------------------------


def _rows_by_action(rows) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(_cell_str(row.get("action")), []).append(row)
    return grouped


def _filled(rows, keys) -> bool:
    return any(_cell_str(row.get(k)) for row in rows for k in keys)


def _resolve_settings(action_row, budget_rows, rh_rows) -> dict:
    """Paramétrage budgétaire d'une action (#600).

    Une valeur saisie dans l'onglet « Actions » fait foi ; une cellule vide
    (ou illisible — signalée à la validation) est déduite de ce que l'action
    renseigne dans « Budgets » et « RH ». Renvoie ``mode``, ``detail`` (case
    « déclinaison par type de coût »), ``auto`` (case « saisie automatique du
    coût salarial ») et ``salary_computed`` — la valeur que la fiche action
    enregistre dans ``cout_salarial_auto``.
    """
    has_org = _filled(budget_rows, ("organisme",)) or _filled(rh_rows, ("organisme",))
    has_poste = _filled(rh_rows, ("poste",))
    has_detail = _filled(budget_rows, _BUDGET_DETAIL_COLS + _BUDGET_SALARY_COLS)
    has_envelopes = _filled(budget_rows, _BUDGET_ENVELOPE_COLS)
    has_invest_time = any(
        _parse_categorie(r.get("categorie_depense")) == CategorieDepense.INVESTISSEMENT
        for r in rh_rows
    )

    mode = _parse_mode(action_row.get("mode_ventilation"))
    if mode is None:
        if has_poste:
            mode = "by_org_type_poste" if has_org else "by_type_poste"
        elif has_detail or has_envelopes or has_invest_time:
            mode = "by_org_type" if has_org else "by_type"
        elif has_org:
            mode = "by_org"
        else:
            mode = "none"

    detail = _parse_bool(action_row.get("declinaison_par_type_cout"))
    if detail is None:
        # Défaut du modèle (cochée), sauf si seules les enveloppes sont saisies.
        detail = not (has_envelopes and not has_detail)

    auto = _parse_bool(action_row.get("cout_salarial_auto"))
    if auto is None:
        auto = not _filled(budget_rows, _BUDGET_SALARY_COLS)

    return {
        "mode": mode,
        "detail": detail,
        "auto": auto,
        "salary_computed": _salary_is_computed(mode, detail, auto),
    }


def _all_settings(parsed: dict) -> dict[str, dict]:
    budgets = _rows_by_action(parsed.get("budgets", []))
    rh = _rows_by_action(parsed.get("rh", []))
    settings: dict[str, dict] = {}
    for row in parsed.get("actions", []):
        code = _cell_str(row.get("code"))
        if code and code not in settings:
            settings[code] = _resolve_settings(
                row, budgets.get(code, []), rh.get(code, [])
            )
    return settings


def _mode_phrase(settings) -> str:
    """« mode « … » » complété du réglage de détail quand il compte."""
    mode = settings["mode"]
    phrase = f"le mode « {_MODE_LABELS[mode]} »"
    if mode in TYPE_VENTILATION_MODES:
        phrase += (
            " avec déclinaison par type de coût"
            if settings["detail"]
            else " sans déclinaison par type de coût"
        )
        if settings["detail"] and mode in _POSTE_MODES and settings["salary_computed"]:
            phrase += " et coût salarial calculé"
    return phrase


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_actions_import(plan, parsed: dict) -> ImportReport:
    report = ImportReport()
    resolver = _NomenclatureResolver()

    plan_indicateur_ids = {ind.id_indicateur for ind, _ in _plan_indicateurs(plan)}
    if not plan_indicateur_ids:
        report.add(
            None,
            None,
            None,
            ERROR,
            "Ce plan n'a pas encore d'indicateurs : importez d'abord "
            "l'arborescence.",
        )

    # Création seule : refuser si des actions existent déjà.
    if _plan_operations(plan).exists():
        report.add(
            None,
            None,
            None,
            ERROR,
            "Ce plan contient déjà des actions. L'import n'est possible "
            "que sur un plan sans action.",
        )

    ref_map = parsed.get("indicateurs", {})
    codes: set[str] = set()
    for row in parsed.get("actions", []):
        r = row["_row"]
        code = _cell_str(row.get("code"))
        if not code:
            report.add("Actions", r, "code", ERROR, "Code manquant.")
        elif code in codes:
            report.add("Actions", r, "code", ERROR, f"Code « {code} » en double.")
        else:
            codes.add(code)

        if not _cell_str(row.get("libelle")):
            report.add("Actions", r, "libelle", ERROR, "« libellé » est obligatoire.")

        ind_code = _cell_str(row.get("indicateur"))
        if not ind_code:
            report.add(
                "Actions",
                r,
                "indicateur",
                ERROR,
                "L'indicateur de rattachement est obligatoire.",
            )
        else:
            ident = ref_map.get(ind_code)
            if ident is None:
                report.add(
                    "Actions",
                    r,
                    "indicateur",
                    ERROR,
                    f"Indicateur « {ind_code} » introuvable dans l'onglet "
                    "« Indicateurs ».",
                )
            elif ident not in plan_indicateur_ids:
                report.add(
                    "Actions",
                    r,
                    "indicateur",
                    ERROR,
                    f"L'indicateur « {ind_code} » n'appartient pas à ce plan.",
                )

        for col, type_mnemo, label in (
            ("type_action", _TYPE_ACTION, "type d'action"),
            ("priorite", _PRIORITE, "priorité"),
        ):
            value = _cell_str(row.get(col))
            if value and resolver.resolve(type_mnemo, value) is None:
                report.add(
                    "Actions",
                    r,
                    col,
                    ERROR,
                    f"Valeur « {value} » non reconnue pour « {label} ».",
                )

        amin, amax = _as_int(row.get("annee_min")), _as_int(row.get("annee_max"))
        for col, raw in (
            ("annee_min", row.get("annee_min")),
            ("annee_max", row.get("annee_max")),
        ):
            if _cell_str(raw) and _as_int(raw) is None:
                report.add("Actions", r, col, ERROR, "L'année doit être un nombre.")
        if amin is not None and amax is not None and amin > amax:
            report.add(
                "Actions",
                r,
                "annee_max",
                ERROR,
                "L'année de fin est antérieure à l'année de début.",
            )

    # --- Paramétrage budgétaire (#600) ---
    for row in parsed.get("actions", []):
        r = row["_row"]
        mode_raw = _cell_str(row.get("mode_ventilation"))
        if mode_raw and _parse_mode(mode_raw) is None:
            report.add(
                "Actions",
                r,
                "mode_ventilation",
                ERROR,
                f"Mode de ventilation « {mode_raw} » non reconnu. Valeurs "
                "possibles : " + ", ".join(_MODE_LABELS.values()) + ".",
            )
        for col, label in (
            ("declinaison_par_type_cout", "déclinaison par type de coût"),
            ("cout_salarial_auto", "saisie automatique du coût salarial"),
        ):
            raw = _cell_str(row.get(col))
            if raw and _parse_bool(raw) is None:
                report.add(
                    "Actions", r, col, ERROR, f"« {label} » : Oui ou Non attendu."
                )

    settings_by_code = _all_settings(parsed)
    for row in parsed.get("actions", []):
        settings = settings_by_code.get(_cell_str(row.get("code")))
        if settings is None:
            continue
        mode, detail = settings["mode"], settings["detail"]
        r = row["_row"]
        if (
            _cell_str(row.get("declinaison_par_type_cout"))
            and mode not in TYPE_VENTILATION_MODES
        ):
            report.add(
                "Actions",
                r,
                "declinaison_par_type_cout",
                WARNING,
                f"Sans effet en mode « {_MODE_LABELS[mode]} » (réservé aux modes "
                "« par type de budget ») : la valeur est ignorée.",
            )
        if _cell_str(row.get("cout_salarial_auto")) and not _salary_option_available(
            mode, detail
        ):
            report.add(
                "Actions",
                r,
                "cout_salarial_auto",
                WARNING,
                "Sans effet pour ce paramétrage (réservé aux modes « + type de "
                "poste » avec déclinaison par type de coût) : la valeur est "
                "ignorée.",
            )

    # --- Budgets et RH (facultatifs), rattachés aux actions par leur code ---
    action_codes = {
        _cell_str(r.get("code"))
        for r in parsed.get("actions", [])
        if _cell_str(r.get("code"))
    }
    spans = {
        _cell_str(r.get("code")): (
            _as_int(r.get("annee_min")),
            _as_int(r.get("annee_max")),
        )
        for r in parsed.get("actions", [])
        if _cell_str(r.get("code"))
    }
    poste_ref = parsed.get("postes", {})
    plan_poste_ids = {p.id_poste for p in _plan_postes(plan)}
    org_ref = parsed.get("organismes", {})
    plan_org_ids = {org.id_organisme for org, _s in _plan_organismes(plan)}

    def _check_action_annee(sheet, row, ac):
        rr = row["_row"]
        if not ac:
            report.add(sheet, rr, "action", ERROR, "Code d'action manquant.")
        elif ac not in action_codes:
            report.add(
                sheet,
                rr,
                "action",
                ERROR,
                f"Action « {ac} » introuvable dans l'onglet « Actions ».",
            )
        annee = _as_int(row.get("annee"))
        if not _cell_str(row.get("annee")):
            report.add(sheet, rr, "annee", ERROR, "L'année est obligatoire.")
        elif annee is None:
            report.add(sheet, rr, "annee", ERROR, "L'année doit être un nombre.")
        elif ac in spans:
            amin, amax = spans[ac]
            if amin is not None and amax is not None and not (amin <= annee <= amax):
                report.add(
                    sheet,
                    rr,
                    "annee",
                    WARNING,
                    f"L'année {annee} est hors de la période de l'action "
                    f"({amin}–{amax}).",
                )
        return annee

    def _check_amount(sheet, row, col, label):
        raw = row.get(col)
        if not _cell_str(raw):
            return
        value = _as_decimal(raw)
        if value is None:
            report.add(sheet, row["_row"], col, ERROR, f"{label} doit être un nombre.")
        elif value < 0:
            report.add(
                sheet, row["_row"], col, ERROR, f"{label} ne peut pas être négatif."
            )

    def _check_ref(sheet, row, col, ref, plan_ids, what, where):
        """Code de poste / d'organisme : connu de l'onglet de référence et
        appartenant bien au plan."""
        code = _cell_str(row.get(col))
        ident = ref.get(code)
        if ident is None:
            report.add(
                sheet,
                row["_row"],
                col,
                ERROR,
                f"{what} « {code} » introuvable dans l'onglet « {where} ».",
            )
        elif ident not in plan_ids:
            report.add(
                sheet,
                row["_row"],
                col,
                ERROR,
                f"{what} « {code} » n'appartient pas à ce plan.",
            )

    def _check_target(sheet, row, col, expected, settings, what):
        """Présence / absence d'une cible (poste, organisme) selon le mode."""
        filled = bool(_cell_str(row.get(col)))
        if expected and not filled:
            report.add(
                sheet,
                row["_row"],
                col,
                ERROR,
                f"{what} obligatoire : l'action est en "
                f"« {_MODE_LABELS[settings['mode']]} ».",
            )
        elif filled and not expected:
            report.add(
                sheet,
                row["_row"],
                col,
                ERROR,
                f"{what} inattendu : l'action est en "
                f"« {_MODE_LABELS[settings['mode']]} ». Laissez la colonne vide "
                "ou changez le mode de ventilation de l'action.",
            )
        return filled

    seen_budget_keys: set[tuple] = set()
    for row in parsed.get("budgets", []):
        ac = _cell_str(row.get("action"))
        annee = _check_action_annee("Budgets", row, ac)
        for col in _BUDGET_VALUE_COLS:
            if col not in _BUDGET_TEXT_COLS:
                _check_amount(
                    "Budgets", row, col, f"« {_BUDGET_HEADER_BY_KEY[col]} »"
                )
        settings = settings_by_code.get(ac)
        if settings is None:
            continue
        mode = settings["mode"]
        if _check_target(
            "Budgets",
            row,
            "organisme",
            mode in ORG_VENTILATION_MODES,
            settings,
            "Organisme",
        ):
            _check_ref(
                "Budgets", row, "organisme", org_ref, plan_org_ids,
                "Organisme", "Organismes",
            )
        allowed = _allowed_budget_cols(
            mode, settings["detail"], settings["salary_computed"]
        )
        for col in _BUDGET_VALUE_COLS:
            if col in allowed or not _cell_str(row.get(col)):
                continue
            report.add(
                "Budgets",
                row["_row"],
                col,
                ERROR,
                f"« {_BUDGET_HEADER_BY_KEY[col]} » n'est pas utilisé par "
                f"{_mode_phrase(settings)} : ce montant n'apparaîtrait pas dans "
                "la fiche action. Colonnes attendues : "
                + ", ".join(f"« {_BUDGET_HEADER_BY_KEY[c]} »" for c in allowed)
                + ".",
            )
        key = (ac, annee, _cell_str(row.get("organisme")))
        if annee is not None and key in seen_budget_keys:
            report.add(
                "Budgets",
                row["_row"],
                "annee",
                ERROR,
                "Ligne en double : un seul budget par action, année"
                + (" et organisme." if mode in ORG_VENTILATION_MODES else "."),
            )
        seen_budget_keys.add(key)

    for row in parsed.get("rh", []):
        ac = _cell_str(row.get("action"))
        _check_action_annee("RH", row, ac)
        _check_amount("RH", row, "jours", "Le nombre de jours")
        categorie_raw = _cell_str(row.get("categorie_depense"))
        categorie = _parse_categorie(categorie_raw)
        if categorie_raw and categorie is None:
            report.add(
                "RH",
                row["_row"],
                "categorie_depense",
                ERROR,
                f"Catégorie de dépense « {categorie_raw} » non reconnue. Valeurs "
                "possibles : " + ", ".join(_CATEGORIE_LABELS.values()) + ".",
            )
        finance = _cell_str(row.get("finance"))
        if finance and _parse_bool(finance) is None:
            report.add(
                "RH", row["_row"], "finance", ERROR, "Valeur attendue : Oui ou Non."
            )
        settings = settings_by_code.get(ac)
        if settings is None:
            continue
        mode = settings["mode"]
        target = _rh_target(mode)
        if _check_target("RH", row, "poste", target == "poste", settings, "Poste"):
            _check_ref(
                "RH", row, "poste", poste_ref, plan_poste_ids, "Poste", "Postes"
            )
        if _check_target(
            "RH", row, "organisme", target == "organisme", settings, "Organisme"
        ):
            _check_ref(
                "RH", row, "organisme", org_ref, plan_org_ids,
                "Organisme", "Organismes",
            )
        if (
            categorie == CategorieDepense.INVESTISSEMENT
            and mode not in TYPE_VENTILATION_MODES
        ):
            # La fiche action ne propose pas la catégorie dans ce mode, mais
            # conserve celle d'une ligne existante : on fait de même.
            report.add(
                "RH",
                row["_row"],
                "categorie_depense",
                WARNING,
                f"« Investissement » n'est pas proposé en mode "
                f"« {_MODE_LABELS[mode]} » (seuls les modes « par type de "
                "budget » distinguent fonctionnement et investissement) : la "
                "catégorie est conservée mais n'apparaîtra pas dans la fiche.",
            )

    report.summary = {
        "actions": len(parsed.get("actions", [])),
        "budgets": len(parsed.get("budgets", [])),
        "rh": len(parsed.get("rh", [])),
    }
    return report


# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------


def _store_budget_row(target, row, allowed, mode) -> None:
    """Recopie les montants d'une ligne « Budgets » sur l'année
    (``OperationAnnee``) ou l'organisme (``OperationAnneeOrganisme``)."""
    for col in allowed:
        if col in _BUDGET_TEXT_COLS:
            setattr(target, col, _cell_str(row.get(col)))
            continue
        value = _as_decimal(row.get(col))
        if col == "budget_total":
            # Même rangement que la fiche action : total direct sur l'année,
            # total d'un organisme côté fonctionnement (mode « Par organisme »).
            if mode == "by_org":
                target.budget_fonctionnement = value
            else:
                target.budget = value
        else:
            setattr(target, col, value)


def _year_total(op, oa, org_lines, rh_lines) -> Decimal | None:
    """Budget total d'une année, calculé comme la fiche action l'enregistre
    dans ``OperationAnnee.budget`` (toutes familles de coût confondues)."""
    if op.ventilation_mode == "none":
        return oa.budget
    fields = (
        _BUDGET_ENVELOPE_COLS + _BUDGET_SALARY_COLS + tuple(
            c for c in _BUDGET_DETAIL_COLS if c not in _BUDGET_TEXT_COLS
        )
    )
    total = Decimal(0)
    found = False
    for src in [oa, *org_lines]:
        for f in fields:
            value = getattr(src, f, None)
            if value is not None:
                total += value
                found = True
    if (
        _budget_layout(op.ventilation_mode, op.declinaison_par_type_cout) == "detail"
        and op.cout_salarial_auto
    ):
        for line in rh_lines:
            if line.categorie_depense == CategorieDepense.BENEVOLAT_PARTENARIAT:
                continue
            cout_jour = line.id_poste.cout_jour if line.id_poste else None
            if line.jours is not None and cout_jour is not None:
                total += line.jours * cout_jour
                found = True
    return total if found else None


@transaction.atomic
def execute_actions_import(plan, parsed: dict, user) -> dict:
    report = validate_actions_import(plan, parsed)
    if not report.can_import:
        raise ValueError(report)

    resolver = _NomenclatureResolver()
    ref_map = parsed.get("indicateurs", {})
    indicateurs = {ind.id_indicateur: ind for ind, _ in _plan_indicateurs(plan)}
    settings_by_code = _all_settings(parsed)

    def nom(type_mnemo, value):
        v = _cell_str(value)
        return resolver.resolve(type_mnemo, v) if v else None

    op_by_code: dict[str, Operation] = {}
    annee_index: dict[tuple[str, int], OperationAnnee] = {}

    n_actions = n_annees = 0
    for i, row in enumerate(parsed.get("actions", [])):
        ident = ref_map.get(_cell_str(row.get("indicateur")))
        indicateur = indicateurs.get(ident)
        amin = _as_int(row.get("annee_min"))
        amax = _as_int(row.get("annee_max"))
        code = _cell_str(row.get("code"))
        settings = settings_by_code[code]
        operation = Operation.objects.create(
            id_indicateur=indicateur,
            libelle=_cell_str(row.get("libelle")),
            code_operation=code or None,
            id_type_action=nom(_TYPE_ACTION, row.get("type_action")),
            id_priorite=nom(_PRIORITE, row.get("priorite")),
            annee_min=amin,
            annee_max=amax,
            operateurs=_cell_str(row.get("operateurs")) or None,
            financeurs=_cell_str(row.get("financeurs")) or None,
            description=_cell_str(row.get("description")) or None,
            # #600 — paramétrage budgétaire, enregistré comme par la fiche action.
            ventilation_mode=settings["mode"],
            declinaison_par_poste=settings["mode"] in _POSTE_MODES,
            declinaison_par_type_cout=settings["detail"],
            cout_salarial_auto=settings["salary_computed"],
            statut="draft",
            ordre=i,
            id_utilisateur_ajout=user,
        )
        op_by_code[code] = operation
        n_actions += 1
        if amin is not None and amax is not None:
            for annee in range(amin, amax + 1):
                oa = OperationAnnee.objects.create(id_operation=operation, annee=annee)
                annee_index[(code, annee)] = oa
                n_annees += 1

    def _get_annee(code, annee):
        """OperationAnnee de (action, année), créée à la volée si nécessaire."""
        nonlocal n_annees
        key = (code, annee)
        oa = annee_index.get(key)
        if oa is None:
            oa = OperationAnnee.objects.create(
                id_operation=op_by_code[code], annee=annee
            )
            annee_index[key] = oa
            n_annees += 1
        return oa

    org_ref = parsed.get("organismes", {})
    organismes = {org.id_organisme: (org, sites) for org, sites in _plan_organismes(plan)}
    org_lines: dict[tuple[str, int], dict[int, OperationAnneeOrganisme]] = {}
    orgs_by_action: dict[str, set[int]] = {}

    def _get_org_line(code, annee, org_id):
        lines = org_lines.setdefault((code, annee), {})
        if org_id not in lines:
            lines[org_id] = OperationAnneeOrganisme(
                id_operation_annee=_get_annee(code, annee),
                id_organisme=organismes[org_id][0],
            )
            orgs_by_action.setdefault(code, set()).add(org_id)
        return lines[org_id]

    # --- Budgets : colonnes du mode de l'action, sur l'année ou l'organisme ---
    n_budgets = 0
    touched: set[tuple[str, int]] = set()
    for row in parsed.get("budgets", []):
        code = _cell_str(row.get("action"))
        annee = _as_int(row.get("annee"))
        if code not in op_by_code or annee is None:
            continue
        settings = settings_by_code[code]
        allowed = _allowed_budget_cols(
            settings["mode"], settings["detail"], settings["salary_computed"]
        )
        if settings["mode"] in ORG_VENTILATION_MODES:
            org_id = org_ref.get(_cell_str(row.get("organisme")))
            target = _get_org_line(code, annee, org_id)
        else:
            target = _get_annee(code, annee)
        _store_budget_row(target, row, allowed, settings["mode"])
        touched.add((code, annee))
        n_budgets += 1

    # --- RH : temps de travail par poste, par organisme ou global (#560) ---
    postes_by_id = {p.id_poste: p for p in _plan_postes(plan)}
    poste_ref = parsed.get("postes", {})
    rh_by_year: dict[tuple[str, int], list[OperationAnneeRH]] = {}
    n_rh = 0
    for row in parsed.get("rh", []):
        code = _cell_str(row.get("action"))
        annee = _as_int(row.get("annee"))
        if code not in op_by_code or annee is None:
            continue
        target = _rh_target(settings_by_code[code]["mode"])
        poste = (
            postes_by_id.get(poste_ref.get(_cell_str(row.get("poste"))))
            if target == "poste"
            else None
        )
        org_id = (
            org_ref.get(_cell_str(row.get("organisme")))
            if target == "organisme"
            else None
        )
        categorie = _parse_categorie(row.get("categorie_depense"))
        finance = _parse_bool(row.get("finance"))
        if categorie is None and finance is None and poste is not None:
            # Défaut de la fiche action : le caractère financé du poste.
            finance = poste.is_finance_par_defaut()
        line = OperationAnneeRH(
            id_operation_annee=_get_annee(code, annee),
            id_poste=poste,
            id_organisme=organismes[org_id][0] if org_id else None,
            jours=_as_decimal(row.get("jours")),
            categorie_depense=categorie or "",
            finance=True if finance is None else finance,
        )
        line.save()  # réconcilie catégorie de dépense et « financé » (#597)
        rh_by_year.setdefault((code, annee), []).append(line)
        if org_id:
            orgs_by_action.setdefault(code, set()).add(org_id)
        touched.add((code, annee))
        n_rh += 1

    # --- Totaux de l'année, comme les enregistre la fiche action ---
    for code, annee in touched:
        op = op_by_code[code]
        oa = annee_index[(code, annee)]
        rh_lines = rh_by_year.get((code, annee), [])
        if _rh_target(op.ventilation_mode) == "organisme":
            # Temps de chaque organisme reporté sur sa ligne de ventilation
            # (créée si l'organisme n'a que du temps, sans budget).
            for rh in rh_lines:
                _get_org_line(code, annee, rh.id_organisme_id)
            for org_id, org_line in org_lines[(code, annee)].items():
                jours = [
                    rh.jours for rh in rh_lines
                    if rh.id_organisme_id == org_id and rh.jours is not None
                ]
                org_line.etp = sum(jours) if jours else None
        lines = org_lines.get((code, annee), {})
        for org_line in lines.values():
            org_line.save()
        jours = [rh.jours for rh in rh_lines if rh.jours is not None]
        oa.etp = sum(jours) if jours else None
        oa.budget = _year_total(op, oa, list(lines.values()), rh_lines)
        # Une année qui porte un montant est « programmée » (autoCheckPeriodicite).
        oa.periodicite = bool((oa.budget or 0) > 0 or (oa.etp or 0) > 0)
        oa.save()

    # Les organismes de la ventilation sont ceux des sites de l'action : sans ce
    # rattachement, la fiche action ne les proposerait pas (plan multi-sites).
    for code, org_ids in orgs_by_action.items():
        site_ids = sorted({s for oid in org_ids for s in organismes[oid][1]})
        CorOperationSite.objects.bulk_create(
            [
                CorOperationSite(id_operation=op_by_code[code], id_site_id=sid)
                for sid in site_ids
            ],
            ignore_conflicts=True,
        )

    return {
        "actions": n_actions,
        "annees": n_annees,
        "budgets": n_budgets,
        "rh": n_rh,
    }
