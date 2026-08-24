import { referencePlan, segmenterSurTerme } from './exploration.model';

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

describe('segmenterSurTerme', () => {
  /** Recompose le texte surligné, pour lire l'intention du test. */
  const rendu = (texte: string, terme: string): string =>
    segmenterSurTerme(texte, terme)
      .map((s) => (s.surligne ? `[${s.texte}]` : s.texte))
      .join('');

  it('surligne le terme cherché', () => {
    expect(rendu('Protection du Flamant rose', 'flamant')).toBe(
      'Protection du [Flamant] rose',
    );
  });

  it('ignore les accents', () => {
    // La recherche plein texte les ignore déjà : surligner autrement ferait
    // croire que le mot trouvé n'est pas celui qui a répondu.
    expect(rendu('Conservation des roselières', 'roselieres')).toBe(
      'Conservation des [roselières]',
    );
  });

  it('surligne un début de mot', () => {
    // La radicalisation fait correspondre « roseli » à « roselières » : exiger
    // une égalité exacte ne surlignerait presque jamais rien.
    expect(rendu('Les roselières du lac', 'roseli')).toBe('Les [roseli]ères du lac');
  });

  it('ne surligne pas au milieu d’un mot', () => {
    // « leur » ne doit pas s'allumer dans « valeur » : le surlignage désigne le
    // mot qui a répondu, pas une suite de lettres.
    expect(rendu('La valeur patrimoniale', 'leur')).toBe('La valeur patrimoniale');
  });

  it('surligne chaque mot de la requête', () => {
    expect(rendu('Flamant rose de Camargue', 'flamant camargue')).toBe(
      '[Flamant] rose de [Camargue]',
    );
  });

  it('rend le texte intact sans terme', () => {
    expect(rendu('Protection des limicoles', '')).toBe('Protection des limicoles');
  });

  it('ignore les mots d’une seule lettre', () => {
    // Sinon « à » ou « l » allumerait la moitié de la page.
    expect(rendu('Le lac et la lagune', 'l')).toBe('Le lac et la lagune');
  });

  it('rend une liste vide pour un texte vide', () => {
    expect(segmenterSurTerme('', 'flamant')).toEqual([]);
  });
});
