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
  id_parent?: number;
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
  role_level: 'utilisateur' | 'referent' | 'admin_og' | 'super_admin';
  active: boolean;
  last_login?: string;
  sites_geres?: AdminSite[];
}

/**
 * User-Site assignment (CorRoleSite)
 */
export interface UserSiteAssignment {
  id_role: number;
  id_site: number;
  referent: boolean;
  referent_valid?: boolean;
  conservateur?: boolean;
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
