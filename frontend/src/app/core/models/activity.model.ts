/**
 * Modeles pour l'historique d'activite.
 */

// Types d'entites
export type ActivityEntityType = 'site' | 'plan' | 'user' | 'organisme' | 'validation';

// Types d'actions
export type ActivityAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'add_member'
  | 'remove_member'
  | 'add_referent'
  | 'remove_referent'
  | 'status_change'
  | 'activate'
  | 'deactivate'
  | 'rgpd_request'
  | 'rgpd_cancelled'
  | 'rgpd_anonymized'
  | 'access_granted'
  | 'access_revoked'
  | 'validation_approved'
  | 'validation_rejected'
  | 'file_upload'
  | 'file_delete';

// Niveaux de visibilite
export type ActivityVisibility = 'public' | 'admin' | 'system';

/**
 * Interface pour un log d'activite (liste).
 */
export interface ActivityLogListItem {
  id: number;
  entity_type: ActivityEntityType;
  entity_type_display: string;
  entity_id: number;
  entity_name: string;
  actor_name: string;
  action: ActivityAction;
  action_display: string;
  description: string;
  related_site?: number;
  related_site_name?: string;
  related_site_slug?: string;
  related_plan?: number;
  related_plan_name?: string;
  related_organisme?: number;
  related_organisme_name?: string;
  related_user?: number;
  related_user_name?: string;
  visibility: ActivityVisibility;
  created_at: string;
}

/**
 * Interface pour le detail d'un log d'activite.
 */
export interface ActivityLogDetail extends ActivityLogListItem {
  actor?: number;
  actor_email?: string;
  changes: Record<string, { old: string | null; new: string | null }>;
  metadata: Record<string, unknown>;
  visibility_display: string;
}

/**
 * Interface pour les statistiques d'activite.
 */
export interface ActivityStats {
  total: number;
  by_type: Record<ActivityEntityType, number>;
  by_action: Record<ActivityAction, number>;
  by_day: Array<{ date: string; count: number }>;
}

/**
 * Interface pour les compteurs d'onglets.
 */
export interface ActivityTabsCounts {
  all: number;
  my_sites: number;
  my_plans: number;
  my_rights?: number;
  validations?: number;
  system?: number;
  rgpd?: number;
}

/**
 * Filtres pour la recherche d'activites.
 */
export interface ActivityFilters {
  entity_type?: ActivityEntityType;
  action?: ActivityAction;
  visibility?: ActivityVisibility;
  site_id?: number;
  plan_id?: number;
  organisme_id?: number;
  user_id?: number;
  actor_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
}

/**
 * Reponse paginee pour les activites.
 */
export interface PaginatedActivityResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ActivityLogListItem[];
}

/**
 * Onglets disponibles pour la page activite.
 */
export type ActivityTab =
  | 'all'
  | 'my_sites'
  | 'my_plans'
  | 'my_rights'
  | 'validations'
  | 'system'
  | 'rgpd';

/**
 * Configuration d'un onglet.
 */
export interface ActivityTabConfig {
  id: ActivityTab;
  labelKey: string;
  icon: string;
  adminOnly?: boolean;
  superAdminOnly?: boolean;
}

/**
 * Mapping des actions vers les icones.
 */
export const ACTION_ICONS: Record<ActivityAction, string> = {
  create: 'fi-rr-add',
  update: 'fi-rr-edit',
  delete: 'fi-rr-trash',
  add_member: 'fi-rr-user-add',
  remove_member: 'fi-rr-user-remove',
  add_referent: 'fi-rr-star',
  remove_referent: 'fi-rr-star',
  status_change: 'fi-rr-refresh',
  activate: 'fi-rr-check-circle',
  deactivate: 'fi-rr-cross-circle',
  rgpd_request: 'fi-rr-shield-exclamation',
  rgpd_cancelled: 'fi-rr-shield-check',
  rgpd_anonymized: 'fi-rr-user-time',
  access_granted: 'fi-rr-key',
  access_revoked: 'fi-rr-ban',
  validation_approved: 'fi-rr-check-circle',
  validation_rejected: 'fi-rr-cross-circle',
  file_upload: 'fi-rr-upload',
  file_delete: 'fi-rr-document-delete',
};

/**
 * Icones specifiques pour les validations selon l'action.
 * Utilisees pour differencier les etats de validation.
 */
export const VALIDATION_ACTION_ICONS: Record<string, string> = {
  create: 'fi-rr-time-forward',         // Demande en attente (horloge)
  validation_approved: 'fi-rr-check-circle',   // Approuvee (check vert)
  validation_rejected: 'fi-rr-cross-circle',   // Rejetee (croix rouge)
};

/**
 * Mapping des types d'entites vers les icones.
 */
export const ENTITY_TYPE_ICONS: Record<ActivityEntityType, string> = {
  site: 'fi-rr-marker',
  plan: 'fi-rr-document',
  user: 'fi-rr-user',
  organisme: 'fi-rr-building',
  validation: 'fi-rr-check-circle',
};

/**
 * Configuration des onglets par defaut.
 */
export const DEFAULT_TAB_CONFIGS: ActivityTabConfig[] = [
  { id: 'all', labelKey: 'activity.tabs.all', icon: 'fi-rr-list' },
  { id: 'my_sites', labelKey: 'activity.tabs.mySites', icon: 'fi-rr-marker' },
  { id: 'my_plans', labelKey: 'activity.tabs.myPlans', icon: 'fi-rr-document' },
  { id: 'my_rights', labelKey: 'activity.tabs.myRights', icon: 'fi-rr-shield-check' },
  { id: 'validations', labelKey: 'activity.tabs.validations', icon: 'fi-rr-check-circle', adminOnly: true },
  { id: 'system', labelKey: 'activity.tabs.system', icon: 'fi-rr-settings', superAdminOnly: true },
  { id: 'rgpd', labelKey: 'activity.tabs.rgpd', icon: 'fi-rr-shield', superAdminOnly: true },
];
