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
    // #453 — si un même libellé est défini sur ≥2 niveaux, la valeur est
    // ambiguë : pas d'auto-calcul (score indéterminé → saisie manuelle).
    const matches: number[] = [];
    for (let i = 1; i <= 5; i++) {
      if (inactive.includes(i)) continue;
      const label = (met[`score_${i}_label`] ?? '').toString().trim();
      if (label && label === v) matches.push(i);
    }
    return matches.length === 1 ? matches[0] : null;
  }

  const num = parseFloat(String(value).replace(',', '.'));
  if (isNaN(num)) return null;

  if (mnemo === 'CHIFFRE') {
    // #453 — même valeur chiffrée sur ≥2 niveaux : ambigu → score indéterminé.
    const matches: number[] = [];
    for (let i = 1; i <= 5; i++) {
      if (inactive.includes(i)) continue;
      const val = met[`score_${i}_val`];
      if (val !== null && val !== undefined && Number(val) === num) matches.push(i);
    }
    return matches.length === 1 ? matches[0] : null;
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

// =============================================================================
// #247 — Score combiné multi-blocs (formule ET/OU + parenthèses)
// Doit refléter exactement le backend `combine_block_scores` / `_mesure_to_score`
// (apps/plans/views_indicateurs.py).
// =============================================================================

type ScoreToken =
  | { k: 'val'; v: number | null }
  | { k: 'op'; v: 'AND' | 'OR' }
  | { k: 'lparen' }
  | { k: 'rparen' };

/**
 * Évalue une expression de scores de blocs combinés par ET(=min)/OU(=max) avec
 * parenthèses. Précédence AND > OR (associativité gauche) ; `null` neutre
 * (`op(null, x) = x`). Shunting-yard, miroir exact du backend.
 */
export function combineBlockScores(tokens: ScoreToken[]): number | null {
  const prec: Record<'AND' | 'OR', number> = { OR: 1, AND: 2 };
  const apply = (op: 'AND' | 'OR', a: number | null, b: number | null): number | null => {
    if (a === null) return b;
    if (b === null) return a;
    return op === 'AND' ? Math.min(a, b) : Math.max(a, b);
  };
  const values: (number | null)[] = [];
  const ops: ('AND' | 'OR' | '(')[] = [];
  const reduce = () => {
    if (values.length < 2 || ops.length === 0) return;
    const op = ops.pop() as 'AND' | 'OR';
    const b = values.pop()!;
    const a = values.pop()!;
    values.push(apply(op, a, b));
  };
  for (const tok of tokens) {
    if (tok.k === 'val') {
      values.push(tok.v);
    } else if (tok.k === 'op') {
      while (ops.length && ops[ops.length - 1] !== '(' &&
             prec[ops[ops.length - 1] as 'AND' | 'OR'] >= prec[tok.v]) {
        reduce();
      }
      ops.push(tok.v);
    } else if (tok.k === 'lparen') {
      ops.push('(');
    } else if (tok.k === 'rparen') {
      while (ops.length && ops[ops.length - 1] !== '(') reduce();
      if (ops.length && ops[ops.length - 1] === '(') ops.pop();
    }
  }
  while (ops.length) {
    if (ops[ops.length - 1] === '(') { ops.pop(); continue; }
    reduce();
  }
  return values.length ? values[0] : null;
}

/**
 * #247 — Chaîne lisible de la formule ET/OU d'une métrique multi-blocs, avec
 * parenthèses, en reprenant les intitulés des blocs (ex.
 * « (Surface arrachée OU Foyers traités) ET Remontée nappe »). Chaîne vide si
 * mono-bloc. Reflète la formule saisie dans l'éditeur (getFormulaText).
 */
export function formatBlockFormula(met: any): string {
  const blocks: any[] = Array.isArray(met?.score_blocks) ? met.score_blocks : [];
  if (blocks.length === 0) return '';
  const label = (intitule: any, fallback: string) =>
    (intitule ?? '').toString().trim() || fallback;
  const entries = [
    {
      label: label(met.bloc_intitule, met.nom_metrique || 'Bloc A'),
      open: Number(met.group_open ?? 0), close: Number(met.group_close ?? 0),
      op: null as string | null,
    },
    ...blocks.map((b, idx) => ({
      label: label(b.intitule, `Bloc ${String.fromCharCode(66 + idx)}`),
      open: Number(b.group_open ?? 0), close: Number(b.group_close ?? 0),
      op: b.logical_op === 'AND' ? 'ET' : 'OU',
    })),
  ];
  const parts: string[] = [];
  entries.forEach((e, i) => {
    if (i > 0 && e.op) parts.push(e.op);
    parts.push('('.repeat(e.open) + e.label + ')'.repeat(e.close));
  });
  return parts.join(' ');
}

/**
 * Score 1-5 combiné d'une métrique multi-blocs à partir d'une valeur par bloc.
 * Mono-bloc (`score_blocks` vide) → `computeMetriqueScore(met, principalValue)`.
 * `blockValues` : valeurs des blocs complémentaires indexées par leur `position`.
 */
export function computeCombinedScore(
  met: any,
  principalValue: any,
  blockValues: Record<string, any> | null | undefined,
): number | null {
  const blocks: any[] = Array.isArray(met?.score_blocks) ? met.score_blocks : [];
  if (blocks.length === 0) {
    return computeMetriqueScore(met, principalValue);
  }
  const vb = blockValues || {};
  const tokens: ScoreToken[] = [];
  // Séquence [principal] + blocs complémentaires.
  const entries: { met: any; value: any; open: number; close: number; op: 'AND' | 'OR' | null }[] = [
    { met, value: principalValue, open: Number(met?.group_open ?? 0), close: Number(met?.group_close ?? 0), op: null },
    ...blocks.map(b => ({
      // Chaque bloc est scoré comme une grille NUMERIQUE via ses propres seuils.
      met: { ...b, type_metrique_mnemonique: 'NUMERIQUE' },
      value: vb[String(b.position)],
      open: Number(b.group_open ?? 0),
      close: Number(b.group_close ?? 0),
      op: (b.logical_op as 'AND' | 'OR') ?? 'OR',
    })),
  ];
  entries.forEach((e, i) => {
    if (i > 0 && e.op) tokens.push({ k: 'op', v: e.op });
    for (let n = 0; n < e.open; n++) tokens.push({ k: 'lparen' });
    tokens.push({ k: 'val', v: computeMetriqueScore(e.met, e.value) });
    for (let n = 0; n < e.close; n++) tokens.push({ k: 'rparen' });
  });
  return combineBlockScores(tokens);
}
