"""
Logique financière **partagée** des exports (fiche action + budget/RH).

Le coût salarial n'étant pas stocké en base, il est recalculé
(Σ jours × ``Poste.cout_jour``). Ce module centralise, pour un plan :

- l'attribution des coûts par **organisme gestionnaire** et par **année** ;
- la ventilation **fonctionnement / investissement** (via ``categorie_depense``
  des lignes RH pour le salarial, via les champs dédiés de
  ``OperationAnneeOrganisme`` pour prestataire / autres coûts) ;
- le **prévisionnel** et le **réalisé** (suivi) ;
- une **synthèse par type de poste** (jours) pour l'export RH.

Réponses produit (issue #607) intégrées :
1. ventilation fonct/invest par ``categorie_depense`` ; prestataire et autres
   coûts existent en fonct **et** en invest ;
2. coût prestataire présent dans les deux blocs (``cout_prestataire`` /
   ``cout_prestataire_invest``) ;
3. modes sans ventilation par organisme (``none`` / ``by_type`` /
   ``by_type_poste``) : pas de bloc par organisme dans la fiche action.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

# Modes de ventilation comportant une répartition par organisme gestionnaire.
ORG_VENTILATION_MODES = {"by_org", "by_org_type", "by_org_type_poste"}

_ZERO = Decimal(0)


def _d(value) -> Decimal:
    if value in (None, ""):
        return _ZERO
    try:
        return Decimal(str(value))
    except Exception:
        return _ZERO


def _txt(value) -> str:
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value)


@dataclass
class CostCell:
    """Composants de coût pour un couple (organisme, année)."""
    # Prévisionnel — jours
    j_fonct: Decimal = _ZERO
    j_invest: Decimal = _ZERO
    j_benevole: Decimal = _ZERO
    # Prévisionnel — coûts
    sal_fonct: Decimal = _ZERO
    sal_invest: Decimal = _ZERO
    prest_fonct: Decimal = _ZERO
    prest_invest: Decimal = _ZERO
    autre_fonct: Decimal = _ZERO      # autre_cout + cout_stage + budget_fonctionnement
    autre_invest: Decimal = _ZERO     # autre_cout_invest + budget_investissement
    # Réalisé — jours
    rj_fonct: Decimal = _ZERO
    rj_invest: Decimal = _ZERO
    rj_benevole: Decimal = _ZERO
    # Réalisé — coûts
    rsal_fonct: Decimal = _ZERO
    rsal_invest: Decimal = _ZERO
    rprest_fonct: Decimal = _ZERO
    rprest_invest: Decimal = _ZERO
    rautre_fonct: Decimal = _ZERO
    rautre_invest: Decimal = _ZERO

    # --- Totaux prévisionnels ---
    @property
    def tot_fonct(self) -> Decimal:
        return self.sal_fonct + self.prest_fonct + self.autre_fonct

    @property
    def tot_invest(self) -> Decimal:
        return self.sal_invest + self.prest_invest + self.autre_invest

    @property
    def tot(self) -> Decimal:
        return self.tot_fonct + self.tot_invest

    @property
    def jours(self) -> Decimal:
        return self.j_fonct + self.j_invest

    # --- Totaux réalisés ---
    @property
    def rtot_fonct(self) -> Decimal:
        return self.rsal_fonct + self.rprest_fonct + self.rautre_fonct

    @property
    def rtot_invest(self) -> Decimal:
        return self.rsal_invest + self.rprest_invest + self.rautre_invest

    @property
    def rtot(self) -> Decimal:
        return self.rtot_fonct + self.rtot_invest

    @property
    def rjours(self) -> Decimal:
        return self.rj_fonct + self.rj_invest

    def add(self, other: "CostCell") -> None:
        for f in (
            "j_fonct", "j_invest", "j_benevole",
            "sal_fonct", "sal_invest", "prest_fonct", "prest_invest",
            "autre_fonct", "autre_invest",
            "rj_fonct", "rj_invest", "rj_benevole",
            "rsal_fonct", "rsal_invest", "rprest_fonct", "rprest_invest",
            "rautre_fonct", "rautre_invest",
        ):
            setattr(self, f, getattr(self, f) + getattr(other, f))


@dataclass
class ActionFinance:
    """Coûts d'une action, ventilés par (organisme, année)."""
    op: object
    enjeu_label: str = ""
    categorie: str = ""            # mnémonique CATEGORIE_ACTION_RESERVE (CS, IP…)
    code: str = ""
    libelle: str = ""
    is_cs: bool = False
    is_org_ventilated: bool = False
    cells: dict = field(default_factory=lambda: defaultdict(CostCell))

    def org_ids(self) -> list:
        return sorted({oid for (oid, _y) in self.cells.keys()}, key=lambda i: (i == 0, i))

    def cell(self, org_id, year) -> CostCell:
        return self.cells.get((org_id, year), CostCell())

    def year_total(self, year) -> CostCell:
        """Somme sur tous les organismes pour une année."""
        acc = CostCell()
        for (oid, y), c in self.cells.items():
            if y == year:
                acc.add(c)
        return acc

    def org_total(self, org_id) -> CostCell:
        acc = CostCell()
        for (oid, y), c in self.cells.items():
            if oid == org_id:
                acc.add(c)
        return acc


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def poste_entry_factory():
    """Entrée d'agrégation par (organisme, type de poste, année)."""
    return {
        "prev": _ZERO, "real": _ZERO,
        "salf_prev": _ZERO, "sali_prev": _ZERO,
        "salf_real": _ZERO, "sali_real": _ZERO,
    }


