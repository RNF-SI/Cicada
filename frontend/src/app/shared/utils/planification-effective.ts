/**
 * #794 — Programmation EFFECTIVE d'une action : l'ajustement annuel s'il en
 * existe un pour l'année, sinon la programmation du plan de gestion.
 *
 * Le suivi (icônes prévu / réalisé, onglets Budget et RH, planification
 * mensuelle, page globale d'une action) lit ses années dans
 * `operation.operation_annees` : `operationAjustee()` rend une copie de
 * l'action dont les années portent le prévu ajusté, sans toucher au réalisé.
 * Le réalisé reste rattaché aux années du plan (`realisation`, et celle de
 * chaque organisme) : un organisme retiré pour l'année mais dont du réalisé
 * est saisi garde sa ligne, sans prévu.
 *
 * Pendant de `Planification.effectif()` côté serveur
 * (`apps/plans/planification_annuelle.py`).
 */
import {
  Operation, OperationAnnee, OperationAnneeOrganisme,
} from '../../core/models/enjeu.model';
import { OperationRHLigne } from '../../core/models/rh.model';
import { AjustementDuPlan } from '../../core/models/planification-annuelle.model';

/** Champs de prévu d'une année et d'un organisme (mêmes noms des deux côtés). */
const CHAMPS_ORGANISME = [
  'budget_fonctionnement', 'budget_investissement', 'cout_salarial', 'cout_salarial_invest',
  'cout_stage', 'cout_prestataire', 'autre_cout', 'cout_prestataire_invest', 'autre_cout_invest',
  'etp', 'autre_cout_commentaire', 'autre_cout_invest_commentaire',
] as const;
const CHAMPS_ANNEE = ['budget', ...CHAMPS_ORGANISME] as const;

/** Ajustements d'un plan rangés par action puis par année. */
export type AjustementsParAction = Map<number, Map<number, AjustementDuPlan>>;

export function ranger(ajustements: readonly AjustementDuPlan[]): AjustementsParAction {
  const parAction: AjustementsParAction = new Map();
  for (const aj of ajustements) {
    if (!parAction.has(aj.id_operation)) parAction.set(aj.id_operation, new Map());
    parAction.get(aj.id_operation)!.set(aj.annee, aj);
  }
  return parAction;
}

function sansPrevu<T extends object>(ligne: T): T {
  const vide = { ...ligne } as Record<string, unknown>;
  for (const champ of CHAMPS_ORGANISME) {
    vide[champ] = champ.endsWith('commentaire') ? '' : null;
  }
  return vide as T;
}

/** L'année ajustée, avec le réalisé de l'année du plan. */
export function anneeAjustee(pg: OperationAnnee | undefined, aj: AjustementDuPlan): OperationAnnee {
  const planifiee = aj.statut === 'planifiee';
  const annee: Record<string, unknown> = {
    ...(pg ?? {}),
    annee: aj.annee,
    periodicite: planifiee,
    periodicite_mensuelle: planifiee ? { ...(aj.periodicite_mensuelle ?? {}) } : {},
    realisation: pg?.realisation ?? null,
    // Repère des vues de suivi : l'année porte un ajustement.
    ajustee: true,
  };
  for (const champ of CHAMPS_ANNEE) {
    annee[champ] = planifiee ? (aj as unknown as Record<string, unknown>)[champ] ?? null
      : (champ.endsWith('commentaire') ? '' : null);
  }
  // Organismes : le prévu de l'ajustement, le réalisé de la ligne du plan.
  const pgOrgs = new Map((pg?.organismes ?? []).map(o => [o.id_organisme, o]));
  const organismes: OperationAnneeOrganisme[] = [];
  for (const org of planifiee ? aj.organismes ?? [] : []) {
    const ligne = pgOrgs.get(org.id_organisme);
    organismes.push({
      ...(ligne ? sansPrevu(ligne) : {}), ...org,
      realisation: ligne?.realisation ?? null,
    } as unknown as OperationAnneeOrganisme);
    pgOrgs.delete(org.id_organisme);
  }
  for (const ligne of pgOrgs.values()) {
    if (ligne.realisation) organismes.push(sansPrevu(ligne));
  }
  annee['organismes'] = organismes;
  annee['rh_lignes'] = (planifiee ? aj.rh_lignes ?? [] : []).map(l => ({
    ...l, jours: l.jours == null ? null : Number(l.jours),
    finance: l.finance ?? l.categorie_depense !== 'benevolat_partenariat',
  })) as OperationRHLigne[];
  return annee as unknown as OperationAnnee;
}

/**
 * Copie de l'action dont les années portent la programmation effective. Sans
 * ajustement, l'action elle-même est rendue (aucune copie).
 */
export function operationAjustee(op: Operation, ajustements: AjustementsParAction): Operation {
  const parAnnee = ajustements.get(op.id_operation);
  if (!parAnnee?.size) return op;
  const annees: OperationAnnee[] = [];
  const vues = new Set<number>();
  for (const oa of op.operation_annees ?? []) {
    const aj = parAnnee.get(oa.annee);
    annees.push(aj ? anneeAjustee(oa, aj) : oa);
    vues.add(oa.annee);
  }
  for (const [annee, aj] of parAnnee) {
    if (!vues.has(annee)) annees.push(anneeAjustee(undefined, aj));
  }
  annees.sort((a, b) => a.annee - b.annee);
  return { ...op, operation_annees: annees };
}
