import { TaxonRef } from '../../core/models/enjeu.model';

/**
 * Sérialisation des taxons référés (#563).
 *
 * Les taxons étaient stockés dans le champ texte `taxon_taxref` sous forme de
 * noms séparés par des virgules, puis relus via un simple `split(',')`. Deux
 * bugs en découlaient au rechargement :
 *  - les noms contenant une virgule (ex. « Orobanche elatior Sutton, 1798 »)
 *    étaient scindés en plusieurs chips (« Orobanche elatior Sutton », « 1798 ») ;
 *  - le `cd_nom` était perdu et affiché à 0.
 *
 * On encode désormais la liste en JSON afin de préserver `cd_nom` et de gérer
 * les virgules. Le parsing reste rétrocompatible avec l'ancien format texte.
 */

interface StoredTaxonRef {
  cd_nom: number;
  nom_complet: string;
}

/** Sérialise une liste de taxons pour stockage dans `taxon_taxref`. */
export function serializeTaxonRefs(items: TaxonRef[] | null | undefined): string {
  const clean = (items ?? []).filter((t) => t && (t.cd_nom || (t.nom_complet ?? '').trim()));
  if (clean.length === 0) {
    return '';
  }
  const stored: StoredTaxonRef[] = clean.map((t) => ({
    cd_nom: t.cd_nom || 0,
    nom_complet: (t.nom_complet ?? '').trim(),
  }));
  return JSON.stringify(stored);
}

/**
 * Reconstruit la liste de taxons depuis `taxon_taxref`.
 * Gère le nouveau format JSON (avec `cd_nom`) et l'ancien format
 * « noms séparés par des virgules » (cd_nom inconnu → 0).
 */
export function parseTaxonRefs(raw: string | null | undefined): TaxonRef[] {
  if (!raw) {
    return [];
  }
  const trimmed = raw.trim();
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed
          .map((o) => ({
            cd_nom: Number(o?.cd_nom) || 0,
            nom_complet: (o?.nom_complet ?? '').toString().trim(),
          }))
          .filter((t) => t.cd_nom || t.nom_complet);
      }
    } catch {
      // format JSON invalide → on retombe sur l'ancien parsing texte
    }
  }
  return trimmed
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((name) => ({ cd_nom: 0, nom_complet: name }));
}

/** Rendu lisible (noms séparés par des virgules) pour l'affichage. */
export function taxonRefsToText(raw: string | null | undefined): string {
  return parseTaxonRefs(raw)
    .map((t) => t.nom_complet || String(t.cd_nom))
    .join(', ');
}
