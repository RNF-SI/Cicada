import { createFilterSet } from './filter-set';

describe('createFilterSet', () => {
  it('expose un signal inscriptible par clé, initialisé', () => {
    const filters = createFilterSet({ enjeu: null as number | null, texte: '' });
    expect(filters.enjeu()).toBeNull();
    expect(filters.texte()).toBe('');

    filters.enjeu.set(3);
    expect(filters.enjeu()).toBe(3);
  });

  it('compte les filtres actifs selon le prédicat par défaut', () => {
    const filters = createFilterSet({
      enjeu: null as number | null,
      texte: '',
      tags: [] as string[],
    });

    expect(filters.activeCount()).toBe(0);
    expect(filters.hasActive()).toBe(false);

    filters.enjeu.set(1);
    filters.tags.set(['a']);
    expect(filters.activeCount()).toBe(2);
    expect(filters.hasActive()).toBe(true);
  });

  it('ne considère pas actives une chaîne d’espaces ni un tableau vide', () => {
    const filters = createFilterSet({ texte: '', tags: [] as string[] });
    filters.texte.set('   ');
    expect(filters.activeCount()).toBe(0);
  });

  it('respecte un prédicat d’activité personnalisé (valeur neutre « all »)', () => {
    const filters = createFilterSet(
      { realisation: 'all' as 'all' | 'realized' },
      { isActive: { realisation: (v) => v !== 'all' } },
    );

    expect(filters.hasActive()).toBe(false);
    filters.realisation.set('realized');
    expect(filters.hasActive()).toBe(true);
  });

  it('reset() restaure les valeurs initiales', () => {
    const filters = createFilterSet({ enjeu: 5 as number | null, texte: 'init' });
    filters.enjeu.set(9);
    filters.texte.set('modifié');

    filters.reset();

    expect(filters.enjeu()).toBe(5);
    expect(filters.texte()).toBe('init');
  });

  it('reset() exécute l’effet de bord onReset', () => {
    const onReset = jest.fn();
    const filters = createFilterSet({ texte: '' }, { onReset });

    filters.reset();

    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it('ne partage pas l’instance des tableaux initiaux (copie défensive)', () => {
    const initialTags: string[] = [];
    const filters = createFilterSet({ tags: initialTags });

    // Mutation en place chez l'appelant : elle ne doit pas contaminer l'état initial.
    filters.tags().push('pollué');
    filters.reset();

    expect(filters.tags()).toEqual([]);
    expect(initialTags).toEqual([]);
  });
});
