/**
 * Tests unitaires pour SuiviSaisieComponent — saisie type-aware des indicateurs
 * de réponse et rappel de la grille d'évaluation (#452/#464/#465).
 *
 * On teste les helpers purs (qui ne dépendent que de `ctrl.value`) sans monter
 * le composant complet.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { computed, signal } from '@angular/core';
import { FormArray, FormBuilder, FormGroup } from '@angular/forms';
import { SuiviSaisieComponent } from './suivi-saisie.component';
import { hasSaisieRealisation } from '../action-status.util';
import { of } from 'rxjs';

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
    // #735 — action annuelle (pas de programmation globale).
    c.operation = signal<any>(null);
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

  describe('#759 — aucune ventilation : un seul temps de travail total', () => {
    const G_AGENT = { id_operation_annee_rh: 21, id_poste: null, id_organisme: null, jours: '25.00', finance: true, categorie_depense: 'fonctionnement' };
    const G_PART = { id_operation_annee_rh: 22, id_poste: null, id_organisme: null, jours: '6.00', finance: false, categorie_depense: 'benevolat_partenariat' };
    function noneComp(mode = 'none'): any {
      const c = rhComp();
      c.operation.set({ ventilation_mode: mode, declinaison_par_type_cout: false, declinaison_par_poste: false });
      return c;
    }

    it('prévu et réalisé en plusieurs lots fusionnent en une ligne', () => {
      const c = noneComp();
      expect(c.rhTotalUnique()).toBe(true);
      c.hydrateRhArray({
        rh_lignes: [G_AGENT, G_PART],
        realisation: { rh_lignes: [reelDe(G_AGENT, { jours: '20.00' }), reelDe(G_PART, { jours: '4.00' })] },
      });
      expect(c.rhLignesFA.length).toBe(1);
      const v = c.rhLignesFA.at(0).value;
      expect(Number(v.plan_jours)).toBe(31);
      expect(Number(v.jours)).toBe(24);
      expect(v.finance).toBe(true);
      expect(v.id_poste).toBeNull();
      expect(v.id_organisme).toBeNull();
    });

    it('sans prévu cette année : une ligne vide à saisir', () => {
      const c = noneComp();
      c.hydrateRhArray({ rh_lignes: [], realisation: null });
      expect(c.rhLignesFA.length).toBe(1);
      expect(c.rhLignesFA.at(0).value.jours).toBeNull();
    });

    it('par type de budget : les lots par catégorie restent distincts', () => {
      const c = noneComp('by_type');
      expect(c.rhTotalUnique()).toBe(false);
      c.hydrateRhArray({ rh_lignes: [G_AGENT, G_PART], realisation: null });
      expect(c.rhLignesFA.length).toBe(2);
    });

    it('gabarit : ni ajout ni suppression de ligne, ni sous-totaux agent / partenaire', () => {
      const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
      expect(html).toMatch(/@if \(!formVerrouille\(\) && !rhTotalUnique\(\)\) \{\s*<button type="button" class="rh-remove-btn"/);
      expect(html).toMatch(/@if \(!formVerrouille\(\) && !rhTotalUnique\(\)\) \{\s*<div class="rh-controls">/);
      expect(html).toMatch(/@if \(!rhTotalUnique\(\)\) \{\s*<tr class="rh-subtotal-row">/);
    });
  });

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

// -----------------------------------------------------------------------------
// #589 — retrait du bouton « Modifier l'action » depuis le suivi
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — actions du hero (#589)', () => {
  const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');

  it('n\'expose plus de bouton de modification de l\'action', () => {
    expect(template).not.toContain('plans.suivis.saisie.editAction');
    expect(template).not.toContain('goEditOperation()');
  });

  it('conserve l\'accès en consultation à la fiche action', () => {
    expect(template).toContain('plans.suivis.saisie.viewFiche');
  });

  it('ne déclare plus la clé i18n editAction', () => {
    const i18n = JSON.parse(
      readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
    );
    expect(i18n.plans.suivis.saisie.editAction).toBeUndefined();
    expect(i18n.plans.suivis.saisie.viewFiche).toBeDefined();
  });
});

// ===========================================================================
// #614 — budget PRÉVISIONNEL réaffiché dans le suivi (ventilation maximale)
// ===========================================================================
describe('SuiviSaisieComponent — budget prévisionnel (#614)', () => {
  /**
   * Année 2025, deux organismes. Le prévisionnel est reconstruit depuis les
   * lignes RH prévues (jours × coût jour) + les coûts saisis sur l'organisme,
   * puisqu'en ventilation maximale `budget_fonctionnement` n'est pas stocké.
   */
  function instance(): any {
    const c: any = comp();
    c.selectedYear = signal(2025);
    c.postes = signal([
      { id_poste: 1, id_organisme: 100, cout_jour: 300 },
      { id_poste: 2, id_organisme: 100, cout_jour: 80 },
      { id_poste: 3, id_organisme: 200, cout_jour: 300 },
    ]);
    c.operation = signal({
      // Ventilation maximale : seul mode (avec « type de budget + poste ») qui
      // calcule le coût salarial (#735 — les autres le saisissent).
      ventilation_mode: 'by_org_type_poste',
      operation_annees: [{
        annee: 2025,
        rh_lignes: [
          { id_poste: 1, categorie_depense: 'fonctionnement', jours: '10.00', finance: true },
          { id_poste: 2, categorie_depense: 'investissement', jours: '5.00', finance: true },
          { id_poste: 3, categorie_depense: 'fonctionnement', jours: '4.00', finance: true },
        ],
        organismes: [
          {
            id_organisme: 100, cout_stage: '200.00', cout_prestataire: '1000.00',
            autre_cout: '500.00', cout_prestataire_invest: '300.00', autre_cout_invest: null,
          },
          { id_organisme: 200, cout_prestataire: '150.00' },
        ],
      }],
    });
    c.organismesList = () => [{ id_organisme: 100, nom: 'A' }, { id_organisme: 200, nom: 'B' }];
    return c;
  }

  it('calcule le coût salarial prévu depuis les lignes RH prévues, par catégorie', () => {
    const c = instance();
    expect(c.prevCoutSalarial(2025, 100, 'fonctionnement')).toBe(3000); // 10 × 300
    expect(c.prevCoutSalarial(2025, 100, 'investissement')).toBe(400);  // 5 × 80
    expect(c.prevCoutSalarial(2025, 200, 'fonctionnement')).toBe(1200); // 4 × 300
    expect(c.prevCoutSalarial(2025, 200, 'investissement')).toBe(0);
  });

  it('totalise le prévu d\'un organisme (salarial + stage + prestataire + autres)', () => {
    const c = instance();
    // 3000 + 200 + 1000 + 500
    expect(c.prevOrgFonctTotal(2025, 100)).toBe(4700);
    // 400 + 300 + 0
    expect(c.prevOrgInvestTotal(2025, 100)).toBe(700);
    expect(c.prevOrgTotal(2025, 100)).toBe(5400);
  });

  it('cumule le prévu de tous les organismes', () => {
    const c = instance();
    expect(c.prevYearFonctTotal(2025)).toBe(4700 + 1200 + 150);
    expect(c.prevYearInvestTotal(2025)).toBe(700);
    expect(c.prevYearTotal(2025)).toBe(4700 + 1350 + 700);
  });

  it('renvoie 0 sur une année sans programmation', () => {
    const c = instance();
    expect(c.prevOrgTotal(2031, 100)).toBe(0);
    expect(c.prevYearTotal(2031)).toBe(0);
  });

  it('affiche une ligne prévisionnelle en regard de chaque coût réalisé', () => {
    const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    for (const key of [
      'table.coutSalarialPrev', 'table.coutStagePrev', 'table.coutPrestatairePrev',
      'table.autresCoutsFonctPrev', 'table.autresCoutsInvestPrev',
      'table.totalFonctPrev', 'table.totalInvestPrev',
      'table.budgetTotalOGPrev', 'table.budgetTotalPrev',
    ]) {
      expect(template).toContain(key);
    }
  });

  it('déclare toutes les clés i18n prévisionnelles', () => {
    const i18n = JSON.parse(
      readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
    );
    const t = i18n.plans.suivis.saisie.table;
    for (const key of [
      'coutSalarialPrev', 'coutStagePrev', 'coutPrestatairePrev',
      'autresCoutsFonctPrev', 'autresCoutsInvestPrev',
      'totalFonctPrev', 'totalInvestPrev', 'budgetTotalOGPrev', 'budgetTotalPrev',
    ]) {
      expect(t[key]).toBeDefined();
    }
  });
});

