/**
 * Export CSV côté client (#637, #638, #639).
 *
 * Les tableaux de suivi (suivi des actions, tableau de bord, bilan) chargent
 * l'arborescence complète du plan puis la filtrent DANS le navigateur. Rejouer
 * ces filtres côté serveur dupliquerait cette logique et divergerait au premier
 * ajout de filtre : on sérialise donc directement les données déjà filtrées
 * affichées à l'écran.
 *
 * Format : séparateur « ; » + BOM UTF-8, pour qu'Excel en locale française
 * ouvre le fichier directement (double-clic) sans assistant d'importation.
 * Les nombres sont écrits avec la virgule décimale, pour la même raison.
 */

export type CsvCell = string | number | null | undefined;

/** Séparateur de colonnes : « ; » = convention Excel FR. */
const SEPARATOR = ';';

/** BOM UTF-8 : sans lui, Excel lit le fichier en ANSI et casse les accents. */
const BOM = '﻿';

/**
 * Échappe une cellule : les guillemets sont doublés, et la cellule est encadrée
 * dès qu'elle contient un séparateur, un guillemet ou un saut de ligne.
 */
export function escapeCsvCell(value: CsvCell): string {
  if (value === null || value === undefined) return '';
  const raw = typeof value === 'number'
    // Virgule décimale (Excel FR). Les entiers ne sont pas modifiés.
    ? String(value).replace('.', ',')
    : String(value);
  return /["\r\n;]/.test(raw) ? `"${raw.replace(/"/g, '""')}"` : raw;
}

/** Sérialise un tableau de lignes en texte CSV (sans BOM). */
export function toCsv(rows: CsvCell[][]): string {
  return rows.map(row => row.map(escapeCsvCell).join(SEPARATOR)).join('\r\n');
}

/**
 * Nom de fichier normalisé : segments accentués/espacés ramenés en kebab-case,
 * suffixés par la date du jour (AAAA-MM-JJ) et l'extension .csv.
 */
export function csvFilename(segments: (string | null | undefined)[], today = new Date()): string {
  const slugged = segments
    .filter((s): s is string => !!s && s.trim().length > 0)
    .map(s => s
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, ''))
    .filter(s => s.length > 0);
  const date = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, '0'),
    String(today.getDate()).padStart(2, '0'),
  ].join('-');
  return `${[...slugged, date].join('_')}.csv`;
}

/** Déclenche le téléchargement d'un CSV construit à partir des lignes fournies. */
export function downloadCsv(filename: string, rows: CsvCell[][]): void {
  const blob = new Blob([BOM + toCsv(rows)], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
