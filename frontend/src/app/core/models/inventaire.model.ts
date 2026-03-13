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
  annee_lancement_suivi?: number;
  annee_fin_suivi?: number;
  id_statut?: number;
  statut_label?: string;
  id_type_suivi?: number;
  type_label?: string;
  actif: boolean;
  nb_operations: number;
  id_pg?: number;
  plan_nom?: string;
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
  prix_indicatif?: number;
  id_type_suivi?: number;
  type_label?: string;
  integre_plan_gestion?: boolean;
  id_pg?: number;
  plan_nom?: string;
  cible_secondaire?: string;
  habitat_ref?: string;
  id_statut?: number;
  statut_label?: string;
  actif: boolean;
  annee_fin_suivi?: number;
  frequence_nombre?: number;
  frequence_unite?: string;
  commentaires?: string;
  // Original fields
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
  prix_indicatif?: number;
  id_type_suivi?: number;
  integre_plan_gestion?: boolean;
  id_pg?: number;
  cible_secondaire?: string;
  habitat_ref?: string;
  id_statut?: number;
  actif?: boolean;
  annee_fin_suivi?: number;
  frequence_nombre?: number;
  frequence_unite?: string;
  commentaires?: string;
  // Original fields
  objectif_principal?: string;
  cibles_principales?: string;
  taxon_taxref?: string;
  annee_lancement_suivi?: number;
  // Protocole (nested writable)
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
  id_type_suivi?: number;
  id_pg?: number;
  annee_min?: number;
  annee_max?: number;
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