def _org_of_rh_line(op, line):
    poste = line.id_poste
    if op.declinaison_par_poste and poste and poste.id_organisme_id:
        return poste.id_organisme
    return line.id_organisme


def _org_key(org, org_names):
    if org is None:
        org_names.setdefault(0, "Non ventilé")
        return 0
    org_names[org.id_organisme] = _txt(org.nom_organisme) or f"Organisme {org.id_organisme}"
    return org.id_organisme


def _primary_fonction(poste):
    if not poste:
        return None
    pfs = list(poste.fonctions.all())
    if not pfs:
        return None
    pf = max(pfs, key=lambda x: (x.pourcentage or 0))
    return pf.id_fonction


def _poste_fonctions_prefetch():
    """
    Fonctions d'un poste, avec leur type (#633).

    Le type de poste étant une nomenclature, on la charge avec la fonction :
    sans cela chaque ligne RH de l'export la relirait une par une.
    """
    from django.db.models import Prefetch

    from .models_operations import Fonction

    return Prefetch(
        "id_poste__fonctions__id_fonction",
        queryset=Fonction.objects.select_related("id_type_poste"),
    )


def _poste_type_label(poste):
    f = _primary_fonction(poste)
    if f is None:
        return "Sans poste"
    tp = getattr(f, "type_poste", "")
    if tp == "benevole":
        return "Bénévoles"
    if tp == "partenaire":
        return "Partenaires"
    return _txt(f.libelle) or "Sans poste"


