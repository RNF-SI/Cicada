import {
  computeMetriqueScore, scoreLevelName,
  combineBlockScores, computeCombinedScore, formatBlockFormula, formatScoreRange,
} from './metrique-seuils.util';

describe('scoreLevelName', () => {
  it('mappe 1-5 vers les noms de niveau', () => {
    expect(scoreLevelName(1)).toBe('very-bad');
    expect(scoreLevelName(2)).toBe('bad');
    expect(scoreLevelName(3)).toBe('neutral');
    expect(scoreLevelName(4)).toBe('good');
    expect(scoreLevelName(5)).toBe('very-good');
  });
  it('renvoie no-data pour null/undefined/0', () => {
    expect(scoreLevelName(null)).toBe('no-data');
    expect(scoreLevelName(undefined)).toBe('no-data');
    expect(scoreLevelName(0)).toBe('no-data');
  });
});

describe('computeMetriqueScore', () => {
  it('renvoie null pour une valeur vide', () => {
    const met = { type_metrique_mnemonique: 'TEXTE', score_1_label: 'Mauvais' };
    expect(computeMetriqueScore(met, '')).toBeNull();
    expect(computeMetriqueScore(met, null)).toBeNull();
    expect(computeMetriqueScore(met, undefined)).toBeNull();
  });

  describe('TEXTE — libellé sélectionné', () => {
    const met = {
      type_metrique_mnemonique: 'TEXTE',
      score_1_label: 'Très mauvais',
      score_2_label: 'Mauvais',
      score_3_label: 'Moyen',
      score_4_label: 'Bon',
      score_5_label: 'Très bon',
    };
    it('retrouve le niveau du libellé', () => {
      expect(computeMetriqueScore(met, 'Très mauvais')).toBe(1);
      expect(computeMetriqueScore(met, 'Moyen')).toBe(3);
      expect(computeMetriqueScore(met, 'Très bon')).toBe(5);
    });
    it('tolère les espaces et renvoie null hors grille', () => {
      expect(computeMetriqueScore(met, '  Bon  ')).toBe(4);
      expect(computeMetriqueScore(met, 'Inconnu')).toBeNull();
    });
    it('ignore les niveaux désactivés', () => {
      expect(computeMetriqueScore({ ...met, inactive_levels: [4] }, 'Bon')).toBeNull();
    });
  });

  describe('CHIFFRE — valeur discrète', () => {
    const met = {
      type_metrique_mnemonique: 'CHIFFRE',
      score_1_val: 10, score_2_val: 20, score_3_val: 30, score_4_val: 40, score_5_val: 50,
    };
    it('retrouve le niveau de la valeur', () => {
      expect(computeMetriqueScore(met, '30')).toBe(3);
      expect(computeMetriqueScore(met, 50)).toBe(5);
    });
    it('renvoie null pour une valeur hors grille', () => {
      expect(computeMetriqueScore(met, '25')).toBeNull();
    });
  });

  describe('#453 — libellé/chiffre dupliqué sur ≥2 niveaux → indéterminé', () => {
    it('TEXTE : un libellé présent sur 2 niveaux devient ambigu (null)', () => {
      const met = {
        type_metrique_mnemonique: 'TEXTE',
        score_1_label: 'Absent', score_2_label: 'Présent', score_3_label: 'Moyen',
        score_4_label: 'Présent', score_5_label: 'Abondant',
      };
      expect(computeMetriqueScore(met, 'Présent')).toBeNull(); // niveaux 2 et 4
      expect(computeMetriqueScore(met, 'Absent')).toBe(1);     // unique
      expect(computeMetriqueScore(met, 'Moyen')).toBe(3);      // unique
    });

    it('CHIFFRE : une valeur présente sur 2 niveaux devient ambiguë (null)', () => {
      const met = {
        type_metrique_mnemonique: 'CHIFFRE',
        score_1_val: 0, score_2_val: 10, score_3_val: 20, score_4_val: 10, score_5_val: 40,
      };
      expect(computeMetriqueScore(met, '10')).toBeNull(); // niveaux 2 et 4
      expect(computeMetriqueScore(met, 0)).toBe(1);       // unique
      expect(computeMetriqueScore(met, '20')).toBe(3);    // unique
    });

    it('le doublon est levé si un des deux niveaux est désactivé', () => {
      const met = {
        type_metrique_mnemonique: 'TEXTE', inactive_levels: [4],
        score_1_label: 'Absent', score_2_label: 'Présent', score_3_label: 'Moyen',
        score_4_label: 'Présent', score_5_label: 'Abondant',
      };
      expect(computeMetriqueScore(met, 'Présent')).toBe(2);
    });
  });

  describe('NUMERIQUE — seuils avec inclusivité (#423)', () => {
    // 2 paliers croissants : [0;35] = niveau 1, ]35;100] = niveau 2
    const met = {
      type_metrique_mnemonique: 'NUMERIQUE',
      score_1_inf: 0, score_1_sup: 35, score_1_sup_inclusive: true,
      score_2_inf: 35, score_2_sup: 100,
    };
    it('classe selon les bornes', () => {
      expect(computeMetriqueScore(met, 20)).toBe(1);
      expect(computeMetriqueScore(met, 80)).toBe(2);
    });
    it('respecte l’inclusivité : 35 tombe dans le palier sup inclusif (niveau 1)', () => {
      expect(computeMetriqueScore(met, 35)).toBe(1);
    });
    it('tolère la virgule décimale française', () => {
      expect(computeMetriqueScore(met, '20,5')).toBe(1);
    });
    it('renvoie null pour une valeur non numérique', () => {
      expect(computeMetriqueScore(met, 'abc')).toBeNull();
    });

    // #545/#554 — inclusivité sens-aware en DÉCROISSANT (miroir du backend).
    // ]50;+∞[ très mauvais / ]35;50] mauvais / ]20;35] moyen / ]10;20] bon / ]0;10] très bon
    describe('DÉCROISSANT (#545/#554)', () => {
      const dec = {
        type_metrique_mnemonique: 'NUMERIQUE',
        sens_variation: 'DECROISSANT',
        score_1_inf: 50, score_1_sup: null,
        score_2_inf: 35, score_2_sup: 50,
        score_3_inf: 20, score_3_sup: 35,
        score_4_inf: 10, score_4_sup: 20,
        score_5_inf: 0, score_5_sup: 10,
        score_1_sup_inclusive: true, score_2_sup_inclusive: true,
        score_3_sup_inclusive: true, score_4_sup_inclusive: true,
        score_5_sup_inclusive: true,
      };
      it('50 tombe dans « mauvais » (borne sup inclusive), pas « très mauvais »', () => {
        expect(computeMetriqueScore(dec, 50)).toBe(2);
        expect(computeMetriqueScore(dec, 51)).toBe(1);
      });
      it('les autres frontières restent cohérentes', () => {
        expect(computeMetriqueScore(dec, 35)).toBe(3);
        expect(computeMetriqueScore(dec, 20)).toBe(4);
        expect(computeMetriqueScore(dec, 10)).toBe(5);
        expect(computeMetriqueScore(dec, 5)).toBe(5);
      });
      it('sup exclusive (score_2) déplace 50 vers « très mauvais »', () => {
        expect(computeMetriqueScore({ ...dec, score_2_sup_inclusive: false }, 50)).toBe(1);
      });
    });
  });
});

