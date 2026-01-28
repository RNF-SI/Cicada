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
 * Informations d'acces de l'utilisateur courant a un site
 */
export interface SiteUserAccess {
  has_access: boolean;
  is_referent: boolean;
  is_conservateur: boolean;
  role_label: string;
}

/**
 * Type de site (nomenclature) - retourné par le backend pour les détails
 */
export interface SiteTypeInfo {
  id_nomenclature: number;
  label: string;
  cd_nomenclature: string;
}

/**
 * Site - model from API
 */
export interface AdminSite {
  id_site: number;
  /** URL slug unique pour le site */
  slug: string;
  nom_site: string;
  id_local?: string;
  id_inpn?: string;
  /** Type de site - objet complet (retourné par SiteDetailSerializer) */
  type_site?: SiteTypeInfo | null;
  /** Label du type de site (retourné par tous les serializers) */
  type_site_label?: string;
  surf_off?: number;
  marin?: boolean;
  outre_mer?: boolean;
  active?: boolean;
  /** Organismes gestionnaires du site */
  organismes?: SiteOrganisme[];
  users?: AdminUser[];
  /** Nombre de plans de gestion associés */
  plans_count?: number;
  // Informations sur l'acces de l'utilisateur courant
  current_user_is_referent?: boolean;
  current_user_access?: SiteUserAccess;
}

/**
 * Create/Update site payload
 */
export interface SiteCreatePayload {
  nom_site: string;
  id_local?: string;
  id_inpn?: string;
  /** ID de nomenclature pour le type de site (envoyé comme type_site_id au backend) */
  type_site_id?: number;
  surf_off?: number;
  marin?: boolean;
  outre_mer?: boolean;
  active?: boolean;
  /** Géométrie polygone au format GeoJSON */
  geom_geojson?: GeoJSONGeometry | null;
  /** Point de référence au format GeoJSON */
  geom_pt_geojson?: GeoJSONGeometry | null;
  /** Demander à devenir référent (seulement pour la création par utilisateur non-admin) */
  request_as_referent?: boolean;
}

// ==================== GEOJSON ====================

/**
 * Géométrie GeoJSON générique
 */
export interface GeoJSONGeometry {
  type: string;
  coordinates: any[];
}

/**
 * Feature GeoJSON (un site avec sa géométrie)
 */
export interface GeoJSONFeature {
  type: 'Feature';
  id?: number;
  geometry: GeoJSONGeometry | null;
  properties: {
    id_site: number;
    slug: string;
    nom_site: string;
    id_local?: string;
    id_inpn?: string;
    type_site?: string;
    surf_off?: number;
    marin?: boolean;
    outre_mer?: boolean;
    active?: boolean;
    organismes_gestionnaires?: Array<{
      organisme: {
        id_organisme: number;
        nom_organisme: string;
      };
      principal: boolean;
    }>;
    [key: string]: any;
  };
}

/**
 * FeatureCollection GeoJSON (collection de sites)
 */
export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
  properties?: {
    count: number;
    note?: string;
  };
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
  // RGPD fields
  deletion_requested_at?: string | null;
  is_anonymized?: boolean;
  anonymized_at?: string | null;
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
  /** Indique si c'est l'organisme principal/gestionnaire du site */
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
 * Membre d'un plan de gestion (via CorRolePlan)
 */
export interface PlanMembre {
  id_role: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  nom_complet?: string;
  referent: boolean;
  date_association?: string;
  commentaire?: string;
}

/**
 * Plan de gestion - modèle complet depuis l'API
 */
export interface AdminPlan {
  id_pg: number;
  nom: string;
  id_cdr?: number;
  rang?: number;
  statut: PlanStatut;
  version?: string;
  annee_debut?: number;
  annee_fin?: number;
  surface?: number;
  gestion_partagee: boolean;
  ct88: boolean;
  risque_incendie: boolean;
  date_validation_cspn?: string;
  id_docgestion_fcen?: string;
  id_evaluation?: number;
  evaluation_label?: string;
  id_redacteur_type?: number;
  redacteur_type_label?: string;
  redacteur_nom?: string;
  redacteurs?: string;
  relecteurs?: string;
  commentaire?: string;
  date_ajout?: string;
  date_maj?: string;
  sites?: PlanSite[];
  referents?: PlanReferent[];
  membres?: PlanMembre[];
  id_utilisateur_ajout?: number;
  id_utilisateur_maj?: number;
}

/**
 * Payload pour créer/modifier un plan de gestion
 */
export interface PlanCreatePayload {
  // Champs obligatoires
  nom: string;
  sites_ids: number[];
  rang: number;
  ct88: boolean;
  annee_debut: number;
  annee_fin: number;
  // Champs optionnels
  statut?: PlanStatut;
  version?: string;
  surface?: number;
  gestion_partagee?: boolean;
  risque_incendie?: boolean;
  date_validation_cspn?: string;
  id_docgestion_fcen?: string;
  id_evaluation?: number;
  id_redacteur_type?: number;
  redacteur_nom?: string;
  redacteurs?: string;
  relecteurs?: string;
  commentaire?: string;
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

// ==================== RGPD ====================

/**
 * Demande de suppression RGPD en attente
 */
export interface RgpdRequest {
  id_role: number;
  email: string;
  full_name: string;
  organisme_name: string | null;
  deletion_requested_at: string;
  active: boolean;
  is_anonymized: boolean;
  days_since_request: number | null;
}

// ==================== DUPLICATE DETECTION ====================

/**
 * Site retourné par l'endpoint de vérification des doublons
 */
export interface DuplicateSite {
  id_site: number;
  nom_site: string;
  id_inpn: string | null;
  id_local: string | null;
  type_site_label: string | null;
  surf_off: number | null;
  organismes: Array<{
    id_organisme: number;
    nom_organisme: string;
    principal: boolean;
  }>;
  /** Indique si le site appartient à l'organisme de l'utilisateur */
  is_user_org: boolean;
  /** Indique si l'utilisateur a déjà accès au site */
  has_access: boolean;
}

/**
 * Résultat de la vérification des doublons de site
 */
export interface DuplicateCheckResult {
  /** Site avec code INPN identique (bloquant) */
  exact_inpn_match: DuplicateSite | null;
  /** Sites avec noms similaires (avertissement) */
  similar_names: DuplicateSite[];
}
