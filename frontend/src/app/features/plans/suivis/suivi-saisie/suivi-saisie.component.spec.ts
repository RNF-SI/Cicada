/**
 * Tests unitaires pour SuiviSaisieComponent — saisie type-aware des indicateurs
 * de réponse et rappel de la grille d'évaluation (#452/#464/#465).
 *
 * On teste les helpers purs (qui ne dépendent que de `ctrl.value`) sans monter
 * le composant complet.
 */
import { computed, signal } from '@angular/core';
import { FormArray, FormBuilder, FormGroup } from '@angular/forms';
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
  // #542 — la page de saisie ne concerne que les indicateurs de RÉPONSE :
  // les métriques d'état/pression liées à l'action ne doivent pas remonter.
  // ---------------------------------------------------------------------------
  describe('responseMetriques (#542)', () => {
    it('ne garde que les métriques des indicateurs de réponse', () => {
      const c = comp();
      const op: any = {
        metriques: [
          { id_metrique: 1, indicateur_type: 'REPONSE' },
          { id_metrique: 2, indicateur_type: 'ETAT' },
          { id_metrique: 3, indicateur_type: 'PRESSION' },
          { id_metrique: 4, indicateur_type: 'reponse' }, // casse tolérée
          { id_metrique: 5 }, // type absent → exclu
        ],
      };
      const ids = (c as any).responseMetriques(op).map((m: any) => m.id_metrique);
      expect(ids).toEqual([1, 4]);
    });

    it('renvoie une liste vide sans métriques', () => {
      const c = comp();
      expect((c as any).responseMetriques({})).toEqual([]);
    });
  });

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
  // Multi-blocs ET/OU (#516 — explication du calcul combiné affichée en clair)
  // ---------------------------------------------------------------------------
  describe('isMultiBlock (gate de l\'explication ET/OU)', () => {
    const c = comp();
    it('vrai dès qu\'il y a au moins un bloc complémentaire', () => {
      expect(c.isMultiBlock(ctrlOf({ meta: { score_blocks: [{ position: 1, logical_op: 'OR' }] } }))).toBe(true);
    });
    it('faux pour une métrique mono-bloc (aucun bloc complémentaire)', () => {
      expect(c.isMultiBlock(ctrlOf({ meta: { score_blocks: [] } }))).toBe(false);
      expect(c.isMultiBlock(ctrlOf({ meta: {} }))).toBe(false);
      expect(c.isMultiBlock(ctrlOf({}))).toBe(false);
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

// -----------------------------------------------------------------------------
// #560 — saisie du temps de travail réalisé (lignes RH)
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — lignes RH (#560)', () => {
  const fb = new FormBuilder();

  /**
   * Composant minimal : `hydrateRhArray` / `sumRh` ne touchent que le
   * FormArray `rhLignes` et le FormBuilder.
   */
  function rhComp(): any {
    const c: any = comp();
    c.fb = fb;
    c.form = fb.group({ rhLignes: fb.array<FormGroup>([]) });
    Object.defineProperty(c, 'rhLignesFA', {
      get: () => c.form.get('rhLignes') as FormArray<FormGroup>,
    });
    return c;
  }

  // Prévu : le poste 7 (financé) sur 8 j ; un poste de bénévoles (non financé) sur 5 j.
  const P1 = { id_operation_annee_rh: 11, id_poste: 7, id_organisme: null, jours: '8.00', finance: true };
  const F_BENEVOLE = { id_operation_annee_rh: 12, id_poste: 3, id_organisme: null, jours: '5.00', finance: false };
  /** Réel rattaché à une ligne prévue via la FK. */
  const reelDe = (prev: any, extra: any) => ({ ...prev, ...extra });

  describe('hydrateRhArray', () => {
    it('pré-remplit le prévu et y fusionne le réalisé correspondant', () => {
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1],
        realisation: { rh_lignes: [reelDe(P1, { jours: '6.50' })] },
      });
      expect(c.rhLignesFA.length).toBe(1);
      const v = c.rhLignesFA.at(0).value;
      expect(v.id_poste).toBe(7);
      expect(v.plan_jours).toBe('8.00');
      expect(v.jours).toBe('6.50');
    });

    it('laisse le réalisé vide quand rien n\'a été saisi', () => {
      const c = rhComp();
      c.hydrateRhArray({ rh_lignes: [P1], realisation: null });
      expect(c.rhLignesFA.at(0).value.jours).toBeNull();
      expect(c.rhLignesFA.at(0).value.plan_jours).toBe('8.00');
    });

    it('apparie via la FK, quel que soit l\'ordre renvoyé', () => {
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1, F_BENEVOLE],
        realisation: { rh_lignes: [reelDe(F_BENEVOLE, { jours: '4.25' }), reelDe(P1, { jours: '9.00' })] },
      });
      expect(c.rhLignesFA.at(0).value.jours).toBe('9.00');
      expect(c.rhLignesFA.at(1).value.jours).toBe('4.25');
    });

    it('garde une seule ligne quand le suivi ré-attribue le temps à un autre poste', () => {
      // Le prévu était « poste 7, financé » ; en réalité ce sont des bénévoles.
      // La FK maintient le lien : une ligne, pas un prévu orphelin + un réel isolé.
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1],
        realisation: {
          rh_lignes: [{
            id_operation_annee_rh: 11,
            id_poste: 3, id_organisme: null, jours: '7.50', finance: false,
          }],
        },
      });
      expect(c.rhLignesFA.length).toBe(1);
      const v = c.rhLignesFA.at(0).value;
      expect(v.id_poste).toBe(3);           // cible = celle du réel
      expect(v.finance).toBe(false);        // financement du réel
      expect(v.plan_jours).toBe('8.00');    // référence du prévu conservée
      expect(v.plan_finance).toBe(true);    // …avec SON financement d'origine
    });

    it('ajoute les lignes réalisées sans lien (réalisé non prévu)', () => {
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1],
        realisation: {
          rh_lignes: [{ id_operation_annee_rh: null, id_poste: 42, id_organisme: null, jours: '3.00', finance: true }],
        },
      });
      expect(c.rhLignesFA.length).toBe(2);
      const ajoutee = c.rhLignesFA.at(1).value;
      expect(ajoutee.id_poste).toBe(42);
      expect(ajoutee.plan_jours).toBeNull(); // non prévue
      expect(ajoutee.jours).toBe('3.00');
    });

    it('vide le tableau sans année active', () => {
      const c = rhComp();
      c.hydrateRhArray({ rh_lignes: [P1], realisation: null });
      c.hydrateRhArray(null);
      expect(c.rhLignesFA.length).toBe(0);
    });
  });

  describe('sumRh', () => {
    function seeded() {
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1, F_BENEVOLE],
        realisation: { rh_lignes: [reelDe(P1, { jours: '6.00' }), reelDe(F_BENEVOLE, { jours: '4.00' })] },
      });
      return c;
    }

    it('totalise le prévu et le réalisé', () => {
      const c = seeded();
      expect(c.sumRh('plan_jours')).toBe(13);
      expect(c.sumRh('jours')).toBe(10);
    });

    it('ventile financé / non financé — la valorisation visée par #560', () => {
      const c = seeded();
      expect(c.sumRh('plan_jours', true)).toBe(8);
      expect(c.sumRh('plan_jours', false)).toBe(5);
      expect(c.sumRh('jours', true)).toBe(6);
      expect(c.sumRh('jours', false)).toBe(4);
    });

    it('ventile chaque colonne selon SON financement après ré-attribution', () => {
      // Prévu : 8 j financés. Réel : 7,5 j par un bénévole (non financé).
      // Le prévisionnel doit rester du côté financé.
      const c = rhComp();
      c.hydrateRhArray({
        rh_lignes: [P1],
        realisation: {
          rh_lignes: [{ id_operation_annee_rh: 11, id_poste: 3, id_organisme: null, jours: '7.50', finance: false }],
        },
      });
      expect(c.sumRh('plan_jours', true)).toBe(8);
      expect(c.sumRh('plan_jours', false)).toBe(0);
      expect(c.sumRh('jours', true)).toBe(0);
      expect(c.sumRh('jours', false)).toBe(7.5);
    });

    it('ignore les cellules vides', () => {
      const c = rhComp();
      c.hydrateRhArray({ rh_lignes: [P1], realisation: null });
      expect(c.sumRh('jours')).toBe(0);
    });
  });

  describe('setRhTarget', () => {
    /** Le mode dépend de l'action : postes si déclinée, sinon organismes. */
    function rhCompMode(mode: 'postes' | 'organismes'): any {
      const c = rhComp();
      c.rhMode = () => mode;
      return c;
    }

    it('bascule vers un poste et efface l\'organisme', () => {
      const c = rhCompMode('postes');
      c.postes = signal([]);
      c.addRhLigne();
      const ctrl = c.rhLignesFA.at(0);
      ctrl.get('id_organisme')!.setValue(3);
      c.setRhTarget(ctrl, 7);
      expect(ctrl.value.id_poste).toBe(7);
      expect(ctrl.value.id_organisme).toBeNull();
    });

    it('applique le financement par défaut du poste choisi', () => {
      const c = rhCompMode('postes');
      c.postes = signal([{ id_poste: 3, libelle: 'Bénévole', finance_par_defaut: false }]);
      c.addRhLigne();
      const ctrl = c.rhLignesFA.at(0);
      expect(ctrl.value.finance).toBe(true);
      c.setRhTarget(ctrl, 3);
      expect(ctrl.value.id_poste).toBe(3);
      expect(ctrl.value.finance).toBe(false);
    });

    it('cible un organisme hors déclinaison par poste', () => {
      const c = rhCompMode('organismes');
      c.addRhLigne();
      const ctrl = c.rhLignesFA.at(0);
      ctrl.get('id_poste')!.setValue(7);
      c.setRhTarget(ctrl, 2);
      expect(ctrl.value.id_organisme).toBe(2);
      expect(ctrl.value.id_poste).toBeNull();
    });

    it('encode la cible courante', () => {
      const c = rhCompMode('postes');
      c.postes = signal([]);
      c.addRhLigne();
      const ctrl = c.rhLignesFA.at(0);
      expect(c.rhTargetValue(ctrl)).toBeNull();
      ctrl.get('id_poste')!.setValue(7);
      expect(c.rhTargetValue(ctrl)).toBe(7);
      ctrl.get('id_poste')!.setValue(null);
      ctrl.get('id_organisme')!.setValue(3);
      expect(c.rhTargetValue(ctrl)).toBe(3);
    });
  });
});
