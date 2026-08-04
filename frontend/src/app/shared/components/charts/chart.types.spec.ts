import { smoothPath, scoreColor, SCORE_PALETTE } from './chart.types';

/**
 * #640 — Le kit UI trace les courbes d'évolution et le polygone du radar en
 * Béziers cubiques. Des segments droits donnaient une étoile anguleuse au
 * radar et une ligne brisée aux séries annuelles.
 */
describe('smoothPath', () => {
  const p = (x: number, y: number) => ({ x, y });

  it('produit des Béziers cubiques, pas des segments droits', () => {
    const d = smoothPath([p(0, 0), p(10, 10), p(20, 0)]);
    expect(d).toMatch(/^M 0 0/);
    expect(d).toContain('C');
    expect(d).not.toContain('L');
  });

  it('passe exactement par chaque point fourni', () => {
    // Les extrémités de chaque Bézier sont les points : une courbe qui « lisse »
    // en s'écartant des valeurs mesurées mentirait sur la donnée.
    const d = smoothPath([p(0, 5), p(10, 8), p(20, 3)]);
    expect(d).toContain('0 5');
    expect(d).toContain('10 8');
    expect(d).toContain('20 3');
  });

  it('referme la courbe et revient au départ quand `closed`', () => {
    const d = smoothPath([p(0, 0), p(10, 0), p(5, 10)], 0.5, true);
    expect(d.endsWith('Z')).toBe(true);
    // Le dernier segment rejoint le premier point : la boucle est continue.
    expect(d).toContain('0 0');
  });

  it('relie deux points par un segment droit, faute de tangente à deviner', () => {
    expect(smoothPath([p(0, 0), p(10, 10)])).toBe('M 0 0 L 10 10');
  });

  it('rend un tracé vide sans point, et un simple déplacement avec un seul', () => {
    expect(smoothPath([])).toBe('');
    expect(smoothPath([p(3, 4)])).toBe('M 3 4');
  });

  it('revient à une polyligne quand la tension est nulle', () => {
    // Points de contrôle confondus avec les extrémités → segments visuellement
    // droits : c'est l'échappatoire si un graphe ne doit pas être lissé.
    const d = smoothPath([p(0, 0), p(10, 10), p(20, 0)], 0);
    expect(d).toContain('C 0 0, 10 10, 10 10');
  });
});

describe('scoreColor', () => {
  it('associe chaque score entier à sa couleur du design system', () => {
    expect(scoreColor(1)).toBe(SCORE_PALETTE[1]);
    expect(scoreColor(5)).toBe(SCORE_PALETTE[5]);
  });

  it('rattache une moyenne continue au score le plus proche', () => {
    expect(scoreColor(3.4)).toBe(SCORE_PALETTE[3]);
    expect(scoreColor(3.6)).toBe(SCORE_PALETTE[4]);
  });

  it('borne les valeurs hors échelle plutôt que de renvoyer undefined', () => {
    expect(scoreColor(-2)).toBe(SCORE_PALETTE[0]);
    expect(scoreColor(99)).toBe(SCORE_PALETTE[5]);
  });
});
