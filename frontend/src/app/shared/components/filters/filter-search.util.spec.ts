import { foldIndexed, foldText, matchesQuery, segmentMatches } from './filter-search.util';

describe('filter-search.util', () => {
  describe('foldText', () => {
    it('met en minuscules et retire les accents', () => {
      expect(foldText('Catégorie D’Action')).toBe('categorie d’action');
      expect(foldText('ÉÈÊËàâäùûüôöîïç')).toBe('eeeeaaauuuooiic');
    });
  });

  describe('foldIndexed', () => {
    it('conserve un offset d’origine par caractère replié', () => {
      const { folded, map } = foldIndexed('Été');
      expect(folded).toBe('ete');
      // Chaque caractère replié pointe vers l'index du caractère d'origine dont il provient.
      expect(map).toEqual([0, 1, 2]);
    });

    it('gère les paires de substitution sans les casser', () => {
      const { folded, map } = foldIndexed('a🌿b');
      expect(folded).toBe('a🌿b');
      // L'emoji occupe deux unités de code : le « b » est donc à l'offset 3.
      expect(map[map.length - 1]).toBe(3);
    });
  });

  describe('matchesQuery', () => {
    it('ignore casse et accents', () => {
      expect(matchesQuery('Catégorie', 'categorie')).toBe(true);
      expect(matchesQuery('Réserve Naturelle', 'NATURELLE')).toBe(true);
    });

    it('renvoie vrai pour une requête vide', () => {
      expect(matchesQuery('quoi que ce soit', '')).toBe(true);
      expect(matchesQuery('quoi que ce soit', '   ')).toBe(true);
    });

    it('renvoie faux sans correspondance', () => {
      expect(matchesQuery('Pressions', 'enjeu')).toBe(false);
    });
  });

  describe('segmentMatches', () => {
    it('renvoie un unique segment non correspondant pour une requête vide', () => {
      expect(segmentMatches('Enjeux', '')).toEqual([{ text: 'Enjeux', match: false }]);
    });

    it('découpe une correspondance simple', () => {
      expect(segmentMatches('Pressions', 'press')).toEqual([
        { text: 'Press', match: true },
        { text: 'ions', match: false },
      ]);
    });

    it('découpe plusieurs occurrences', () => {
      expect(segmentMatches('Corse-du-Sud et Haute-Corse', 'corse')).toEqual([
        { text: 'Corse', match: true },
        { text: '-du-Sud et Haute-', match: false },
        { text: 'Corse', match: true },
      ]);
    });

    it('surligne la portion accentuée EXACTE malgré le repliage', () => {
      // Le piège central : replier la chaîne entière changerait sa longueur et décalerait
      // le gras. `catégorie` doit être surligné en entier, accent compris.
      expect(segmentMatches("Catégorie d'action", 'categorie')).toEqual([
        { text: 'Catégorie', match: true },
        { text: " d'action", match: false },
      ]);
    });

    it('surligne correctement au milieu d’une chaîne accentuée', () => {
      expect(segmentMatches('Réserve Générale', 'generale')).toEqual([
        { text: 'Réserve ', match: false },
        { text: 'Générale', match: true },
      ]);
    });

    it('traite les métacaractères de regex comme du texte littéral', () => {
      // Une implémentation à base de `new RegExp(query)` lèverait ou matcherait tout.
      expect(() => segmentMatches('coût (net)', '(')).not.toThrow();
      expect(segmentMatches('coût (net)', '(net)')).toEqual([
        { text: 'coût ', match: false },
        { text: '(net)', match: true },
      ]);
      // Le point ne doit pas se comporter comme un joker.
      expect(segmentMatches('abc', '.')).toEqual([{ text: 'abc', match: false }]);
    });

    it('renvoie le texte intact quand rien ne correspond', () => {
      expect(segmentMatches('Enjeux', 'zzz')).toEqual([{ text: 'Enjeux', match: false }]);
    });
  });
});
