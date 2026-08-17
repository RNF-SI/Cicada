import { referencePlan } from './exploration.model';

describe('referencePlan', () => {
  it('utilise la référence quand le plan vient de la fédération', () => {
    // Deux instances produisent couramment le même slug pour des plans
    // différents : sans l'instance dans l'URL, on ouvrirait l'homonyme local.
    expect(referencePlan({ slug: 'camargue', reference: 'rnf:camargue' })).toBe(
      'rnf:camargue',
    );
  });

  it('retombe sur le slug hors fédération', () => {
    // Un index local n'a qu'une seule provenance et n'envoie pas de référence :
    // le comportement historique doit rester intact.
    expect(referencePlan({ slug: 'camargue' })).toBe('camargue');
  });

  it('retombe sur le slug si la référence est vide', () => {
    // Une chaîne vide produirait une URL `/exploration/plans/` sans identifiant,
    // donc une navigation vers la liste plutôt qu'une fiche — un échec muet.
    expect(referencePlan({ slug: 'camargue', reference: '' })).toBe('camargue');
  });
});
