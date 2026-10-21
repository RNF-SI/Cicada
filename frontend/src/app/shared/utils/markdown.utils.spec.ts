import { renderMarkdown } from './markdown.utils';

describe('renderMarkdown (#746)', () => {
  it('rend titres, paragraphes et emphase', () => {
    const html = renderMarkdown('# Titre\n\n## Sous-titre\n\nUn **gras** et un *italique*.');
    expect(html).toContain('<h1>Titre</h1>');
    expect(html).toContain('<h2>Sous-titre</h2>');
    expect(html).toContain('<p>Un <strong>gras</strong> et un <em>italique</em>.</p>');
  });

  it('rend les listes à puces et numérotées', () => {
    expect(renderMarkdown('- un\n- deux')).toBe('<ul><li>un</li><li>deux</li></ul>');
    expect(renderMarkdown('1. un\n2. deux')).toBe('<ol><li>un</li><li>deux</li></ol>');
  });

  it('rend les liens http(s) dans un nouvel onglet, pas les autres schémas', () => {
    expect(renderMarkdown('[RNF](https://rnf.fr)'))
      .toBe('<p><a href="https://rnf.fr" target="_blank" rel="noopener">RNF</a></p>');
    expect(renderMarkdown('[x](javascript:alert(1))')).not.toContain('<a');
  });

  it('échappe le HTML saisi', () => {
    const html = renderMarkdown('<script>alert(1)</script> & "x"');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
    expect(html).toContain('&amp;');
  });

  it('joint les lignes d\'un même paragraphe', () => {
    expect(renderMarkdown('ligne 1\nligne 2')).toBe('<p>ligne 1<br>ligne 2</p>');
  });
});
