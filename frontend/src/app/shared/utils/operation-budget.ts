/**
 * Dérivation du budget et du temps de travail d'une année d'action (#613/#616).
 *
 * Selon le mode de ventilation, le budget d'une année n'est PAS stocké au même
 * endroit :
 *
 * | Mode                  | Porteur du budget                                   |
 * |-----------------------|-----------------------------------------------------|
 * | `none`                | `OperationAnnee.budget`                             |
 * | `by_type`             | `budget_fonctionnement` / `budget_investissement`   |
 * | `by_org` / `by_org_type` | idem, sur chaque `organismes[]`                  |
 * | `by_type_poste` (#624)| détail des coûts de l'année + coût salarial calculé |
 * | `by_org_type_poste`   | détail des coûts de chaque organisme + salarial     |
 *
 * Dans les deux derniers modes, les enveloppes fonctionnement / investissement
 * ne sont volontairement pas enregistrées : elles se recalculent depuis leurs
 * composants (sinon les exports les compteraient deux fois). Les vues de
 * synthèse qui lisaient seulement `budget_fonctionnement` affichaient donc
 * 0 € (#613 fiche action, #616 vue globale du budget et fiche globale).
 *
 * Ce module est la source de vérité côté front, pendant de
 * `services_export_finance` côté back : on additionne TOUS les porteurs de
 * coût (année + organismes + salarial calculé). Un mode donné n'en alimente
 * qu'une famille, la somme est donc exacte quel que soit le mode — et reste
 * juste pour les données saisies avant un changement de mode.
 *
 * Le **coût salarial** n'est pas stocké tant qu'il est calculé : il vaut alors
 * Σ jours × coût jour du poste, ventilé par catégorie de dépense de la ligne
 * RH. Le temps « bénévolat partenariat » est valorisé en jours mais ne pèse
 * aucun euro.
 *
 * #600 (retour 08/2026) — deux réglages de l'action modulent tout ceci dès que
 * le mode ventile par type de budget :
 * - `declinaison_par_type_cout` : décochée, le budget se réduit aux enveloppes
 *   fonctionnement / investissement saisies (aucun coût salarial ajouté) ;
 * - `cout_salarial_auto` : décochée, le coût salarial est SAISI (et stocké
 *   dans `cout_salarial` / `cout_salarial_invest`) au lieu d'être calculé.
 */

import { Operation, OperationAnnee, OperationAnneeOrganisme } from '../../core/models/enjeu.model';
import { CategorieDepense, OperationRHLigne } from '../../core/models/rh.model';

/** Catégories qui pèsent en euros (le bénévolat est valorisé en jours seuls). */
type CategorieCout = 'fonctionnement' | 'investissement';

/** Budget d'une année, ventilé quand le mode le permet. */
export interface BudgetSplit {
  /** `null` = le mode ne ventile pas (ou aucune donnée saisie). */
  fonctionnement: number | null;
  investissement: number | null;
  /** `null` = aucune donnée saisie pour l'année. */
  total: number | null;
}

/** Détail des composants de coût d'une année (fiche action, #613). */
export interface CostDetail {
  salarial: number;
  stage: number;
  prestataire: number;
  autres: number;
  total: number;
}

