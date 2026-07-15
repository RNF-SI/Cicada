/**
 * Modèles pour la gestion des ressources humaines des plans de gestion (#560) :
 * référentiel de fonctions/postes, personnes rattachées à un PG et lignes de
 * temps de travail (prévisionnel / réalisé) par personne ou fonction, avec
 * distinction financé / non financé.
 */

/** Fonction / poste du référentiel global (conservateur, garde, écovolontaire…). */
export interface Fonction {
  id_fonction: number;
  libelle: string;
  /** Caractère financé par défaut, surchargeable à chaque saisie de temps. */
  finance_par_defaut: boolean;
  /** Fonction issue du socle de référence (protégée en suppression). */
  is_socle?: boolean;
  actif?: boolean;
}

/** Fonction occupée par une personne, avec quotité optionnelle (0-100). */
export interface PersonneFonction {
  id_personne_fonction?: number;
  id_fonction: number;
  fonction_libelle?: string;
  finance_par_defaut?: boolean;
  pourcentage?: number | string | null;
}

/** Personne rattachée à un plan de gestion. */
export interface PersonnePlan {
  id_personne_plan?: number;
  id_pg: number;
  nom: string;
  /** Lien facultatif vers un compte utilisateur CICADA. */
  id_role?: number | null;
  role_email?: string | null;
  role_nom?: string | null;
  date_arrivee?: string | null;
  date_depart?: string | null;
  fonctions?: PersonneFonction[];
  date_ajout?: string;
  date_maj?: string;
}

/** Payload d'écriture d'une personne (fonctions imbriquées). */
export interface PersonnePlanPayload {
  id_pg: number;
  nom: string;
  id_role?: number | null;
  date_arrivee?: string | null;
  date_depart?: string | null;
  fonctions?: Array<{ id_fonction: number; pourcentage?: number | string | null }>;
}

/**
 * Ligne RH d'une année d'opération (prévisionnel comme réalisé) : pointe
 * facultativement vers une personne OU une fonction, exprime des jours et un
 * caractère financé / non financé.
 */
export interface OperationRHLigne {
  id_operation_annee_rh?: number;
  id_realisation_operation_annee_rh?: number;
  id_personne_plan?: number | null;
  personne_nom?: string | null;
  id_fonction?: number | null;
  fonction_libelle?: string | null;
  jours: number | null;
  finance: boolean;
}
