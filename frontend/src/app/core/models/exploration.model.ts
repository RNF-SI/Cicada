/**
 * Modèles de l'exploration des données (`/exploration`).
 *
 * Deux modes de recherche, servis par deux endpoints distincts :
 * `contenus` interroge l'index de contenu des plans, `plans` retrouve un plan
 * par son nom, celui d'un site, d'un département ou d'une région.
 */

/** Type d'objet explorable dans le contenu d'un plan. */
export type ExplorationType =
  | 'enjeu'
  | 'facteur'
  | 'pression'
  | 'objectif_lt'
  | 'objectif_op'
  | 'indicateur'
  | 'action';

/**
 * Onglets de résultats et entrées du dropdown « Type de données », dans
 * l'ordre de la maquette.
 *
 * Un onglet peut couvrir plusieurs types : la maquette n'affiche qu'un onglet
 * « Objectifs », la distinction long terme / opérationnel étant reléguée au
 * groupe de facettes correspondant de la barre latérale.
 */
export interface ExplorationOnglet {
  /** Identifiant de l'onglet, utilisé dans l'URL. */
  cle: string;
  /** Types de contenu qu'il regroupe. */
  types: ExplorationType[];
  /** Clé de traduction du libellé. */
  label: string;
}

export const EXPLORATION_ONGLETS: ExplorationOnglet[] = [
  { cle: 'pression', types: ['pression'], label: 'exploration.types.pression.pluriel' },
  { cle: 'facteur', types: ['facteur'], label: 'exploration.types.facteur.pluriel' },
  {
    cle: 'objectif',
    types: ['objectif_lt', 'objectif_op'],
    label: 'exploration.filters.objectifs',
  },
  {
    cle: 'indicateur',
    types: ['indicateur'],
    label: 'exploration.types.indicateur.pluriel',
  },
  { cle: 'enjeu', types: ['enjeu'], label: 'exploration.types.enjeu.pluriel' },
  { cle: 'action', types: ['action'], label: 'exploration.types.action.pluriel' },
];

/** Statuts proposés par le filtre « statut du plan de gestion ». */
export type ExplorationStatut = 'en_cours' | 'valide' | 'archive';

export type ExplorationTri = 'pertinence' | 'alphabetique' | 'recent';

/** Site tel qu'affiché sur une tuile de résultat. */
export interface ExplorationSite {
  id_site: number;
  nom_site: string;
  slug: string;
}

/**
 * Bandeau « Plan de gestion / Gestionnaire / Période » d'une tuile.
 *
 * `reference` et `instance_id` ne sont renseignés que par l'exploration
 * fédérée (#636), où un plan peut venir d'une autre instance CICADA. Un index
 * local n'a qu'une seule provenance et ne les envoie pas.
 */
export interface ExplorationPlanResume {
  id_pg: number;
  nom: string;
  slug: string;
  statut: string;
  annee_debut: number | null;
  annee_fin: number | null;
  type_document: string | null;
  sites: ExplorationSite[];
  gestionnaire_principal: string | null;
  reference?: string;
  instance_id?: string;
  url_instance?: string;
}

/**
 * Identifiant à mettre dans l'URL de la fiche d'un plan.
 *
 * Le slug seul ne suffit pas en fédération : deux instances produisent
 * couramment le même slug pour des plans différents, et l'ouvrir sans dire
 * d'où il vient afficherait l'homonyme local — une réponse fausse et
 * silencieuse. `reference` porte l'instance (« rnf:camargue ») ; hors
 * fédération elle est absente et le slug reprend son rôle.
 */
export function referencePlan(
  plan: Pick<ExplorationPlanResume, 'slug' | 'reference'>,
): string {
  return plan.reference || plan.slug;
}

/** Une tuile du mode « contenu d'un plan de gestion ». */
export interface ExplorationContenu {
  id: number;
  type_contenu: ExplorationType;
  id_objet: number;
  titre: string;
  description: string;
  parent_type: string | null;
  parent_libelle: string | null;
  sous_type: string | null;
  sous_type_libelle: string | null;
  plan: ExplorationPlanResume;
  /** Instance d'origine du document — fédération uniquement (#636). */
  instance_id?: string;
}

/** Une tuile du mode « plan de gestion ». */
export interface ExplorationPlan {
  id_pg: number;
  nom: string;
  slug: string;
  statut: string;
  rang: number;
  annee_debut: number | null;
  annee_fin: number | null;
  type_document: string | null;
  sites: ExplorationSite[];
  gestionnaire_principal: string | null;
  reference?: string;
  instance_id?: string;
  url_instance?: string;
}

export interface ExplorationPagination {
  count: number;
  current_page: number;
  total_pages: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ExplorationReponse<T> {
  links: { next: string | null; previous: string | null };
  pagination: ExplorationPagination;
  results: T[];
  /** Compteurs par type, présents seulement en mode « contenu ». */
  compteurs?: Record<string, number>;
}

/**
 * Critères de recherche, communs aux deux modes.
 *
 * Les champs propres au mode « contenu » sont ignorés par l'endpoint `plans`,
 * ce qui permet de conserver les filtres en basculant d'un mode à l'autre.
 */
export interface ExplorationCriteres {
  q?: string;
  titresSeulement?: boolean;
  types?: ExplorationType[];
  /** Types couverts par l'onglet actif. Vide = onglet « Tout ». */
  onglet?: ExplorationType[];
  zones?: number[];
  organismes?: number[];
  typesSite?: string[];
  categoriesEnjeu?: string[];
  typesIndicateur?: string[];
  categoriesAction?: string[];
  statuts?: ExplorationStatut[];
  tri?: ExplorationTri;
  page?: number;
}

/** Département du filtre « zone géographique ». */
export interface ZoneDepartement {
  id_area: number;
  code: string;
  nom: string;
}

/** Région et ses départements. */
export interface ZoneRegion extends ZoneDepartement {
  departements: ZoneDepartement[];
}

/** Organisme du filtre « organismes gestionnaires ». */
export interface OrganismePublic {
  id: number;
  nom_organisme: string;
}

/** Entrée de nomenclature servant de facette (type d'aire, catégorie d'action). */
export interface NomenclatureOption {
  id_nomenclature: number;
  cd_nomenclature: string | null;
  mnemonique: string;
  label: string;
}
