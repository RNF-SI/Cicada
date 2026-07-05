/**
 * #379 — Statut de réalisation annuel d'une action (icône prévu × réalisé),
 * partagé entre le tableau de suivi des actions et la page globale d'une action.
 */
import { Operation } from '../../../core/models/enjeu.model';

export type ActionStatus =
  | 'planned'
  | 'planned-realized'
  | 'planned-partial'
  | 'planned-not-realized'
  | 'realized-unplanned'
  | 'partial-unplanned';

/** Icône (asset) par statut. */
export const ACTION_ICON_MAP: Record<ActionStatus, string> = {
  'planned': 'assets/images/icons/prevu.png',
  'planned-realized': 'assets/images/icons/prevu-realise.png',
  'planned-partial': 'assets/images/icons/prevu-partiellement-realise.png',
  'planned-not-realized': 'assets/images/icons/non-realise.svg',
  'realized-unplanned': 'assets/images/icons/realise.png',
  'partial-unplanned': 'assets/images/icons/partiellement-realise.png',
};

/** Légende complète (clés i18n) des statuts annuels. */
export const ACTION_LEGEND_ITEMS: { status: ActionStatus; labelKey: string }[] = [
  { status: 'planned', labelKey: 'plans.suivis.actions.actionPrevue' },
  { status: 'planned-realized', labelKey: 'plans.suivis.actions.actionPrevueRealisee' },
  { status: 'planned-partial', labelKey: 'plans.suivis.actions.actionPrevuePartielle' },
  { status: 'planned-not-realized', labelKey: 'plans.suivis.actions.actionNonRealisee' },
  { status: 'realized-unplanned', labelKey: 'plans.suivis.actions.actionRealiseeNonPrevue' },
  { status: 'partial-unplanned', labelKey: 'plans.suivis.actions.actionPartielleNonPrevue' },
];

/** Chemin de l'icône pour un statut. */
export function getActionIcon(status: ActionStatus | null): string {
  return status ? (ACTION_ICON_MAP[status] || '') : '';
}

/**
 * #460 — Rendu du statut de réalisation GLOBAL d'une action dans le tableau
 * de suivi. Contrairement aux 3 icônes historiques (réalisé / partiel / non
 * réalisé), on distingue explicitement « en cours » (sablier, tant que la
 * dernière année n'est pas renseignée) et « non commencée » (aucune réponse
 * saisie). ABANDONNE / REPORTE / NON_REALISE restent « non réalisé ».
 */
export type GlobalRealisationKind =
  | 'realise'
  | 'partiel'
  | 'en-cours'
  | 'non-commencee'
  | 'non-realise';

/** Regroupe le mnémonique NIVEAU_REALISATION global en un « kind » d'affichage. */
export function getGlobalRealisationKind(
  mnemonique: string | null | undefined,
): GlobalRealisationKind {
  switch (mnemonique) {
    case 'TERMINE': return 'realise';
    case 'PARTIEL': return 'partiel';
    case 'EN_COURS': return 'en-cours';
    case 'NON_REALISE':
    case 'ABANDONNE':
    case 'REPORTE': return 'non-realise';
    // NON_DEMARRE, null, undefined, aucune année programmée → non commencée
    default: return 'non-commencee';
  }
}

/** Clé i18n du libellé pour chaque « kind » de statut global. */
export const GLOBAL_REALISATION_LABEL_KEYS: Record<GlobalRealisationKind, string> = {
  'realise': 'plans.suivis.actionGlobal.statut.realise',
  'partiel': 'plans.suivis.actionGlobal.statut.partiel',
  'en-cours': 'plans.suivis.actionGlobal.statut.enCours',
  'non-commencee': 'plans.suivis.actionGlobal.statut.nonCommencee',
  'non-realise': 'plans.suivis.actionGlobal.statut.nonRealise',
};

/** Clé i18n du libellé du statut global à partir du mnémonique. */
export function getGlobalRealisationLabelKey(mnemonique: string | null | undefined): string {
  return GLOBAL_REALISATION_LABEL_KEYS[getGlobalRealisationKind(mnemonique)];
}

/**
 * Statut d'une (opération, année) en combinant la périodicité prévue (planifié)
 * et le niveau de réalisation observé (TERMINE / PARTIEL / NON_REALISE).
 */
export function getActionStatusForYear(op: Operation, year: number): ActionStatus | null {
  if (!op.operation_annees) return null;
  const annee = op.operation_annees.find(a => a.annee === year);
  if (!annee) return null;

  const prevu = !!annee.periodicite;
  const niveau = annee.realisation?.niveau_realisation_mnemonique ?? null;
  const realiseTotal = niveau === 'TERMINE';
  const realisePartiel = niveau === 'PARTIEL';
  const nonRealise = niveau === 'NON_REALISE';

  if (prevu) {
    if (realiseTotal) return 'planned-realized';
    if (realisePartiel) return 'planned-partial';
    if (nonRealise) return 'planned-not-realized';
    return 'planned';
  }
  if (realiseTotal) return 'realized-unplanned';
  if (realisePartiel) return 'partial-unplanned';
  return null;
}
