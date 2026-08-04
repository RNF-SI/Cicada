/**
 * Contrat d'export d'une **grille affichée** vers un classeur Excel mis en
 * forme (#637 / #638).
 *
 * Ces tableaux sont filtrés et calculés côté client : c'est lui qui envoie les
 * lignes telles qu'il les montre, le serveur ne fait que la mise en forme —
 * un CSV ne porte ni couleur d'en-tête ni case colorée. Voir
 * `apps/plans/services_export_grille.py` pour le rendu.
 */

/** Niveaux de la palette de scores du design system. */
export type GridScoreLevel =
  | 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

/**
 * Cellule exportée :
 * - une chaîne ou un **nombre** (écrit comme tel, pour rester sommable) ;
 * - `{ t, s }` pour une case que le serveur colore selon le niveau de score ;
 * - `null` pour une case vide.
 */
export type GridCell =
  | string
  | number
  | null
  | { t: string | number; s: GridScoreLevel };

export interface GridRow {
  /**
   * `normal` : ligne courante · `detail` : sous-ligne rattachée à la
   * précédente (tramée) · `total` : ligne de synthèse (aplat distinct).
   */
  type?: 'normal' | 'detail' | 'total';
  cellules: GridCell[];
}

export interface GridExportPayload {
  titre: string;
  /** Nom de l'onglet du classeur. */
  onglet?: string;
  /** Rappel des filtres actifs, en couples libellé / valeur. */
  meta: [string, string][];
  entetes: string[];
  /** Nombre de colonnes d'identification à figer à gauche. */
  gel?: number;
  lignes: GridRow[];
}
