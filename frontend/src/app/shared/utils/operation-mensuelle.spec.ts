import {
  checkedMonths, deriveMonthlyTemplate, emptyMonths, monthsToFlags, monthsToSave,
} from './operation-mensuelle';

describe('operation-mensuelle (#673)', () => {
  const year = (...ms: number[]) => ({ periodicite_mensuelle: monthsToFlags(ms) });

  describe('checkedMonths', () => {
    it('ne garde que les mois cochés, triés, dans 1..12', () => {
      expect(checkedMonths({ '10': true, '2': true, '3': false, '13': true, 'x': true })).toEqual([2, 10]);
    });
    it('accepte null / undefined', () => {
      expect(checkedMonths(null)).toEqual([]);
      expect(checkedMonths(undefined)).toEqual([]);
    });
  });

  describe('deriveMonthlyTemplate', () => {
    it('grille vide + mois identiques chaque année → la grille reprend ces mois', () => {
      const s = deriveMonthlyTemplate({}, [year(3, 4, 5, 6), year(3, 4, 5, 6)]);
      expect(checkedMonths(s.template)).toEqual([3, 4, 5, 6]);
      expect(s.perYear).toBe(false);
    });

    it('grille vide + années divergentes → union des mois, détail par année conservé', () => {
      const s = deriveMonthlyTemplate({}, [year(3, 4), year(9)]);
      expect(checkedMonths(s.template)).toEqual([3, 4, 9]);
      expect(s.perYear).toBe(true);
    });

    it('une année sans mois n\'est pas une divergence', () => {
      const s = deriveMonthlyTemplate(emptyMonths(), [year(6, 7), year(), { periodicite_mensuelle: null }]);
      expect(checkedMonths(s.template)).toEqual([6, 7]);
      expect(s.perYear).toBe(false);
    });

    it('grille enregistrée cohérente avec les années → inchangée', () => {
      const s = deriveMonthlyTemplate(monthsToFlags([2, 3]), [year(2, 3), year()]);
      expect(checkedMonths(s.template)).toEqual([2, 3]);
      expect(s.perYear).toBe(false);
    });

    it('grille enregistrée mais une année s\'en écarte → détail par année conservé', () => {
      const s = deriveMonthlyTemplate(monthsToFlags([2, 3]), [year(2, 3), year(11)]);
      expect(checkedMonths(s.template)).toEqual([2, 3]);
      expect(s.perYear).toBe(true);
    });

    it('rien de saisi → grille vide aux 12 clés', () => {
      const s = deriveMonthlyTemplate(undefined, []);
      expect(Object.keys(s.template)).toHaveLength(12);
      expect(checkedMonths(s.template)).toEqual([]);
      expect(s.perYear).toBe(false);
    });
  });

  describe('monthsToSave', () => {
    it('applique la grille commune par défaut', () => {
      expect(checkedMonths(monthsToSave(monthsToFlags([5]), monthsToFlags([1]), false))).toEqual([5]);
    });
    it('conserve les mois de l\'année en mode par année', () => {
      expect(checkedMonths(monthsToSave(monthsToFlags([5]), monthsToFlags([1, 12]), true))).toEqual([1, 12]);
    });
    it('renvoie une copie (pas la grille partagée)', () => {
      const t = monthsToFlags([5]);
      expect(monthsToSave(t, null, false)).not.toBe(t);
    });
  });
});