// #247 — score combiné multi-blocs (miroir du backend combine_block_scores)
describe('combineBlockScores', () => {
  it('OU prend le max, ET prend le min', () => {
    expect(combineBlockScores([{ k: 'val', v: 4 }, { k: 'op', v: 'OR' }, { k: 'val', v: 2 }])).toBe(4);
    expect(combineBlockScores([{ k: 'val', v: 4 }, { k: 'op', v: 'AND' }, { k: 'val', v: 2 }])).toBe(2);
  });
  it('respecte les parenthèses : (A OU B) ET C', () => {
    expect(combineBlockScores([
      { k: 'lparen' }, { k: 'val', v: 4 }, { k: 'op', v: 'OR' }, { k: 'val', v: 2 }, { k: 'rparen' },
      { k: 'op', v: 'AND' }, { k: 'val', v: 3 },
    ])).toBe(3);
  });
  it('ET prioritaire sur OU : A OU B ET C = A OU (B ET C)', () => {
    expect(combineBlockScores([
      { k: 'val', v: 1 }, { k: 'op', v: 'OR' }, { k: 'val', v: 5 }, { k: 'op', v: 'AND' }, { k: 'val', v: 3 },
    ])).toBe(3);
  });
  it('null est neutre', () => {
    expect(combineBlockScores([{ k: 'val', v: 4 }, { k: 'op', v: 'AND' }, { k: 'val', v: null }])).toBe(4);
    expect(combineBlockScores([{ k: 'val', v: null }, { k: 'op', v: 'OR' }, { k: 'val', v: null }])).toBeNull();
  });
  it('cas dégénérés', () => {
    expect(combineBlockScores([])).toBeNull();
    expect(combineBlockScores([{ k: 'val', v: 3 }])).toBe(3);
  });
});

