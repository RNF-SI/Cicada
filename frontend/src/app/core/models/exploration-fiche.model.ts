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

export interface FicheMetrique {
  id_metrique: number;
  nom_metrique: string;
  unite: string | null;
  description: string | null;
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
  operateurs: string | null;
  partenaires: string | null;
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
