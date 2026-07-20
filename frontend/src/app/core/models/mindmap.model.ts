export interface MindmapNode {
  name: string;
  entityType: MindmapEntityType;
  id?: number;
  /** Slug exposé pour les types `enjeu` et `fcr` (route `/enjeux/:enjeuSlug`). */
  slug?: string;
  /**
   * Branche de l'arborescence à laquelle appartient un indicateur / une métrique (#591).
   * `etat` = branche état actuel → OLT → NE ; `reponse` = branche facteur → pression → OO → RA.
   * Sert à colorer et libeller distinctement les colonnes « indicateur d'état » et
   * « indicateur de réponse », qui partagent le même `entityType`.
   */
  branche?: MindmapBranche;
  children?: MindmapNode[];
  _children?: MindmapNode[];
}

export type MindmapBranche = 'etat' | 'reponse';

export type MindmapEntityType =
  | 'plan' | 'enjeu' | 'fcr' | 'facteur' | 'pression'
  | 'olt' | 'etat_enjeu' | 'niveau_exigence'
  | 'oo' | 'resultat_attendu'
  | 'indicateur' | 'metrique' | 'mesure'
  | 'operation' | 'operation_annee' | 'finance'
  | 'suivi' | 'protocole';

/**
 * Clé de style d'une case : le `entityType`, sauf pour les indicateurs et
 * métriques de la branche « réponse » qui ont leur propre couleur / libellé.
 */
export type MindmapStyleKey =
  | MindmapEntityType
  | 'indicateur_reponse'
  | 'metrique_reponse';

/** Résout la clé de style d'un nœud (cf. `MindmapStyleKey`). */
export function mindmapStyleKey(node: Pick<MindmapNode, 'entityType' | 'branche'>): MindmapStyleKey {
  if (node.branche === 'reponse' && (node.entityType === 'indicateur' || node.entityType === 'metrique')) {
    return `${node.entityType}_reponse`;
  }
  return node.entityType;
}

/**
 * Palette du tableau d'arborescence (#591).
 *
 * Les couleurs sont définies par colonne : toutes les cases d'une même colonne
 * partagent un fond, ce qui fait lire le tableau horizontalement. Elles sont
 * fournies telles quelles par la maquette de l'issue #591 ; `#F8CAB8` et
 * `#FED4A6` sont des teintes claires respectivement de `$secondary-orange-salmon`
 * et `$secondary-yellow`, qui n'existent pas encore comme tokens du design system.
 *
 * Note : ces valeurs sont consommées depuis le TypeScript (styles inline sur les
 * cases), pas depuis le SCSS — d'où la table de constantes plutôt que des
 * variables SCSS.
 */
export const MINDMAP_COLORS: Record<MindmapStyleKey, string> = {
  // Colonne 1 — enjeu / FCR
  plan: '#025359',
  enjeu: '#025359',
  fcr: '#025359',
  // Colonne 2-3 — état actuel (2 cases) / facteur d'influence + pression
  etat_enjeu: '#C0E3CF',
  facteur: '#C0E3CF',
  pression: '#C0E3CF',
  // Colonne 4-5 — OLT + niveau d'exigence (branche état) / OO + RA (branche réponse)
  olt: '#F5B399',
  niveau_exigence: '#F5B399',
  oo: '#FEC180',
  resultat_attendu: '#FEC180',
  // Colonne 6-7 — indicateurs et métriques, par branche
  indicateur: '#F8CAB8',
  metrique: '#F8CAB8',
  indicateur_reponse: '#FED4A6',
  metrique_reponse: '#FED4A6',
  // Colonne 8 — action
  operation: '#B74D5D',
  // Hors tableau principal (vue inverse, sous-niveaux)
  mesure: '#746F6E',
  operation_annee: '#C6C6C6',
  finance: '#FEC180',
  suivi: '#04854B',
  protocole: '#C0E3CF',
};

/**
 * Couleur de texte imposée par la maquette (#591). Les fonds clairs portent le
 * primary `#025359`, les fonds foncés du blanc — combinaisons validées WCAG AA
 * (cf. CLAUDE.md). Les types absents retombent sur un calcul de luminance.
 */
export const MINDMAP_TEXT_COLORS: Partial<Record<MindmapStyleKey, string>> = {
  plan: '#ffffff',
  enjeu: '#ffffff',
  fcr: '#ffffff',
  operation: '#ffffff',
  etat_enjeu: '#025359',
  facteur: '#025359',
  pression: '#025359',
  olt: '#025359',
  niveau_exigence: '#025359',
  oo: '#025359',
  resultat_attendu: '#025359',
  indicateur: '#025359',
  metrique: '#025359',
  indicateur_reponse: '#025359',
  metrique_reponse: '#025359',
};

/**
 * Nombre de colonnes occupées par une case (#591). L'état actuel n'a pas
 * d'équivalent de la « pression » dans sa branche : il occupe deux colonnes pour
 * que les OLT s'alignent avec les OO, et donc que les deux branches d'un enjeu
 * se terminent sur la même colonne « Action ».
 */
export const MINDMAP_SPANS: Partial<Record<MindmapStyleKey, number>> = {
  etat_enjeu: 2,
};

/** Clés i18n des libellés de type (`plans.mindmap.entities.*`). */
export const MINDMAP_LABEL_KEYS: Record<MindmapStyleKey, string> = {
  plan: 'plans.mindmap.entities.plan',
  enjeu: 'plans.mindmap.entities.enjeu',
  fcr: 'plans.mindmap.entities.fcr',
  facteur: 'plans.mindmap.entities.facteur',
  pression: 'plans.mindmap.entities.pression',
  olt: 'plans.mindmap.entities.olt',
  etat_enjeu: 'plans.mindmap.entities.etat_enjeu',
  niveau_exigence: 'plans.mindmap.entities.niveau_exigence',
  oo: 'plans.mindmap.entities.oo',
  resultat_attendu: 'plans.mindmap.entities.resultat_attendu',
  indicateur: 'plans.mindmap.entities.indicateur',
  indicateur_reponse: 'plans.mindmap.entities.indicateur_reponse',
  metrique: 'plans.mindmap.entities.metrique',
  metrique_reponse: 'plans.mindmap.entities.metrique_reponse',
  mesure: 'plans.mindmap.entities.mesure',
  operation: 'plans.mindmap.entities.operation',
  operation_annee: 'plans.mindmap.entities.operation_annee',
  finance: 'plans.mindmap.entities.finance',
  suivi: 'plans.mindmap.entities.suivi',
  protocole: 'plans.mindmap.entities.protocole',
};
