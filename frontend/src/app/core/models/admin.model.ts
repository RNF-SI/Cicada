/**
 * Models for administration features
 */

/**
 * Organisme (organization) - full model from API
 */
export interface AdminOrganisme {
  id_organisme: number;
  uuid_organisme?: string;
  nom_organisme: string;
  adresse_organisme?: string;
  cp_organisme?: string;
  ville_organisme?: string;
  tel_organisme?: string;
  fax_organisme?: string;
  email_organisme?: string;
  url_organisme?: string;
  url_logo?: string;
  id_parent?: number;
  parent?: AdminOrganisme;
  users_count?: number;
  sites_count?: number;
}

/**
 * Create/Update organisme payload
 */
export interface OrganismeCreatePayload {
  nom_organisme: string;
  adresse_organisme?: string;
  cp_organisme?: string;
  ville_organisme?: string;
  tel_organisme?: string;
  email_organisme?: string;
  url_organisme?: string;
  parent_id?: number | null;
}

/**
 * Site - model from API
 */
export interface AdminSite {
  id_site: number;
  nom_site: string;
  id_local?: string;
  id_inpn?: string;
  id_type_site?: number;
  type_site_label?: string;
  surf_off?: number;
  marin?: boolean;
  outre_mer?: boolean;
  active?: boolean;
  organismes?: AdminOrganisme[];
  users?: AdminUser[];
}

/**
 * Create/Update site payload
 */
export interface SiteCreatePayload {
  nom_site: string;
  id_local?: string;
  id_inpn?: string;
  id_type_site?: number;
  surf_off?: number;
  marin?: boolean;
  outre_mer?: boolean;
  active?: boolean;
}

/**
 * User-Site relationship with role details
 */
export interface UserSiteRelation {
  site: {
    id_site: number;
    nom_site: string;
    surf_off?: number;
    active?: boolean;
  };
  referent: boolean;
  referent_valid?: boolean;
}

/**
 * User-Plan relationship (plans where user is referent)
 */
export interface UserPlanRelation {
  id_pg: number;
  nom: string;
  statut: PlanStatut;
  annee_debut?: number;
  annee_fin?: number;
}

/**
 * User - admin list model
 */
export interface AdminUser {
  id_role: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  identifiant?: string;
  id_organisme?: number;
  organisme?: AdminOrganisme;
  role_level: 'utilisateur' | 'admin_og' | 'super_admin';
  active: boolean;
  last_login?: string;
  sites_lies?: UserSiteRelation[];
  plans_referent?: UserPlanRelation[];
}

/**
 * User-Site assignment (CorRoleSite)
 */
export interface UserSiteAssignment {
  id_role: number;
  id_site: number;
  referent: boolean;
  referent_valid?: boolean;
}

/**
 * Organisme-Site assignment (CorOgSite)
 */
export interface OrganismeSiteAssignment {
  id_organisme: number;
  id_site: number;
  principal?: boolean;
}

/**
 * Site linked to an organisme (from /organismes/{id}/sites/ endpoint)
 */
export interface OrganismeSite {
  id_site: number;
  nom_site: string;
  surf_off?: number;
  type_site?: string;
  type_site_label?: string;
  active?: boolean;
  principal?: boolean;
}

/**
 * Organisme linked to a site (from /sites/{id}/organismes/ endpoint)
 */
export interface SiteOrganisme {
  id_organisme: number;
  nom_organisme: string;
  ville_organisme?: string;
  email_organisme?: string;
  principal: boolean;
}

/**
 * Paginated API response (format standard DRF)
 */
export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

/**
 * Paginated API response (format personnalisé avec pagination imbriquée)
 * Utilisé par les endpoints /api/users/*
 */
export interface PaginatedResponseNested<T> {
  links: {
    next: string | null;
    previous: string | null;
  };
  pagination: {
    count: number;
    current_page: number;
    total_pages: number;
    page_size: number;
    has_next: boolean;
    has_previous: boolean;
  };
  results: T[];
}

// ==================== PLANS DE GESTION ====================

/**
 * Statuts possibles d'un plan de gestion
 */
export type PlanStatut = 'draft' | 'valide' | 'archive';

/**
 * Site associé à un plan de gestion
 */
export interface PlanSite {
  id_site: number;
  nom_site: string;
  type_site_label?: string;
  surf_off?: number;
  rang?: number;
}

/**
 * Référent d'un plan de gestion
 */
export interface PlanReferent {
  id_role: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  nom_complet?: string;
}

/**
 * Plan de gestion - modèle complet depuis l'API
 */
export interface AdminPlan {
  id_pg: number;
  nom: string;
  id_cdr?: number;
  statut: PlanStatut;
  version?: string;
  annee_debut?: number;
  annee_fin?: number;
  gestion_partagee: boolean;
  ct88: boolean;
  risque_incendie: boolean;
  id_evaluation?: number;
  evaluation_label?: string;
  id_redacteur_type?: number;
  redacteur_type_label?: string;
  redacteur_nom?: string;
  commentaire?: string;
  date_ajout?: string;
  date_maj?: string;
  sites?: PlanSite[];
  referents?: PlanReferent[];
  id_utilisateur_ajout?: number;
  id_utilisateur_maj?: number;
}

/**
 * Payload pour créer/modifier un plan de gestion
 */
export interface PlanCreatePayload {
  nom: string;
  statut?: PlanStatut;
  version?: string;
  annee_debut?: number;
  annee_fin?: number;
  gestion_partagee?: boolean;
  ct88?: boolean;
  risque_incendie?: boolean;
  id_evaluation?: number;
  id_redacteur_type?: number;
  redacteur_nom?: string;
  commentaire?: string;
  sites_ids?: number[];
  referents_ids?: number[];
}

/**
 * Type d'évaluation (nomenclature)
 */
export interface EvaluationType {
  id_nomenclature: number;
  cd_nomenclature: string;
  label: string;
}

/**
 * Type de rédacteur (nomenclature)
 */
export interface RedacteurType {
  id_nomenclature: number;
  cd_nomenclature: string;
  label: string;
}
