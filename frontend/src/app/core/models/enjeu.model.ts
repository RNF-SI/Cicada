/**
 * Models for Enjeux (conservation issues) and FCR (Key Success Factors)
 */

/**
 * GeoJSON geometry type for enjeux
 */
export interface GeoJSONGeometry {
  type: 'MultiPolygon' | 'Polygon' | 'Point';
  coordinates: number[][][] | number[][] | number[];
}

/**
 * Taxon reference from TaxRef
 */
export interface TaxonRef {
  id?: number;
  cd_nom: number;
  nom_complet?: string;
  nom_vern?: string;
  regne?: string;
}

/**
 * Habitat reference from HabRef
 */
export interface HabitatRef {
  id?: number;
  cd_hab: string;
  lb_hab_fr?: string;
}

/**
 * Geology reference from INPG
 */
export interface GeologieRef {
  id?: number;
  id_inpg: string;
  nom?: string;
}

/**
 * Enjeu / FCR categories
 */
export type EnjeuCategorie = 'ENJEU' | 'FCR';

/**
 * FCR categories
 */
export type FcrCategorie = 'CONNAISSANCE' | 'ANCRAGE' | 'FONCTIONNEMENT' | 'AUTRE';

/**
 * Enjeu priority levels
 */
export type EnjeuPriorite = 1 | 2 | 3;

/**
 * Enjeu - conservation issue or key success factor
 */
export interface Enjeu {
  id_enjeu: number;
  id_pg: number;
  plan_nom?: string;
  slug?: string;

  // Type (Enjeu or FCR)
  id_categorie: number;
  categorie_label?: string;
  categorie_mnemonique?: EnjeuCategorie;

  // Common fields
  libelle: string;
  intitule_court?: string;
  description?: string;

  // Enjeu-specific fields
  rang?: EnjeuPriorite;
  categorie_ecologique?: boolean; // true=Ecological, false=Socio-economic
  habitat: boolean;
  espece: boolean;
  processus: boolean;
  etat_enjeu?: string;

  // FCR-specific fields
  id_categorie_fcr?: number;
  categorie_fcr_label?: string;

  // Optional fields
  id_importance?: number;
  importance_label?: string;
  geom?: GeoJSONGeometry;

  // Taxonomic relations
  taxons?: TaxonRef[];
  habitats?: HabitatRef[];
  geologies?: GeologieRef[];

  // Counts (from list serializer)
  nb_taxons?: number;
  nb_habitats?: number;
  nb_geologies?: number;

  // Facteurs d'influence
  facteurs_influence?: FacteurInfluence[];
  nb_facteurs_influence?: number;

  // Objectifs à Long Terme (OLT)
  objectifs_long_terme?: ObjectifLongTerme[];
  nb_olt?: number;

  // Objectifs Opérationnels (OO)
  objectifs_operationnels?: ObjectifOperationnel[];
  nb_oo?: number;

  // Audit
  date_ajout: string;
  date_maj: string;
  id_utilisateur_ajout?: number;
  createur_nom?: string;
}

/**
 * Pression exercée sur un facteur d'influence
 */
