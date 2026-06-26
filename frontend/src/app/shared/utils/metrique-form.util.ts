/**
 * #452 — Helpers de conversion pour l'éditeur de grille de métrique
 * (`MetriqueFormComponent`), réutilisés pour les indicateurs de réponse en
 * format GRILLE. La logique reflète `enjeux-list.buildMetriquePayload` /
 * `metriqueToFormData` (état/pression) pour rester cohérente.
 */
import { MetriqueFormData, MetriqueRef } from '../../core/models/enjeu.model';

/** MetriqueFormData vierge (grille vide, NUMERIQUE par défaut). */
export function blankMetriqueFormData(): MetriqueFormData {
  return {
    nom_metrique: '',
    type_metrique: null,
    format_metrique: null,
    unite: '',
    bloc_intitule: '',
    ponderation: null,
    etat_reference: '',
    scores: {
      1: { inf: null, sup: null, val: null, label: '' },
      2: { inf: null, sup: null, val: null, label: '' },
      3: { inf: null, sup: null, val: null, label: '' },
      4: { inf: null, sup: null, val: null, label: '' },
      5: { inf: null, sup: null, val: null, label: '' },
    },
    sens_variation: 'CROISSANT',
    score_1_sup_inclusive: true,
    score_2_sup_inclusive: true,
    score_3_sup_inclusive: true,
    score_4_sup_inclusive: true,
    has_score1_optional_bound: false,
    has_score5_optional_bound: false,
    _inactiveLevels: [],
    _expanded: true,
  };
}

/** Construit une MetriqueFormData depuis une métrique de réponse sauvegardée
 *  (MetriqueRef enrichie avec la grille par le backend). */
export function metriqueRefToFormData(ref: MetriqueRef): MetriqueFormData {
  const num = (v: number | null | undefined) => (v === null || v === undefined ? null : Number(v));
  return {
    id_metrique: ref.id_metrique,
    nom_metrique: ref.nom_metrique || '',
    type_metrique: ref.type_metrique_id ?? null,
    format_metrique: ref.format_metrique_id ?? null,
    unite: '',
    bloc_intitule: '',
    ponderation: null,
    etat_reference: ref.etat_reference || '',
    scores: {
      1: { inf: num(ref.score_1_inf), sup: num(ref.score_1_sup), val: num(ref.score_1_val), label: ref.score_1_label || '' },
      2: { inf: num(ref.score_2_inf), sup: num(ref.score_2_sup), val: num(ref.score_2_val), label: ref.score_2_label || '' },
      3: { inf: num(ref.score_3_inf), sup: num(ref.score_3_sup), val: num(ref.score_3_val), label: ref.score_3_label || '' },
      4: { inf: num(ref.score_4_inf), sup: num(ref.score_4_sup), val: num(ref.score_4_val), label: ref.score_4_label || '' },
      5: { inf: num(ref.score_5_inf), sup: num(ref.score_5_sup), val: num(ref.score_5_val), label: ref.score_5_label || '' },
    },
    sens_variation: ref.sens_variation || 'CROISSANT',
    score_1_sup_inclusive: ref.score_1_sup_inclusive ?? true,
    score_2_sup_inclusive: ref.score_2_sup_inclusive ?? true,
    score_3_sup_inclusive: ref.score_3_sup_inclusive ?? true,
    score_4_sup_inclusive: ref.score_4_sup_inclusive ?? true,
    has_score1_optional_bound: ref.has_borne_score1 ?? false,
    has_score5_optional_bound: ref.has_borne_score5 ?? false,
    _inactiveLevels: Array.isArray(ref.inactive_levels) ? [...ref.inactive_levels] : [],
    _expanded: true,
  };
}

function isOptionalBound(met: MetriqueFormData, level: number, field: 'inf' | 'sup'): boolean {
  if (met.sens_variation === 'CROISSANT') {
    return (level === 1 && field === 'inf') || (level === 5 && field === 'sup');
  }
  return (level === 1 && field === 'sup') || (level === 5 && field === 'inf');
}

/**
 * Convertit une MetriqueFormData en champs de grille « plats » pour l'API
 * (score_X_*, sens_variation, inclusivité, bornes, inactive_levels). Le
 * `mnemonique` (CHIFFRE / TEXTE / NUMERIQUE) détermine quels champs sont émis.
 * Renvoie un objet partiel à fusionner avec le reste du payload métrique.
 */
export function buildMetriqueGridFields(
  met: MetriqueFormData,
  mnemonique: string,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (let level = 1; level <= 5; level++) {
    const s = met.scores[level];
    if (mnemonique === 'CHIFFRE') {
      if (s?.val != null) payload[`score_${level}_val`] = s.val;
    } else if (mnemonique === 'TEXTE') {
      if (s?.label?.trim()) payload[`score_${level}_label`] = s.label.trim();
    } else {
      // NUMERIQUE
      if ((met._inactiveLevels || []).includes(level)) {
        payload[`score_${level}_inf`] = null;
        payload[`score_${level}_sup`] = null;
        continue;
      }
      const isOptInf = isOptionalBound(met, level, 'inf');
      const isOptSup = isOptionalBound(met, level, 'sup');
      if (isOptInf) {
        const hasOpt = level === 1 ? met.has_score1_optional_bound : met.has_score5_optional_bound;
        payload[`score_${level}_inf`] = (hasOpt && s?.inf != null) ? s.inf : null;
      } else if (s?.inf != null) {
        payload[`score_${level}_inf`] = s.inf;
      }
      if (isOptSup) {
        const hasOpt = level === 5 ? met.has_score5_optional_bound : met.has_score1_optional_bound;
        payload[`score_${level}_sup`] = (hasOpt && s?.sup != null) ? s.sup : null;
      } else if (s?.sup != null) {
        payload[`score_${level}_sup`] = s.sup;
      }
    }
  }

  if (mnemonique === 'CHIFFRE' || mnemonique === 'TEXTE') {
    payload['inactive_levels'] = Array.isArray(met._inactiveLevels) ? [...met._inactiveLevels] : [];
  }

  if (mnemonique === 'NUMERIQUE') {
    payload['sens_variation'] = met.sens_variation;
    payload['score_1_sup_inclusive'] = met.score_1_sup_inclusive;
    payload['score_2_sup_inclusive'] = met.score_2_sup_inclusive;
    payload['score_3_sup_inclusive'] = met.score_3_sup_inclusive;
    payload['score_4_sup_inclusive'] = met.score_4_sup_inclusive;
    payload['has_borne_score1'] = met.has_score1_optional_bound;
    payload['has_borne_score5'] = met.has_score5_optional_bound;
    payload['inactive_levels'] = Array.isArray(met._inactiveLevels) ? [...met._inactiveLevels] : [];
  }
  return payload;
}