// ===========================================================================
// #623 — « Financé / Non financé » remplacés par un vocabulaire métier
// ===========================================================================
describe('Libellés RH financé / non financé (#623)', () => {
  const i18n = JSON.parse(
    readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
  );

  it('nomme les sous-totaux RH « Temps agent » / « Temps partenaire / bénévole »', () => {
    expect(i18n.plans.rh.finance).toBe('Temps agent (gestionnaire)');
    expect(i18n.plans.rh.nonFinance).toBe('Temps partenaire / bénévole (valorisé)');
  });

  it('ne mentionne plus « financé » dans les aides de saisie du temps de travail', () => {
    const rh = i18n.enjeux.operations.rh;
    for (const key of ['hintGlobal', 'addLineHint']) {
      expect(rh[key].toLowerCase()).not.toContain('financé');
    }
  });
});

// -----------------------------------------------------------------------------
// #615 — catégorie de dépense (menu déroulant) au lieu de « financé » (case)
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — catégorie de dépense du temps de travail (#615)', () => {
  const fb = new FormBuilder();

  function catComp(): any {
    const c: any = comp();
    c.fb = fb;
    // #735 — action annuelle (pas de programmation globale).
    c.operation = signal<any>(null);
    c.form = fb.group({ rhLignes: fb.array<FormGroup>([]) });
    Object.defineProperty(c, 'rhLignesFA', {
      get: () => c.form.get('rhLignes') as FormArray<FormGroup>,
    });
    return c;
  }

  it('dérive « financé » de la catégorie choisie', () => {
    const c = catComp();
    c.addRhLigne();
    const ctrl = c.rhLignesFA.at(0);

    c.setRhCategorie(ctrl, 'investissement');
    expect(ctrl.value.categorie_depense).toBe('investissement');
    expect(ctrl.value.finance).toBe(true);

    c.setRhCategorie(ctrl, 'benevolat_partenariat');
    expect(ctrl.value.categorie_depense).toBe('benevolat_partenariat');
    expect(ctrl.value.finance).toBe(false);

    c.setRhCategorie(ctrl, 'fonctionnement');
    expect(ctrl.value.finance).toBe(true);
  });

  it('conserve la catégorie saisie au suivi (le réalisé prime sur le prévu)', () => {
    const c = catComp();
    c.hydrateRhArray({
      rh_lignes: [{ id_operation_annee_rh: 1, id_poste: 7, jours: '8.00', finance: true, categorie_depense: 'fonctionnement' }],
      realisation: {
        rh_lignes: [{ id_operation_annee_rh: 1, id_poste: 7, jours: '8.00', finance: true, categorie_depense: 'investissement' }],
      },
    });
    expect(c.rhLignesFA.at(0).value.categorie_depense).toBe('investissement');
  });

  it('déduit la catégorie du financement pour les lignes antérieures à #597', () => {
    const c = catComp();
    c.hydrateRhArray({
      rh_lignes: [
        { id_operation_annee_rh: 1, id_poste: 7, jours: '8.00', finance: true },
        { id_operation_annee_rh: 2, id_poste: 3, jours: '5.00', finance: false },
      ],
      realisation: null,
    });
    expect(c.rhLignesFA.at(0).value.categorie_depense).toBe('fonctionnement');
    expect(c.rhLignesFA.at(1).value.categorie_depense).toBe('benevolat_partenariat');
  });

  it('remplace la case « Financé » par le menu déroulant dans le template', () => {
    const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    // #741 — le template a désormais des cases (réglages du suivi), mais plus
    // aucune dans le tableau du temps de travail.
    const rhTable = template.slice(template.indexOf('class="rh-table"'), template.indexOf('rh-controls'));
    expect(rhTable).not.toContain('<app-checkbox');
    expect(template).toContain('setRhCategorie(ctrl, $event)');
    expect(template).toContain('plans.rh.colCategorie');
  });

  it('déclare la clé i18n de l\'en-tête de colonne', () => {
    const i18n = JSON.parse(
      readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
    );
    expect(i18n.plans.rh.colCategorie).toBeDefined();
    expect(Object.keys(i18n.plans.rh.categorieDepense)).toEqual([
      'fonctionnement', 'investissement', 'benevolat_partenariat',
    ]);
  });
});