export interface Pression {
  id_pression: number;
  id_facteur_influence: number;
  id_pressref?: string;
  libelle: string;
  description?: string;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Facteur d'influence rattaché à un enjeu
 */
export interface FacteurInfluence {
  id_facteur_influence: number;
  id_enjeu: number;
  libelle: string;
  description?: string;
  pressions?: Pression[];
  nb_pressions?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Payload for creating a Facteur d'Influence
 */
export interface FacteurInfluenceCreatePayload {
  id_enjeu: number;
  libelle: string;
  description?: string;
}

/**
 * Payload for creating a Pression
 */
export interface PressionCreatePayload {
  id_facteur_influence: number;
  libelle: string;
  description?: string;
}

/**
 * Objectif à Long Terme (OLT)
 */
export interface ObjectifLongTerme {
  id_olt: number;
  id_enjeu: number;
  libelle: string;
  description?: string;
  etat_actuel?: EtatActuel;
  niveaux_exigence?: NiveauExigence[];
  nb_niveaux_exigence?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * État actuel d'un OLT (1:1)
 */
export interface EtatActuel {
  id_etat_actuel: number;
  id_olt: number;
  libelle: string;
  description?: string;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Niveau d'Exigence
 */
export interface NiveauExigence {
  id_ne: number;
  id_olt: number;
  libelle: string;
  description?: string;
  indicateurs?: Indicateur[];
  nb_indicateurs?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Objectif Opérationnel (OO)
 */
export interface ObjectifOperationnel {
  id_oo: number;
  id_enjeu: number;
  libelle: string;
  description?: string;
  id_facteur_influence?: number;
  facteur_influence_libelle?: string;
  resultats_attendus?: ResultatAttendu[];
  nb_resultats_attendus?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Résultat Attendu
 */
export interface ResultatAttendu {
  id_ra: number;
  id_oo: number;
  libelle: string;
  description?: string;
  indicateurs?: Indicateur[];
  nb_indicateurs?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Indicateur d'état rattaché à un niveau d'exigence ou résultat attendu
 */
export interface Indicateur {
  id_indicateur: number;
  id_ne?: number;
  id_resultat_attendu?: number;
  nom_indicateur: string;
  description?: string;
  type_indicateur?: number;
  type_indicateur_label?: string;
  est_standardise: boolean;
  metriques?: Metrique[];
  nb_metriques?: number;
  operations?: Operation[];
  nb_operations?: number;
  taxons?: TaxonRef[];
  habitats?: HabitatRef[];
  geologies?: GeologieRef[];
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Métrique rattachée à un indicateur
 */
export interface Metrique {
  id_metrique: number;
  id_indicateur: number;
  nom_metrique: string;
  description?: string;
  type_metrique?: number;
  type_metrique_label?: string;
  unite?: string;
  ponderation?: number;
  etat_reference?: string;
  score_1_inf?: number; score_1_sup?: number; score_1_label?: string;
  score_2_inf?: number; score_2_sup?: number; score_2_label?: string;
  score_3_inf?: number; score_3_sup?: number; score_3_label?: string;
  score_4_inf?: number; score_4_sup?: number; score_4_label?: string;
  score_5_inf?: number; score_5_sup?: number; score_5_label?: string;
  mesures?: Mesure[];
  nb_mesures?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Mesure datée rattachée à une métrique
 */
export interface Mesure {
  id_mesure: number;
  id_metrique: number;
  valeur: string;
  date_mesure?: string;
  commentaire?: string;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Protocole associé à un suivi/inventaire
 */
export interface Protocole {
  id_protocole?: number;
  protocole_dans_campanule?: boolean;
  protocole_campanule_nom?: string;
  nom_protocole?: string;
  respect_protocole?: boolean;
  justification_non_respect?: string;
  differences_protocole?: string;
  description_protocole?: string;
  objectif_protocole?: string;
  periode_echantillonnage?: string;
  mode_validation?: string;
  // Audit
  date_ajout?: string;
  date_maj?: string;
}

/**
 * Suivi / Inventaire lié à une opération
 */
export interface SuiviInventaire {
  id_suivi_inventaire?: number;
  // Détails
  objectif_principal?: string;
  cibles_principales?: string;
  taxon_taxref?: string;
  annee_lancement_suivi?: number;
  // Protocole (nested)
  protocole?: Protocole;
  // Bancarisation
  outil_bancarisation?: string;
  outil_saisie?: string;
  transmission_donnee?: boolean;
  // Audit
  date_ajout?: string;
  date_maj?: string;
}

/**
 * Opération (action) rattachée à un ou plusieurs indicateurs
 */
/**
 * Programmation annuelle row data (per year) - LEGACY, kept for backwards compat
 */
export interface ProgrammationAnnuelleRow {
  ponctuelle: boolean;
  budget: number | null;
  travail: number | null;
}

/**
 * Programmation annuelle d'une opération (table relationnelle)
 */
export interface OperationAnnee {
  id_operation_annee?: number;
  annee: number;
  periodicite: boolean;
  budget: number | null;
  etp: number | null;
  id_operateur?: number | null;
  operateur_label?: string;
  periodicite_mensuelle: Record<string, boolean>;
  geom?: GeoJSONGeometry;
}

/**
 * Source de financement d'une opération
 */
export interface FinanceOperation {
  id_finance_operation?: number;
  libelle: string;
  id_categorie?: number | null;
  categorie_label?: string;
}

export interface Operation {
  id_operation: number;
  libelle: string;
  id_priorite?: number;
  priorite_label?: string;
  id_type_action?: number;
  type_action_label?: string;
  id_referentiel_operations?: string;
  code_operation?: string;
  description?: string;
  annee_min?: number;
  annee_max?: number;
  // Suivi/inventaire
  est_suivi_existant?: boolean;
  id_suivi?: number;
  suivi_inventaire?: SuiviInventaire;
  // Fréquence & acteurs
  frequence_nombre?: number;
  frequence_unite?: string;
  operateurs?: string;
  partenaires?: string;
  financeurs?: string;
  programmation_annuelle?: Record<string, ProgrammationAnnuelleRow>;
  programmation_mensuelle?: Record<string, Record<string, boolean>>;
  programmation_mensuelle_defaut?: Record<string, boolean>;
  geom?: GeoJSONGeometry;
  indicateur_ids?: number[];
  nb_indicateurs?: number;
  site_ids?: number[];
  nb_sites?: number;
  metrique_ids?: number[];
  nb_metriques?: number;
  // Nested relational data
  operation_annees?: OperationAnnee[];
  finances?: FinanceOperation[];
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Payload for creating an Operation
 */
export interface OperationCreatePayload {
  libelle: string;
  id_priorite?: number;
  id_type_action?: number;
  id_referentiel_operations?: string;
  code_operation?: string;
  description?: string;
  annee_min?: number;
  annee_max?: number;
  // Suivi/inventaire
  est_suivi_existant?: boolean;
  suivi_inventaire?: Omit<SuiviInventaire, 'id_suivi_inventaire' | 'date_ajout' | 'date_maj'>;
  // Fréquence & acteurs
  frequence_nombre?: number;
  frequence_unite?: string;
  operateurs?: string;
  partenaires?: string;
  financeurs?: string;
  programmation_annuelle?: Record<string, ProgrammationAnnuelleRow>;
  programmation_mensuelle?: Record<string, Record<string, boolean>>;
  programmation_mensuelle_defaut?: Record<string, boolean>;
  indicateur_ids?: number[];
  site_ids?: number[];
  metrique_ids?: number[];
  // Nested relational data
  operation_annees?: Omit<OperationAnnee, 'id_operation_annee' | 'operateur_label'>[];
  finances?: Omit<FinanceOperation, 'id_finance_operation' | 'categorie_label'>[];
}

/**
 * Form data for a metrique within the unified indicateur creation form
 */
export interface MetriqueFormData {
  id_metrique?: number;  // undefined = new, number = existing
  nom_metrique: string;
  type_metrique: number | null;
  unite: string;
  ponderation: number | null;
  etat_reference: string;
  scores: { [level: number]: { inf: number | null; sup: number | null } };
  _deleted?: boolean;  // marked for deletion
}

/**
 * Payload for creating an Indicateur
 */
export interface IndicateurCreatePayload {
  id_ne?: number;
  id_resultat_attendu?: number;
  nom_indicateur: string;
  description?: string;
  type_indicateur?: number;
  est_standardise?: boolean;
}

/**
 * Payload for creating an ObjectifOperationnel
 */
export interface ObjectifOperationnelCreatePayload {
  id_enjeu: number;
  libelle: string;
  description?: string;
  id_facteur_influence?: number;
}

/**
 * Payload for creating a ResultatAttendu
 */
export interface ResultatAttenduCreatePayload {
  id_oo: number;
  libelle: string;
  description?: string;
}

/**
 * Payload for creating a Metrique
 */
export interface MetriqueCreatePayload {
  id_indicateur: number;
  nom_metrique: string;
  description?: string;
  type_metrique?: number;
  unite?: string;
  ponderation?: number;
  etat_reference?: string;
  score_1_inf?: number; score_1_sup?: number; score_1_label?: string;
  score_2_inf?: number; score_2_sup?: number; score_2_label?: string;
  score_3_inf?: number; score_3_sup?: number; score_3_label?: string;
  score_4_inf?: number; score_4_sup?: number; score_4_label?: string;
  score_5_inf?: number; score_5_sup?: number; score_5_label?: string;
}

/**
 * Payload for creating a Mesure
 */
export interface MesureCreatePayload {
  id_metrique: number;
  valeur: string;
  date_mesure?: string;
  commentaire?: string;
}

/**
 * Payload for creating an EtatActuel
 */
export interface EtatActuelCreatePayload {
  id_olt: number;
  libelle: string;
  description?: string;
}

/**
 * Payload for creating an ObjectifLongTerme
 */
export interface ObjectifLongTermeCreatePayload {
  id_enjeu: number;
  libelle: string;
  description?: string;
}

/**
 * Payload for creating a NiveauExigence
 */
export interface NiveauExigenceCreatePayload {
  id_olt: number;
  libelle: string;
  description?: string;
}

/**
 * Payload for creating an ENJEU
 */
export interface EnjeuCreatePayload {
  id_pg: number;
  id_categorie: number; // ID nomenclature "ENJEU"
  libelle: string;
  intitule_court?: string;
  rang: EnjeuPriorite;
  categorie_ecologique: boolean;
  habitat?: boolean;
  espece?: boolean;
  processus?: boolean;
  etat_enjeu?: string;
  description?: string;
  id_importance?: number;
  geom?: GeoJSONGeometry;
  // Taxonomic relations
  taxon_ids?: number[];
  habitat_ids?: string[];
  geologie_ids?: string[];
  taxons_data?: TaxonRef[];
  habitats_data?: HabitatRef[];
  geologies_data?: GeologieRef[];
}

/**
 * Payload for creating a FCR
 */
export interface FcrCreatePayload {
  id_pg: number;
  id_categorie: number; // ID nomenclature "FCR"
  libelle: string;
  intitule_court?: string;
  id_categorie_fcr: number;
  description?: string;
  // Taxonomic relations (optional for FCR)
  taxon_ids?: number[];
  habitat_ids?: string[];
}

/**
 * Payload for updating an Enjeu or FCR
 */
export interface EnjeuUpdatePayload {
  libelle?: string;
  intitule_court?: string;
  description?: string;
  rang?: EnjeuPriorite;
  categorie_ecologique?: boolean;
  habitat?: boolean;
  espece?: boolean;
  processus?: boolean;
  etat_enjeu?: string;
  id_categorie_fcr?: number;
  id_importance?: number;
  geom?: GeoJSONGeometry;
  taxon_ids?: number[];
  habitat_ids?: string[];
  geologie_ids?: string[];
  taxons_data?: TaxonRef[];
  habitats_data?: HabitatRef[];
  geologies_data?: GeologieRef[];
}

/**
 * Response from /enjeux/by-plan/{id}/ endpoint
 */
export interface PlanEnjeuxResponse {
  plan_id: number;
  plan_nom: string;
  plan_slug?: string;
  enjeux: Enjeu[];
  fcr: Enjeu[];
  total_enjeux: number;
  total_fcr: number;
}

/**
 * Enjeu statistics
 */
export interface EnjeuStats {
  total_enjeux: number;
  total_fcr: number;
  par_priorite: {
    priorite_1: number;
    priorite_2: number;
    priorite_3: number;
  };
  par_type: {
    habitat: number;
    espece: number;
    processus: number;
  };
}

/**
 * Filters for listing enjeux
 */
export interface EnjeuFilters {
  id_pg?: number;
  categorie?: EnjeuCategorie;
  is_enjeu?: boolean;
  is_fcr?: boolean;
  rang?: EnjeuPriorite;
  rang_min?: number;
  rang_max?: number;
  categorie_ecologique?: boolean;
  habitat?: boolean;
  espece?: boolean;
  processus?: boolean;
  categorie_fcr?: FcrCategorie;
  has_taxons?: boolean;
  has_habitats?: boolean;
  search?: string;
  page?: number;
}

/**
 * Paginated response for enjeux list
 */
export interface PaginatedEnjeuxResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Enjeu[];
}

// =============================================================================
// Responsabilites
// =============================================================================

/**
 * Type of responsibility
 */
export type ResponsabiliteType =
  | 'FLORISTIQUE'
  | 'FAUNISTIQUE'
  | 'HABITAT'
  | 'GEOLOGIQUE'
  | 'PAYSAGER';

/**
 * Level of responsibility
 */
export type ResponsabiliteNiveau = 'LOCAL' | 'REGIONAL' | 'NATIONAL' | 'INTERNATIONAL';

/**
 * Enjeu linked to a responsibility (simplified)
 */
export interface ResponsabiliteEnjeuLie {
  id_enjeu: number;
  libelle: string;
}

/**
 * Responsabilite - site responsibility
 */
export interface Responsabilite {
  id_responsabilite: number;
  id_site: number;
  site_nom?: string;

