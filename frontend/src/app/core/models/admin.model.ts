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
  id_type_organisme?: number;
  type_organisme_code?: string;
  type_organisme_label?: string;
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
  is_referent?: boolean;
  is_conservateur?: boolean;
  role_label: string;
  /** Type d'accès pour le styling frontend */
  access_type?: 'super_admin' | 'redacteur_principal' | 'referent' | 'conservateur' | 'membre' | 'admin_og' | 'organisme' | 'plan';
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
  /** Précision du type de site quand le type est "Autre" */
  type_site_precision?: string | null;
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
  /** Géométrie polygone (retournée par SiteDetailSerializer) */
  geom_geojson?: GeoJSONGeometry | null;
  /** Point de référence (retourné par SiteDetailSerializer) */
  geom_pt_geojson?: GeoJSONGeometry | null;
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
  /** Précision du type de site quand le type est "Autre" */
  type_site_precision?: string | null;
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
  /** Précision du type de site quand le type est "Autre" */
  type_site_precision?: string | null;
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
  type_organisme_code?: string;
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

// ==================== FICHIERS PLANS ====================

/**
 * Types de fichiers attachés à un plan de gestion
 */
export type FichierType = 'document' | 'annexe' | 'carte' | 'photo' | 'rapport' | 'autre';

/**
 * Fichier attaché à un plan de gestion
 */
export interface PlanFichier {
  id: number;
  nom_fichier: string;
  chemin_fichier: string;
  url: string | null;
  type_fichier: FichierType;
  titre: string | null;
  description: string | null;
  auteur: string | null;
  public: boolean;
  ordre_affichage: number;
  taille_fichier: number | null;
  file_size_human: string | null;
  extension: string | null;
  is_image: boolean;
  is_document: boolean;
  date_upload: string;
  date_document: string | null;
}

// ==================== PLANS DE GESTION ====================

/**
 * Statuts possibles d'un plan de gestion.
 *
 * Notes — attributs orthogonaux au statut (un plan validé peut les cumuler) :
 * - « Étendu » (#250) : `annees_extension > 0`.
 * - « En cours de révision » (#278) : `en_revision = true`. Le plan reste
 *   fonctionnellement validé pendant la rédaction du rang suivant. La
 *   révision peut être lancée avant ou après le dépassement de `annee_fin`.
 * - « Évaluation mi-parcours » (#276) : `is_mi_parcours = true`. Indique
 *   qu'une modification est l'évaluation mi-parcours du plan. Unique par chaîne.
 *
 * Seul `draft` autorise l'édition (#248).
 *
 * Depuis #277 (refactor) : le workflow CSRPN (avis_csrpn → comite_consultatif →
 * arrete_pref) est extrait dans l'attribut orthogonal {@link ValidationStep}.
 */
export type PlanStatut =
  | 'draft'
  | 'valide'
  | 'modifie'
  | 'archive';

/**
 * Statuts proposés comme filtres sur la liste des plans (#635).
 * Ordre d'affichage des chips « Filtrer par statut ».
 */
export const PLAN_STATUS_OPTIONS: PlanStatut[] = ['draft', 'valide', 'modifie', 'archive'];

/**
 * #277 — Étape du workflow de validation CSRPN. Attribut orthogonal au
 * statut, présent uniquement sur les plans `draft` en cours de validation.
 * `null` (ou absent) = pas dans le workflow.
 */
export type ValidationStep =
  | 'avis_csrpn'
  | 'comite_consultatif'
  | 'arrete_pref';

/**
 * Site associé à un plan de gestion
 */
export interface PlanSiteOrganisme {
  id_organisme: number;
  nom_organisme: string;
  principal: boolean;
  type_organisme_code?: string;
}

