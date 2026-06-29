/**
 * Tests unitaires pour SuiviSaisieComponent — saisie type-aware des indicateurs
 * de réponse et rappel de la grille d'évaluation (#452/#464/#465).
 *
 * On teste les helpers purs (qui ne dépendent que de `ctrl.value`) sans monter
 * le composant complet.
 */
import { SuiviSaisieComponent } from './suivi-saisie.component';

/** Faux AbstractControl minimal : seul `value` est lu par les helpers. */
function ctrlOf(value: unknown): any {
  return { value };
}

function comp(): SuiviSaisieComponent {
  return Object.create(SuiviSaisieComponent.prototype) as SuiviSaisieComponent;
}

describe('SuiviSaisieComponent — indicateurs de réponse', () => {
  // ---------------------------------------------------------------------------
  // saisieMode (#452/#464/#465)
  // ---------------------------------------------------------------------------
  describe('saisieMode', () => {
    const c = comp();
    it('grille TEXTE → menu déroulant des libellés', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'GRILLE', type_mnemo: 'TEXTE' }))).toBe('text-select');
    });
    it('grille CHIFFRE → menu déroulant des valeurs', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'GRILLE', type_mnemo: 'CHIFFRE' }))).toBe('chiffre-select');
    });
    it('CHIFFRE/NUMERIQUE simple → champ numérique', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'SIMPLE', type_mnemo: 'NUMERIQUE' }))).toBe('number');
      expect(c.saisieMode(ctrlOf({ format_mnemo: null, type_mnemo: 'CHIFFRE' }))).toBe('number');
    });
    it('défaut → texte libre', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'SIMPLE', type_mnemo: 'TEXTE' }))).toBe('text');
    });
  });

  // ---------------------------------------------------------------------------
  // isGrille + gridLevels (#452 — rappel de la grille d'évaluation)
  // ---------------------------------------------------------------------------
  describe('isGrille', () => {
    const c = comp();
    it('vrai uniquement pour le format GRILLE', () => {
      expect(c.isGrille(ctrlOf({ format_mnemo: 'GRILLE' }))).toBe(true);
      expect(c.isGrille(ctrlOf({ format_mnemo: 'SIMPLE' }))).toBe(false);
      expect(c.isGrille(ctrlOf({}))).toBe(false);
    });
  });

  describe('gridLevels', () => {
    const c = comp();

    it('grille TEXTE : 5 niveaux libellés + niveau actif = libellé saisi', () => {
      const meta = {
        type_metrique_mnemonique: 'TEXTE',
        score_1_label: 'Non engagé', score_2_label: 'Balisage partiel',
        score_3_label: 'Balisage complet', score_4_label: 'Balisage et surveillance',
        score_5_label: 'Pleinement opérationnelle',
      };
      const levels = c.gridLevels(ctrlOf({ meta, valeur: 'Balisage complet' }));
      expect(levels.map(l => l.text)).toEqual([
        'Non engagé', 'Balisage partiel', 'Balisage complet',
        'Balisage et surveillance', 'Pleinement opérationnelle',
      ]);
      expect(levels.map(l => l.name)).toEqual(['very-bad', 'bad', 'neutral', 'good', 'very-good']);
      expect(levels.find(l => l.active)?.level).toBe(3); // « Balisage complet »
    });

    it('grille CHIFFRE : niveau actif = valeur saisie', () => {
      const meta = {
        type_metrique_mnemonique: 'CHIFFRE',
        score_1_val: 0, score_2_val: 25, score_3_val: 50, score_4_val: 75, score_5_val: 100,
      };
      const levels = c.gridLevels(ctrlOf({ meta, valeur: '75' }));
      expect(levels.map(l => l.text)).toEqual(['0', '25', '50', '75', '100']);
      expect(levels.find(l => l.active)?.level).toBe(4);
    });

    it('marque les niveaux désactivés (inactive_levels)', () => {
      const meta = {
        type_metrique_mnemonique: 'CHIFFRE', inactive_levels: [1, 5],
        score_2_val: 25, score_3_val: 50, score_4_val: 75,
      };
      const levels = c.gridLevels(ctrlOf({ meta, valeur: '' }));
      expect(levels.filter(l => l.inactive).map(l => l.level)).toEqual([1, 5]);
      expect(levels.every(l => !l.active)).toBe(true); // pas de valeur → aucun actif
    });

    it('retourne [] si pas de meta', () => {
      expect(c.gridLevels(ctrlOf({}))).toEqual([]);
    });
  });
});
