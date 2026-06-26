import { computeMetriqueScore, scoreLevelName } from './metrique-seuils.util';

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
  });
});
