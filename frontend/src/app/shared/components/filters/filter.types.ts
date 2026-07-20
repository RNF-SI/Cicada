/**
 * Types partagés du système de filtres (#592).
 *
 * Voir le Figma « 🔎 Filtres » (node 4487:31534) pour les 4 familles couvertes :
 * dropdown multiselect (+ recherche), dropdown multiselect avec case maître,
 * arbre à cases avec recherche, et filtres horizontaux.
 */

/** Valeur portée par une option de filtre. */
export type FilterValue = string | number;

/** Option d'une liste de filtre plate. */
export interface FilterOption<T extends FilterValue = FilterValue> {
  value: T;
  label: string;
  disabled?: boolean;
  /** Compteur optionnel affiché à droite du label (ex : « Actions (16) »). */
  count?: number;
}

/** Nœud d'un filtre hiérarchique (zone géographique, typologies…). */
export interface FilterTreeNode<T extends FilterValue = FilterValue> extends FilterOption<T> {
  children?: FilterTreeNode<T>[];
}

/**
 * Contexte de rendu.
 * - `light` : fond de page clair (barres de filtres horizontales).
 * - `dark` : carte primary #025359 (sidebar « exploration des données »).
 */
export type FilterTheme = 'light' | 'dark';

/** État d'une case à trois états (maître de liste, parent d'arbre). */
export type TriState = 'checked' | 'unchecked' | 'indeterminate';

/**
 * Apparence du déclencheur de dropdown.
 * - `field` : champ blanc 44px bordé (famille A du Figma, sidebar).
 * - `inline` : bouton 36px transparent en gras primary (famille B, barres horizontales).
 */
export type FilterTriggerVariant = 'field' | 'inline';
