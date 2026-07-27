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
    expect(template).not.toContain('<app-checkbox');
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
    c.planNotValidated = () => false;
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