// -----------------------------------------------------------------------------
// #612 — ordre de saisie : le temps de travail (RH) AVANT le budget
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — ordre de saisie RH puis budget (#612)', () => {
  const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');

  it('place la carte « Temps de travail réalisé » avant la matrice budgétaire', () => {
    const rh = template.indexOf('plans.suivis.saisie.rh.title');
    const budget = template.indexOf('plans.suivis.saisie.sections.programmationBudget');
    const matrix = template.indexOf('class="realisation-matrix"');
    expect(rh).toBeGreaterThan(-1);
    expect(budget).toBeGreaterThan(-1);
    expect(rh).toBeLessThan(budget);
    expect(budget).toBeLessThan(matrix);
  });

  it('laisse le niveau de réalisation en tête de formulaire', () => {
    const niveau = template.indexOf('plans.suivis.saisie.fields.niveau');
    const rh = template.indexOf('plans.suivis.saisie.rh.title');
    expect(niveau).toBeLessThan(rh);
  });

  it('déclare la clé i18n du nouveau titre de carte', () => {
    const i18n = JSON.parse(
      readFileSync(join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8'),
    );
    expect(i18n.plans.suivis.saisie.sections.programmationBudget).toBeDefined();
  });
});

// ===========================================================================
// #609 — niveau obligatoire + périodicité dérivée du niveau
// ===========================================================================
describe('SuiviSaisieComponent — périodicité dérivée du niveau (#609)', () => {
  const NIVEAUX = [
    { id_nomenclature: 10, mnemonique: 'TERMINE', label: 'Réalisée' },
    { id_nomenclature: 11, mnemonique: 'PARTIEL', label: 'Partiellement réalisée' },
    { id_nomenclature: 12, mnemonique: 'NON_REALISE', label: 'Non réalisée' },
  ];

  function instance(): any {
    const c = comp() as any;
    c.niveaux = signal(NIVEAUX);
    return c;
  }

  it('« réalisé » ou « partiel » ⇒ périodicité cochée', () => {
    const c = instance();
    expect(c.periodiciteFromNiveau(10)).toBe(true);
    expect(c.periodiciteFromNiveau(11)).toBe(true);
  });

  it('« non réalisé » ou vide ⇒ périodicité décochée', () => {
    const c = instance();
    expect(c.periodiciteFromNiveau(12)).toBe(false);
    expect(c.periodiciteFromNiveau(null)).toBe(false);
  });

  it('submit bloque sans niveau et signale l\'erreur (#609)', () => {
    const c = instance();
    const fb = new FormBuilder();
    c.form = fb.group({ id_niveau_realisation: [null] });
    c.showNiveauError = signal(false);
    c.saisieBloquee = () => false;  // #740 — verrou unique des actions (plan non validé OU consultation)
    c.snack = { open: jest.fn() };
    c.translate = { instant: (k: string) => k };
    c.realisationService = { upsert: jest.fn() };

    c.submit();

    expect(c.showNiveauError()).toBe(true);
    expect(c.realisationService.upsert).not.toHaveBeenCalled();
  });
});

// ===========================================================================
// #608 — coût salarial réalisé calculé (ventilation maximale)
// ===========================================================================
describe('SuiviSaisieComponent — coût salarial réalisé (#608)', () => {
  function instance(): any {
    const c = comp() as any;
    const fb = new FormBuilder();
    c.selectedYear = signal(2025);
    c.postes = signal([
      { id_poste: 1, id_organisme: 100, cout_jour: 300 },
      { id_poste: 2, id_organisme: 100, cout_jour: 80 },
      { id_poste: 3, id_organisme: 200, cout_jour: 300 },
    ]);
    // #722 — coût salarial calculé (case cochée) : seul cas où il dérive des jours.
    c.operation = signal({ ventilation_mode: 'by_org_type_poste', cout_salarial_auto: true });
    // 3 lignes RH réalisées : poste 1 (fonct, 10j), poste 2 (invest, 5j), poste 3 (fonct, 4j)
    c.form = fb.group({
      rhLignes: fb.array([
        fb.group({ id_poste: [1], categorie_depense: ['fonctionnement'], jours: [10] }),
        fb.group({ id_poste: [2], categorie_depense: ['investissement'], jours: [5] }),
        fb.group({ id_poste: [3], categorie_depense: ['fonctionnement'], jours: [4] }),
      ]),
      organismes: fb.array([
        fb.group({ id_organisme: [100], cout_prestataire_realise: [1000], autre_cout_realise: [500] }),
      ]),
    });
    return c;
  }

  it('somme jours × coût jour des postes de l\'organisme, par catégorie', () => {
    const c = instance();
    // Org 100 fonctionnement : poste 1 → 10 × 300 = 3000
    expect(c.realCoutSalarial(2025, 100, 'fonctionnement')).toBe(3000);
    // Org 100 investissement : poste 2 → 5 × 80 = 400
    expect(c.realCoutSalarial(2025, 100, 'investissement')).toBe(400);
    // Org 200 fonctionnement : poste 3 → 4 × 300 = 1200
    expect(c.realCoutSalarial(2025, 200, 'fonctionnement')).toBe(1200);
  });

  it('total fonctionnement réalisé = salarial + prestataire + autres', () => {
    const c = instance();
    // 3000 (salarial) + 1000 (presta) + 500 (autres) = 4500
    expect(c.realOrgFonctTotal(2025, 100)).toBe(4500);
  });
});

