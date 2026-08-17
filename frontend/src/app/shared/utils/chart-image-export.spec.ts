import { buildChartsSvg, collectChartCards, inlineComputedStyles } from './chart-image-export';

/**
 * #639 (retour recette) — les graphiques du bilan doivent aussi s'exporter en
 * image. La planche SVG est composée depuis le DOM affiché : c'est cette
 * composition qui est testée ici (la rasterisation dépend d'un `<canvas>`,
 * indisponible en test unitaire).
 */
describe('chart-image-export — planche JPG des graphiques (#639)', () => {
  let root: HTMLElement;

  /** Tuile graphique minimale, telle que rendue par `app-chart-card`. */
  const card = (title: string, body: string) => `
    <article class="chart-card">
      <header class="chart-card__head"><h3 class="chart-card__title">${title}</h3></header>
      <div class="chart-card__body">${body}</div>
    </article>`;

  const chartSvg = '<svg viewBox="0 0 400 200" class="bar-svg"><text class="bar-tick">5</text></svg>';

  const legend = `
    <ul class="legend">
      <li class="legend__item">
        <svg class="legend__swatch" viewBox="0 0 16 16"><rect width="16" height="16" fill="#025359"></rect></svg>
        <span class="legend__label">Prévisionnel</span>
        <strong class="legend__value">42</strong>
      </li>
    </ul>`;

  beforeEach(() => {
    root = document.createElement('div');
    root.innerHTML =
      card('Réalisation par enjeu', chartSvg + legend)
      + card('Budget', '<table><tr><td>1 000 €</td></tr></table>');
    document.body.appendChild(root);
  });

  afterEach(() => root.remove());

  const texts = (svg: SVGSVGElement) =>
    Array.from(svg.querySelectorAll('text')).map(t => t.textContent);

  it('ne retient que les tuiles porteuses d’un graphique', () => {
    // La tuile budget n'a que des chiffres : ils sont déjà dans l'export CSV,
    // une image n'y ajouterait rien.
    const cards = collectChartCards(root);
    expect(cards).toHaveLength(1);
    expect(cards[0].querySelector('.chart-card__title')?.textContent).toBe('Réalisation par enjeu');
  });

  it('rappelle les filtres en cours en tête de planche', () => {
    const svg = buildChartsSvg(collectChartCards(root), {
      title: 'Bilan — Plan test',
      lines: ['Portée : Annuel', 'Année : 2027', 'Enjeux/FCR : Enjeu 7'],
    });
    expect(texts(svg)).toEqual(expect.arrayContaining([
      'Bilan — Plan test', 'Portée : Annuel', 'Année : 2027', 'Enjeux/FCR : Enjeu 7',
    ]));
  });

  it('reprend le titre de la tuile et sa légende, valeur comprise', () => {
    const svg = buildChartsSvg(collectChartCards(root), { title: 'Bilan', lines: [] });
    expect(texts(svg)).toContain('Réalisation par enjeu');
    // La légende est du HTML à l'écran : elle est redessinée en SVG, sinon elle
    // disparaîtrait de l'image.
    expect(texts(svg)).toContain('Prévisionnel : 42');
    expect(svg.querySelector('svg[viewBox="0 0 16 16"]')).not.toBeNull();
  });

  it('imbrique le graphique en respectant son rapport d’aspect', () => {
    const svg = buildChartsSvg(collectChartCards(root), { title: 'Bilan', lines: [] });
    const chart = svg.querySelector('svg[viewBox="0 0 400 200"]') as SVGSVGElement;
    expect(chart).not.toBeNull();
    const w = Number(chart.getAttribute('width'));
    const h = Number(chart.getAttribute('height'));
    expect(w / h).toBeCloseTo(2, 5);
    // Hauteur totale = en-tête + graphique + légende : la planche doit être
    // dimensionnée, sinon la rasterisation sort une image vide.
    expect(Number(svg.getAttribute('height'))).toBeGreaterThan(h);
    expect(svg.getAttribute('viewBox')).toBe(
      `0 0 ${svg.getAttribute('width')} ${svg.getAttribute('height')}`,
    );
  });

  it('inline les styles calculés sur le clone (les feuilles CSS ne suivent pas l’image)', () => {
    const source = root.querySelector('svg') as SVGSVGElement;
    const clone = source.cloneNode(true) as SVGSVGElement;
    jest.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (p: string) => (p === 'fill' ? 'rgb(2, 83, 89)' : ''),
    } as unknown as CSSStyleDeclaration);

    inlineComputedStyles(source, clone);

    expect(clone.getAttribute('style')).toBe('fill:rgb(2, 83, 89)');
    expect(clone.querySelector('text')?.getAttribute('style')).toBe('fill:rgb(2, 83, 89)');
    jest.restoreAllMocks();
  });

  it('produit une planche vide mais valide sans aucun graphique', () => {
    const svg = buildChartsSvg([], { title: 'Bilan', lines: [] });
    expect(Number(svg.getAttribute('height'))).toBeGreaterThan(0);
  });
});