def build_action_finance(op, org_names, poste_jours) -> ActionFinance:
    """Construit l'``ActionFinance`` d'une opération et alimente les synthèses.

    ``org_names`` (dict) et ``poste_jours`` (dict) sont mutés en place pour
    agréger au niveau du plan.
    """
    from .models_operations import (
        OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
        RealisationOperationAnneeRH,
    )

    af = ActionFinance(op=op)
    af.is_org_ventilated = op.ventilation_mode in ORG_VENTILATION_MODES

    def cell(oid, year):
        return af.cells[(oid, year)]

    # --- RH prévisionnel : jours + salarial ---
    rh = (
        OperationAnneeRH.objects
        .filter(id_operation_annee__id_operation=op)
        .select_related("id_operation_annee", "id_poste", "id_poste__id_organisme",
                        "id_organisme")
        .prefetch_related(_poste_fonctions_prefetch())
    )
    for line in rh:
        year = line.id_operation_annee.annee
        org = _org_of_rh_line(op, line)
        oid = _org_key(org, org_names)
        jours = _d(line.jours)
        poste = line.id_poste
        cout_jour = _d(getattr(poste, "cout_jour", None)) if poste else _ZERO
        cat = line.categorie_depense or "fonctionnement"
        label = _poste_type_label(poste)
        pj = poste_jours[(oid, label, year)]
        if cout_jour and "cout_jour" not in pj:
            pj["cout_jour"] = cout_jour
        c = cell(oid, year)
        if cat == "benevolat_partenariat":
            c.j_benevole += jours
            pj["prev"] += jours
            continue
        if cat == "investissement":
            c.j_invest += jours
            c.sal_invest += jours * cout_jour
            pj["sali_prev"] += jours * cout_jour
        else:
            c.j_fonct += jours
            c.sal_fonct += jours * cout_jour
            pj["salf_prev"] += jours * cout_jour
        pj["prev"] += jours

    # --- RH réalisé : jours + salarial ---
    rrh = (
        RealisationOperationAnneeRH.objects
        .filter(id_realisation_operation_annee__id_operation_annee__id_operation=op)
        .select_related(
            "id_realisation_operation_annee__id_operation_annee",
            "id_poste", "id_poste__id_organisme", "id_organisme")
        .prefetch_related(_poste_fonctions_prefetch())
    )
    for line in rrh:
        year = line.id_realisation_operation_annee.id_operation_annee.annee
        org = _org_of_rh_line(op, line)
        oid = _org_key(org, org_names)
        jours = _d(line.jours)
        poste = line.id_poste
        cout_jour = _d(getattr(poste, "cout_jour", None)) if poste else _ZERO
        cat = getattr(line, "categorie_depense", None) or "fonctionnement"
        label = _poste_type_label(poste)
        pj = poste_jours[(oid, label, year)]
        if cout_jour and "cout_jour" not in pj:
            pj["cout_jour"] = cout_jour
        c = cell(oid, year)
        if cat == "benevolat_partenariat":
            c.rj_benevole += jours
            pj["real"] += jours
            continue
        if cat == "investissement":
            c.rj_invest += jours
            c.rsal_invest += jours * cout_jour
            pj["sali_real"] += jours * cout_jour
        else:
            c.rj_fonct += jours
            c.rsal_fonct += jours * cout_jour
            pj["salf_real"] += jours * cout_jour
        pj["real"] += jours

    # --- Coûts organisme (prestataire / autres / budgets) prév + réalisé ---
    org_lines = (
        OperationAnneeOrganisme.objects
        .filter(id_operation_annee__id_operation=op)
        .select_related("id_operation_annee", "id_organisme", "realisation")
    )
    has_org_lines = False
    for line in org_lines:
        has_org_lines = True
        year = line.id_operation_annee.annee
        oid = _org_key(line.id_organisme, org_names)
        c = cell(oid, year)
        c.prest_fonct += _d(line.cout_prestataire)
        c.prest_invest += _d(line.cout_prestataire_invest)
        c.autre_fonct += _d(line.autre_cout) + _d(line.cout_stage) + _d(line.budget_fonctionnement)
        c.autre_invest += _d(line.autre_cout_invest) + _d(line.budget_investissement)
        real = getattr(line, "realisation", None)
        if real:
            c.rprest_fonct += _d(real.cout_prestataire_realise)
            c.rprest_invest += _d(real.cout_prestataire_invest_realise)
            c.rautre_fonct += _d(real.autre_cout_realise) + _d(real.cout_stage_realise) + _d(real.budget_fonctionnement_realise)
            c.rautre_invest += _d(real.autre_cout_invest_realise) + _d(real.budget_investissement_realise)

    # --- Modes sans ventilation par organisme : budgets portés par l'année ---
    if not has_org_lines:
        annees = OperationAnnee.objects.filter(id_operation=op).select_related("realisation")
        for oa in annees:
            fonct = _d(oa.budget_fonctionnement) or (_d(oa.budget) if op.ventilation_mode == "none" else _ZERO)
            invest = _d(oa.budget_investissement)
            c = cell(0, oa.annee)
            # #624 — le mode « by_type_poste » détaille les coûts au niveau de
            # l'année (mêmes composants que par organisme, sans organisme) :
            # on les agrège comme le fait la branche par organisme ci-dessus.
            c.prest_fonct += _d(oa.cout_prestataire)
            c.prest_invest += _d(oa.cout_prestataire_invest)
            c.autre_fonct += fonct + _d(oa.autre_cout) + _d(oa.cout_stage)
            c.autre_invest += invest + _d(oa.autre_cout_invest)
            if c.prest_fonct or c.prest_invest or c.autre_fonct or c.autre_invest:
                org_names.setdefault(0, "Non ventilé")
            real = getattr(oa, "realisation", None)
            if real:
                rf = _d(real.budget_fonctionnement_realise) or (_d(real.budget_realise) if op.ventilation_mode == "none" else _ZERO)
                c.rprest_fonct += _d(real.cout_prestataire_realise)
                c.rprest_invest += _d(real.cout_prestataire_invest_realise)
                c.rautre_fonct += rf + _d(real.autre_cout_realise) + _d(real.cout_stage_realise)
                c.rautre_invest += _d(real.budget_investissement_realise) + _d(real.autre_cout_invest_realise)

    return af