// ===========================================================================
// #624 — mode « par type de budget + type de poste » : même détail des coûts
// que la ventilation maximale, mais GLOBAL (sans organisme).
// ===========================================================================
describe('SuiviSaisieComponent — détail des coûts sans organisme (#624)', () => {
  /**
   * Année 2025 (active). Deux postes de deux organismes différents : tout se
   * cumule au global. Les coûts prévus sont portés par l'ANNÉE (et non par
   * l'organisme), les coûts réalisés de l'année active par le formulaire.
   */
  function instance(): any {
    const c: any = comp();
    c.selectedYear = signal(2025);
    c.postes = signal([
      { id_poste: 1, id_organisme: 100, cout_jour: 300 },
      { id_poste: 2, id_organisme: 200, cout_jour: 80 },
    ]);
    c.operation = signal({
      ventilation_mode: 'by_type_poste',
      operation_annees: [{
        annee: 2025,
        cout_stage: '200.00',
        cout_prestataire: '1000.00',
        autre_cout: '500.00',
        cout_prestataire_invest: '300.00',
        autre_cout_invest: null,
        rh_lignes: [
          { id_poste: 1, categorie_depense: 'fonctionnement', jours: '10.00', finance: true },
          { id_poste: 2, categorie_depense: 'investissement', jours: '5.00', finance: true },
        ],
        realisation: {},
      }],
    });
    // Formulaire de l'année active : coûts réalisés + lignes RH réalisées.
    const values: Record<string, unknown> = {
      cout_stage_realise: 150,
      cout_prestataire_realise: 800,
      autre_cout_realise: 50,
      cout_prestataire_invest_realise: 100,
      autre_cout_invest_realise: 0,
    };
    c.form = { get: (name: string) => ctrlOf(values[name] ?? null) };
    Object.defineProperty(c, 'rhLignesFA', {
      value: {
        controls: [
          { get: (n: string) => ctrlOf({ id_poste: 1, categorie_depense: 'fonctionnement', jours: 8 }[n as never]) },
          { get: (n: string) => ctrlOf({ id_poste: 2, categorie_depense: 'investissement', jours: 5 }[n as never]) },
        ],
      },
    });
    return c;
  }

  it('cumule le coût salarial de tous les postes, sans distinction d\'organisme', () => {
    const c = instance();
    // Prévu : poste 1 → 10 × 300 (fonct), poste 2 → 5 × 80 (invest)
    expect(c.prevGlobalCoutSalarial(2025, 'fonctionnement')).toBe(3000);
    expect(c.prevGlobalCoutSalarial(2025, 'investissement')).toBe(400);
    // Réalisé (année active, lu dans le formulaire) : 8 × 300 et 5 × 80
    expect(c.realGlobalCoutSalarial(2025, 'fonctionnement')).toBe(2400);
    expect(c.realGlobalCoutSalarial(2025, 'investissement')).toBe(400);
  });

  it('totalise prévu et réalisé (salarial + stage + prestataire + autres)', () => {
    const c = instance();
    expect(c.prevGlobalFonctTotal(2025)).toBe(3000 + 200 + 1000 + 500);
    expect(c.prevGlobalInvestTotal(2025)).toBe(400 + 300);
    expect(c.prevGlobalTotal(2025)).toBe(5400);

    expect(c.realGlobalFonctTotal(2025)).toBe(2400 + 150 + 800 + 50);
    expect(c.realGlobalInvestTotal(2025)).toBe(400 + 100);
    expect(c.realGlobalTotal(2025)).toBe(3900);
  });

  it('renvoie 0 sur une année sans programmation', () => {
    const c = instance();
    expect(c.prevGlobalTotal(2031)).toBe(0);
  });

  it('rend le détail des coûts dans le template', () => {
    const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    expect(template).toContain('isGlobalDetailVentilation()');
    for (const helper of [
      'prevGlobalCoutSalarial', 'realGlobalCoutSalarial',
      'prevGlobalFonctTotal', 'realGlobalFonctTotal',
      'prevGlobalInvestTotal', 'realGlobalInvestTotal',
      'prevGlobalTotal', 'realGlobalTotal',
    ]) {
      expect(template).toContain(helper);
    }
    // Les coûts réalisés de l'année active sont saisis au niveau du formulaire.
    for (const control of [
      'cout_stage_realise', 'cout_prestataire_realise', 'autre_cout_realise',
      'autre_cout_commentaire_realise', 'cout_prestataire_invest_realise',
      'autre_cout_invest_realise', 'autre_cout_invest_commentaire_realise',
    ]) {
      expect(template).toContain(control);
    }
  });
});

// ===========================================================================
// #722 — coût salarial SAISI : le réalisé l'est aussi (même case qu'au prévu).
// ===========================================================================
describe('SuiviSaisieComponent — coût salarial réalisé saisi (#722)', () => {
  function instance(mode: 'by_org_type_poste' | 'by_type_poste'): any {
    const c: any = comp();
    const fb = new FormBuilder();
    c.selectedYear = signal(2025);
    c.postes = signal([{ id_poste: 1, id_organisme: 100, cout_jour: 300 }]);
    c.operation = signal({
      ventilation_mode: mode, declinaison_par_type_cout: true, cout_salarial_auto: false,
      operation_annees: [{
        annee: 2024,
        organismes: [{ id_organisme: 100, realisation: { cout_salarial_realise: '900.00' } }],
        realisation: { cout_salarial_realise: '700.00', cout_salarial_invest_realise: '50.00' },
      }],
    });
    c.form = fb.group({
      cout_salarial_realise: [1200],
      cout_salarial_invest_realise: [100],
      rhLignes: fb.array([
        fb.group({ id_poste: [1], categorie_depense: ['fonctionnement'], jours: [10] }),
      ]),
      organismes: fb.array([
        fb.group({ id_organisme: [100], cout_salarial_realise: [1500], cout_salarial_invest_realise: [200] }),
      ]),
    });
    return c;
  }

  it('ventilation maximale : montant saisi par organisme, pas jours × coût jour', () => {
    const c = instance('by_org_type_poste');
    expect(c.realCoutSalarial(2025, 100, 'fonctionnement')).toBe(1500);   // et non 3000
    expect(c.realCoutSalarial(2025, 100, 'investissement')).toBe(200);
    expect(c.realCoutSalarial(2024, 100, 'fonctionnement')).toBe(900);    // année enregistrée
  });

  it('sans organisme : montant saisi sur l’année', () => {
    const c = instance('by_type_poste');
    expect(c.realGlobalCoutSalarial(2025, 'fonctionnement')).toBe(1200);
    expect(c.realGlobalCoutSalarial(2025, 'investissement')).toBe(100);
    expect(c.realGlobalCoutSalarial(2024, 'investissement')).toBe(50);
  });

  it('le template propose la saisie du coût salarial réalisé', () => {
    const template = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    expect(template).toContain('formControlName="cout_salarial_realise"');
    expect(template).toContain('formControlName="cout_salarial_invest_realise"');
  });
});

