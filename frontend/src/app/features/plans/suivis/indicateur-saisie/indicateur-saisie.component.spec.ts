/**
 * Tests unitaires — IndicateurSaisieComponent (#510).
 *
 * On teste la logique métier de l'éditeur unifié (forçage manuel du résultat,
 * réouverture depuis le récap, scoring d'une métrique) via des méthodes
 * prototype, sans monter le composant complet.
 */
import { signal } from '@angular/core';
import { IndicateurSaisieComponent } from './indicateur-saisie.component';

function comp(): IndicateurSaisieComponent {
  return Object.create(IndicateurSaisieComponent.prototype) as IndicateurSaisieComponent;
}

describe('IndicateurSaisieComponent — éditeur unifié (#510)', () => {

  // ---------------------------------------------------------------------------
  // valueToScore — palier d'une métrique selon ses seuils
  // ---------------------------------------------------------------------------
  describe('valueToScore', () => {
    const c = comp();
    const met: any = {
      score_1_inf: 0, score_1_sup: 1,
      score_2_inf: 1, score_2_sup: 3,
      score_3_inf: 3, score_3_sup: 5,
      score_4_inf: 5, score_4_sup: 10,
      score_5_inf: 10, score_5_sup: 60,
    };
    it('classe la valeur dans le bon palier', () => {
      expect(c.valueToScore('0.5', met)).toBe(1);
      expect(c.valueToScore('4', met)).toBe(3);
      expect(c.valueToScore('8', met)).toBe(4);
      expect(c.valueToScore('20', met)).toBe(5);
    });
    it('tolère la virgule décimale française', () => {
      expect(c.valueToScore('6,5', met)).toBe(4);
    });
    it('retourne null pour une valeur non numérique', () => {
      expect(c.valueToScore('', met)).toBeNull();
      expect(c.valueToScore('abc', met)).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // setManualOverride — la case « Forcer le résultat manuellement »
  // ---------------------------------------------------------------------------
  describe('setManualOverride', () => {
    it('à l\'activation, initialise le score forcé sur le score auto courant', () => {
      const c = comp();
      (c as any).manualOverride = signal(false);
      (c as any).scoreOverride = signal<number | null>(null);
      (c as any).liveAutoScore = signal<number | null>(4);
      c.setManualOverride(true);
      expect(c.manualOverride()).toBe(true);
      expect(c.scoreOverride()).toBe(4); // pré-rempli depuis l'auto
    });

    it('ne réécrit pas un score forcé déjà choisi', () => {
      const c = comp();
      (c as any).manualOverride = signal(false);
      (c as any).scoreOverride = signal<number | null>(2);
      (c as any).liveAutoScore = signal<number | null>(5);
      c.setManualOverride(true);
      expect(c.scoreOverride()).toBe(2); // conservé
    });

    it('désactivation : conserve le score en mémoire (toggle réversible)', () => {
      const c = comp();
      (c as any).manualOverride = signal(true);
      (c as any).scoreOverride = signal<number | null>(3);
      (c as any).liveAutoScore = signal<number | null>(1);
      c.setManualOverride(false);
      expect(c.manualOverride()).toBe(false);
      expect(c.scoreOverride()).toBe(3); // non effacé
    });
  });

  // ---------------------------------------------------------------------------
  // editFromRecap — réouverture de l'éditeur en préservant l'état overridden
  // (cœur du bug #510 : la saisie manuelle ne doit pas être perdue)
  // ---------------------------------------------------------------------------
  describe('editFromRecap', () => {
    it('rouvre en mode édition AVEC forçage manuel si un override existe', () => {
      const c = comp();
      (c as any).isOverridden = signal(true);
      (c as any).manualOverride = signal(false);
      (c as any).mode = signal<'recap' | 'edit'>('recap');
      c.editFromRecap();
      expect(c.manualOverride()).toBe(true);
      expect(c.mode()).toBe('edit');
    });

    it('rouvre en mode auto si aucun override', () => {
      const c = comp();
      (c as any).isOverridden = signal(false);
      (c as any).manualOverride = signal(true);
      (c as any).mode = signal<'recap' | 'edit'>('recap');
      c.editFromRecap();
      expect(c.manualOverride()).toBe(false);
      expect(c.mode()).toBe('edit');
    });
  });

  // ---------------------------------------------------------------------------
  // pickManualScore
  // ---------------------------------------------------------------------------
  describe('pickManualScore', () => {
    it('fixe le score forcé', () => {
      const c = comp();
      (c as any).scoreOverride = signal<number | null>(null);
      c.pickManualScore(5);
      expect(c.scoreOverride()).toBe(5);
    });
  });
});