/** Décimal DRF (souvent une chaîne « 500.00 ») → nombre, `null` si absent. */
function num(v: number | string | null | undefined): number | null {
  if (v == null || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function add(...values: (number | string | null | undefined)[]): number {
  return values.reduce<number>((sum, v) => sum + (num(v) ?? 0), 0);
}

/** Vrai si au moins une des valeurs est renseignée (0 compte comme une saisie). */
function anySet(...values: (number | string | null | undefined)[]): boolean {
  return values.some(v => num(v) != null);
}

/** Catégorie d'une ligne RH, avec le repli historique sur `finance` (#597). */
function categorieOf(ligne: OperationRHLigne): CategorieDepense {
  return ligne.categorie_depense ?? (ligne.finance ? 'fonctionnement' : 'benevolat_partenariat');
}

/** Coût salarial d'un jeu de lignes RH pour une catégorie : Σ jours × coût jour. */
export function salarialCost(
  lignes: readonly OperationRHLigne[] | null | undefined,
  categorie: CategorieCout,
): number {
  return (lignes ?? []).reduce((sum, l) => {
    if (categorieOf(l) !== categorie) return sum;
    return sum + (num(l.jours) ?? 0) * (num(l.poste_cout_jour) ?? 0);
  }, 0);
}

/** Somme des jours d'un jeu de lignes RH (financées ou non). */
export function sumJours(lignes: readonly OperationRHLigne[] | null | undefined): number {
  return (lignes ?? []).reduce((sum, l) => sum + (num(l.jours) ?? 0), 0);
}

const orgs = (oa: OperationAnnee): OperationAnneeOrganisme[] => oa.organismes ?? [];

/**
 * Modes ventilant par type de budget : eux seuls portent le détail des coûts
 * (#600 — case « déclinaison par type de coût », cochée par défaut).
 */
const TYPE_VENTILATION_MODES = [
  'by_type', 'by_org_type', 'by_type_poste', 'by_org_type_poste',
];

type OpMode = Pick<Operation, 'ventilation_mode' | 'declinaison_par_type_cout' | 'cout_salarial_auto'>;

/**
 * Vrai si le budget de l'action est décomposé en types de coût (salarial,
 * stage, prestataire, autres). Sinon le gestionnaire saisit lui-même les
 * enveloppes fonctionnement / investissement, qui incluent déjà tout : y
 * ajouter un coût salarial le doublerait.
 */
function hasCostDetail(op: OpMode): boolean {
  return TYPE_VENTILATION_MODES.includes(op.ventilation_mode ?? 'none')
    && op.declinaison_par_type_cout !== false;
}

/** Coût salarial CALCULÉ (jours × coût jour) plutôt que saisi (#600). */
function derivesSalary(op: OpMode): boolean {
  return hasCostDetail(op) && op.cout_salarial_auto !== false;
}

/** Coût salarial SAISI à la main sur l'année / les organismes (#600). */
function manualSalary(op: OpMode, oa: OperationAnnee, invest: boolean): number {
  if (!hasCostDetail(op) || op.cout_salarial_auto !== false) return 0;
  return invest
    ? add(oa.cout_salarial_invest, ...orgs(oa).map(o => o.cout_salarial_invest))
    : add(oa.cout_salarial, ...orgs(oa).map(o => o.cout_salarial));
}

/**
 * Vrai si l'année porte un montant saisi quelque part (année ou organisme).
 * Sert à distinguer le mode « totaux directs » (seul `budget` est rempli) des
 * modes ventilés, sans se fier uniquement au mode déclaré — celui-ci peut
 * avoir changé après la saisie.
 */
function hasMonetaryDetail(oa: OperationAnnee): boolean {
  return anySet(
    oa.budget_fonctionnement, oa.budget_investissement,
    oa.cout_salarial, oa.cout_salarial_invest,
    oa.cout_stage, oa.cout_prestataire, oa.autre_cout,
    oa.cout_prestataire_invest, oa.autre_cout_invest,
    ...orgs(oa).flatMap(o => [
      o.budget_fonctionnement, o.budget_investissement,
      o.cout_salarial, o.cout_salarial_invest, o.cout_stage,
      o.cout_prestataire, o.autre_cout, o.cout_prestataire_invest, o.autre_cout_invest,
    ]),
  );
}

// ---------------------------------------------------------------------------
// Prévisionnel
// ---------------------------------------------------------------------------

/** Composants du budget de fonctionnement PRÉVU d'une année (#613). */
export function fonctDetailPrev(op: OpMode, oa: OperationAnnee): CostDetail {
  const detail = {
    salarial: derivesSalary(op)
      ? salarialCost(oa.rh_lignes, 'fonctionnement')
      : manualSalary(op, oa, false),
    stage: add(oa.cout_stage, ...orgs(oa).map(o => o.cout_stage)),
    prestataire: add(oa.cout_prestataire, ...orgs(oa).map(o => o.cout_prestataire)),
    // Les enveloppes saisies (modes sans détail) sont des « autres coûts » du
    // point de vue de la décomposition — même convention qu'à l'export.
    autres: add(
      oa.autre_cout, oa.budget_fonctionnement,
      ...orgs(oa).map(o => o.autre_cout), ...orgs(oa).map(o => o.budget_fonctionnement),
    ),
    total: 0,
  };
  detail.total = detail.salarial + detail.stage + detail.prestataire + detail.autres;
  return detail;
}

/** Composants du budget d'investissement PRÉVU d'une année (#613). */
export function investDetailPrev(op: OpMode, oa: OperationAnnee): CostDetail {
  const detail = {
    salarial: derivesSalary(op)
      ? salarialCost(oa.rh_lignes, 'investissement')
      : manualSalary(op, oa, true),
    stage: 0,
    prestataire: add(oa.cout_prestataire_invest, ...orgs(oa).map(o => o.cout_prestataire_invest)),
    autres: add(
      oa.autre_cout_invest, oa.budget_investissement,
      ...orgs(oa).map(o => o.autre_cout_invest), ...orgs(oa).map(o => o.budget_investissement),
    ),
    total: 0,
  };
  detail.total = detail.salarial + detail.prestataire + detail.autres;
  return detail;
}

/**
 * Budget PRÉVU d'une année, quel que soit le mode de ventilation.
 * `null` partout quand rien n'est saisi (l'appelant affiche « — »).
 */
export function yearBudgetPrev(op: OpMode, oa: OperationAnnee): BudgetSplit {
  // Ni montant ventilé ni coût salarial dérivé : c'est une saisie en total
  // direct (ou une année non programmée).
  if (!hasMonetaryDetail(oa) && !derivesSalary(op)) {
    return { fonctionnement: null, investissement: null, total: num(oa.budget) };
  }
  const fonctionnement = fonctDetailPrev(op, oa).total;
  const investissement = investDetailPrev(op, oa).total;
  if (!hasMonetaryDetail(oa) && fonctionnement === 0 && investissement === 0) {
    // Mode « + type de poste » sans aucune saisie sur l'année.
    return { fonctionnement: null, investissement: null, total: num(oa.budget) };
  }
  return { fonctionnement, investissement, total: fonctionnement + investissement };
}

/**
 * Jours PRÉVUS d'une année, depuis les lignes RH (#560).
 * `legacyEtp` autorise le repli sur l'ancien champ scalaire `etp` : les vues
 * de suivi le veulent (données antérieures à #560), la fiche action non
 * (le champ y est explicitement ignoré).
 */
export function yearJoursPrev(oa: OperationAnnee, legacyEtp = false): number | null {
  const lignes = oa.rh_lignes ?? [];
  if (lignes.length) return sumJours(lignes);
  return legacyEtp ? num(oa.etp) : null;
}

// ---------------------------------------------------------------------------
// Réalisé
// ---------------------------------------------------------------------------

/** Composants du budget de fonctionnement RÉALISÉ d'une année. */
export function fonctDetailReal(op: OpMode, oa: OperationAnnee): CostDetail {
  const r = oa.realisation;
  const ro = orgs(oa).map(o => o.realisation);
  const detail = {
    salarial: derivesSalary(op) ? salarialCost(r?.rh_lignes, 'fonctionnement') : 0,
    stage: add(r?.cout_stage_realise, ...ro.map(x => x?.cout_stage_realise)),
    prestataire: add(r?.cout_prestataire_realise, ...ro.map(x => x?.cout_prestataire_realise)),
    autres: add(
      r?.autre_cout_realise, r?.budget_fonctionnement_realise,
      ...ro.map(x => x?.autre_cout_realise), ...ro.map(x => x?.budget_fonctionnement_realise),
    ),
    total: 0,
  };
  detail.total = detail.salarial + detail.stage + detail.prestataire + detail.autres;
  return detail;
}

/** Composants du budget d'investissement RÉALISÉ d'une année. */
export function investDetailReal(op: OpMode, oa: OperationAnnee): CostDetail {
  const r = oa.realisation;
  const ro = orgs(oa).map(o => o.realisation);
  const detail = {
    salarial: derivesSalary(op) ? salarialCost(r?.rh_lignes, 'investissement') : 0,
    stage: 0,
    prestataire: add(
      r?.cout_prestataire_invest_realise, ...ro.map(x => x?.cout_prestataire_invest_realise),
    ),
    autres: add(
      r?.autre_cout_invest_realise, r?.budget_investissement_realise,
      ...ro.map(x => x?.autre_cout_invest_realise), ...ro.map(x => x?.budget_investissement_realise),
    ),
    total: 0,
  };
  detail.total = detail.salarial + detail.prestataire + detail.autres;
  return detail;
}

/** Vrai si un montant réalisé a été saisi pour l'année (année ou organismes). */
function hasRealMonetaryDetail(oa: OperationAnnee): boolean {
  const r = oa.realisation;
  const ro = orgs(oa).map(o => o.realisation);
  return anySet(
    r?.budget_fonctionnement_realise, r?.budget_investissement_realise,
    r?.cout_stage_realise, r?.cout_prestataire_realise, r?.autre_cout_realise,
    r?.cout_prestataire_invest_realise, r?.autre_cout_invest_realise,
    ...ro.flatMap(x => [
      x?.budget_fonctionnement_realise, x?.budget_investissement_realise,
      x?.cout_stage_realise, x?.cout_prestataire_realise, x?.autre_cout_realise,
      x?.cout_prestataire_invest_realise, x?.autre_cout_invest_realise,
    ]),
  );
}

/**
 * Budget RÉALISÉ d'une année. `hasValue` distingue « aucun suivi saisi »
 * (afficher « — ») de « suivi saisi à 0 € ».
 */
export function yearBudgetReal(
  op: OpMode, oa: OperationAnnee,
): BudgetSplit & { hasValue: boolean } {
  const r = oa.realisation;
  const salarial = derivesSalary(op) && (r?.rh_lignes ?? []).length > 0;
  if (!hasRealMonetaryDetail(oa) && !salarial) {
    const total = num(r?.budget_realise);
    return { fonctionnement: null, investissement: null, total, hasValue: total != null };
  }
  const fonctionnement = fonctDetailReal(op, oa).total;
  const investissement = investDetailReal(op, oa).total;
  return {
    fonctionnement, investissement,
    total: fonctionnement + investissement,
    hasValue: true,
  };
}

/**
 * Jours RÉALISÉS d'une année : lignes RH réalisées, avec repli sur les anciens
 * champs scalaires (`etp_realise`, global ou par organisme). `null` = aucun
 * suivi du temps de travail saisi.
 */
export function yearJoursReal(oa: OperationAnnee): number | null {
  const lignes = oa.realisation?.rh_lignes ?? [];
  if (lignes.length) return sumJours(lignes);
  const parOrg = orgs(oa)
    .map(o => num(o.realisation?.etp_realise))
    .filter((v): v is number => v != null);
  if (parOrg.length) return parOrg.reduce((a, b) => a + b, 0);
  return num(oa.realisation?.etp_realise);
}
