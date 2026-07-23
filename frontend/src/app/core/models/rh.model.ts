/**
 * Modèles pour la gestion des ressources humaines des plans de gestion (#560) :
 * référentiel de fonctions, postes d'un PG et lignes de temps de travail
 * (prévisionnel / réalisé) par poste ou par organisme, avec distinction
 * financé / non financé.
 *
 * Aucune donnée nominative n'est manipulée (RGPD) : on décrit des postes, pas
 * des personnes.
 */

/** Type de poste porté par une fonction (#596). */
export type TypePoste = 'salarie' | 'stagiaire' | 'prestataire' | 'benevole';

/** Fonction du référentiel global (conservateur, garde, écovolontaire…). */
export interface Fonction {
  id_fonction: number;
  libelle: string;
  /** Catégorie de la fonction : conditionne la saisie du coût jour (#596). */
  type_poste?: TypePoste;
  /** Libellé lisible du type de poste (lecture seule). */
  type_poste_display?: string;
  /** Caractère financé par défaut, surchargeable à chaque saisie de temps. */
  finance_par_defaut: boolean;
  /** Fonction issue du socle de référence (protégée en suppression). */
  is_socle?: boolean;
  actif?: boolean;
}

/**
 * Fonction portée par un poste, avec quotité optionnelle (0-100).
 *
 * Quotité vide = le poste cumule ses fonctions sur tout son temps
 * (« garde animateur » à 1 ETP). Quotités renseignées = répartition explicite,
 * dont la somme doit faire 100 %.
 */
export interface PosteFonction {
  id_poste_fonction?: number;
  id_fonction: number;
  fonction_libelle?: string;
  finance_par_defaut?: boolean;
  /** Type de poste de la fonction (lecture seule, #596). */
  type_poste?: TypePoste;
  pourcentage?: number | string | null;
}

/** Poste d'un plan de gestion. Décrit par ses fonctions, jamais par un nom. */
export interface Poste {
  id_poste?: number;
  id_pg: number;
  /** Libellé dérivé des fonctions, calculé côté serveur (lecture seule). */
  libelle?: string;
  id_organisme?: number | null;
  organisme_nom?: string | null;
  /** Nom d'organisme saisi librement (prestataire hors référentiel, #599). */
  organisme_libre?: string | null;
  /** Organisme à afficher : référentiel s'il existe, sinon saisie libre (lecture). */
  organisme_affichage?: string | null;
  /** Combien de postes de ce type (ex. 3 stagiaires). */
  nombre: number;
  /** ETP pour ce poste, TOTAL sur les `nombre` postes. */
  etp?: number | string | null;
  /** Coût jour (€) du poste — sert au calcul du coût salarial (#596). */
  cout_jour?: number | string | null;
  fonctions?: PosteFonction[];
  /** Faux seulement si toutes les fonctions sont non financées. */
  finance_par_defaut?: boolean;
  date_ajout?: string;
  date_maj?: string;
}

/** Payload d'écriture d'un poste (fonctions imbriquées). */
export interface PostePayload {
  id_pg: number;
  id_organisme?: number | null;
  organisme_libre?: string | null;
  nombre: number;
  etp?: number | string | null;
  cout_jour?: number | string | null;
  fonctions?: Array<{ id_fonction: number; pourcentage?: number | string | null }>;
}

/**
 * Ligne RH d'une année d'opération (prévisionnel comme réalisé).
 *
 * La cible dépend du mode de saisie de l'action : un poste (déclinaison par
 * poste), un organisme (budget ventilé par organisme), ou rien.
 */
export interface OperationRHLigne {
  id_operation_annee_rh?: number | null;
  id_realisation_operation_annee_rh?: number;
  id_poste?: number | null;
  poste_libelle?: string | null;
  /** Organisme du poste, affiché sous son libellé en déclinaison par poste. */
  poste_organisme_nom?: string | null;
  id_organisme?: number | null;
  organisme_nom?: string | null;
  jours: number | null;
  finance: boolean;
}
