import { escapeCsvCell, toCsv, csvFilename } from './csv-export';

describe('csv-export (#637/#638/#639)', () => {
  describe('escapeCsvCell', () => {
    it('rend une chaîne vide pour null/undefined', () => {
      expect(escapeCsvCell(null)).toBe('');
      expect(escapeCsvCell(undefined)).toBe('');
    });

    it('écrit les décimales avec une virgule (Excel FR)', () => {
      expect(escapeCsvCell(12.5)).toBe('12,5');
      expect(escapeCsvCell(12)).toBe('12');
    });

    it('encadre et double les guillemets', () => {
      expect(escapeCsvCell('Action "phare"')).toBe('"Action ""phare"""');
    });

    it('encadre les valeurs contenant le séparateur ou un saut de ligne', () => {
      expect(escapeCsvCell('a;b')).toBe('"a;b"');
      expect(escapeCsvCell('a\nb')).toBe('"a\nb"');
    });

    it('laisse les valeurs simples intactes', () => {
      expect(escapeCsvCell('CS1')).toBe('CS1');
    });
  });

  describe('toCsv', () => {
    it('joint colonnes et lignes', () => {
      expect(toCsv([['a', 'b'], [1, 2]])).toBe('a;b\r\n1;2');
    });
  });

  describe('csvFilename', () => {
    it('normalise les segments et suffixe la date', () => {
      expect(csvFilename(['Suivi des actions', 'Réserve de Camargue'], new Date(2026, 7, 3)))
        .toBe('suivi-des-actions_reserve-de-camargue_2026-08-03.csv');
    });

    it('ignore les segments vides', () => {
      expect(csvFilename(['bilan', null, '', undefined], new Date(2026, 0, 9)))
        .toBe('bilan_2026-01-09.csv');
    });
  });
});
