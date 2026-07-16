/**
 * Models for Enjeux (conservation issues) and FCR (Key Success Factors)
 */
import { OperationRHLigne } from './rh.model';

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
  id_rang?: string;
}

/**
 * Habitat reference from HabRef
 */
export interface HabitatRef {
  id?: number;
  /** Code HabRef. Vide/null pour un habitat saisi librement (hors référentiel, #368). */
  cd_hab?: string | null;
  lb_hab_fr?: string;
  /** Code propre dans la typologie d'origine (ex. « G1.6 »). #89 */
  lb_code?: string;
  /** Typologie d'origine (ex. « EUNIS »). #89 */
  lb_typo?: string;
  /** Nom complet (avec auteur). #89 */
  lb_hab_fr_complet?: string;
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
 * #237 — Objet géologique sélectionné sur un enjeu.
 * `id_objet_geologique` référence une nomenclature TYPE_OBJET_GEOLOGIQUE ;
 * `code`/`libelle` sont dénormalisés (lecture seule, depuis la nomenclature) ;
 * `precision` est une saisie libre pour un objet de type « Autre ».
 */
export interface ObjetGeologiqueRef {
  id?: number;
  id_objet_geologique?: number;
  code?: string;
  libelle?: string;
  precision?: string;
}

/**
 * #237 — Document du patrimoine « Documents » d'un enjeu géologique.
 * `support='numerique'` → fichier téléversé ; `support='papier'` → référence.
 */
export interface EnjeuDocument {
  id: number;
  id_enjeu?: number;
  support: 'numerique' | 'papier';
  nom_fichier?: string;
  titre?: string;
  description?: string;
  taille_fichier?: number | null;
  file_size_human?: string | null;
  extension?: string;
  url?: string | null;
  date_upload?: string;
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
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;

  // Enjeu-specific fields
  rang?: EnjeuPriorite;
  // Catégorie exclusive : true = conservation patrimoine naturel, false = socio-économique
  categorie_ecologique?: boolean;
  // Ecological checkboxes
  habitat: boolean;
  espece: boolean;
  patrimoine_geologique: boolean;
  geo_ex_situ: boolean;
  geo_in_situ: boolean;
  geo_documents: boolean;
  geo_autre: boolean;
  geo_autre_precision?: string;
  fonctionnalite_ecosysteme: boolean;
  autre_ecologique: boolean;
  autre_ecologique_precision?: string;
  processus: boolean; // legacy
  // Socio-economic checkboxes
  valeur_paysagere: boolean;
  patrimoine_culturel: boolean;
  developpement_durable: boolean;
  usages: boolean;
  valeur_ajoutee: boolean;
  autre_socioeco: boolean;
  autre_socioeco_precision?: string;
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
  objets_geologiques?: ObjetGeologiqueRef[];
  documents?: EnjeuDocument[];

  // Counts (from list serializer)
  nb_taxons?: number;
  nb_habitats?: number;
  nb_geologies?: number;

  // Facteurs d'influence (avec OO imbriqués)
  facteurs_influence?: FacteurInfluence[];
  nb_facteurs_influence?: number;

  // #552 — Ordre des OO propre à CET enjeu ({id_oo: ordre}). Un OO partagé
  // entre plusieurs enjeux peut y être ordonné différemment ; un OO absent du
  // map retombe sur son `ordre` global.
  oo_ordre?: Record<number, number>;

  // Objectifs à long terme (avec NE imbriqués)
  objectifs_long_terme?: ObjectifLongTerme[];
  nb_objectifs_long_terme?: number;

