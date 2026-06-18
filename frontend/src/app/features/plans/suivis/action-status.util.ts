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