// -----------------------------------------------------------------------------
// #699 — Effacer la saisie d'une année (retour à « non encore saisie »).
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — effacer la saisie (#699)', () => {
  function setup(opts: { confirmed: boolean; notValidated?: boolean; fail?: boolean }) {
    const c = Object.create(SuiviSaisieComponent.prototype) as any;
    const oa: any = {
      id_operation_annee: 42, annee: 2025, periodicite: true,
      realisation: { id_niveau_realisation: 7 },
      organismes: [{ id_operation_annee_organisme: 1, realisation: { etp_realise: 3 } }],
    };
    c.operation = signal<any>({ operation_annees: [oa] });
    c.selectedYear = signal(2025);
    c.currentOperationAnnee = computed(
      () => c.operation()?.operation_annees?.find((o: any) => o.annee === c.selectedYear()) ?? null,
    );
    c.hasSaisieForYear = computed(() => hasSaisieRealisation(c.currentOperationAnnee()));
    c.saisieBloquee = signal(!!opts.notValidated);  // #740 — verrou unique des actions
    c.editionDemandee = signal(true);  // #762 — « Modifier » cliqué avant d'effacer
    c.enLecture = computed(() => !c.saisieBloquee() && c.hasSaisieForYear() && !c.editionDemandee());
    c.isSaving = signal(false);
    c.pendingGeomRealisee = signal<any>({ type: 'Point' });
    c.isEditingGeom = signal(true);
    c.empriseSnapshot = signal<any>(null);
    c.hydrateFormFromCurrentYear = jest.fn();
    c.translate = { instant: (k: string) => k };
    c.snack = { open: jest.fn() };
    c.dialog = { open: jest.fn(() => ({ afterClosed: () => ({ subscribe: (fn: any) => fn(opts.confirmed) }) })) };
    c.realisationService = {
      effacer: jest.fn(() => ({
        subscribe: (o: any) => (opts.fail ? o.error(new Error('x')) : o.next()),
      })),
    };
    return { c, oa };
  }

  it('hasSaisieRealisation : vrai dès qu\'une réalisation existe pour l\'année', () => {
    expect(hasSaisieRealisation({ realisation: { id_niveau_realisation: 7 } } as any)).toBe(true);
    // ventilation organisme seule
    expect(hasSaisieRealisation({ realisation: null, organismes: [{ realisation: { etp_realise: 1 } }] } as any)).toBe(true);
    expect(hasSaisieRealisation({ realisation: null, organismes: [{ realisation: null }] } as any)).toBe(false);
    expect(hasSaisieRealisation(null)).toBe(false);
  });

  it('après confirmation, efface côté serveur puis vide la réalisation locale', () => {
    const { c } = setup({ confirmed: true });
    c.clearSaisie();
    expect(c.realisationService.effacer).toHaveBeenCalledWith(42);
    const oa = c.currentOperationAnnee();
    expect(oa.realisation).toBeNull();
    expect(oa.organismes[0].realisation).toBeNull();
    expect(oa.periodicite).toBe(true); // prévisionnel conservé
    expect(c.hasSaisieForYear()).toBe(false);
    expect(c.pendingGeomRealisee()).toBeUndefined();
    expect(c.isEditingGeom()).toBe(false);
    expect(c.hydrateFormFromCurrentYear).toHaveBeenCalled();
    expect(c.isSaving()).toBe(false);
    // #762 — plus de saisie : retour automatique en saisie.
    expect(c.editionDemandee()).toBe(false);
    expect(c.enLecture()).toBe(false);
  });

  it('sans confirmation, rien n\'est effacé', () => {
    const { c, oa } = setup({ confirmed: false });
    c.clearSaisie();
    expect(c.realisationService.effacer).not.toHaveBeenCalled();
    expect(oa.realisation).not.toBeNull();
  });

  it('plan non validé : pas de dialogue ni d\'appel', () => {
    const { c } = setup({ confirmed: true, notValidated: true });
    c.clearSaisie();
    expect(c.dialog.open).not.toHaveBeenCalled();
    expect(c.realisationService.effacer).not.toHaveBeenCalled();
  });

  it('en cas d\'erreur serveur, la saisie locale est conservée', () => {
    const { c, oa } = setup({ confirmed: true, fail: true });
    c.clearSaisie();
    expect(oa.realisation).not.toBeNull();
    expect(c.snack.open).toHaveBeenCalledWith(
      'plans.suivis.saisie.errors.clearFailed', expect.anything(), expect.anything());
    expect(c.isSaving()).toBe(false);
  });

  it('le template n\'affiche le bouton que si une saisie existe et le plan est validé', () => {
    const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    expect(html).toMatch(/@if \(hasSaisieForYear\(\)\)[\s\S]*?\(click\)="clearSaisie\(\)"/);
  });
});

// -----------------------------------------------------------------------------
// #758 — « Effacer les données de l'année » doit apparaître dès l'enregistrement,
// sans rafraîchir : l'année enregistrée doit être une NOUVELLE référence, sinon
// `currentOperationAnnee` rend le même objet et `hasSaisieForYear` ne se
// réévalue pas.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — bouton Effacer après enregistrement (#758)', () => {
  function setup(oa: any, saved: any, savedOrgs: any[] = []) {
    const c = Object.create(SuiviSaisieComponent.prototype) as any;
    c.fb = new FormBuilder();
    c.form = c.fb.group({
      id_niveau_realisation: [7], commentaires: [''], operateurs_realises: [''], financeurs_realises: [''],
      organismes: c.fb.array([]), indicateurs: c.fb.array([]), rhLignes: c.fb.array([]),
    });
    c.operation = signal<any>({ operation_annees: oa ? [oa] : [] });
    c.operationId = signal(5);
    c.selectedYear = signal(2025);
    c.currentOperationAnnee = computed(
      () => c.operation()?.operation_annees?.find((o: any) => o.annee === c.selectedYear()) ?? null,
    );
    c.hasSaisieForYear = computed(() => hasSaisieRealisation(c.currentOperationAnnee()));
    c.saisieBloquee = signal(false);
    c.editionDemandee = signal(false);
    c.enLecture = computed(() => !c.saisieBloquee() && c.hasSaisieForYear() && !c.editionDemandee());
    c.formVerrouille = computed(() => c.saisieBloquee() || c.enLecture());
    c.showNiveauError = signal(false);
    c.isSaving = signal(false);
    c.niveaux = signal([]);
    c.reglagesProposes = signal<any>(null);  // #761 — pas de réglage proposé
    c.isOrgVentilation = signal(savedOrgs.length > 0);
    c.isGlobalDetailVentilation = signal(false);
    c.isByType = signal(false);
    c.isMaxVentilation = signal(false);
    c.ventilationMode = signal(savedOrgs.length ? 'by_org' : 'none');
    c.pendingGeomRealisee = signal<any>(undefined);
    c.isEditingGeom = signal(false);
    c.empriseSnapshot = signal<any>(null);
    c.mesuresByMetrique = new Map();
    c.translate = { instant: (k: string) => k };
    c.snack = { open: jest.fn() };
    c.realisationService = {
      upsert: jest.fn(() => of(saved)),
      upsertOrganisme: jest.fn((p: any) => of(savedOrgs.find(s => s.id_operation_annee_organisme === p.id_operation_annee_organisme))),
    };
    return c;
  }

  it('année programmée : le bouton apparaît dès la réponse du serveur', () => {
    const oa = { id_operation_annee: 42, annee: 2025, periodicite: true, organismes: [], realisation: null };
    const c = setup(oa, { id_operation_annee: 42, id_niveau_realisation: 7 });
    expect(c.hasSaisieForYear()).toBe(false);
    c.submit();
    expect(c.hasSaisieForYear()).toBe(true);
    expect(c.currentOperationAnnee().realisation.id_niveau_realisation).toBe(7);    // #762 — l'année enregistrée passe en lecture.
    expect(c.enLecture()).toBe(true);
    expect(c.form.disabled).toBe(true);
  });

  it('ventilation par organisme : la réalisation par organisme suffit à afficher le bouton', () => {
    const oa = {
      id_operation_annee: 42, annee: 2025, periodicite: true, realisation: null,
      organismes: [{ id_operation_annee_organisme: 3, id_organisme: 1, realisation: null }],
    };
    const c = setup(oa, null as any, [{ id_operation_annee_organisme: 3, etp_realise: 2 }]);
    c.realisationService.upsert = jest.fn(() => of({ id_operation_annee: 42 }));
    c.organismesFA.push(c.fb.group({ id_operation_annee_organisme: [3], budget_fonctionnement_realise: [10], etp_realise: [2] }));
    expect(c.hasSaisieForYear()).toBe(false);
    c.submit();
    expect(c.hasSaisieForYear()).toBe(true);
    expect(c.currentOperationAnnee().organismes[0].realisation.etp_realise).toBe(2);
  });
});