  // #337 — Objectifs opérationnels rattachés directement (cas FCR, sans pression)
  objectifs_operationnels?: ObjectifOperationnel[];
  nb_objectifs_operationnels?: number;

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
  id_type_pression?: number;
  pressref_code?: string;
  pressref_label?: string;
  pressref_definition?: string;
  libelle: string;
  description?: string;
  objectifs_operationnels?: ObjectifOperationnel[];
  nb_objectifs_operationnels?: number;
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
  /**
   * #552 — Identifiants de TOUS les enjeux sous lesquels ce facteur est partagé
   * (M2M CorFacteurEnjeu). Longueur > 1 ⇒ élément lié : toute modification se
   * répercute partout.
   */
  enjeu_ids?: number[];
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
  id_type_pression?: number;
  libelle: string;
  description?: string;
}

/**
 * Objectif à Long Terme (OLT) rattaché directement à un enjeu.
 * Hiérarchie : Enjeu → OLT → NiveauExigence.
 */
export interface ObjectifLongTerme {
  id_olt: number;
  id_enjeu: number;
  libelle: string;
  description?: string;
  /** #442 — Numéro global fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
  niveaux_exigence?: NiveauExigence[];
  nb_niveaux_exigence?: number;
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
 * Pression légère pour affichage dans un OO (M2M)
 */
export interface PressionLight {
  id_pression: number;
  libelle: string;
  facteur_influence_libelle?: string;
}

/**
 * Objectif Opérationnel (OO)
 */
export interface ObjectifOperationnel {
  id_oo: number;
  pressions: PressionLight[];
  pression_ids: number[];
  // #337 — rattachement direct à un enjeu/FCR (sans pression). null pour les OO classiques.
  id_enjeu?: number | null;
  libelle: string;
  description?: string;
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
  /**
   * #552 — Numéro d'affichage plan-wide, identique sous tous les enjeux où l'OO
   * est partagé (calculé par le back à la première rencontre). Fourni par
   * l'endpoint by-plan ; absent des réponses plates → repli sur la
   * numérotation par enjeu.
   */
  numero_affichage?: number | null;
  /**
   * #552 — Identifiants des enjeux sous lesquels cet OO est partagé (via ses
   * pressions M2M et/ou rattachement direct FCR). Longueur > 1 ⇒ élément lié.
   */
  shared_enjeu_ids?: number[];
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
  type_indicateur_mnemonique?: string;
  est_standardise: boolean;
  metriques?: Metrique[];
  nb_metriques?: number;
  // #367 — actions rattachées directement à l'indicateur (sans métrique)
  operations?: Operation[];
  taxons?: TaxonRef[];
  habitats?: HabitatRef[];
  geologies?: GeologieRef[];
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
  // #420 — slug de l'enjeu, pour le deep-link « Modifier l'indicateur »
  enjeu_slug?: string | null;
  // #518 — scores forcés manuellement par année (clé = année, valeur = score 1..5).
  // Le tableau de bord les affiche en priorité sur le calcul automatique.
  score_overrides?: Record<string, number>;
  // #518 — évaluation globale forcée manuellement (#356) : score 1..5 ou null.
  // Prime sur le calcul « état courant » dans la colonne « Global » du tableau de bord.
  global_score_override?: number | null;
}

/**
 * Bloc de scoring complémentaire d'une métrique numérique (#247).
 *
 * Même structure qu'un bloc principal : 5 paliers, sens de variation,
 * inclusivités, bornes extrêmes optionnelles. Les blocs sont combinés au
 * principal (et entre eux) via `logical_op` (OR par défaut, AND aussi).
 *
 * Parenthésage explicite via `group_open` / `group_close` pour gérer la
 * précédence ET/OU sur 3+ blocs.
 * Exemple : (B1 OR B2) AND (B3 OR B4) →
 *   B1{open=1,close=0,op=null}, B2{open=0,close=1,op=OR},
 *   B3{open=1,close=0,op=AND}, B4{open=0,close=1,op=OR}.
 */
export interface MetriqueScoreBlock {
  id_score_block?: number;          // undefined = nouveau, number = existant
  position: number;                 // ordre du bloc parmi les complémentaires (1-N)
  intitule?: string | null;         // intitulé du bloc (ex: recouvrement)
  unite?: string | null;            // unité du bloc (optionnelle, ex: %, m)
  logical_op: 'OR' | 'AND';         // combinaison avec le bloc précédent
  group_open: number;               // nombre de '(' à ouvrir avant ce bloc
  group_close: number;              // nombre de ')' à fermer après ce bloc
  sens_variation: 'CROISSANT' | 'DECROISSANT';
  score_1_inf: number | null; score_1_sup: number | null;
  score_2_inf: number | null; score_2_sup: number | null;
  score_3_inf: number | null; score_3_sup: number | null;
  score_4_inf: number | null; score_4_sup: number | null;
  score_5_inf: number | null; score_5_sup: number | null;
  score_1_sup_inclusive: boolean;
  score_2_sup_inclusive: boolean;
  score_3_sup_inclusive: boolean;
  score_4_sup_inclusive: boolean;
  score_5_sup_inclusive?: boolean;
  has_borne_score1: boolean;
  has_borne_score5: boolean;
  inactive_levels?: number[];       // paliers désactivés (1..5)
  // Lettre stable affichée dans la formule (A, B, C, …). Reste attachée au
  // bloc à travers les drag-and-drop. Frontend uniquement — réassignée à
  // chaque chargement depuis l'ordre courant.
  _letter?: string;
}

/**
 * Métrique rattachée à un indicateur
 */
export interface Metrique {
  id_metrique: number;
  id_indicateur: number;
  nom_metrique: string;
  description?: string;
  ordre?: number;
  type_metrique?: number;
  type_metrique_label?: string;
  type_metrique_mnemonique?: string;
  // #452 — format de présentation (SIMPLE / GRILLE)
  format_metrique?: number;
  format_metrique_mnemonique?: string;
  unite?: string;
  // Intitulé du bloc principal quand la métrique combine plusieurs blocs (ex: hauteur)
  bloc_intitule?: string;
  ponderation?: number;
  etat_reference?: string;
  score_1_inf?: number; score_1_sup?: number; score_1_val?: number; score_1_label?: string;
  score_2_inf?: number; score_2_sup?: number; score_2_val?: number; score_2_label?: string;
  score_3_inf?: number; score_3_sup?: number; score_3_val?: number; score_3_label?: string;
  score_4_inf?: number; score_4_sup?: number; score_4_val?: number; score_4_label?: string;
  score_5_inf?: number; score_5_sup?: number; score_5_val?: number; score_5_label?: string;
  // Direction et inclusivité des bornes
  sens_variation?: 'CROISSANT' | 'DECROISSANT';
  score_1_sup_inclusive?: boolean;
  score_2_sup_inclusive?: boolean;
  score_3_sup_inclusive?: boolean;
  score_4_sup_inclusive?: boolean;
  score_5_sup_inclusive?: boolean;
  has_borne_score1?: boolean;
  has_borne_score5?: boolean;
  inactive_levels?: number[];
  // Parenthésage du bloc principal (#247 — symétrie avec MetriqueScoreBlock)
  group_open?: number;
  group_close?: number;
  score_blocks?: MetriqueScoreBlock[];  // #247
  mesures?: Mesure[];
  nb_mesures?: number;
  operations?: Operation[];
  nb_operations?: number;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Mesure datée rattachée à une métrique
 */
/**
 * Saisie annuelle au niveau Indicateur (override manuel du score auto).
 */
export interface IndicateurMesure {
  id_indicateur_mesure?: number;
  id_indicateur: number;
  annee: number;
  score_override?: number | null;     // 1-5
  commentaire_override?: string | null;
  date_ajout?: string;
  date_maj?: string;
  id_utilisateur_maj?: number | null;
}

export interface IndicateurAutoScoreResponse {
  id_indicateur: number;
  annee: number;
  score: number | null;
  has_data: boolean;
  per_metrique: Array<{
    id_metrique: number;
    score: number | null;
    valeur: string | null;
    ponderation: number;
  }>;
}

export interface IndicateurResolvedResponse {
  id_indicateur: number;
  annee: number;
  // #424 — id de l'override (IndicateurMesure) pour pouvoir le supprimer
  id_indicateur_mesure?: number | null;
  score_auto: number | null;
  score_override: number | null;
  commentaire_override: string | null;
  is_overridden: boolean;
  score_effective: number | null;
  per_metrique: Array<{
    id_metrique: number;
    score: number | null;
    valeur: string | null;
    ponderation: number;
  }>;
}

export interface Mesure {
  id_mesure: number;
  id_metrique: number;
  valeur: string;
  // #247 — valeurs des blocs de scoring complémentaires (métrique multi-blocs),
  // indexées par position de bloc. `valeur` = valeur du bloc principal.
  valeurs_blocs?: Record<string, string>;
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
  cd_protocole_campanule?: number;
  nb_etp_cycle?: number;
  nom_protocole?: string;
  respect_protocole?: boolean;
  justification_non_respect?: string;
  differences_protocole?: string;
  description_protocole?: string;
  objectif_protocole?: string;
  periode_echantillonnage?: string;
  mode_validation?: string;
  periode_suivi?: string;
  documentation_disponible?: boolean;
  url_documentation?: string;
  // Audit
  date_ajout?: string;
  date_maj?: string;
}

/**
 * Suivi / Inventaire lié à une opération
 */
export interface SuiviInventaire {
  id_suivi_inventaire?: number;
  intitule?: string;
  actif?: boolean;
  // Détails
  objectif_principal?: string;
  objectif_secondaire?: string;
  cibles_principales?: string;
  cible_secondaire?: string;
  taxon_taxref?: string;
  habitat_ref?: string;
  /** Habitats structurés [{cd_hab, lb_hab_fr}] — pour les correspondances. */
  habitats?: { cd_hab: string; lb_hab_fr?: string }[];
  date_lancement_suivi?: string;
  // Protocole (nested)
  protocole?: Protocole;
  // Bancarisation
  outil_bancarisation?: string;
  bancarisation_label?: string;
  outil_saisie?: string;
  outil_saisie_label?: string;
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
 * Suivi de réalisation ventilé par organisme (1-1 avec OperationAnneeOrganisme).
 */
export interface RealisationOperationAnneeOrganisme {
  id_realisation_op_annee_organisme?: number;
  id_operation_annee_organisme: number;
  budget_fonctionnement_realise: number | null;
  budget_investissement_realise: number | null;
  etp_realise: number | null;
  date_ajout?: string;
  date_maj?: string;
}

/**
 * Suivi de réalisation annuel (1-1 avec OperationAnnee).
 */
export interface RealisationOperationAnnee {
  id_realisation_operation_annee?: number;
  id_operation_annee: number;
  id_niveau_realisation?: number | null;
  niveau_realisation_label?: string;
  niveau_realisation_mnemonique?: string;
  periodicite_realisee: boolean;
  periodicite_mensuelle_realisee?: Record<string, boolean>;
  commentaires?: string | null;
  geom_realisee?: GeoJSONGeometry | null;
  budget_realise?: number | null;
  budget_fonctionnement_realise?: number | null;
  budget_investissement_realise?: number | null;
  etp_realise?: number | null;
  // #541 — opérateur(s)/financeur(s) réalisés, saisis par année dans le suivi.
  operateurs_realises?: string | null;
  financeurs_realises?: string | null;
  // #560 — lignes RH réalisées (personne/fonction × jours × financé).
  rh_lignes?: OperationRHLigne[];
  date_ajout?: string;
  date_maj?: string;
  id_utilisateur_maj?: number | null;
}

/**
 * Ventilation budget/travail par organisme pour une année d'opération
 */
export interface OperationAnneeOrganisme {
  id_operation_annee_organisme?: number;
  id_organisme: number;
  organisme_nom?: string;
  budget_fonctionnement: number | null;
  budget_investissement: number | null;
  etp: number | null;
  realisation?: RealisationOperationAnneeOrganisme | null;
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
  budget_fonctionnement?: number | null;
  budget_investissement?: number | null;
  periodicite_mensuelle: Record<string, boolean>;
  geom?: GeoJSONGeometry;
  organismes?: OperationAnneeOrganisme[];
  // #560 — lignes RH prévisionnelles (personne/fonction × jours × financé).
  rh_lignes?: OperationRHLigne[];
  realisation?: RealisationOperationAnnee | null;
}

/**
 * Payload d'upsert d'une réalisation annuelle (envoi formulaire de saisie).
 */
export interface RealisationUpsertPayload {
  id_operation_annee?: number;
  // #418 — saisie d'un suivi pour une année NON planifiée : le backend crée
  // l'OperationAnnee à la volée à partir de (id_operation, annee).
  id_operation?: number;
  annee?: number;
  id_niveau_realisation?: number | null;
  periodicite_realisee?: boolean;
  periodicite_mensuelle_realisee?: Record<string, boolean>;
  commentaires?: string | null;
  budget_realise?: number | null;
  budget_fonctionnement_realise?: number | null;
  budget_investissement_realise?: number | null;
  etp_realise?: number | null;
  // #541 — opérateur(s)/financeur(s) réalisés (par année).
  operateurs_realises?: string | null;
  financeurs_realises?: string | null;
  // #560 — lignes RH réalisées (remplacement complet à chaque upsert).
  rh_lignes?: OperationRHLigne[];
  /** Emprise spatiale réalisée (GeoJSON), null pour effacer. */
  geom_realisee?: GeoJSONGeometry | null;
}

/**
 * Payload d'upsert d'une réalisation ventilée par organisme.
 */
export interface RealisationOrganismeUpsertPayload {
  id_operation_annee_organisme: number;
  budget_fonctionnement_realise?: number | null;
  budget_investissement_realise?: number | null;
  etp_realise?: number | null;
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

export interface MetriqueRef {
  id_metrique: number;
  nom_metrique: string;
  indicateur_id: number;
  indicateur_nom: string;
  /** Type de l'indicateur parent (ETAT / PRESSION / REPONSE). Distingue les
   *  indicateurs de réponse des métriques associées (état/pression). */
  indicateur_type?: string | null;
  etat_reference?: string;
  type_metrique_id?: number | null;
  type_metrique_label?: string | null;
  // #452 — unité et pondération de la métrique (éditées dans la grille d'un
  // indicateur de réponse), exposées par le backend pour ré-affichage et save.
  unite?: string | null;
  ponderation?: number | string | null;
  // #452 — format + grille de scoring (exposés par le backend pour les
  // métriques d'indicateur de réponse, afin d'alimenter une saisie/visu
  // type-aware et l'éditeur de grille).
  format_metrique_id?: number | null;
  format_metrique_mnemonique?: string | null;
  type_metrique_mnemonique?: string | null;
  sens_variation?: 'CROISSANT' | 'DECROISSANT';
  has_borne_score1?: boolean;
  has_borne_score5?: boolean;
  inactive_levels?: number[];
  score_1_inf?: number | null; score_1_sup?: number | null; score_1_val?: number | null; score_1_label?: string | null;
  score_2_inf?: number | null; score_2_sup?: number | null; score_2_val?: number | null; score_2_label?: string | null;
  score_3_inf?: number | null; score_3_sup?: number | null; score_3_val?: number | null; score_3_label?: string | null;
  score_4_inf?: number | null; score_4_sup?: number | null; score_4_val?: number | null; score_4_label?: string | null;
  score_5_inf?: number | null; score_5_sup?: number | null; score_5_val?: number | null; score_5_label?: string | null;
  score_1_sup_inclusive?: boolean;
  score_2_sup_inclusive?: boolean;
  score_3_sup_inclusive?: boolean;
  score_4_sup_inclusive?: boolean;
  score_5_sup_inclusive?: boolean;
  // #247/#452 — bloc principal (intitulé + parenthésage) et blocs de scoring
  // complémentaires (ET/OU) d'une métrique de réponse NUMERIQUE en grille,
  // exposés par le backend pour alimenter l'éditeur multi-blocs et les visus.
  bloc_intitule?: string | null;
  group_open?: number;
  group_close?: number;
  score_blocks?: MetriqueScoreBlock[];
}

export type OperationStatut = 'draft' | 'valide';

export interface Operation {
  id_operation: number;
  libelle: string;
  /** #251 — Brouillon tant que la validation complète n'a pas été déclenchée. */
  statut?: OperationStatut;
  id_priorite?: number;
  priorite_label?: string;
  id_type_action?: number;
  type_action_label?: string;
  // #228 — Catégorie d'action réserve CT88 (optionnel)
  id_categorie_action_reserve?: number | null;
  categorie_action_reserve_label?: string;
  categorie_action_reserve_code?: string;
  // Code calculé : préfixe 2 lettres + rang dans le plan (CS1, IP2, ...)
  code_prefix?: string;
  code_affichage?: string;
  /** #485 — Numéro fixé manuellement dans le code (null = numérotation automatique). */
  numero_manuel?: number | null;
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
  ventilation_mode?: 'none' | 'by_org' | 'by_type' | 'by_org_type';
  /** #560 — détaille le temps de travail poste par poste. */
  declinaison_par_poste?: boolean;
  geom?: GeoJSONGeometry | string;
  geom_geojson?: GeoJSONGeometry | null;
  // M2M to Metriques
  metriques?: MetriqueRef[];
  metrique_ids?: number[];
  site_ids?: number[];
  nb_sites?: number;
  /** #531 — slug de l'enjeu parent (via les métriques), pour naviguer vers la
   *  position de l'action dans l'architecture du plan depuis la fiche action. */
  enjeu_slug?: string | null;
  // Nested relational data
  operation_annees?: OperationAnnee[];
  finances?: FinanceOperation[];
  // #355 — Niveau de réalisation GLOBAL (sur la période) : surcharge sinon calcul auto
  niveau_realisation_global_mnemonique?: string | null;
  niveau_realisation_global_label?: string | null;
  niveau_realisation_global_manuel?: boolean;
  niveau_realisation_global_commentaire?: string | null;
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Payload for creating an Operation
 */
export interface OperationCreatePayload {
  libelle: string;
  /** #251 — Statut envoyé selon le bouton utilisé : 'valide' pour Valider, 'draft' pour Enregistrer. */
  statut?: OperationStatut;
  /** Emprise spatiale en GeoJSON (#342). null = effacement. */
  geom_geojson?: any | null;
  id_priorite?: number;
  id_type_action?: number;
  // #367 — rattachement direct à un indicateur (action sans métrique préalable)
  id_indicateur?: number | null;
  // #228 — Catégorie d'action réserve CT88 (optionnel)
  id_categorie_action_reserve?: number | null;
  id_referentiel_operations?: string;
  code_operation?: string;
  /** #485 — Numéro fixé manuellement dans le code (null = numérotation automatique). */
  numero_manuel?: number | null;
  description?: string;
  annee_min?: number;
  annee_max?: number;
  // Suivi/inventaire
  est_suivi_existant?: boolean;
  id_suivi?: number;
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
  ventilation_mode?: 'none' | 'by_org' | 'by_type' | 'by_org_type';
  /** #560 — détaille le temps de travail poste par poste. */
  declinaison_par_poste?: boolean;
  metrique_ids?: number[];
  site_ids?: number[];
  // Nested relational data
  operation_annees?: Omit<OperationAnnee, 'id_operation_annee'>[];
  finances?: Omit<FinanceOperation, 'id_finance_operation' | 'categorie_label'>[];
}

/**
 * Form data for a metrique within the unified indicateur creation form
 */
export interface MetriqueFormData {
  id_metrique?: number;  // undefined = new, number = existing
  nom_metrique: string;
  type_metrique: number | null;
  // #452 — format de présentation (id nomenclature FORMAT_METRIQUE : SIMPLE / GRILLE).
  // Pertinent pour les indicateurs de réponse ; null/SIMPLE = saisie d'une valeur libre.
  format_metrique?: number | null;
  unite: string;
  // Intitulé du bloc principal (utilisé quand la métrique combine plusieurs blocs).
  bloc_intitule: string;
  ponderation: number | null;
  etat_reference: string;
  /** #4 — Ordre d'affichage parmi les métriques d'un indicateur (réordonnancement DnD). */
  ordre?: number;
  scores: { [level: number]: { inf: number | null; sup: number | null; val: number | null; label: string } };
  // Direction et inclusivité des bornes (NUMERIQUE only)
  sens_variation: 'CROISSANT' | 'DECROISSANT';
  score_1_sup_inclusive: boolean;
  score_2_sup_inclusive: boolean;
  score_3_sup_inclusive: boolean;
  score_4_sup_inclusive: boolean;
  score_5_sup_inclusive?: boolean;
  has_score1_optional_bound: boolean;  // checkbox: borne extrême score 1 (inf si croissant, sup si décroissant)
  has_score5_optional_bound: boolean;  // checkbox: borne extrême score 5 (sup si croissant, inf si décroissant)
  // Liste des niveaux désactivés via le tag « Niveaux actifs » du nouveau composant
  // de saisie. Côté API on stocke `null` sur les bornes correspondantes — ce champ
  // sert uniquement à mémoriser l'intention de l'utilisateur pendant l'édition.
  _inactiveLevels?: number[];
  // Parenthésage du bloc principal (#247) — le principal participe désormais
  // aux groupes au même titre qu'un bloc complémentaire.
  group_open?: number;
  group_close?: number;
  // Lettre stable du bloc principal (cf. MetriqueScoreBlock._letter).
  _letter?: string;
  // #247 — Intervalles complémentaires (OR/AND avec l'intervalle principal du même palier).
  // À la sauvegarde, la liste complète est envoyée au backend (le serializer remplace).
  score_blocks?: MetriqueScoreBlock[];
  // État UI (#2) : déplié dans le formulaire d'édition d'indicateur. Par défaut
  // une métrique existante est repliée (affichage compact) ; une métrique
  // nouvellement ajoutée s'ouvre dépliée.
  _expanded?: boolean;
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
  // #337 — un OO est rattaché soit à des pressions (Enjeu), soit à un enjeu (FCR)
  pression_ids?: number[];
  id_enjeu?: number;
  libelle: string;
  description?: string;
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
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
  ordre?: number;
  type_metrique?: number;
  // #452 — format de présentation (id nomenclature FORMAT_METRIQUE)
  format_metrique?: number | null;
  unite?: string | null;
  bloc_intitule?: string | null;
  ponderation?: number;
  etat_reference?: string;
  score_1_inf?: number; score_1_sup?: number; score_1_val?: number; score_1_label?: string;
  score_2_inf?: number; score_2_sup?: number; score_2_val?: number; score_2_label?: string;
  score_3_inf?: number; score_3_sup?: number; score_3_val?: number; score_3_label?: string;
  score_4_inf?: number; score_4_sup?: number; score_4_val?: number; score_4_label?: string;
  score_5_inf?: number; score_5_sup?: number; score_5_val?: number; score_5_label?: string;
  // Direction et inclusivité des bornes
  sens_variation?: 'CROISSANT' | 'DECROISSANT';
  score_1_sup_inclusive?: boolean;
  score_2_sup_inclusive?: boolean;
  score_3_sup_inclusive?: boolean;
  score_4_sup_inclusive?: boolean;
  score_5_sup_inclusive?: boolean;
  has_borne_score1?: boolean;
  has_borne_score5?: boolean;
  inactive_levels?: number[];
  group_open?: number;
  group_close?: number;
  // #247 — Intervalles complémentaires (envoyés en bloc, remplacement intégral côté serveur)
  score_blocks?: MetriqueScoreBlock[];
}

/**
 * Payload for creating a Mesure
 */
export interface MesureCreatePayload {
  id_metrique: number;
  valeur: string;
  // #247 — valeurs des blocs complémentaires (métrique multi-blocs), par position.
  valeurs_blocs?: Record<string, string>;
  date_mesure?: string;
  commentaire?: string;
}

/**
 * Payload for creating an ObjectifLongTerme
 */
export interface ObjectifLongTermeCreatePayload {
  id_enjeu: number;
  libelle: string;
  description?: string;
  /** #442 — Numéro global fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
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
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
  rang: EnjeuPriorite;
  categorie_ecologique: boolean;
  // Ecological checkboxes
  habitat?: boolean;
  espece?: boolean;
  patrimoine_geologique?: boolean;
  geo_ex_situ?: boolean;
  geo_in_situ?: boolean;
  geo_documents?: boolean;
  geo_autre?: boolean;
  geo_autre_precision?: string;
  fonctionnalite_ecosysteme?: boolean;
  autre_ecologique?: boolean;
  autre_ecologique_precision?: string;
  processus?: boolean;
  // Socio-economic checkboxes
  valeur_paysagere?: boolean;
  patrimoine_culturel?: boolean;
  developpement_durable?: boolean;
  usages?: boolean;
  valeur_ajoutee?: boolean;
  autre_socioeco?: boolean;
  autre_socioeco_precision?: string;
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
  objets_geologiques_data?: ObjetGeologiqueRef[];
}

/**
 * Payload for creating a FCR
 */
export interface FcrCreatePayload {
  id_pg: number;
  id_categorie: number; // ID nomenclature "FCR"
  libelle: string;
  intitule_court?: string;
  // #479 — priorité facultative pour les FCR (null = « non définie »)
  rang?: EnjeuPriorite | null;
  id_categorie_fcr: number;
  description?: string;
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
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
  /** #526 — Numéro fixé manuellement (null = numérotation automatique). */
  numero_manuel?: number | null;
  rang?: EnjeuPriorite | null;
  categorie_ecologique?: boolean;
  // Ecological checkboxes
  habitat?: boolean;
  espece?: boolean;
  patrimoine_geologique?: boolean;
  geo_ex_situ?: boolean;
  geo_in_situ?: boolean;
  geo_documents?: boolean;
  geo_autre?: boolean;
  geo_autre_precision?: string;
  fonctionnalite_ecosysteme?: boolean;
  autre_ecologique?: boolean;
  autre_ecologique_precision?: string;
  processus?: boolean;
  // Socio-economic checkboxes
  valeur_paysagere?: boolean;
  patrimoine_culturel?: boolean;
  developpement_durable?: boolean;
  usages?: boolean;
  valeur_ajoutee?: boolean;
  autre_socioeco?: boolean;
  autre_socioeco_precision?: string;
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
  objets_geologiques_data?: ObjetGeologiqueRef[];
}

/**
 * Response from /enjeux/by-plan/{id}/ endpoint
 */
export interface PlanEnjeuxResponse {
  plan_id: number;
  plan_nom: string;
  plan_slug?: string;
  /** Statut du plan : utilisé pour verrouiller l'édition hors brouillon (#248). */
  plan_statut?: 'draft' | 'valide' | 'archive';
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
