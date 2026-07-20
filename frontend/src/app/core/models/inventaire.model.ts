/**
 * Models for Suivis/Inventaires (standalone module).
 */

import { Protocole } from './enjeu.model';

/**
 * Suivi/Inventaire - lightweight for list display
 */
export interface SuiviInventaireList {
  id_suivi_inventaire: number;
  intitule: string;
  date_lancement_suivi?: string;
  annee_fin_suivi?: number;
  id_statut?: number;
  statut_label?: string;
  id_type_action?: number;
  type_action_code?: string;
  type_action_label?: string;
  actif: boolean;
  nb_operations: number;
  id_pg?: number;
  plan_nom?: string;
  sites_list?: string | null;
  date_ajout: string;
  date_maj: string;
}

/**
 * Suivi/Inventaire - full detail
 */
export interface SuiviInventaireDetail {
  id_suivi_inventaire: number;
  // Standalone fields
  intitule: string;
  id_type_action?: number;
  type_action_code?: string;
  type_action_label?: string;
  integre_plan_gestion?: boolean;
  suit_indicateur?: boolean;
  type_indicateur?: string;
  id_pg?: number;
  plan_nom?: string;
  cible_secondaire?: string;
  habitat_ref?: string;
  /** Habitats structurés [{cd_hab, lb_hab_fr}] — pour les correspondances. */
  habitats?: { cd_hab: string; lb_hab_fr?: string }[];
  id_statut?: number;
  statut_label?: string;
  actif: boolean;
  annee_fin_suivi?: number;
  frequence_nombre?: number;
  frequence_unite?: string;
  frequence_unite_precision?: string;
  commentaires?: string;
  // Original fields
  objectif_principal?: string;
  objectif_secondaire?: string;
  cibles_principales?: string;
  taxon_taxref?: string;
  date_lancement_suivi?: string;
  // Protocoles (#252) — `protocole` = premier de la liste, déprécié
  protocoles?: Protocole[];
  protocole?: Protocole;
  // Bancarisation
  outil_bancarisation?: string;
  bancarisation_label?: string;
  outil_saisie?: string;
  outil_saisie_label?: string;
  transmission_donnee?: boolean;
  // Computed
  nb_operations: number;
  // Audit
  date_ajout: string;
  date_maj: string;
  createur_nom?: string;
}

/**
 * Payload for creating/updating a suivi/inventaire
 */
export interface SuiviInventaireCreatePayload {
  intitule: string;
  id_type_action: number;
  integre_plan_gestion?: boolean;
  suit_indicateur?: boolean;
  type_indicateur?: string;
  id_pg?: number;
  cible_secondaire?: string;
  habitat_ref?: string;
  /** Habitats structurés [{cd_hab, lb_hab_fr}] — pour les correspondances. */
  habitats?: { cd_hab: string; lb_hab_fr?: string }[];
  id_statut?: number;
  actif?: boolean;
  annee_fin_suivi?: number;
  frequence_nombre?: number;
  frequence_unite?: string;
  frequence_unite_precision?: string;
  commentaires?: string;
  // Original fields
  objectif_principal?: string;
  objectif_secondaire?: string;
  cibles_principales?: string;
  taxon_taxref?: string;
  date_lancement_suivi?: string;
  // Protocoles (nested writable, #252) — `protocole` singulier déprécié
  protocoles?: Omit<Protocole, 'id_protocole' | 'date_ajout' | 'date_maj'>[];
  protocole?: Omit<Protocole, 'id_protocole' | 'date_ajout' | 'date_maj'>;
  // Bancarisation
  outil_bancarisation?: string;
  outil_saisie?: string;
  transmission_donnee?: boolean;
}

/**
 * Filters for listing suivis/inventaires
 */
export interface InventaireFilters {
  actif?: boolean;
  id_statut?: number;
  id_type_action?: number;
  type_action_prefix?: string;
  id_pg?: number;
  /** #358 — date de lancement minimale (YYYY-MM-DD) ; accepte aussi une année. */
  annee_min?: number | string;
  annee_max?: number;
  /** #358 — filtre par site (via les opérations du suivi). */
  site?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

/**
 * Paginated response for suivis/inventaires list
 */
export interface PaginatedInventairesResponse {
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
  results: SuiviInventaireList[];
}