// -----------------------------------------------------------------------------
// #762 — année enregistrée en lecture + « Modifier » ; « Effacer » en haut à
// droite ; plus de report de saisie d'une année sur l'autre.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — lecture d\'une année enregistrée (#762)', () => {
  function setup(opts: { bloquee?: boolean } = {}) {
    const c = Object.create(SuiviSaisieComponent.prototype) as any;
    const fb = new FormBuilder();
    c.form = fb.group({ id_niveau_realisation: [null], commentaires: [''] });
    c.operation = signal<any>({
      operation_annees: [
        { id_operation_annee: 1, annee: 2024, periodicite: true, organismes: [], realisation: { id_niveau_realisation: 7 } },
        { id_operation_annee: 2, annee: 2025, periodicite: true, organismes: [], realisation: null },
      ],
    });
    c.selectedYear = signal(2024);
    c.currentOperationAnnee = computed(
      () => c.operation()?.operation_annees?.find((o: any) => o.annee === c.selectedYear()) ?? null,
    );
    c.hasSaisieForYear = computed(() => hasSaisieRealisation(c.currentOperationAnnee()));
    c.saisieBloquee = signal(!!opts.bloquee);
    c.editionDemandee = signal(false);
    c.enLecture = computed(() => !c.saisieBloquee() && c.hasSaisieForYear() && !c.editionDemandee());
    c.formVerrouille = computed(() => c.saisieBloquee() || c.enLecture());
    c.hydrateFormFromCurrentYear = jest.fn(() => c.applyReadOnlyLock());
    c.refreshIndicateursForYear = jest.fn();
    c.pendingGeomRealisee = signal<any>(undefined);
    c.isEditingGeom = signal(false);
    c.empriseSnapshot = signal<any>(null);
    return c;
  }

  it('année enregistrée : en lecture, formulaire désactivé', () => {
    const c = setup();
    c.applyReadOnlyLock();
    expect(c.enLecture()).toBe(true);
    expect(c.form.disabled).toBe(true);
  });

  it('« Modifier » repasse en saisie', () => {
    const c = setup();
    c.applyReadOnlyLock();
    c.modifier();
    expect(c.enLecture()).toBe(false);
    expect(c.form.enabled).toBe(true);
  });

  it('année jamais saisie : directement en saisie ; retour sur l\'année enregistrée : en lecture', () => {
    const c = setup();
    c.modifier();
    c.selectYear(2025);
    expect(c.enLecture()).toBe(false);
    expect(c.form.enabled).toBe(true);
    c.selectYear(2024);
    expect(c.editionDemandee()).toBe(false);
    expect(c.enLecture()).toBe(true);
    expect(c.form.disabled).toBe(true);
  });

  it('saisie bloquée (#379 / #740) : jamais de « Modifier », formulaire verrouillé', () => {
    const c = setup({ bloquee: true });
    c.modifier();
    expect(c.editionDemandee()).toBe(false);
    expect(c.enLecture()).toBe(false);
    expect(c.formVerrouille()).toBe(true);
    c.applyReadOnlyLock();
    expect(c.form.disabled).toBe(true);
  });

  it('gabarit : « Modifier » et « Effacer » dans la barre du haut, plus en bas du formulaire', () => {
    const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    const toolbar = html.slice(html.indexOf('class="saisie-toolbar"'), html.indexOf('</form>'));
    expect(html.indexOf('class="saisie-toolbar"')).toBeGreaterThan(html.indexOf('<form'));
    expect(html.indexOf('class="saisie-toolbar"')).toBeLessThan(html.indexOf('saisie-card'));
    expect(toolbar).toMatch(/@if \(enLecture\(\)\)[\s\S]*?\(click\)="modifier\(\)"/);
    const bottom = html.slice(html.indexOf('class="bottom-actions"'));
    expect(bottom).not.toContain('clearSaisie()');
    expect(bottom).toMatch(/@if \(!formVerrouille\(\)\)[\s\S]*?type="submit"/);
  });

  it('gabarit : les lignes de temps réalisé sont suivies par contrôle, pas par index', () => {
    const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    expect(html).toContain('@for (ctrl of rhLignesFA.controls; track ctrl;');
  });
});

