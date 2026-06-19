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
