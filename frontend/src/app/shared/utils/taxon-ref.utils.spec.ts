import { serializeTaxonRefs, parseTaxonRefs, taxonRefsToText } from './taxon-ref.utils';

describe('taxon-ref serialization (#563)', () => {
  it('round-trips a taxon whose name contains a comma, preserving cd_nom', () => {
    const items = [
      { cd_nom: 111532, nom_complet: 'Orobanche elatior Sutton, 1798' },
      { cd_nom: 3540, nom_complet: 'Caprimulgus europaeus Linnaeus, 1758' },
    ];
    const raw = serializeTaxonRefs(items);
    const parsed = parseTaxonRefs(raw);

    // Deux chips (pas quatre : la virgule du nom ne scinde plus)
    expect(parsed).toHaveLength(2);
    expect(parsed[0]).toEqual({ cd_nom: 111532, nom_complet: 'Orobanche elatior Sutton, 1798' });
    expect(parsed[1]).toEqual({ cd_nom: 3540, nom_complet: 'Caprimulgus europaeus Linnaeus, 1758' });
  });

  it('serializes an empty list to an empty string', () => {
    expect(serializeTaxonRefs([])).toBe('');
    expect(serializeTaxonRefs(null)).toBe('');
    expect(serializeTaxonRefs(undefined)).toBe('');
  });

  it('parses legacy comma-joined strings (cd_nom unknown → 0)', () => {
    const parsed = parseTaxonRefs('Aves, Chiroptera');
    expect(parsed).toEqual([
      { cd_nom: 0, nom_complet: 'Aves' },
      { cd_nom: 0, nom_complet: 'Chiroptera' },
    ]);
  });

  it('returns [] for empty / nullish input', () => {
    expect(parseTaxonRefs('')).toEqual([]);
    expect(parseTaxonRefs(null)).toEqual([]);
    expect(parseTaxonRefs(undefined)).toEqual([]);
  });

  it('falls back to legacy parsing on invalid JSON', () => {
    const parsed = parseTaxonRefs('[not valid json');
    expect(parsed).toEqual([{ cd_nom: 0, nom_complet: '[not valid json' }]);
  });

  it('taxonRefsToText renders readable names from JSON', () => {
    const raw = serializeTaxonRefs([
      { cd_nom: 111532, nom_complet: 'Orobanche elatior Sutton, 1798' },
      { cd_nom: 3540, nom_complet: 'Caprimulgus europaeus Linnaeus, 1758' },
    ]);
    expect(taxonRefsToText(raw)).toBe(
      'Orobanche elatior Sutton, 1798, Caprimulgus europaeus Linnaeus, 1758',
    );
  });
});
