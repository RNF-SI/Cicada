/**
 * Models for CAMPanule protocol reference data.
 */

/**
 * Autocomplete result for a CAMPanule protocol
 */
export interface CampanuleAutocomplete {
  cd_protocole: number;
  search_name: string;
  lb_protocole_court: string;
  lb_protocole_complet?: string;
  cible?: string;
  categorie_prot?: string;
  prot_auteur?: string;
}

/**
 * Plan d'échantillonnage
 */
export interface CampanuleEchantillonnage {
  cd_prot_echantillonnage: number;
  cd_protocole: number;
  unite?: string;
  nb_unite?: string;
  duree?: string;
  taille?: string;
  passages_an?: string;
  periode_an?: string;
  plan_ech?: string;
  commentaire?: string;
  niveau?: string;
}

/**
 * Méthode associée à un protocole
 */
export interface CampanuleMethode {
  cd_methode: number;
  lb_methode_court?: string;
  lb_methode_complet?: string;
  descr_methode?: string;
}

/**
 * Technique associée à un protocole
 */
export interface CampanuleTechnique {
  cd_technique: number;
  lb_technique_fr?: string;
  lb_tech_complet_fr?: string;
  descr_technique?: string;
  categorie_tech?: string;
}

/**
 * Full detail of a CAMPanule protocol
 */
export interface CampanuleProtocoleDetail {
  cd_protocole: number;
  lb_protocole_court: string;
  lb_protocole_complet?: string;
  lb_protocole_en?: string;
  description?: string;
  cible?: string;
  categorie_prot?: string;
  prot_auteur?: string;
  descr_cible_prot?: string;
  descr_objectif_prot?: string;
  date_publi?: string;
  version?: string;
  obsolete?: string;
  url_perm?: string;
  url?: string;
  url_complementaire?: string;
  echelle_restit?: string;
  saisie?: string;
  biologie?: string;
  abiotique?: string;
  nature_donnees?: string;
  analyse_reference?: string;
  guide_sinp_donnees?: string;
  norme?: string;
  indicateur?: string;
  uuid?: string;
  // Nested
  echantillonnages?: CampanuleEchantillonnage[];
  methodes?: CampanuleMethode[];
  techniques?: CampanuleTechnique[];
}