  // Type and level
  id_type_responsabilite: number;
  type_label?: string;
  id_niveau_responsabilite: number;
  niveau_label?: string;

  description?: string;

  // Taxonomic relations
  taxons?: TaxonRef[];
  habitats?: HabitatRef[];
  geologies?: GeologieRef[];
  enjeux_lies?: ResponsabiliteEnjeuLie[];

  // Counts
  nb_taxons?: number;
  nb_habitats?: number;
  nb_enjeux_lies?: number;

  // Audit
  date_ajout: string;
  date_maj: string;
  id_utilisateur_ajout?: number;
  createur_nom?: string;
}

/**
 * Payload for creating a Responsabilite
 */
export interface ResponsabiliteCreatePayload {
  id_site: number;
  id_type_responsabilite: number;
  id_niveau_responsabilite: number;
  description?: string;
  taxon_ids?: number[];
  habitat_ids?: string[];
  geologie_ids?: string[];
  enjeu_ids?: number[];
  taxons_data?: TaxonRef[];
  habitats_data?: HabitatRef[];
  geologies_data?: GeologieRef[];
}

/**
 * Response from /responsabilites/by-site/{id}/ endpoint
 */
export interface SiteResponsabilitesResponse {
  site_id: number;
  site_nom: string;
  responsabilites: Responsabilite[];
  total: number;
}

/**
 * Responsabilite statistics
 */
export interface ResponsabiliteStats {
  total: number;
  par_type: Record<string, number>;
  par_niveau: Record<string, number>;
}
