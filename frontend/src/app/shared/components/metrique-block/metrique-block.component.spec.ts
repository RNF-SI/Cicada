import { MetriqueBlockComponent, ScoreBlockData } from './metrique-block.component';

/**
 * Bloc de scoring par défaut (grille vierge). On ne définit volontairement PAS
 * `score_5_sup_inclusive` (absent de l'interface) : c'est précisément le champ
 * sans défaut qui causait l'incohérence #450 en sens décroissant.
 */
function makeBlock(overrides: Partial<ScoreBlockData> = {}): ScoreBlockData {
  return {
    sens_variation: 'DECROISSANT',
    score_1_inf: null, score_1_sup: null,
    score_2_inf: null, score_2_sup: null,
    score_3_inf: null, score_3_sup: null,
    score_4_inf: null, score_4_sup: null,
    score_5_inf: null, score_5_sup: null,
    score_1_sup_inclusive: true,
    score_2_sup_inclusive: true,
    score_3_sup_inclusive: true,
    score_4_sup_inclusive: true,
    has_borne_score1: false,
    has_borne_score5: false,
    inactive_levels: [],
    ...overrides,
  } as ScoreBlockData;
}

function makeComponent(block: ScoreBlockData): MetriqueBlockComponent {
  const c = new MetriqueBlockComponent();
  c.block = block;
  return c;
}

describe('MetriqueBlockComponent', () => {
  describe('#450 — cohérence toggle / intervalle (frontière très bon / bon en décroissant)', () => {
    it('toggle « inclu dans » par défaut sur la gauche (très bon), cohérent avec « x ≤ »', () => {
      // Décroissant : ordre d'affichage [5,4,3,2,1] → frontière TB(5)/Bon(4) = colonne i=0.
      // score_5_sup_inclusive est undefined (jamais défini par défaut).
      const c = makeComponent(makeBlock({ score_5_sup: 33 }));

      // Avant #450 : isBoundaryInLeftAt(0) renvoyait undefined (→ Bon actif),
      // alors que l'intervalle affichait « x ≤ 33 » (très bon inclusif).
      expect(c.isBoundaryInLeftAt(0)).toBe(true); // très bon (gauche) actif
      expect(c.getIntervalText(5)).toBe('x ≤ 33'); // très bon inclut 33
      expect(c.getIntervalText(4)).toBe('x > 33'); // bon exclut 33
    });

    it('bascule sur « bon » → intervalles cohérents (TB exclut, Bon inclut)', () => {
      const c = makeComponent(makeBlock({ score_5_sup: 33 }));
      c.toggleBoundaryInclusionAt(0); // score_5_sup_inclusive → false

      expect(c.isBoundaryInLeftAt(0)).toBe(false); // bon (droite) actif
      expect(c.getIntervalText(5)).toBe('x < 33'); // très bon exclut 33
      expect(c.getIntervalText(4)).toBe('x ≥ 33'); // bon inclut 33
    });
  });

  describe('#451 — changement de sens : grille de bornes réinitialisée', () => {
    it('réinitialise valeurs et inclusivités au passage croissant → décroissant', () => {
      const block = makeBlock({
        sens_variation: 'CROISSANT',
        score_1_sup: 10, score_2_inf: 10, score_2_sup: 20, score_3_inf: 20,
        score_1_sup_inclusive: false, score_2_sup_inclusive: false,
      });
      const c = makeComponent(block);

      c.onSensVariationChange('DECROISSANT');

      expect(block.sens_variation).toBe('DECROISSANT');
      // Toutes les bornes effacées
      for (let lvl = 1 as 1 | 2 | 3 | 4 | 5; lvl <= 5; lvl++) {
        expect((block as any)[`score_${lvl}_inf`]).toBeNull();
        expect((block as any)[`score_${lvl}_sup`]).toBeNull();
      }
      // Inclusivités remises à true
      for (let lvl = 1; lvl <= 5; lvl++) {
        expect((block as any)[`score_${lvl}_sup_inclusive`]).toBe(true);
      }
    });

    it('ne fait rien si le sens est identique', () => {
      const block = makeBlock({ sens_variation: 'CROISSANT', score_1_sup: 10 });
      const c = makeComponent(block);
      c.onSensVariationChange('CROISSANT');
      expect(block.score_1_sup).toBe(10); // inchangé
    });
  });
});