export interface PlanSite {
  id_site: number;
  nom_site: string;
  slug?: string;
  type_site_label?: string;
  /** Mnémonique du type de site (RNN, RNR, PNR, ENS, ENSD...) — #281 */
  type_site_mnemonique?: string | null;
  /** Précision du type de site quand le type est "Autre" */
  type_site_precision?: string | null;
  surf_off?: number;
  rang?: number;
  /** Indique si l'utilisateur courant a accès à ce site */
  current_user_has_access?: boolean;
  /** Statut du lien plan-site (active = lié, pending = en attente de validation) */
  status?: 'active' | 'pending';
  /** Organismes liés au site */
  organismes?: PlanSiteOrganisme[];
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
 * Élément de la chaîne de versions d'un plan de gestion
 */
export interface PlanVersionChainItem {
  id_pg: number;
  nom: string;
  slug: string;
  version: string;
  statut: PlanStatut;
  rang?: number;
  annee_debut?: number;
  annee_fin?: number;
  /** #250 — Années d'extension (0, 1 ou 2) du plan de la chaîne. */
  annees_extension?: number;
  /** #278 — Plan en cours de révision. */
  en_revision?: boolean;
  /** #276 — Plan portant l'évaluation mi-parcours. */
  is_mi_parcours?: boolean;
  /** #278 — Lien vers le brouillon du rang suivant. */
  next_rang_plan_id?: number | null;
  type_document?: string;
  type_document_mnemonique?: string;
  is_current: boolean;
}

/**
 * Plan de gestion - modèle complet depuis l'API
 */
export interface AdminPlan {
  id_pg: number;
  nom: string;
  slug?: string;
  id_cdr?: number;
  rang?: number;
  statut: PlanStatut;
  version?: string;
  annee_debut?: number;
  annee_fin?: number;
  /** #250 — Années d'extension ajoutées au plan (0, 1 ou 2). Attribut
   *  indépendant du statut : un plan validé/modifié peut être étendu. */
  annees_extension?: number;
  /** #250 — Vrai quand annees_extension > 0 (read-only API). */
  is_extended?: boolean;
  /** #250 — Vrai si le plan est éligible à l'extension : statut validé,
   *  pas déjà étendu, et année courante ∈ [annee_fin-1, annee_fin+2] (read-only API). */
  peut_etre_etendu?: boolean;
  /** #250 — annee_fin + annees_extension (read-only API) */
  annee_fin_effective?: number | null;
  /** #278 — Plan en cours de révision (le rang suivant est en rédaction).
   *  Attribut orthogonal au statut : le plan reste validé fonctionnellement. */
  en_revision?: boolean;
  /** #278 — Identique à `en_revision` (read-only API). */
  is_in_revision?: boolean;
  /** #278 — Lien vers le brouillon du rang suivant. */
  next_rang_plan_id?: number | null;
  next_rang_plan_nom?: string | null;
  next_rang_plan_slug?: string | null;
  /** #276 — Cette version est l'évaluation mi-parcours du plan.
   *  Attribut orthogonal au statut. Unique par chaîne. */
  is_mi_parcours?: boolean;
  /** #276 — Identique à `is_mi_parcours` (read-only API). */
  is_mid_term?: boolean;
  /** #277 — Étape du workflow CSRPN en cours (orthogonal au statut).
   *  null/absent = pas dans le workflow. Présent uniquement sur les drafts. */
  validation_step?: ValidationStep | null;
  /** #277 — Libellé traduit de validation_step (read-only API). */
  validation_step_display?: string | null;
  /** #277 — Vrai si validation_step renseigné (read-only API). */
  is_in_csrpn_workflow?: boolean;
  /** Vrai si le plan a déjà un brouillon enfant en cours.
   *  Bloque la création d'une nouvelle version (read-only API). */
  has_draft_child?: boolean;
  /** Vrai si on peut créer une nouvelle version (brouillon enfant) :
   *  statut ∈ {valide, modifie, archive} ET pas de brouillon enfant.
   *  (read-only API) */
  can_create_modification?: boolean;
  surface?: number;
  gestion_partagee: boolean;
  ct88: boolean;
  risque_incendie: boolean;
  date_avis_csrpn?: string;
  /** #277 — Workflow CSRPN : étape 2 (validation comité consultatif). */
  date_validation_comite?: string;
  /** #277 — Workflow CSRPN : étape 3 (arrêté préfectoral, RNN uniquement). */
  date_arrete_pref?: string;
  /** #277 — Numéro de référence de l'arrêté préfectoral. */
  numero_arrete_pref?: string;
  id_docgestion_fcen?: string;
  id_evaluation?: number;
  evaluation_display?: string;
  id_redacteur_type?: number;
  redacteur_type_display?: string;
  redacteur_nom?: string;
  redacteurs?: string;
  relecteurs?: string;
  autres_contributeurs?: string;
  organismes_redacteurs_list?: Array<{ id_organisme: number; nom_organisme: string }>;
  commentaire?: string;
  date_ajout?: string;
  date_maj?: string;
  sites?: PlanSite[];
  referents?: PlanReferent[];
  membres?: PlanMembre[];
  id_utilisateur_ajout?: number;
  id_utilisateur_maj?: number;
  // Fichiers
  fichiers?: PlanFichier[];
  nb_fichiers?: number;
  // Version chain fields
  plan_parent_id?: number | null;
  plan_parent_nom?: string | null;
  plan_parent_slug?: string | null;
  /** #433 — rang/version du plan parent (rappel du contexte chaîne de versions). */
  plan_parent_rang?: number | null;
  plan_parent_version?: string | null;
  type_document_display?: string | null;
  children_count?: number;
  version_chain?: PlanVersionChainItem[];
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
  date_avis_csrpn?: string;
  id_docgestion_fcen?: string;
  id_evaluation?: number;
  id_redacteur_type?: number;
  redacteur_nom?: string;
  redacteurs?: string;
  relecteurs?: string;
  autres_contributeurs?: string;
  organismes_redacteurs_ids?: number[];
  commentaire?: string;
  referents_ids?: number[];
  /**
   * Plan du rang précédent auquel rattacher ce plan (conservation de la
   * chaîne de versions). Posé à la création standard quand l'utilisateur
   * confirme le rattachement suggéré, ou modifié depuis le formulaire de
   * modification pour établir/retirer un lien entre deux PG séparés (#506).
   * `null` retire explicitement le rattachement.
   */
  plan_parent_id?: number | null;
}

/**
 * Résumé d'un plan validé/archivé associé à un site (endpoint for-sites).
 */
export interface SitePlanSummary {
  id_pg: number;
  nom: string;
  slug: string;
  statut: PlanStatut;
  statut_display: string;
  rang: number;
  version: string;
  annee_debut: number | null;
  annee_fin: number | null;
  is_mi_parcours: boolean;
}

/** Plans validés/archivés d'un site. */
export interface SitePlansEntry {
  site_id: number;
  site_nom: string;
  plans: SitePlanSummary[];
}

/** Réponse de GET /api/plans/plans/for-sites/. */
export interface SitePlansResponse {
  sites: SitePlansEntry[];
}

/**
 * Options pour la duplication d'un plan de gestion
 */
export interface PlanDuplicateOptions {
  copy_sites: boolean;
  copy_referents: boolean;
  copy_fichiers: boolean;
  copy_enjeux: boolean;
  copy_sub_elements: boolean;
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
  slug: string;
  nom_site: string;
  id_inpn: string | null;
  id_local: string | null;
  type_site_label: string | null;
  /** Précision du type de site quand le type est "Autre" */
  type_site_precision?: string | null;
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

// ==================== BULK IMPORT ====================

/** Mapping des champs source vers les champs cibles */
export type BulkImportFieldMapping = Record<string, string>;

/** Informations de doublon détecté */
export interface BulkImportDuplicateInfo {
  type: 'exact_inpn';
  existing_site_id: number;
  existing_site_name: string;
}

/** Une ligne de site dans le résultat de validation */
export interface BulkImportSiteRow {
  row_index: number;
  original_properties: Record<string, any>;
  mapped_data: Record<string, any>;
  geometry?: any | null;
  has_geometry: boolean;
  errors: string[];
  warnings: string[];
  duplicate_info: BulkImportDuplicateInfo | null;
  /** Sites avec noms similaires (avertissement non bloquant) */
  similar_names?: { id_site: number; nom_site: string }[];
  /** Sélectionné pour import (état local, non retourné par l'API) */
  selected?: boolean;
}

/** Résultat de la validation d'import en masse */
export interface BulkImportValidationResult {
  detected_properties: string[];
  suggested_mapping: BulkImportFieldMapping;
  applied_mapping: BulkImportFieldMapping;
  sites: BulkImportSiteRow[];
  total: number;
  valid: number;
  errors: number;
  warnings: number;
  duplicates: number;
}

/** Détail du résultat d'import par site */
export interface BulkImportDetailItem {
  row_index: number;
  nom_site: string;
  status: 'created' | 'validation_pending' | 'failed';
  site_id?: number;
  validation_request_id?: number;
  error?: string;
}

/** Résultat de l'exécution d'import en masse */
export interface BulkImportResult {
  async: boolean;
  job_id?: number;
  message?: string;
  created?: number;
  failed?: number;
  validation_pending?: number;
  details?: BulkImportDetailItem[];
}

/** Statut d'un job d'import asynchrone */
export interface BulkImportJobStatus {
  job_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_sites: number;
  processed_sites: number;
  created_sites: number;
  failed_sites: number;
  validation_pending_sites: number;
  result_data: any;
  created_at: string | null;
  completed_at: string | null;
}

/**
 * Import Excel de l'arborescence d'un plan (V1). Voir backend
 * `apps/plans/services_import.py`.
 */
export interface ArborescenceImportIssue {
  /** Onglet concerné (null pour une anomalie globale). */
  sheet: string | null;
  /** Ligne Excel (null pour une anomalie globale). */
  row: number | null;
  /** Colonne concernée (null si non applicable). */
  column: string | null;
  level: 'error' | 'warning';
  message: string;
}

/** Mode d'import : create (plan vide), add (ajout), replace (remplacement). */
export type ImportMode = 'create' | 'add' | 'replace';

/** Une ligne de données (clés de colonne → valeur) + numéro de ligne Excel. */
export type ParsedRow = Record<string, unknown> & { _row?: number | null };
/** Données parsées, une liste de lignes par onglet. */
export type ParsedData = Record<string, ParsedRow[]>;

/** Rapport de validation (dry-run) d'un fichier d'import d'arborescence. */
export interface ArborescenceImportReport {
  can_import: boolean;
  n_errors: number;
  n_warnings: number;
  issues: ArborescenceImportIssue[];
  /** Décompte de ce qui serait créé, par onglet. */
  summary: Record<string, number>;
  /** Données parsées (pour la correction interactive #9). */
  data?: ParsedData;
}

/** Description d'une colonne du format (schéma d'import). */
export interface ImportColumn {
  key: string;
  header: string;
  required: boolean;
  multi: boolean;
  boolean: boolean;
  nomenclature: string | null;
  ref: string | null;
  vocab: string | null;
  help: string;
}

/** Description d'un onglet du format d'import. */
export interface ImportSheet {
  key: string;
  name: string;
  description: string;
  columns: ImportColumn[];
}

/** Onglet d'un classeur Excel quelconque (lecture pour le mapping #10). */
export interface ForeignSheet {
  name: string;
  headers: string[];
  rows: string[][];
}

/** Résultat d'un import d'arborescence exécuté. */
export interface ArborescenceImportResult {
  created: Record<string, number>;
  total: number;
}