// -----------------------------------------------------------------------------
// #760 — case « Déclinaison par type de poste » du temps de travail réalisé.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — déclinaison par type de poste au suivi (#760)', () => {
  function c760(op: any): any {
    const c: any = comp();
    c.operation = signal<any>(op);
    return c;
  }
  const NONE = { ventilation_mode: 'none', declinaison_par_type_cout: false, declinaison_par_poste: false };
  const BY_ORG = { ventilation_mode: 'by_org', declinaison_par_type_cout: false, declinaison_par_poste: false };
  const PAR_POSTE = { ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true, declinaison_par_poste: true };

  it('décochée par défaut sans déclinaison à la programmation : temps global', () => {
    const c = c760({ ...NONE });
    expect(c.declinaisonPosteRealise()).toBe(false);
    expect(c.declinaisonPosteVerrouillee()).toBe(false);
    expect(c.computeRhMode()).toBe('global');
  });

  it('cochée au suivi : saisie par poste, même en « aucune ventilation »', () => {
    const c = c760({ ...NONE, declinaison_par_poste_realise: true });
    expect(c.computeRhMode()).toBe('postes');
    expect(c.rhTotalUnique()).toBe(false);
  });

  it('décochée en ventilation par organisme : lignes par organisme', () => {
    expect(c760({ ...BY_ORG }).computeRhMode()).toBe('organismes');
  });

  it('programmation par poste : cochée et verrouillée', () => {
    const c = c760({ ...PAR_POSTE });
    expect(c.declinaisonPosteRealise()).toBe(true);
    expect(c.declinaisonPosteVerrouillee()).toBe(true);
    expect(c.computeRhMode()).toBe('postes');
  });

  it('enregistrement refusé si une ligne de temps n\'a pas de poste', () => {
    const c = c760({ ...NONE, declinaison_par_poste_realise: true });
    const fb = new FormBuilder();
    c.form = fb.group({ id_niveau_realisation: [7], rhLignes: fb.array([
      fb.group({ id_poste: [null], jours: [5] }),
    ]) });
    c.saisieBloquee = () => false;
    c.showNiveauError = signal(false);
    c.translate = { instant: (k: string) => k };
    c.snack = { open: jest.fn() };
    c.realisationService = { upsert: jest.fn() };
    c.submit();
    expect(c.realisationService.upsert).not.toHaveBeenCalled();
    expect(c.snack.open).toHaveBeenCalledWith(
      'plans.suivis.saisie.errors.posteRequired', expect.anything(), expect.anything());
  });

  it('changer la case enregistre le réglage et recharge le temps de travail', () => {
    const c = c760({ id_operation: 3, ...NONE });
    c.isSavingReglages = signal(false);
    c.reglagesProposes = signal<any>(null);  // #761
    c.hydrateRhArray = jest.fn();
    c.currentOperationAnnee = () => null;
    c.enjeuService = { setSuiviReglages: jest.fn(() => of({
      declinaison_par_type_cout_realise: false, cout_salarial_auto_realise: false,
      declinaison_par_poste_realise: true,
    })) };
    c.setReglage('declinaison_par_poste_realise', true);
    expect(c.enjeuService.setSuiviReglages).toHaveBeenCalledWith(3, { declinaison_par_poste_realise: true });
    expect(c.operation().declinaison_par_poste_realise).toBe(true);
    expect(c.hydrateRhArray).toHaveBeenCalled();
  });

  it('gabarit : case au-dessus du temps de travail réalisé, liste « Poste »', () => {
    const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    const rh = html.slice(html.indexOf('saisie-card rh-card'), html.indexOf('class="rh-table"'));
    expect(rh).toContain("setReglage('declinaison_par_poste_realise', $event)");
    expect(rh).toContain('declinaisonPosteVerrouillee()');
    expect(html).toContain("'plans.suivis.saisie.rh.selectPoste'");
  });
});

// -----------------------------------------------------------------------------
// #761 — réglages du 1er suivi du plan proposés aux autres actions.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — réglages du 1er suivi proposés (#761)', () => {
  const NONE = { id_operation: 5, ventilation_mode: 'none', declinaison_par_type_cout: false,
    declinaison_par_poste: false, reglages_suivi_definis: false,
    declinaison_par_type_cout_realise: false, declinaison_par_poste_realise: false,
    operation_annees: [{ annee: 2027, realisation: null, organismes: [] }] };
  const DEFAULTS = { plan_id: 1, source_operation_id: 9,
    declinaison_par_type_cout_realise: true, declinaison_par_poste_realise: true };

  function c761(op: any, defaults: any = DEFAULTS): any {
    const c: any = comp();
    c.operation = signal<any>(op);
    c.planId = signal<number | null>(1);
    c.saisieBloquee = () => false;
    c.reglagesProposes = signal<any>(null);
    c.hydrateRhArray = jest.fn();
    c.currentOperationAnnee = () => null;
    c.isSavingReglages = signal(false);
    c.enjeuService = {
      getSuiviDefaults: jest.fn(() => of(defaults)),
      setSuiviReglages: jest.fn((_id: number, r: any) => of({
        declinaison_par_type_cout_realise: r.declinaison_par_type_cout_realise,
        cout_salarial_auto_realise: false,
        declinaison_par_poste_realise: r.declinaison_par_poste_realise,
      })),
    };
    return c;
  }

  it('action sans suivi ni réglage : propose ceux du 1er suivi du plan', () => {
    const c = c761({ ...NONE });
    c.proposerReglagesDuPlan();
    expect(c.enjeuService.getSuiviDefaults).toHaveBeenCalledWith(1);
    expect(c.declinaisonRealise()).toBe(true);
    expect(c.declinaisonPosteRealise()).toBe(true);
    expect(c.reglagesProposes()).toEqual({
      declinaison_par_type_cout_realise: true, declinaison_par_poste_realise: true });
    expect(c.hydrateRhArray).toHaveBeenCalled();
    // Rien n'est enregistré tant que le suivi ne l'est pas.
    expect(c.enjeuService.setSuiviReglages).not.toHaveBeenCalled();
  });

  it('réglages déjà posés ou suivi déjà saisi : rien n\'est proposé', () => {
    const definis = c761({ ...NONE, reglages_suivi_definis: true });
    definis.proposerReglagesDuPlan();
    expect(definis.enjeuService.getSuiviDefaults).not.toHaveBeenCalled();
    const saisie = c761({ ...NONE, operation_annees: [{ annee: 2027, realisation: { id_niveau_realisation: 1 } }] });
    saisie.proposerReglagesDuPlan();
    expect(saisie.enjeuService.getSuiviDefaults).not.toHaveBeenCalled();
  });

  it('pas de suivi dans le plan : les réglages de la programmation restent', () => {
    const c = c761({ ...NONE }, { ...DEFAULTS, source_operation_id: null,
      declinaison_par_type_cout_realise: null, declinaison_par_poste_realise: null });
    c.proposerReglagesDuPlan();
    expect(c.reglagesProposes()).toBeNull();
    expect(c.declinaisonPosteRealise()).toBe(false);
  });

  it('les règles de la programmation priment sur la proposition', () => {
    const c = c761({ ...NONE, ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true,
      declinaison_par_poste: true, declinaison_par_type_cout_realise: true, declinaison_par_poste_realise: true },
    { ...DEFAULTS, declinaison_par_type_cout_realise: false, declinaison_par_poste_realise: false });
    c.proposerReglagesDuPlan();
    expect(c.declinaisonRealise()).toBe(true);
    expect(c.declinaisonPosteRealise()).toBe(true);
  });

  it('changer une case enregistre aussi la proposition de l\'autre', () => {
    const c = c761({ ...NONE });
    c.proposerReglagesDuPlan();
    c.translate = { instant: (k: string) => k };
    c.snack = { open: jest.fn() };
    c.setReglage('declinaison_par_poste_realise', false);
    expect(c.enjeuService.setSuiviReglages).toHaveBeenCalledWith(5, {
      declinaison_par_type_cout_realise: true, declinaison_par_poste_realise: false });
    expect(c.reglagesProposes()).toBeNull();
  });

  it('le 1er enregistrement du suivi enregistre les réglages proposés', () => {
    const c = c761({ ...NONE });
    c.proposerReglagesDuPlan();
    c.persisterReglagesProposes().subscribe();
    expect(c.enjeuService.setSuiviReglages).toHaveBeenCalledWith(5, {
      declinaison_par_type_cout_realise: true, declinaison_par_poste_realise: true });
    expect(c.reglagesProposes()).toBeNull();
  });
});

