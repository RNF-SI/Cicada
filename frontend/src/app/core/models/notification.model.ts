/**
 * Modeles pour les notifications et validations.
 */

// Types de notifications
export type NotificationType =
  | 'validation_request'
  | 'validation_approved'
  | 'validation_rejected'
  | 'user_associated_site'
  | 'user_associated_plan'
  | 'user_removed_site'
  | 'user_removed_plan'
  | 'account_deactivated'
  | 'account_activated'
  | 'site_orphaned'
  | 'organisme_no_admin'
  | 'system_alert'
  | 'info';

// Priorites
export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical';

// Types de demandes de validation
export type ValidationRequestType =
  | 'user_registration'
  | 'site_creation'
  | 'site_access'
  | 'plan_access'
  | 'module_access'
  | 'admin_deactivation'
  | 'admin_promotion'
  | 'admin_demotion'
  | 'referent_validation'
  | 'site_org_link'
  | 'plan_site_link'
  | 'invite_org_to_site'
  | 'invite_user_to_site';

// Modules disponibles pour les demandes d'accès
export type ModuleCode = 'zonages' | 'inventaires' | 'plans' | 'sites';

export interface ApplicationModule {
  code: ModuleCode;
  name: string;
  description: string;
  icon: string;
  route: string;
  requiresAccess: boolean;
}

// Statuts de validation
export type ValidationStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'expired';

/**
 * Interface pour une notification.
 */
export interface Notification {
  id: number;
  notification_type: NotificationType;
  notification_type_display?: string;
  title: string;
  message: string;
  priority: NotificationPriority;
  priority_display?: string;
  related_user?: {
    id: number;
    email: string;
    nom_complet?: string;
  };
  related_site?: {
    id: number;
    nom_site: string;
  };
  related_plan?: {
    id: number;
    nom: string;
  };
  related_organisme?: {
    id: number;
    nom_organisme: string;
  };
  related_validation?: number;
  action_url?: string;
  read: boolean;
  read_at?: string;
  created_at: string;
}

/**
 * Interface pour une notification simplifiee (liste).
 */
export interface NotificationListItem {
  id: number;
  notification_type: NotificationType;
  notification_type_display?: string;
  title: string;
  message: string;
  priority: NotificationPriority;
  action_url?: string;
  read: boolean;
  created_at: string;
}

/**
 * Interface pour une demande de validation.
 */
export interface ValidationRequest {
  id: number;
  request_type: ValidationRequestType;
  request_type_display?: string;
  status: ValidationStatus;
  status_display?: string;
  requester?: {
    id: number;
    email: string;
    nom_complet?: string;
  };
  target_site?: {
    id: number;
    nom_site: string;
  };
  target_plan?: {
    id: number;
    nom: string;
  };
  target_module?: {
    code: string;
    name: string;
  };
  target_user?: {
    id: number;
    email: string;
    nom_complet?: string;
  };
  requested_organisme?: {
    id: number;
    nom_organisme: string;
  };
  requested_role_level?: string;
  justification?: string;
  validator?: {
    id: number;
    email: string;
    nom_complet?: string;
  };
  validation_comment?: string;
  validated_at?: string;
  pending_user_info?: PendingUserInfo;
  can_validate?: boolean;
  /** Indique si le demandeur souhaite devenir référent (pour site_creation et site_access) */
  request_as_referent?: boolean;
  /** Indique si cette demande site_access est bloquée par un site_org_link en attente */
  blocked_by_org_link?: boolean;
  created_at: string;
  updated_at?: string;
}

/**
 * Interface pour les infos d'un utilisateur en attente.
 */
export interface PendingUserInfo {
  email: string;
  nom_role?: string;
  prenom_role?: string;
  nom_complet: string;
  justification?: string;
  created_at?: string;
}

/**
 * Interface pour une demande de validation simplifiee (liste).
 */
export interface ValidationRequestListItem {
  id: number;
  request_type: ValidationRequestType;
  request_type_display?: string;
  status: ValidationStatus;
  status_display?: string;
  requester_id: number;
  requester_name: string;
  target_name?: string;
  target_site_id?: number;
  target_site_name?: string;
  target_plan_id?: number;
  target_plan_name?: string;
  justification?: string;
  validator_name?: string;
  validator_comment?: string;
  validated_at?: string;
  created_at: string;
  /** Indique si le demandeur souhaite devenir référent (pour site_creation et site_access) */
  request_as_referent?: boolean;
  /** Indique si cette demande site_access est bloquée par un site_org_link en attente */
  blocked_by_org_link?: boolean;
}

/**
 * Validateur pouvant traiter une demande (nom + rôle).
 */
export interface ValidatorInfo {
  id: number;
  name: string;
  email: string;
  role_level: string;
  role_label: string;
  organisme: string | null;
}

/**
 * Réponse de GET /api/validations/{id}/validators/
 */
export interface RequestValidatorsResponse {
  validators: ValidatorInfo[];
  is_self_validator: boolean;
}

/**
 * Réponse de GET /api/users/sites/creation-validators/ (aperçu avant création).
 */
export interface SiteCreationValidatorsResponse {
  auto_validated: boolean;
  validators: ValidatorInfo[];
}

/**
 * Reponse du endpoint poll.
 */
export interface NotificationPollResponse {
  notifications: NotificationListItem[];
  unread_count: number;
  pending_validations: number;
  has_updates: boolean;
  timestamp: string;
}

/**
 * Reponse compteur notifications.
 */
export interface NotificationCountResponse {
  unread_count: number;
}

/**
 * Reponse compteur validations.
 */
export interface ValidationCountResponse {
  pending_count: number;
}

/**
 * Donnees pour l'inscription publique.
 */
export interface PublicRegistrationData {
  email: string;
  password: string;
  password_confirm: string;
  nom_role?: string;
  prenom_role?: string;
  requested_organisme_id?: number;
  justification?: string;
}

/**
 * Reponse inscription publique.
 */
export interface PublicRegistrationResponse {
  message: string;
  validation_request_id: number;
}

/**
 * Reponse statut inscription.
 */
export interface RegistrationStatusResponse {
  status: 'pending' | 'registered' | 'not_found';
  message: string;
  created_at?: string;
}

/**
 * Donnees pour approuver une demande.
 */
export interface ValidationApproveData {
  comment?: string;
  /** Si défini, surcharge le choix du demandeur pour le statut référent */
  approve_as_referent?: boolean;
}

/**
 * Donnees pour rejeter une demande.
 */
export interface ValidationRejectData {
  comment: string;
}

/**
 * Donnees pour demander acces a un site.
 */
export interface SiteAccessRequestData {
  justification?: string;
  request_as_referent?: boolean;
}

/**
 * Donnees pour demander acces a un plan.
 */
export interface PlanAccessRequestData {
  justification?: string;
  request_as_referent?: boolean;
}

/**
 * Donnees pour demander acces a un module.
 */
export interface ModuleAccessRequestData {
  module_code: ModuleCode;
  justification?: string;
}

/**
 * Reponse action validation.
 */
export interface ValidationActionResponse {
  status: 'approved' | 'rejected' | 'cancelled';
  message: string;
}
