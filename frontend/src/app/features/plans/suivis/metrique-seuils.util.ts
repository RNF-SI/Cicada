/**
 * Formatage des seuils de score d'une métrique (parité d'affichage entre la
 * saisie d'un PG — arborescence des enjeux — et les pages de suivi des
 * indicateurs, cf. #421).
 *
 * Produit la notation par intervalles utilisée dans la saisie PG :
 *   - NUMERIQUE : « [50 ; 200] », « ]30 ; 50] », « ≥ 50 », « ≤ 10 », « - - - »
 *   - CHIFFRE   : la valeur unique du palier
 *   - TEXTE     : le libellé du palier
 * en respectant l'inclusivité des bornes (`score_N_sup_inclusive`) et les
 * paliers désactivés (`inactive_levels`).
 */

function formatNum(val: number): string {
  return parseFloat(val.toFixed(2)).toString();
}

/** Détecte le type de métrique d'après les données présentes si non renseigné. */
function resolveMnemonique(met: any): string {
  let mnemonique = met.type_metrique_mnemonique;
  if (!mnemonique) {
    const hasLabels = [1, 2, 3, 4, 5].some(l => met[`score_${l}_label`]?.toString().trim());
    const hasVals = [1, 2, 3, 4, 5].some(l => met[`score_${l}_val`] != null);
    const hasBounds = [1, 2, 3, 4, 5].some(l => met[`score_${l}_inf`] != null || met[`score_${l}_sup`] != null);
    if (hasLabels && !hasBounds) mnemonique = 'TEXTE';
    else if (hasVals && !hasBounds) mnemonique = 'CHIFFRE';
    else mnemonique = 'NUMERIQUE';
  }
  return mnemonique;
}

/** Intervalle/valeur d'un palier (1-5) formaté pour l'affichage. */
export function formatScoreRange(met: any, level: number): string {
  const mnemonique = resolveMnemonique(met);

  if (mnemonique === 'CHIFFRE') {
    if ((met.inactive_levels || []).includes(level)) return '-';
    const val = met[`score_${level}_val`];
    return val != null ? formatNum(Number(val)) : '-';
  }
  if (mnemonique === 'TEXTE') {
    if ((met.inactive_levels || []).includes(level)) return '-';
    const label = met[`score_${level}_label`];
    return label?.trim() || '-';
  }

  // NUMERIQUE
  if ((met.inactive_levels || []).includes(level)) return '- - -';

  const inf = met[`score_${level}_inf`];
  const sup = met[`score_${level}_sup`];
  if (inf == null && sup == null) return '- - -';

  // Inclusivité côté inf (dérivée de la borne sup du palier précédent).
  let infInclusive = true; // niveau 1 : inclusif par défaut
  if (level > 1) {
    const prevSupInclusive = met[`score_${level - 1}_sup_inclusive`];
    infInclusive = !(prevSupInclusive === true || prevSupInclusive == null);
  }

  // Inclusivité côté sup.
  let supInclusive = true; // niveau 5 : inclusif par défaut
  if (level < 5) {
    const si = met[`score_${level}_sup_inclusive`];
    supInclusive = (si === true || si == null);
  }

  // Intervalle ouvert : une seule borne → notation compacte.
  if (inf != null && sup == null) {
    return `${infInclusive ? '≥' : '>'} ${formatNum(Number(inf))}`;
  }
  if (inf == null && sup != null) {
    return `${supInclusive ? '≤' : '<'} ${formatNum(Number(sup))}`;
  }

  // Deux bornes : notation par crochets [0 ; 20], ]20 ; 40[
  const leftBracket = infInclusive ? '[' : ']';
  const rightBracket = supInclusive ? ']' : '[';
  return `${leftBracket}${formatNum(Number(inf))} ; ${formatNum(Number(sup))}${rightBracket}`;
}

/** Vrai si la métrique est de type indéterminé. */
export function isMetriqueIndetermine(met: any): boolean {
  return (met?.type_metrique_mnemonique ?? '') === 'INDETERMINE';
}

export type ScoreLevelName = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

/** Convertit un score 1-5 en nom de niveau (sert au nom de badge SVG). */
export function scoreLevelName(score: number | null | undefined): ScoreLevelName {
  const map: ScoreLevelName[] = ['no-data', 'very-bad', 'bad', 'neutral', 'good', 'very-good'];
  return (score && map[score]) || 'no-data';
}

/**
 * #452 — Calcule le score 1-5 d'une valeur saisie selon la grille d'une
 * métrique : TEXTE = libellé sélectionné, CHIFFRE = valeur discrète,
 * NUMERIQUE = seuils (avec inclusivité des bornes, cf. #423). Renvoie null si
 * non scorable (valeur vide, hors grille, ou format simple sans grille).
 */
export function computeMetriqueScore(met: any, value: any): number | null {
  if (!met || value === null || value === undefined || String(value).trim() === '') return null;
  const mnemo = resolveMnemonique(met);
  const inactive: number[] = Array.isArray(met.inactive_levels) ? met.inactive_levels : [];

  if (mnemo === 'TEXTE') {
    const v = String(value).trim();
    for (let i = 1; i <= 5; i++) {
      if (inactive.includes(i)) continue;
      const label = (met[`score_${i}_label`] ?? '').toString().trim();
      if (label && label === v) return i;
    }
    return null;
  }

  const num = parseFloat(String(value).replace(',', '.'));
  if (isNaN(num)) return null;

  if (mnemo === 'CHIFFRE') {
    for (let i = 1; i <= 5; i++) {
      if (inactive.includes(i)) continue;
      const val = met[`score_${i}_val`];
      if (val !== null && val !== undefined && Number(val) === num) return i;
    }
    return null;
  }

  // NUMERIQUE — seuils
  for (let i = 1; i <= 5; i++) {
    if (inactive.includes(i)) continue;
    const inf = met[`score_${i}_inf`];
    const sup = met[`score_${i}_sup`];
    const hasInf = inf !== null && inf !== undefined;
    const hasSup = sup !== null && sup !== undefined;
    if (!hasInf && !hasSup) continue;
    const infIncl = i <= 1 ? true : met[`score_${i - 1}_sup_inclusive`] === false;
    const supIncl = i >= 5 ? true : met[`score_${i}_sup_inclusive`] !== false;
    const lowerOk = !hasInf || (infIncl ? num >= Number(inf) : num > Number(inf));
    const upperOk = !hasSup || (supIncl ? num <= Number(sup) : num < Number(sup));
    if (lowerOk && upperOk) return i;
  }
  return null;
}