describe('computeCombinedScore', () => {
  const seuils = {
    score_1_inf: 0, score_1_sup: 2, score_2_inf: 2, score_2_sup: 4,
    score_3_inf: 4, score_3_sup: 6, score_4_inf: 6, score_4_sup: 8,
    score_5_inf: 8, score_5_sup: 10,
  };
  it('mono-bloc délègue à computeMetriqueScore', () => {
    const met = { type_metrique_mnemonique: 'NUMERIQUE', ...seuils, score_blocks: [] };
    expect(computeCombinedScore(met, '5', {})).toBe(3);
  });
  it('multi-bloc OU = max(principal, bloc)', () => {
    const met = {
      type_metrique_mnemonique: 'NUMERIQUE', ...seuils,
      score_blocks: [{ position: 1, logical_op: 'OR', ...seuils }],
    };
    expect(computeCombinedScore(met, '5', { '1': '9' })).toBe(5); // 3 OU 5
  });
  it('multi-bloc parenthésé : (principal OU b1) ET b2', () => {
    const met = {
      type_metrique_mnemonique: 'NUMERIQUE', ...seuils, group_open: 1,
      score_blocks: [
        { position: 1, logical_op: 'OR', group_close: 1, ...seuils },
        { position: 2, logical_op: 'AND', ...seuils },
      ],
    };
    // val=1 (1), b1=9 (5), b2=5 (3) → (max(1,5)=5) ET 3 = 3
    expect(computeCombinedScore(met, '1', { '1': '9', '2': '5' })).toBe(3);
  });
  it('bloc sans valeur est ignoré (neutre)', () => {
    const met = {
      type_metrique_mnemonique: 'NUMERIQUE', ...seuils,
      score_blocks: [{ position: 1, logical_op: 'AND', ...seuils }],
    };
    expect(computeCombinedScore(met, '5', {})).toBe(3);
  });
});

describe('formatBlockFormula', () => {
  it('renvoie une chaîne vide en mono-bloc', () => {
    expect(formatBlockFormula({ score_blocks: [] })).toBe('');
  });
  it('reprend les intitulés et les liens ET/OU avec parenthèses', () => {
    const met = {
      bloc_intitule: 'Surface', group_open: 1,
      score_blocks: [
        { intitule: 'Foyers', logical_op: 'OR', group_close: 1 },
        { intitule: 'Nappe', logical_op: 'AND' },
      ],
    };
    expect(formatBlockFormula(met)).toBe('(Surface OU Foyers) ET Nappe');
  });
  // #550 — libellés par défaut = « Bloc A/B/C/D » (et non le nom de la métrique)
  it('utilise les lettres A/B/C/D quand les blocs n’ont pas d’intitulé', () => {
    const met = {
      nom_metrique: 'Phosphore', bloc_intitule: '',
      score_blocks: [{ logical_op: 'OR' }, { logical_op: 'OR' }],
    };
    expect(formatBlockFormula(met)).toBe('Bloc A OU Bloc B OU Bloc C');
  });
});

describe('formatScoreRange', () => {
  const nbsp = (v: string) => v.replace(/\u00A0/g, ' ');
  // #555 — précision préservée (≤ 4 décimales), plus d'arrondi à 2 décimales
  it('n’arrondit plus les bornes à 2 décimales', () => {
    const met = {
      type_metrique_mnemonique: 'NUMERIQUE',
      score_1_inf: 0.665, score_1_sup: null,
      score_2_inf: null, score_2_sup: 0.665,
    };
    // NB : le formateur insère un espace insécable ( ) après l'opérateur.
    expect(nbsp(formatScoreRange(met, 1))).toBe('≥ 0.665');
    expect(nbsp(formatScoreRange(met, 2))).toBe('≤ 0.665');
  });
  // #545/#554/#558 — intervalle sens-aware, cohérent avec le scoring
  it('affiche l’intervalle décroissant cohérent (borne sup inclusive)', () => {
    const dec = {
      type_metrique_mnemonique: 'NUMERIQUE', sens_variation: 'DECROISSANT',
      score_1_inf: 50, score_1_sup: null,
      score_2_inf: 35, score_2_sup: 50,
      score_2_sup_inclusive: true,
    };
    // très mauvais = x > 50 (50 appartient au mauvais), pas « ≥ 50 »
    expect(nbsp(formatScoreRange(dec, 1))).toBe('> 50');
    expect(nbsp(formatScoreRange({ ...dec, score_2_sup_inclusive: false }, 1))).toBe('≥ 50');
  });
});
