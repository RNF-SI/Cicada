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
  /**
   * Nom de la structure d'origine — fédération uniquement (#636).
   *
   * L'identifiant technique (« rnf ») trace la donnée, il ne la présente pas :
   * c'est ce libellé qui est affiché sur la tuile. Absent hors fédération, où
   * tout vient de l'instance courante.
   */
  instance_libelle?: string;
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
  /** Nom de la structure d'origine — fédération uniquement (#636). */
  instance_libelle?: string;
  /**
   * #650 — Champs ayant répondu à la recherche (`titre`, `rattachements`,
   * `description`, `contexte`). Vide sans mot-clé.
   */
  correspondances?: string[];
  /**
   * #650 — Fragment de l'espèce, habitat ou protocole rattaché qui a répondu.
   *
   * Ces objets sont interrogés mais jamais affichés sur la tuile : sans cet
   * extrait, un résultat dont le titre n'a aucun rapport avec la requête
   * paraît arbitraire.
   */
  extrait_rattachements?: string | null;
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
  /** Nom de la structure d'origine — fédération uniquement (#636). */
  instance_libelle?: string;
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
  /**
   * #651 — Aucun résultat exact : ceux affichés sont des termes approchants.
   *
   * Sans cette information, l'utilisateur croit avoir trouvé ce qu'il
   * cherchait. C'est précisément ce qui a été rapporté comme « la recherche
   * dans les titres ne marche pas » : « fleur » remontait un titre contenant
   * « leur ».
   */
  approximatif?: boolean;
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
  /**
   * #636 — Structures d'origine retenues (identifiants d'instance).
   *
   * Sans effet hors fédération : un index local n'a qu'une provenance, et le
   * filtre correspondant n'est pas affiché.
   */
  instances?: string[];
  tri?: ExplorationTri;
  page?: number;
}

/**
 * Une structure dont les données alimentent l'exploration (#636).
 *
 * Rendue par `/api/exploration/instances/`, servie par le hub ou par l'instance
 * elle-même. Répond à la question que pose tout résultat manquant : ce plan
 * n'existe pas, ou sa structure ne publie pas ?
 */
export interface ExplorationInstance {
  instance_id: string;
  libelle: string;
  url_publique: string;
  plans: number;
  contenus: number;
  derniere_publication: string | null;
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

/** Un fragment de texte, surligné ou non, pour l'affichage des résultats. */
export interface SegmentTexte {
  texte: string;
  surligne: boolean;
}

/**
 * Découpe un texte en segments, en marquant ceux qui répondent au terme cherché (#650).
 *
 * Le surlignage se fait par **segments** et non par injection de HTML : le
 * texte vient de la base, et le passer par `innerHTML` ouvrirait une porte
 * qu'aucun surlignage ne justifie.
 *
 * La comparaison ignore les accents et la casse, et retient les **débuts de
 * mot** : la recherche plein texte radicalise (« roselieres » trouve
 * « roselières »), donc exiger une égalité exacte ne surlignerait presque
 * jamais rien — l'utilisateur verrait des résultats sans savoir quel mot a
 * répondu, c'est-à-dire le problème qu'on cherche à résoudre.
 */
export function segmenterSurTerme(texte: string, terme: string): SegmentTexte[] {
  if (!texte) {
    return [];
  }
  // Normalisation caractère par caractère : `normalize('NFD')` sur la chaîne
  // entière décale les indices, et on ne saurait plus où découper l'original.
  // Indexation par unité UTF-16, comme `texte.length` et `texte[i]` : itérer
  // par points de code désalignerait les indices dès qu'un caractère hors du
  // plan de base apparaît, et le découpage tomberait au milieu d'une paire.
  const aplati = (valeur: string): string => {
    let sortie = '';
    for (let i = 0; i < valeur.length; i++) {
      sortie += valeur[i].normalize('NFD')[0].toLowerCase();
    }
    return sortie;
  };

  const mots = [
    ...new Set(
      aplati(terme)
        .split(/[^\p{L}\p{N}]+/u)
        .filter((mot) => mot.length >= 2),
    ),
  ];
  if (!mots.length) {
    return [{ texte, surligne: false }];
  }

  const cible = aplati(texte);
  const marques = new Array<boolean>(texte.length).fill(false);

  // Un début de mot : le caractère précédent n'est ni lettre ni chiffre.
  const debutDeMot = (index: number): boolean =>
    index === 0 || !/[\p{L}\p{N}]/u.test(cible[index - 1]);

  for (const mot of mots) {
    let depuis = cible.indexOf(mot);
    while (depuis !== -1) {
      if (debutDeMot(depuis)) {
        for (let i = depuis; i < depuis + mot.length; i++) {
          marques[i] = true;
        }
      }
      depuis = cible.indexOf(mot, depuis + 1);
    }
  }

  const segments: SegmentTexte[] = [];
  for (let i = 0; i < texte.length; i++) {
    const surligne = marques[i];
    if (segments.length && segments[segments.length - 1].surligne === surligne) {
      segments[segments.length - 1].texte += texte[i];
    } else {
      segments.push({ texte: texte[i], surligne });
    }
  }
  return segments;
}
