/**
 * Tests unitaires pour SuiviSaisieComponent — saisie type-aware des indicateurs
 * de réponse et rappel de la grille d'évaluation (#452/#464/#465).
 *
 * On teste les helpers purs (qui ne dépendent que de `ctrl.value`) sans monter
 * le composant complet.
 */
import { computed, signal } from '@angular/core';
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
    const TEXTE_META = { score_1_label: 'A', score_2_label: 'B', score_3_label: 'C', score_4_label: 'D', score_5_label: 'E' };
    const CHIFFRE_META = { score_1_val: 0, score_2_val: 1, score_3_val: 2, score_4_val: 3, score_5_val: 4 };

    it('grille TEXTE → menu déroulant des libellés', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'GRILLE', type_mnemo: 'TEXTE', meta: TEXTE_META }))).toBe('text-select');
    });
    it('grille CHIFFRE → menu déroulant des valeurs', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'GRILLE', type_mnemo: 'CHIFFRE', meta: CHIFFRE_META }))).toBe('chiffre-select');
    });
    it('#464/#465 — CHIFFRE/TEXTE état/pression (format null, avec options) → select', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: null, type_mnemo: 'CHIFFRE', meta: CHIFFRE_META }))).toBe('chiffre-select');
      expect(c.saisieMode(ctrlOf({ format_mnemo: null, type_mnemo: 'TEXTE', meta: TEXTE_META }))).toBe('text-select');
    });
    it('réponse SIMPLE → champ libre (pas de select)', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'SIMPLE', type_mnemo: 'CHIFFRE', meta: CHIFFRE_META }))).toBe('number');
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'SIMPLE', type_mnemo: 'TEXTE', meta: TEXTE_META }))).toBe('text');
    });
    it('NUMERIQUE → champ numérique', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: 'GRILLE', type_mnemo: 'NUMERIQUE' }))).toBe('number');
    });
    it('CHIFFRE sans options → champ numérique', () => {
      expect(c.saisieMode(ctrlOf({ format_mnemo: null, type_mnemo: 'CHIFFRE' }))).toBe('number');
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

  // ---------------------------------------------------------------------------
  // Copie de l'emprise prévue + retour en arrière (#511)
  // ---------------------------------------------------------------------------
  describe('copyPlannedEmprise / undoCopyPlannedEmprise', () => {
    const PLANNED = { type: 'Point', coordinates: [1, 2] };

    // `structuredClone` (utilisé par copyPlannedEmprise) absent du runtime jsdom.
    beforeAll(() => {
      const g = globalThis as unknown as { structuredClone?: <T>(v: T) => T };
      g.structuredClone ??= (v) => JSON.parse(JSON.stringify(v));
    });

    /** Monte un composant avec les signaux d'emprise initialisés à la main. */
    function empriseComp(plannedGeom: unknown) {
      const c = comp();
      c.plannedGeom = signal<any>(plannedGeom) as any;
      c.pendingGeomRealisee = signal<any | undefined>(undefined);
      c.isEditingGeom = signal(false);
      const snap = signal<{ geom: any | undefined; editing: boolean } | null>(null);
      (c as any).empriseSnapshot = snap;
      c.canUndoCopyEmprise = computed(() => snap() != null) as any;
      return c;
    }

    it('copie l\'emprise prévue (clone), passe en édition et autorise l\'annulation', () => {
      const c = empriseComp(PLANNED);
      c.copyPlannedEmprise();
      expect(c.pendingGeomRealisee()).toEqual(PLANNED);
      expect(c.pendingGeomRealisee()).not.toBe(PLANNED); // clone, pas la même référence
      expect(c.isEditingGeom()).toBe(true);
      expect(c.canUndoCopyEmprise()).toBe(true);
    });

    it('ne fait rien s\'il n\'y a pas d\'emprise prévue', () => {
      const c = empriseComp(null);
      c.copyPlannedEmprise();
      expect(c.pendingGeomRealisee()).toBeUndefined();
      expect(c.isEditingGeom()).toBe(false);
      expect(c.canUndoCopyEmprise()).toBe(false);
    });

    it('revient en arrière en restaurant l\'état précédent', () => {
      const c = empriseComp(PLANNED);
      const previous = { type: 'Point', coordinates: [9, 9] };
      c.pendingGeomRealisee.set(previous);
      c.copyPlannedEmprise();
      expect(c.pendingGeomRealisee()).toEqual(PLANNED);

      c.undoCopyPlannedEmprise();
      expect(c.pendingGeomRealisee()).toBe(previous);
      expect(c.isEditingGeom()).toBe(false);
      expect(c.canUndoCopyEmprise()).toBe(false);
    });

    it('undo sans copie préalable est un no-op', () => {
      const c = empriseComp(PLANNED);
      c.pendingGeomRealisee.set(PLANNED);
      c.undoCopyPlannedEmprise();
      expect(c.pendingGeomRealisee()).toBe(PLANNED);
    });
  });
});