describe('SuiviSaisieComponent — réglages propres au suivi (#741)', () => {
  const OA = {
    annee: 2025,
    budget: null, budget_fonctionnement: '4000.00', budget_investissement: '1000.00',
    cout_salarial: null,
    rh_lignes: [{ id_poste: 1, categorie_depense: 'fonctionnement', jours: '10.00', poste_cout_jour: '300.00' }],
    organismes: [],
  };

  function instance(op: any): any {
    const c: any = comp();
    c.selectedYear = signal(2026);
    c.postes = signal([{ id_poste: 1, id_organisme: 100, cout_jour: 300 }]);
    c.operation = signal({ operation_annees: [OA], ...op });
    return c;
  }

  it('coût salarial réalisé saisi quand le suivi le demande, prévu toujours calculé', () => {
    const c = instance({
      ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true, cout_salarial_auto: true,
      declinaison_par_type_cout_realise: true, cout_salarial_auto_realise: false,
    });
    expect(c.salaireCalcule()).toBe(false);
    expect(c.salaireCalculePrev()).toBe(true);
    expect(c.prevGlobalCoutSalarial(2025, 'fonctionnement')).toBe(3000);
    expect(c.showSalaireRealiseOption()).toBe(true);
  });

  it('réalisé détaillé alors que la programmation ne l\'est pas', () => {
    const c = instance({
      ventilation_mode: 'by_type', declinaison_par_type_cout: false, cout_salarial_auto: true,
      declinaison_par_type_cout_realise: true,
    });
    // Tableau du réalisé détaillé…
    expect(c.declinaisonRealise()).toBe(true);
    expect(c.declinaisonVerrouillee()).toBe(false);
    // …le prévu n'est rappelé qu'en totaux (enveloppes saisies).
    expect(c.prevDetail()).toBe(false);
    expect(c.prevGlobalFonctTotal(2025)).toBe(4000);
    expect(c.prevGlobalInvestTotal(2025)).toBe(1000);
  });

  it('programmation détaillée : la déclinaison du suivi est verrouillée', () => {
    const c = instance({ ventilation_mode: 'by_type', declinaison_par_type_cout: true });
    expect(c.declinaisonRealise()).toBe(true);
    expect(c.declinaisonVerrouillee()).toBe(true);
  });

  it('enregistre un réglage et met à jour le tableau', () => {
    const c = instance({ id_operation: 9, ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true });
    const post = jest.fn().mockReturnValue({
      subscribe: (o: any) => o.next({
        id_operation: 9, declinaison_par_type_cout_realise: true,
        cout_salarial_auto_realise: false, declinaison_verrouillee: true,
      }),
    });
    c.enjeuService = { setSuiviReglages: post };
    c.isSavingReglages = signal(false);
    c.reglagesProposes = signal<any>(null);  // #761
    c.setReglage('cout_salarial_auto_realise', false);
    expect(post).toHaveBeenCalledWith(9, { cout_salarial_auto_realise: false });
    expect(c.salaireCalcule()).toBe(false);
  });
});

// -----------------------------------------------------------------------------
// #740 — un utilisateur lié au plan consulte le suivi sans pouvoir le saisir.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — lecture seule (#740)', () => {
  it('bloque l\'enregistrement sans droit de saisie, même plan validé', () => {
    const c = comp() as any;
    c.saisieBloquee = () => true;
    c.realisationService = { upsert: jest.fn() };
    expect(() => c.submit()).not.toThrow();
    expect(c.realisationService.upsert).not.toHaveBeenCalled();
  });

  it('le gabarit désactive la saisie et affiche le bandeau de consultation', () => {
    const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');
    expect(html).toContain('plans.suivis.readOnlyBanner.title');
    expect(html).not.toMatch(/\[disabled\]="planNotValidated\(\)/);
    // #762 — le gabarit se verrouille via `formVerrouille()`, qui inclut
    // `saisieBloquee()` (vérifié dans le bloc #762).
    expect(html).toMatch(/\[disabled\]="formVerrouille\(\)/);
    expect(html).not.toMatch(/\[disabled\]="saisieBloquee\(\)/);
  });
});

// -----------------------------------------------------------------------------
// #735 (retour 21/10) — sans type de budget, aucune catégorisation du temps
// réalisé ; temps décliné par poste dès que les coûts sont détaillés.
// -----------------------------------------------------------------------------
describe('SuiviSaisieComponent — #735 sans type de budget', () => {
  const html = readFileSync(join(__dirname, 'suivi-saisie.component.html'), 'utf8');

  function instance(op: any): any {
    const c: any = comp();
    c.operation = signal({ operation_annees: [], ...op });
    return c;
  }

  it('ne demande la catégorie du temps réalisé que si le mode ventile par type de budget', () => {
    for (const mode of ['none', 'by_org']) {
      expect(instance({ ventilation_mode: mode }).showRhCategorie()).toBe(false);
    }
    for (const mode of ['by_type', 'by_org_type', 'by_type_poste', 'by_org_type_poste']) {
      expect(instance({ ventilation_mode: mode }).showRhCategorie()).toBe(true);
    }
    // Colonne et menu déroulant conditionnés dans le gabarit.
    expect(html).toMatch(/@if \(showRhCategorie\(\)\) \{\s*<th class="rh-categorie-col">/);
    expect(html).toMatch(/@if \(showRhCategorie\(\)\) \{\s*<td class="rh-categorie-col">/);
  });

  it('décline le temps réalisé par poste dès que les coûts sont détaillés', () => {
    expect(instance({ ventilation_mode: 'none', declinaison_par_type_cout: true }).computeRhMode()).toBe('postes');
    expect(instance({ ventilation_mode: 'by_org', declinaison_par_type_cout: true }).computeRhMode()).toBe('postes');
    expect(instance({ ventilation_mode: 'by_org', declinaison_par_type_cout: false }).computeRhMode()).toBe('organismes');
    expect(instance({ ventilation_mode: 'none', declinaison_par_type_cout: false }).computeRhMode()).toBe('global');
  });

  it('propose le coût salarial réalisé calculé dans tous les modes détaillés', () => {
    expect(instance({ ventilation_mode: 'none', declinaison_par_type_cout: true }).showSalaireRealiseOption()).toBe(true);
  });

  it('rappel du prévu de la période : deux tuiles prévu / réalisé, sans fonctionnement hors type de budget', () => {
    expect(html).toContain('class="prevu-periode__tile"');
    expect(html).toMatch(/@if \(showInvest\(\) && p\.invest\)/);
  });
});
