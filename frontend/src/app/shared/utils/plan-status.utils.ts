import { PlanStatut } from '../../core/models/admin.model';

/**
 * Mnémonique des types de sites (nomenclature `TYPE_SITE`) qui pilote le
 * libellé contextuel du badge d'extension d'un plan (#281).
 */
export type SiteTypeMnemonique = 'RNN' | 'RNR' | 'PNR' | 'ENS' | 'ENSD' | string;

/**
 * Clé i18n du statut d'un plan.
 *
 * Depuis le retour de test #250, l'extension n'est plus un statut mais un
 * attribut indépendant (annees_extension). On retourne donc systématiquement
 * la clé brute `plans.status.<statut>`. Le badge "Étendu" éventuel est géré
 * séparément via {@link getExtensionBadgeKey}.
 */
export function getPlanStatusKey(statut: PlanStatut | string): string {
  return `plans.status.${statut}`;
}

/**
 * Clé i18n du tooltip pédagogique du chip statut. Explique à l'utilisateur
 * la signification de chaque statut. Disponible pour les 4 statuts :
 * draft / valide / modifie / archive.
 */
export function getPlanStatusTooltipKey(statut: PlanStatut | string): string {
  return `plans.status.${statut}Tooltip`;
}

/**
 * Classe CSS du chip statut. Aligné sur les chips globaux Material
 * (`_material-overrides.scss`). Source de vérité unique pour l'affichage
 * du statut d'un plan partout dans l'application.
 *
 * - draft   → status-warning (orange)
 * - valide  → status-success (vert)
 * - modifie → status-info (bleu ciel)
 * - archive → status-neutre (terra-cotta)
 */
export function getPlanStatusClass(statut: PlanStatut | string): string {
  const map: Record<string, string> = {
    draft: 'status-warning',
    valide: 'status-success',
    modifie: 'status-info',
    archive: 'status-neutre',
  };
  return map[statut] || '';
}

/**
 * Clé i18n du badge "Étendu" affiché en complément du statut, lorsque
 * `annees_extension > 0`. Le libellé est contextualisé selon le type de site
 * principal du plan (#281) :
 * - RNN / RNR  → `plans.extension.badge_rnn`  ("Plan prolongé")
 * - PNR        → `plans.extension.badge_pnr`  ("Plan en renouvellement")
 * - ENS / ENSD → `plans.extension.badge_ens`  ("Plan étendu")
 * - défaut     → `plans.extension.badge`       ("Étendu")
 */
export function getExtensionBadgeKey(siteTypeMnemonique?: string | null): string {
  switch ((siteTypeMnemonique || '').toUpperCase()) {
    case 'RNN':
    case 'RNR':
      return 'plans.extension.badge_rnn';
    case 'PNR':
      return 'plans.extension.badge_pnr';
    case 'ENS':
    case 'ENSD':
      return 'plans.extension.badge_ens';
    default:
      return 'plans.extension.badge';
  }
}
