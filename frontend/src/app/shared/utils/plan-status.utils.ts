import { PlanStatut } from '../../core/models/admin.model';

/**
 * Mnémonique des types de sites (nomenclature `TYPE_SITE`) qui pilote le
 * libellé contextuel du statut `etendu` côté UI (#281).
 */
export type SiteTypeMnemonique = 'RNN' | 'RNR' | 'PNR' | 'ENS' | 'ENSD' | string;

/**
 * Calcule la clé i18n du statut d'un plan en tenant compte du type d'aire
 * protégée du site principal (#281).
 *
 * - RNN / RNR  → `plans.status.etendu_rnn`  ("Plan prolongé")
 * - PNR        → `plans.status.etendu_pnr`  ("Plan en renouvellement")
 * - ENS / ENSD → `plans.status.etendu_ens`  ("Plan étendu")
 * - défaut     → `plans.status.etendu`       ("Étendu")
 *
 * Pour tous les autres statuts, on retourne la clé `plans.status.<statut>`
 * sans contextualisation.
 */
export function getPlanStatusKey(
  statut: PlanStatut | string,
  siteTypeMnemonique?: string | null,
): string {
  if (statut !== 'etendu') {
    return `plans.status.${statut}`;
  }
  switch ((siteTypeMnemonique || '').toUpperCase()) {
    case 'RNN':
    case 'RNR':
      return 'plans.status.etendu_rnn';
    case 'PNR':
      return 'plans.status.etendu_pnr';
    case 'ENS':
    case 'ENSD':
      return 'plans.status.etendu_ens';
    default:
      return 'plans.status.etendu';
  }
}