# ---------------------------------------------------------------------------
# Niveau plan
# ---------------------------------------------------------------------------

def _enjeu_label(op):
    """Libellé de l'enjeu / FCR rattaché à l'action (via indicateur → NE/RA)."""
    from .services_export_fiche_action import _linked_indicateurs
    for ind in _linked_indicateurs(op):
        ne = getattr(ind, "id_ne", None)
        ra = getattr(ind, "id_resultat_attendu", None)
        enj = None
        if ne and getattr(ne, "id_olt", None):
            enj = getattr(ne.id_olt, "id_enjeu", None)
        elif ra and getattr(ra, "id_oo", None):
            enj = getattr(ra.id_oo, "id_enjeu", None)
        if enj:
            return _txt(enj.intitule_court) or _txt(enj.libelle)
    return ""


def plan_operations(plan):
    """Opérations de l'arborescence du plan (via métriques ou indicateur direct)."""
    from .models_operations import Operation
    qs = (
        Operation.objects
        .filter(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
        .select_related("id_priorite", "id_categorie_action_reserve", "id_indicateur",
                        "id_suivi")
        .prefetch_related(
            "metriques__id_indicateur__id_ne__id_olt__id_enjeu",
            "metriques__id_indicateur__id_resultat_attendu__id_oo",
        )
        .distinct()
    )
    seen = {o.id_operation for o in qs}
    direct = (
        Operation.objects
        .filter(id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
        .select_related("id_priorite", "id_categorie_action_reserve", "id_indicateur",
                        "id_suivi")
        .exclude(id_operation__in=seen)
        .distinct()
    )
    ops = list(qs) + list(direct)
    # tri par catégorie (code simplifié) puis code action
    ops.sort(key=lambda o: (
        _txt(getattr(o.id_categorie_action_reserve, "mnemonique", "")) or "zzz",
        _txt(o.code_operation),
        o.id_operation,
    ))
    return ops


@dataclass
class PlanFinance:
    plan: object
    years: list
    actions: list
    org_names: dict
    poste_jours: dict         # (org_id, label, year) -> {'prev','real'}

    def org_ids(self) -> list:
        ids = set()
        for af in self.actions:
            ids |= {oid for (oid, _y) in af.cells.keys()}
        return sorted(ids, key=lambda i: (i == 0, self.org_names.get(i, "")))


def build_plan_finance(plan) -> PlanFinance:
    # #618 — Le « code action PG » affiché partout dans l'application est le code
    # calculé (CS1, IP2…), pas le champ libre `code_operation` (quasi toujours
    # vide). On le calcule une fois pour tout le plan.
    from .serializers_operations import compute_operation_codes_for_plan

    y0 = plan.annee_debut or 0
    y1 = plan.annee_fin or y0
    years = list(range(y0, y1 + 1)) if y0 else []

    codes = compute_operation_codes_for_plan(plan.pk)

    org_names: dict = {}
    poste_jours: dict = defaultdict(poste_entry_factory)
    actions = []
    for op in plan_operations(plan):
        af = build_action_finance(op, org_names, poste_jours)
        cat = getattr(op, "id_categorie_action_reserve", None)
        af.categorie = _txt(getattr(cat, "mnemonique", "")) if cat else ""
        af.is_cs = af.categorie.upper() == "CS"
        af.code = (
            _txt(codes.get(op.id_operation))
            or _txt(op.code_operation)
            or (f"n°{op.numero_manuel}" if op.numero_manuel else "")
        )
        af.libelle = _txt(op.libelle)
        af.enjeu_label = _enjeu_label(op)
        actions.append(af)

    return PlanFinance(
        plan=plan, years=years, actions=actions,
        org_names=org_names, poste_jours=dict(poste_jours),
    )
