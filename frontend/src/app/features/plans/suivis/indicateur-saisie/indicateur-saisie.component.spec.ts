/**
 * Tests unitaires — IndicateurSaisieComponent (#510).
 *
 * On teste la logique métier de l'éditeur unifié (forçage manuel du résultat,
 * réouverture depuis le récap, scoring d'une métrique) via des méthodes
 * prototype, sans monter le composant complet.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { signal } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
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
  // metriqueCellLines — cellule multi-blocs du tableau récap (#573)
  // ---------------------------------------------------------------------------
  describe('metriqueCellLines (#573)', () => {
    const c = comp();
    const met: any = {
      bloc_intitule: 'Flux de phosphore', unite: 'kg P/an',
      score_3_inf: 100, score_3_sup: 150,
      score_blocks: [
        {
          position: 2, logical_op: 'OR', intitule: "Flux d'azote", unite: 'kg N/an',
          score_3_inf: 600, score_3_sup: 1000,
        },
      ],
    };

    it('produit une ligne par bloc (principal + complémentaires) avec l’opérateur', () => {
      const lines = c.metriqueCellLines(met, 3);
      expect(lines.length).toBe(2);
      expect(lines[0].label).toContain('Flux de phosphore');
      expect(lines[0].text).toContain('100');
      expect(lines[0].text).toContain('150');
      expect(lines[1].label).toContain("Flux d'azote");
      expect(lines[1].op).toBe('OR');
      expect(lines[1].text).toContain('600');
    });

    it('n’ajoute pas de ligne pour un bloc sans intervalle à ce palier', () => {
      // Au palier 1, aucun des blocs n'a de bornes → cellule vide.
      expect(c.metriqueCellLines(met, 1).length).toBe(0);
    });
  });

  // ---------------------------------------------------------------------------
  // weightedMetricMean — moyenne pondérée brute (#548) partagée par le score
  // auto et l'affichage de la moyenne.
  // ---------------------------------------------------------------------------
  describe('weightedMetricMean (#548)', () => {
    const setup = (metriques: any[]) => {
      const c = comp();
      (c as any).formTick = () => 0;
      (c as any).indicateur = () => ({ metriques });
      (c as any).metricScore = (m: any) => m._score;
      return c;
    };
    it('renvoie la moyenne pondérée non arrondie', () => {
      const c = setup([{ _score: 1, ponderation: 1 }, { _score: 4, ponderation: 1 }]);
      expect(c.weightedMetricMean()).toBeCloseTo(2.5, 5);
    });
    it('pondère par `ponderation`', () => {
      const c = setup([{ _score: 1, ponderation: 4 }, { _score: 5, ponderation: 1 }]);
      expect(c.weightedMetricMean()).toBeCloseTo(1.8, 5); // (1×4 + 5×1) / 5
    });
    it('ignore les métriques non scorées et renvoie null si aucune ne l’est', () => {
      expect(setup([{ _score: null, ponderation: 1 }, { _score: 3, ponderation: 1 }]).weightedMetricMean()).toBeCloseTo(3, 5);
      expect(setup([{ _score: null, ponderation: 1 }]).weightedMetricMean()).toBeNull();
      expect(setup([]).weightedMetricMean()).toBeNull();
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

    // #519 — l'état « indéterminé » est forçable manuellement (score 0 = rond gris).
    it('permet de forcer l\'état indéterminé (score 0)', () => {
      const c = comp();
      (c as any).scoreOverride = signal<number | null>(3);
      c.pickManualScore(0);
      expect(c.scoreOverride()).toBe(0);
      expect(c.scoreToLevel(0)).toBe('no-data');
    });
  });

  // ---------------------------------------------------------------------------
  // #510 (retour de test) — le bloc « résultat automatique » est grisé dès que
  // la saisie manuelle (forçage) est sélectionnée, pour ne pas perdre l'utilisateur.
  // ---------------------------------------------------------------------------
  describe('autoResultDimmed', () => {
    it('grise le résultat automatique quand le forçage manuel est actif', () => {
      const c = comp();
      (c as any).manualOverride = signal(true);
      expect(c.autoResultDimmed()).toBe(true);
    });

    it('laisse le résultat automatique pleinement visible en mode auto', () => {
      const c = comp();
      (c as any).manualOverride = signal(false);
      expect(c.autoResultDimmed()).toBe(false);
    });

    it('suit la bascule de la case « Forcer le résultat manuellement »', () => {
      const c = comp();
      (c as any).manualOverride = signal(false);
      (c as any).scoreOverride = signal<number | null>(null);
      (c as any).liveAutoScore = signal<number | null>(3);
      c.setManualOverride(true);
      expect(c.autoResultDimmed()).toBe(true);
      c.setManualOverride(false);
      expect(c.autoResultDimmed()).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // #464/#465 — saisie d'une métrique CHIFFRE/TEXTE via un select des options
  // de la grille (au lieu d'un champ texte libre).
  // ---------------------------------------------------------------------------
  describe('metricSaisieMode / metricGridOptions', () => {
    const c = comp();
    const TEXTE: any = {
      type_metrique_mnemonique: 'TEXTE',
      score_1_label: 'Très mauvais', score_2_label: 'Mauvais', score_3_label: 'Moyen',
      score_4_label: 'Bon', score_5_label: 'Très bon', inactive_levels: [],
    };
    const CHIFFRE: any = {
      type_metrique_mnemonique: 'CHIFFRE',
      score_1_val: 0, score_2_val: 25, score_3_val: 50, score_4_val: 75, score_5_val: 100,
      inactive_levels: [2],
    };
    const NUMERIQUE: any = { type_metrique_mnemonique: 'NUMERIQUE', score_1_inf: 0, score_1_sup: 10 };

    it('TEXTE → select des libellés', () => {
      expect(c.metricSaisieMode(TEXTE)).toBe('text-select');
      expect(c.metricGridOptions(TEXTE)).toEqual(['Très mauvais', 'Mauvais', 'Moyen', 'Bon', 'Très bon']);
    });
    it('CHIFFRE → select des valeurs (niveaux inactifs exclus)', () => {
      expect(c.metricSaisieMode(CHIFFRE)).toBe('chiffre-select');
      expect(c.metricGridOptions(CHIFFRE)).toEqual(['0', '50', '75', '100']); // niveau 2 inactif exclu
    });
    it('NUMERIQUE → champ libre', () => {
      expect(c.metricSaisieMode(NUMERIQUE)).toBe('free');
      expect(c.metricGridOptions(NUMERIQUE)).toEqual([]);
    });

    // #464 — les valeurs CHIFFRE stockées en DecimalField (« 2.000 ») ne doivent
    // plus afficher les zéros décimaux superflus dans le select.
    it('CHIFFRE → retire les zéros décimaux superflus (2.000 → « 2 », 2.5000 → « 2.5 »)', () => {
      const CHIFFRE_DEC: any = {
        type_metrique_mnemonique: 'CHIFFRE',
        score_1_val: '0.000', score_2_val: '2.000', score_3_val: '2.5000',
        score_4_val: '10.2500', score_5_val: '100.0000', inactive_levels: [],
      };
      expect(c.metricGridOptions(CHIFFRE_DEC)).toEqual(['0', '2', '2.5', '10.25', '100']);
    });
  });

  // ---------------------------------------------------------------------------
  // #375 — Saisie des résultats verrouillée tant que le plan n'est pas validé.
  // ---------------------------------------------------------------------------
  // ---------------------------------------------------------------------------
  // #453 (retour de test 06/07) — grille à paliers dupliqués : la saisie doit
  // désigner les paliers en conflit au lieu de rester muette.
  // ---------------------------------------------------------------------------
  describe('ambiguousLevels / hasAmbiguousGrid (#453)', () => {
    // Grille exacte du retour de test : Bien / Bien / Cool / Très cool / Très cool.
    const MET: any = {
      id_metrique: 7,
      type_metrique_mnemonique: 'TEXTE',
      score_1_label: 'Bien', score_2_label: 'Bien', score_3_label: 'Cool',
      score_4_label: 'Très cool', score_5_label: 'Très cool',
      inactive_levels: [],
    };

    function withValue(value: string) {
      const c = comp();
      (c as any).form = new FormGroup({ m_7: new FormControl(value) });
      return c;
    }

    it('désigne les deux paliers en conflit quand le libellé est dupliqué', () => {
      const c = withValue('Bien');
      expect(c.ambiguousLevels(MET)).toEqual([1, 2]);
      expect(c.hasAmbiguousGrid(MET)).toBe(true);
    });

    it('désigne le second groupe de doublons', () => {
      const c = withValue('Très cool');
      expect(c.ambiguousLevels(MET)).toEqual([4, 5]);
    });

    it('reste silencieux sur un libellé unique (score auto)', () => {
      const c = withValue('Cool');
      expect(c.ambiguousLevels(MET)).toEqual([]);
      expect(c.hasAmbiguousGrid(MET)).toBe(false);
    });

    it('reste silencieux quand aucune valeur n\'est choisie', () => {
      const c = withValue('');
      expect(c.hasAmbiguousGrid(MET)).toBe(false);
    });
  });

  describe('statusAllowsSuivi / applyReadonlyState', () => {
    const c = comp();

    it('autorise la saisie uniquement sur un plan validé/actif', () => {
      expect(c.statusAllowsSuivi('valide')).toBe(true);
      expect(c.statusAllowsSuivi('modifie')).toBe(true);
    });

    it('bloque la saisie hors validation (brouillon, CSRPN, archive, null)', () => {
      for (const s of ['draft', 'avis_csrpn', 'comite_consultatif', 'arrete_pref', 'archive', null, undefined]) {
        expect(c.statusAllowsSuivi(s)).toBe(false);
      }
    });

    it('applyReadonlyState désactive le formulaire quand la saisie est interdite', () => {
      const c2 = comp();
      const form = new FormGroup({ m_1: new FormControl('x') });
      (c2 as any).form = form;
      (c2 as any).canEnterSuivi = () => false;
      (c2 as any).applyReadonlyState();
      expect(form.disabled).toBe(true);
    });

    it('applyReadonlyState réactive le formulaire quand la saisie est permise', () => {
      const c2 = comp();
      const form = new FormGroup({ m_1: new FormControl('x') });
      form.disable();
      (c2 as any).form = form;
      (c2 as any).canEnterSuivi = () => true;
      (c2 as any).applyReadonlyState();
      expect(form.enabled).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // #528 — Effacer les valeurs d'une métrique existante doit supprimer la mesure.
  // ---------------------------------------------------------------------------
  describe('validate — effacement des valeurs (#528)', () => {
    function setupValidate(formValue: string, existing: any) {
      const c2 = comp();
      const enjeu: any = {
        updateMesure: jest.fn(() => ({ subscribe: () => {} })),
        createMesure: jest.fn(() => ({ subscribe: () => {} })),
        deleteMesure: jest.fn(() => ({ subscribe: () => {} })),
        upsertIndicateurMesure: jest.fn(),
        deleteIndicateurMesure: jest.fn(),
      };
      (c2 as any).enjeuService = enjeu;
      (c2 as any).indicateur = () => ({ metriques: [{ id_metrique: 1, score_blocks: [] }] });
      (c2 as any).indicateurId = () => 42;
      (c2 as any).selectedYear = () => 2025;
      (c2 as any).canEnterSuivi = () => true;
      (c2 as any).isSaving = signal(false);
      (c2 as any).manualOverride = () => false;
      (c2 as any).scoreOverride = () => null;
      (c2 as any).overrideId = () => null;
      (c2 as any).commentaireOverride = () => '';
      (c2 as any).snack = { open: jest.fn() };
      (c2 as any).translate = { instant: (k: string) => k };
      (c2 as any).loadResolvedAndMesures = jest.fn();
      (c2 as any).mode = signal('edit');
      (c2 as any).form = new FormGroup({ m_1: new FormControl(formValue) });
      const map = new Map<number, any>();
      if (existing) map.set(1, existing);
      (c2 as any).mesuresByMetrique = map;
      return { c2, enjeu };
    }

    it('supprime la mesure existante quand toutes les valeurs sont effacées', () => {
      const { c2, enjeu } = setupValidate('', { id_mesure: 7 });
      (c2 as any).validate();
      expect(enjeu.deleteMesure).toHaveBeenCalledWith(7);
      expect(enjeu.updateMesure).not.toHaveBeenCalled();
      expect(enjeu.createMesure).not.toHaveBeenCalled();
    });

    it('ne supprime rien si le champ est vide et aucune mesure préexistante', () => {
      const { c2, enjeu } = setupValidate('', null);
      (c2 as any).validate();
      expect(enjeu.deleteMesure).not.toHaveBeenCalled();
      expect(enjeu.createMesure).not.toHaveBeenCalled();
    });

    it('met à jour la mesure existante quand une valeur est saisie', () => {
      const { c2, enjeu } = setupValidate('5', { id_mesure: 7 });
      (c2 as any).validate();
      expect(enjeu.updateMesure).toHaveBeenCalled();
      expect(enjeu.deleteMesure).not.toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------------
  // #589 — « Modifier l'indicateur » remplacé par « Voir l'indicateur »
  // ---------------------------------------------------------------------------
  describe('actions du hero (#589)', () => {
    const template = readFileSync(join(__dirname, 'indicateur-saisie.component.html'), 'utf8');

    it('n\'expose plus de bouton de modification de l\'indicateur', () => {
      expect(template).not.toContain('plans.suivis.indicateur.editIndicateur');
    });

    it('expose un bouton « Voir l\'indicateur » vers le détail de l\'enjeu', () => {
      expect(template).toContain('plans.suivis.indicateur.viewIndicateur');
      expect(template).toContain('fi-rr-eye');
    });

    it('déclare la clé i18n viewIndicateur et plus editIndicateur', () => {
      const i18n = JSON.parse(
        readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
      );
      const bloc = i18n.plans.suivis.indicateur;
      expect(bloc.viewIndicateur).toBe("Voir l'indicateur");
      expect(bloc.editIndicateur).toBeUndefined();
    });
  });
});
