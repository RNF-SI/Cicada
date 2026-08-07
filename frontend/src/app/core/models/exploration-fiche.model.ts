/**
 * Fiche publique d'un plan de gestion (`/exploration/plans/:slug`).
 *
 * Reflet exact de `apps/search/serializers_fiche.py` : la structure du plan,
 * sans budget, ressources humaines, mesures ni réalisations. Si un champ manque
 * ici, c'est qu'il n'est pas publié — et c'est volontaire.
 */

export interface FicheTaxon {
  cd_nom: number;
  nom_complet: string;
  nom_vern: string | null;
}

export interface FicheHabitat {
  cd_hab: string;
  lb_hab_fr: string | null;
}

/**
 * Palier de la grille de lecture d'une métrique : ce qui fait qu'une mesure
 * vaut « bon » plutôt que « moyen ». Le barème est publié, jamais les mesures.
 */
export interface FichePalier {
  niveau: 1 | 2 | 3 | 4 | 5;
  libelle: string;
  valeur: string | null;
}

export interface FicheMetrique {
  id_metrique: number;
  nom_metrique: string;
  unite: string | null;
  description: string | null;
  /** `null` quand la métrique n'a pas de grille de lecture (#634). */
  grille: FichePalier[] | null;
}

export interface FicheIndicateur {
  id_indicateur: number;
  nom_indicateur: string;
  description: string | null;
  type_indicateur: string | null;
  est_standardise: boolean;
  metriques: FicheMetrique[];
}

export interface FicheNiveauExigence {
  id_ne: number;
  libelle: string;
  description: string | null;
  indicateurs: FicheIndicateur[];
}

export interface FicheObjectifLongTerme {
  id_olt: number;
  libelle: string;
  description: string | null;
  niveaux_exigence: FicheNiveauExigence[];
}

export interface FicheResultatAttendu {
  id_ra: number;
  libelle: string;
  description: string | null;
  indicateurs: FicheIndicateur[];
}

export interface FicheObjectifOperationnel {
  id_oo: number;
  libelle: string;
  description: string | null;
  resultats_attendus: FicheResultatAttendu[];
}

export interface FichePression {
  id_pression: number;
  libelle: string;
  description: string | null;
  type_pression: string | null;
}

export interface FicheFacteur {
  id_facteur_influence: number;
  libelle: string;
  description: string | null;
  pressions: FichePression[];
}

export interface FicheEnjeu {
  id_enjeu: number;
  libelle: string;
  intitule_court: string | null;
  description: string | null;
  etat_enjeu: string | null;
  rang: number | null;
  categorie: string | null;
  categorie_ecologique: boolean | null;
  taxons: FicheTaxon[];
  habitats: FicheHabitat[];
  facteurs: FicheFacteur[];
  objectifs_long_terme: FicheObjectifLongTerme[];
  objectifs_operationnels: FicheObjectifOperationnel[];
}

/** Métrique suivie par une action, dans le cadre de celle-ci. */
export interface FicheActionMetrique {
  id_metrique: number;
  nom_metrique: string;
  unite: string | null;
}

/** Protocole d'un suivi : comment la donnée est collectée. */
export interface FicheProtocole {
  id_protocole: number;
  /** Issu du catalogue CAMPanule, par opposition à une saisie libre. */
  standardise: boolean | null;
  nom: string | null;
  description: string | null;
  objectif: string | null;
  /** `false` = appliqué avec des écarts, que `differences` détaille. */
  respecte: boolean | null;
  justification_non_respect: string | null;
  differences: string | null;
  periode_echantillonnage: string | null;
  /** Mois de suivi, déjà traduits en libellés par l'API. */
  periode_suivi: string[];
  mode_validation: string | null;
  documentation_disponible: boolean | null;
  url_documentation: string | null;
}

/** Habitat ciblé par un suivi ; `cd_hab` est nul pour un habitat hors HabRef. */
export interface FicheSuiviHabitat {
  cd_hab: string | null;
  lb_hab_fr: string | null;
}

/** Suivi ou inventaire porté par une action : ce qui est observé, et comment. */
export interface FicheSuivi {
  id_suivi: number;
  intitule: string;
  statut: string | null;
  actif: boolean;
  objectif_principal: string | null;
  objectif_secondaire: string | null;
  cible_principale: string | null;
  cible_secondaire: string | null;
  /** Espèce ciblée (TaxRef). */
  taxon: string | null;
  habitats: FicheSuiviHabitat[];
  frequence: string | null;
  annee_fin_suivi: number | null;
  date_lancement: string | null;
  outil_saisie: string | null;
  outil_bancarisation: string | null;
  transmission_donnee: boolean | null;
  commentaires: string | null;
  protocoles: FicheProtocole[];
}

/** Site couvert par une action. */
export interface FicheActionSite {
  id_site: number;
  nom_site: string;
  slug: string;
}

/** Action de gestion : ce qui est prévu, jamais ce que ça coûte. */
export interface FicheAction {
  id_operation: number;
  libelle: string;
  code_operation: string | null;
  description: string | null;
  categorie: string | null;
  type_action: string | null;
  priorite: string | null;
  annee_min: number | null;
  annee_max: number | null;
  frequence: string | null;
  operateurs: string | null;
  partenaires: string | null;
  sites: FicheActionSite[];
  /** Indicateur servi par l'action : la rattache à l'arborescence (#634). */
  id_indicateur: number | null;
  /** Indicateur d'état ou de pression ; les indicateurs de réponse sont à part. */
  indicateur: string | null;
  metriques: FicheActionMetrique[];
  /** Ce qui mesure l'effet de l'action, avec métriques et grille (#626). */
  indicateurs_reponse: FicheIndicateur[];
  suivi: FicheSuivi | null;
}

export interface FicheSite {
  id_site: number;
  nom_site: string;
  slug: string;
  type_site: string | null;
}

export interface FichePlan {
  id_pg: number;
  nom: string;
  slug: string;
  statut: string;
  rang: number;
  annee_debut: number | null;
  annee_fin: number | null;
  surface: string | null;
  type_document: string | null;
  sites: FicheSite[];
  gestionnaire_principal: string | null;
  enjeux: FicheEnjeu[];
  actions: FicheAction[];
}
