/**
 * Programmation mensuelle d'une action (#673).
 *
 * Le formulaire d'action édite une grille UNIQUE (`programmation_mensuelle_defaut`)
 * recopiée dans `periodicite_mensuelle` de chaque année. Mais une action peut
 * porter des mois propres à chaque année avec une grille vide ou différente
 * (données antérieures à la grille commune, reprises, jeu d'essai). Sans
 * précaution, le formulaire s'ouvrait alors sur une grille vide et le premier
 * enregistrement effaçait les mois de toutes les années.
 */

export type MonthFlags = Record<string, boolean>;

export const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const;

/** Grille aux 12 mois décochés. */
export function emptyMonths(): MonthFlags {
  const out: MonthFlags = {};
  for (const m of MONTHS) out[String(m)] = false;
  return out;
}

/** Mois cochés d'une grille, triés (clés hors 1..12 ignorées). */
export function checkedMonths(flags: MonthFlags | null | undefined): number[] {
  if (!flags) return [];
  return Object.entries(flags)
    .filter(([, v]) => v === true)
    .map(([k]) => Number(k))
    .filter(m => m >= 1 && m <= 12)
    .sort((a, b) => a - b);
}

/** Grille complète (12 clés) à partir d'une liste de mois. */
export function monthsToFlags(months: Iterable<number>): MonthFlags {
  const out = emptyMonths();
  for (const m of months) out[String(m)] = true;
  return out;
}

export interface MonthlyTemplateState {
  /** Grille à afficher dans le formulaire. */
  template: MonthFlags;
  /**
   * Vrai si les années portent des mois différents de la grille : leur détail
   * doit alors être conservé tant que l'utilisateur ne retouche pas la grille.
   */
  perYear: boolean;
}

/**
 * Grille à afficher au chargement d'une action.
 *
 * - grille enregistrée non vide → on la garde ; `perYear` si une année
 *   renseignée s'en écarte ;
 * - grille vide, années identiques → la grille est ces mois-là ;
 * - grille vide, années divergentes → union des mois, `perYear`.
 *
 * Une année sans aucun mois coché n'est pas une divergence : elle n'a
 * simplement pas de détail mensuel.
 */
export function deriveMonthlyTemplate(
  defaut: MonthFlags | null | undefined,
  annees: ReadonlyArray<{ periodicite_mensuelle?: MonthFlags | null }>,
): MonthlyTemplateState {
  const key = (ms: number[]) => ms.join(',');
  const yearSets = new Map<string, number[]>();
  for (const a of annees) {
    const ms = checkedMonths(a.periodicite_mensuelle);
    if (ms.length) yearSets.set(key(ms), ms);
  }
  const stored = checkedMonths(defaut);

  if (stored.length) {
    const perYear = [...yearSets.keys()].some(k => k !== key(stored));
    return { template: monthsToFlags(stored), perYear };
  }
  if (yearSets.size === 0) return { template: emptyMonths(), perYear: false };
  if (yearSets.size === 1) {
    return { template: monthsToFlags([...yearSets.values()][0]), perYear: false };
  }
  const union = new Set<number>();
  for (const ms of yearSets.values()) ms.forEach(m => union.add(m));
  return { template: monthsToFlags(union), perYear: true };
}

/**
 * Mois à enregistrer pour une année : ceux de la grille commune, sauf si le
 * détail par année doit être conservé (`perYear`).
 */
export function monthsToSave(
  template: MonthFlags,
  yearMonths: MonthFlags | null | undefined,
  perYear: boolean,
): MonthFlags {
  return perYear ? monthsToFlags(checkedMonths(yearMonths)) : { ...template };
}
