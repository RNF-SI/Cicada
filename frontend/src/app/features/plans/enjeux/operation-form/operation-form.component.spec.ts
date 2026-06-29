/**
 * Tests unitaires pour OperationFormComponent — ventilation budgétaire 4 modes.
 *
 * On teste la logique métier (helpers, save payload, inférence mode au chargement)
 * sans monter le composant complet (trop de dépendances).
 */
import { TestBed } from '@angular/core/testing';
import { signal, computed } from '@angular/core';
import { Subject, of } from 'rxjs';
import {
  OperationFormComponent,
  buildResponseTypeOptions,
  buildGridTypeMetriqueOptions,
} from './operation-form.component';

// ---------------------------------------------------------------------------
// Helpers réutilisables
// ---------------------------------------------------------------------------

/** Crée un composant minimal en accédant directement aux propriétés publiques. */
function createComponentInstance(): OperationFormComponent {
  // On instancie "à la main" pour tester la logique sans le template
  const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;

  // Reproduire les propriétés de state utilisées par les helpers
  comp.operationAnnees = [];
  comp.orgBudgets = {};
  comp.directTotals = {};
  comp.typeBudgets = {};
  comp.orgByOrgData = {};
  comp.programmationMensuelleDefaut = {};

  // Signals (reproduits manuellement car pas d'injection Angular)
  (comp as any).ventilationMode = signal<'none' | 'by_org' | 'by_type' | 'by_org_type'>('none');
  (comp as any).directTotalMode = computed(() => (comp as any).ventilationMode() === 'none');
  (comp as any).selectedSiteIdsVersion = signal(0);
  (comp as any).planSites = signal([
    {
      id_site: 1, nom_site: 'Site A',
      organismes: [
        { id_organisme: 100, nom_organisme: 'Org A', principal: true },
        { id_organisme: 101, nom_organisme: 'Org B', principal: false },
      ]
    }
  ]);
  comp.selectedSiteIds = { 1: true };
  (comp as any).availableOrganismes = computed(() => {
    (comp as any).selectedSiteIdsVersion();
    const sites = (comp as any).planSites();
    const selectedIds = comp.selectedSiteIds;
    const orgMap = new Map<number, { id_organisme: number; nom_organisme: string }>();
    for (const site of sites) {
      if (!selectedIds[site.id_site]) continue;
      for (const org of (site as any).organismes || []) {
        if (!orgMap.has(org.id_organisme)) {
          orgMap.set(org.id_organisme, { id_organisme: org.id_organisme, nom_organisme: org.nom_organisme });
        }
      }
    }
    return Array.from(orgMap.values());
  });

  // Initialiser 2 années
  comp.operationAnnees = [
    { annee: 2024, periodicite: false, budget: null, etp: null, periodicite_mensuelle: {} },
    { annee: 2025, periodicite: false, budget: null, etp: null, periodicite_mensuelle: {} },
  ];

  return comp;
}

// ===========================================================================
// Tests
// ===========================================================================

describe('OperationFormComponent — ventilation budgétaire', () => {
  let comp: OperationFormComponent;

  beforeEach(() => {
    comp = createComponentInstance();
  });

  // -------------------------------------------------------------------------
  // Helpers mode 'none' (totaux directs)
  // -------------------------------------------------------------------------

  describe('mode none — helpers', () => {
    it('getDirectTotal should initialise empty entry', () => {
      const entry = comp.getDirectTotal(0);
      expect(entry).toEqual({ budget: null, etp: null });
    });

    it('updateDirectBudget should set budget', () => {
      comp.updateDirectBudget(0, '5000');
      expect(comp.getDirectTotal(0).budget).toBe(5000);
    });

    it('updateDirectEtp should set etp', () => {
      comp.updateDirectEtp(0, '10.5');
      expect(comp.getDirectTotal(0).etp).toBe(10.5);
    });

    it('should handle empty string as null', () => {
      comp.updateDirectBudget(0, '');
      expect(comp.getDirectTotal(0).budget).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // Helpers mode 'by_type' (fonct/invest global)
  // -------------------------------------------------------------------------

  describe('mode by_type — helpers', () => {
    it('getTypeBudget should initialise empty entry', () => {
      const entry = comp.getTypeBudget(0);
      expect(entry).toEqual({ fonct: null, invest: null, etp: null });
    });

    it('updateTypeFonct should set fonctionnement', () => {
      comp.updateTypeFonct(0, '3000');
      expect(comp.getTypeBudget(0).fonct).toBe(3000);
    });

    it('updateTypeInvest should set investissement', () => {
      comp.updateTypeInvest(0, '2000');
      expect(comp.getTypeBudget(0).invest).toBe(2000);
    });

    it('updateTypeEtp should set etp', () => {
      comp.updateTypeEtp(0, '8');
      expect(comp.getTypeBudget(0).etp).toBe(8);
    });
  });

  // -------------------------------------------------------------------------
  // Helpers mode 'by_org' (totaux par organisme)
  // -------------------------------------------------------------------------

  describe('mode by_org — helpers', () => {
    it('getOrgByOrgData should initialise empty entry', () => {
      const entry = comp.getOrgByOrgData(0, 100);
      expect(entry).toEqual({ budget: null, etp: null });
    });

    it('updateOrgByOrgBudget should set budget', () => {
      comp.updateOrgByOrgBudget(0, 100, '4000');
      expect(comp.getOrgByOrgData(0, 100).budget).toBe(4000);
    });

    it('updateOrgByOrgEtp should set etp', () => {
      comp.updateOrgByOrgEtp(0, 100, '6');
      expect(comp.getOrgByOrgData(0, 100).etp).toBe(6);
    });

    it('getByOrgYearTotalBudget should sum across organismes', () => {
      comp.updateOrgByOrgBudget(0, 100, '3000');
      comp.updateOrgByOrgBudget(0, 101, '2000');
      expect(comp.getByOrgYearTotalBudget(0)).toBe(5000);
    });

    it('getByOrgYearTotalEtp should sum across organismes', () => {
      comp.updateOrgByOrgEtp(0, 100, '6');
      comp.updateOrgByOrgEtp(0, 101, '4');
      expect(comp.getByOrgYearTotalEtp(0)).toBe(10);
    });
  });

  // -------------------------------------------------------------------------
  // Helpers mode 'by_org_type' (fonct/invest par organisme)
  // -------------------------------------------------------------------------

  describe('mode by_org_type — helpers', () => {
    it('getOrgBudget should initialise empty entry', () => {
      const entry = comp.getOrgBudget(0, 100);
      expect(entry).toEqual({ fonct: null, invest: null, etp: null });
    });

    it('should compute org total from fonct+invest', () => {
      comp.orgBudgets['0-100'] = { fonct: 3000, invest: 2000, etp: 5 };
      expect(comp.getOrgTotal(0, 100)).toBe(5000);
    });

    it('getYearTotalBudget should sum fonct+invest across all orgs', () => {
      comp.orgBudgets['0-100'] = { fonct: 2000, invest: 1000, etp: 4 };
      comp.orgBudgets['0-101'] = { fonct: 1500, invest: 500, etp: 3 };
      expect(comp.getYearTotalBudget(0)).toBe(5000);
    });

    it('getYearTotalEtp should sum etp across all orgs', () => {
      comp.orgBudgets['0-100'] = { fonct: 0, invest: 0, etp: 4 };
      comp.orgBudgets['0-101'] = { fonct: 0, invest: 0, etp: 3 };
      expect(comp.getYearTotalEtp(0)).toBe(7);
    });
  });

  // -------------------------------------------------------------------------
  // Mode toggle
  // -------------------------------------------------------------------------

  describe('onModeToggle', () => {
    it('should set ventilationMode to none', () => {
      comp.onModeToggle('none');
      expect((comp as any).ventilationMode()).toBe('none');
    });

    it('should set ventilationMode to by_org', () => {
      comp.onModeToggle('by_org');
      expect((comp as any).ventilationMode()).toBe('by_org');
    });

    it('should set ventilationMode to by_type', () => {
      comp.onModeToggle('by_type');
      expect((comp as any).ventilationMode()).toBe('by_type');
    });

    it('should set ventilationMode to by_org_type', () => {
      comp.onModeToggle('by_org_type');
      expect((comp as any).ventilationMode()).toBe('by_org_type');
    });
  });

  // -------------------------------------------------------------------------
  // formatNum (limiter à 2 décimales — via getScoreRange upstream, mais
  // vérifions aussi les helpers numériques)
  // -------------------------------------------------------------------------

  describe('numeric precision', () => {
    it('should store floats from string input', () => {
      comp.updateDirectBudget(0, '1234.567');
      expect(comp.getDirectTotal(0).budget).toBeCloseTo(1234.567);
    });

    it('should handle integer input', () => {
      comp.updateTypeFonct(0, '10000');
      expect(comp.getTypeBudget(0).fonct).toBe(10000);
    });
  });

  // -------------------------------------------------------------------------
  // #228 — code calculé (préfixe 2 lettres : catégorie réserve OU type action)
  // -------------------------------------------------------------------------

  describe('previewCode (code d\'action calculé)', () => {
    // Le composant principal n'est pas instancié via Angular ; on reproduit ici
    // les 3 signaux + le computed previewCode pour valider la logique pure.
    function makeMini() {
      const categorieActionReserveOptions = signal<any[]>([]);
      const selectedTypeAction = signal<any>(null);
      const categorieActionReserveCtrl = { value: null as number | null };
      const previewCode = computed<string | null>(() => {
        const catId = categorieActionReserveCtrl.value;
        if (catId != null) {
          const cat = categorieActionReserveOptions().find((c: any) => c.id_nomenclature === catId);
          if (cat?.cd_nomenclature) {
            return cat.cd_nomenclature.substring(0, 2).toUpperCase();
          }
        }
        const ta = selectedTypeAction();
        if (ta) {
          const code = ta.cd_nomenclature || ta.mnemonique || '';
          let letters = '';
          for (const ch of code) {
            if (/[A-Za-z]/.test(ch)) letters += ch; else break;
          }
          if (letters) return letters.substring(0, 2).toUpperCase();
        }
        return null;
      });
      return { categorieActionReserveOptions, selectedTypeAction, categorieActionReserveCtrl, previewCode };
    }

    it('utilise le code de la catégorie réserve quand renseigné', () => {
      const m = makeMini();
      m.categorieActionReserveOptions.set([
        { id_nomenclature: 1, cd_nomenclature: 'CS', label: 'Connaissance et suivi' },
      ]);
      m.categorieActionReserveCtrl.value = 1;
      expect(m.previewCode()).toBe('CS');
    });

    it('priorise la catégorie réserve même si un type action est défini', () => {
      const m = makeMini();
      m.categorieActionReserveOptions.set([
        { id_nomenclature: 1, cd_nomenclature: 'IP', label: 'Interventions' },
      ]);
      m.categorieActionReserveCtrl.value = 1;
      m.selectedTypeAction.set({ id_nomenclature: 2, cd_nomenclature: 'CS1', label: 'Surveillance' });
      expect(m.previewCode()).toBe('IP');
    });

    it('fallback sur les lettres du type action quand pas de catégorie réserve', () => {
      const m = makeMini();
      m.categorieActionReserveCtrl.value = null;
      m.selectedTypeAction.set({ id_nomenclature: 1, cd_nomenclature: 'CS1.2', label: 'Suivi' });
      expect(m.previewCode()).toBe('CS');
    });

    it('extrait IP de IP1.5.3 (lettres de tête uniquement)', () => {
      const m = makeMini();
      m.categorieActionReserveCtrl.value = null;
      m.selectedTypeAction.set({ id_nomenclature: 1, cd_nomenclature: 'IP1.5.3', label: 'Pâturage' });
      expect(m.previewCode()).toBe('IP');
    });

    it('retourne null quand ni catégorie réserve ni type action', () => {
      const m = makeMini();
      m.categorieActionReserveCtrl.value = null;
      m.selectedTypeAction.set(null);
      expect(m.previewCode()).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // #374 — anneeIndexHasData : détecte une année réellement saisie (sert de
  // départ par défaut dans la modale « Appliquer aux années »).
  // -------------------------------------------------------------------------
  describe('#374 anneeIndexHasData', () => {
    function setup() {
      const c = createComponentInstance();
      c.operationAnnees = [];
      c.directTotals = {};
      for (let y = 2025; y <= 2031; y++) {
        c.operationAnnees.push({ annee: y, periodicite: false, budget: null, etp: null, periodicite_mensuelle: {} });
      }
      return c;
    }
    it('détecte un budget direct saisi', () => {
      const c = setup();
      c.directTotals[1] = { budget: 1000, etp: null };
      expect((c as any).anneeIndexHasData(0)).toBe(false);
      expect((c as any).anneeIndexHasData(1)).toBe(true);
    });
    it('détecte un ETP/jours direct saisi', () => {
      const c = setup();
      c.directTotals[6] = { budget: null, etp: 4 };
      expect((c as any).anneeIndexHasData(6)).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Verrouillage des colonnes non programmées (saisie budget/ETP grisée)
  // -------------------------------------------------------------------------
  describe('isYearLocked', () => {
    it('verrouille les années dont la périodicité n\'est pas cochée', () => {
      const c = createComponentInstance();
      c.operationAnnees = [
        { annee: 2025, periodicite: true, budget: null, etp: null, periodicite_mensuelle: {} },
        { annee: 2026, periodicite: false, budget: null, etp: null, periodicite_mensuelle: {} },
      ];
      expect(c.isYearLocked(0)).toBe(false);
      expect(c.isYearLocked(1)).toBe(true);
    });

    it('verrouille un index hors plage (sécurité)', () => {
      const c = createComponentInstance();
      c.operationAnnees = [];
      expect(c.isYearLocked(0)).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // #452 — Types de métrique d'un indicateur de réponse selon le format
  //   SIMPLE (case décochée)  → « Pas de réponse » (vide) + Chiffrée + Textuelle
  //   GRILLE (case cochée)    → tous les types (Intervalle numérique inclus)
  // -------------------------------------------------------------------------
  describe('#452 buildResponseTypeOptions / buildGridTypeMetriqueOptions', () => {
    const NOMENCLATURES = [
      { id_nomenclature: 1, mnemonique: 'NUMERIQUE', label: 'Intervalle numérique' },
      { id_nomenclature: 2, mnemonique: 'CHIFFRE', label: 'Chiffre' },
      { id_nomenclature: 3, mnemonique: 'TEXTE', label: 'Texte' },
      { id_nomenclature: 4, mnemonique: 'INDETERMINE', label: 'Indéterminé' },
    ];

    it('saisie SIMPLE : n\'expose que Chiffrée et Textuelle (pas NUMERIQUE ni INDETERMINE)', () => {
      const ids = buildResponseTypeOptions(NOMENCLATURES, (k) => k).map(o => o.id);
      expect(ids).toEqual([2, 3]); // CHIFFRE, TEXTE
      expect(ids).not.toContain(1); // pas d'Intervalle numérique en saisie simple
    });

    it('mode GRILLE : expose tous les types sauf INDETERMINE (Intervalle numérique inclus)', () => {
      const mnemos = buildGridTypeMetriqueOptions(NOMENCLATURES).map(o => o.mnemonique);
      expect(mnemos).toEqual(['NUMERIQUE', 'CHIFFRE', 'TEXTE']);
      expect(mnemos).not.toContain('INDETERMINE');
    });
  });

  // -------------------------------------------------------------------------
  // #452 — setResponseFormat : mise à jour OPTIMISTE (l'éditeur de grille
  // s'affiche immédiatement, sans attendre l'aller-retour serveur), avec revert
  // si la sauvegarde réseau échoue.
  // -------------------------------------------------------------------------
  describe('#452 setResponseFormat — mise à jour optimiste', () => {
    function setup() {
      const c = createComponentInstance();
      (c as any).formatMetriqueOptions = signal([
        { id_nomenclature: 10, mnemonique: 'SIMPLE', label: 'Simple' },
        { id_nomenclature: 11, mnemonique: 'GRILLE', label: 'Grille' },
      ]);
      (c as any).existingOperation = signal({
        id_operation: 1,
        metriques: [{
          id_metrique: 5, indicateur_type: 'REPONSE',
          format_metrique_id: 10, format_metrique_mnemonique: 'SIMPLE',
        }],
      });
      const subj = new Subject<unknown>();
      const calls: { id: number; payload: unknown }[] = [];
      (c as any).enjeuService = {
        updateMetrique: (id: number, payload: unknown) => { calls.push({ id, payload }); return subj; },
      };
      const ref = (c as any).existingOperation().metriques[0];
      return { c, subj, calls, ref };
    }

    it('passe la métrique en GRILLE immédiatement, avant toute réponse serveur', () => {
      const { c, calls, ref } = setup();
      c.setResponseFormat(ref, true);
      const m = (c as any).existingOperation().metriques[0];
      expect(m.format_metrique_mnemonique).toBe('GRILLE'); // affichage instantané
      expect(m.format_metrique_id).toBe(11);
      expect(calls).toEqual([{ id: 5, payload: { format_metrique: 11 } }]); // save déclenché
    });

    it('restaure l\'état précédent si la sauvegarde échoue', () => {
      const { c, subj, ref } = setup();
      c.setResponseFormat(ref, true);
      expect((c as any).existingOperation().metriques[0].format_metrique_mnemonique).toBe('GRILLE');
      subj.error(new Error('network'));
      const m = (c as any).existingOperation().metriques[0];
      expect(m.format_metrique_mnemonique).toBe('SIMPLE'); // revert
      expect(m.format_metrique_id).toBe(10);
    });
  });

  // -------------------------------------------------------------------------
  // #452/#248 — applyPlanReadOnly : verrou lecture seule selon le statut du plan
  // (empêche le « cochée puis décochée » de la case grille sur un plan validé,
  //  où le PATCH renvoie 403).
  // -------------------------------------------------------------------------
  describe('#452 applyPlanReadOnly', () => {
    function comp(initial = false): OperationFormComponent {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).isReadOnly = signal(initial);
      return c;
    }

    it('verrouille le formulaire si le plan n\'est pas en brouillon', () => {
      for (const statut of ['valide', 'modifie', 'mi_parcours', 'archive', 'avis_csrpn']) {
        const c = comp(false);
        (c as any).applyPlanReadOnly(statut);
        expect(c.isReadOnly()).toBe(true);
      }
    });

    it('laisse le formulaire éditable si le plan est en brouillon', () => {
      const c = comp(false);
      (c as any).applyPlanReadOnly('draft');
      expect(c.isReadOnly()).toBe(false);
    });

    it('n\'abaisse jamais un verrou déjà posé (route lecture seule)', () => {
      const c = comp(true);
      (c as any).applyPlanReadOnly('draft');
      expect(c.isReadOnly()).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // #452 — handlePlanLocked : une mutation refusée (403, plan non modifiable)
  // verrouille le formulaire et l'explique (corbeille / case grille incluses).
  // -------------------------------------------------------------------------
  describe('#452 handlePlanLocked', () => {
    function comp() {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).isReadOnly = signal(false);
      const opened: unknown[] = [];
      (c as any).snackBar = { open: (...a: unknown[]) => opened.push(a) };
      (c as any).translate = { instant: (k: string) => k };
      return { c, opened };
    }

    it('sur 403 : verrouille le formulaire, affiche un message, et renvoie true', () => {
      const { c, opened } = comp();
      const handled = (c as any).handlePlanLocked({ status: 403 });
      expect(handled).toBe(true);
      expect(c.isReadOnly()).toBe(true);
      expect(opened.length).toBe(1);
    });

    it('sur une autre erreur : ne verrouille pas et renvoie false', () => {
      const { c, opened } = comp();
      const handled = (c as any).handlePlanLocked({ status: 500 });
      expect(handled).toBe(false);
      expect(c.isReadOnly()).toBe(false);
      expect(opened.length).toBe(0);
    });
  });

  // -------------------------------------------------------------------------
  // #452 — flushResponseGrids : enregistre le dernier état de grille en attente
  // au moment du submit (sinon l'auto-save débouncé est perdu si on valide
  // aussitôt → type/valeurs/libellés non sauvegardés, grille « vide » au reload).
  // -------------------------------------------------------------------------
  describe('#452 flushResponseGrids', () => {
    function comp() {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).typeMetriqueOptions = signal([
        { id_nomenclature: 1351, mnemonique: 'CHIFFRE', label: 'Chiffre' },
      ]);
      (c as any).formatMetriqueOptions = signal([
        { id_nomenclature: 1371, mnemonique: 'GRILLE', label: 'Grille' },
      ]);
      const calls: { id: number; p: any }[] = [];
      (c as any).enjeuService = {
        updateMetrique: (id: number, p: any) => { calls.push({ id, p }); return of(p); },
      };
      (c as any).latestGridData = new Map();
      return { c, calls };
    }

    it('PATCHe le dernier état CHIFFRE de chaque grille puis vide la file', () => {
      const { c, calls } = comp();
      (c as any).latestGridData.set(5, {
        nom_metrique: 'Taux', type_metrique: 1351,
        scores: { 1: { val: 0 }, 2: { val: 25 }, 3: { val: 50 }, 4: { val: 75 }, 5: { val: 100 } },
        _inactiveLevels: [],
      });
      let done = false;
      (c as any).flushResponseGrids().subscribe(() => { done = true; });
      expect(done).toBe(true);
      expect(calls.length).toBe(1);
      expect(calls[0].id).toBe(5);
      expect(calls[0].p.type_metrique).toBe(1351);
      expect(calls[0].p.format_metrique).toBe(1371); // GRILLE
      expect(calls[0].p.score_1_val).toBe(0);
      expect(calls[0].p.score_5_val).toBe(100);
      expect((c as any).latestGridData.size).toBe(0); // file vidée
    });

    it('sans grille en attente : ne déclenche aucun PATCH', () => {
      const { c, calls } = comp();
      let done = false;
      (c as any).flushResponseGrids().subscribe(() => { done = true; });
      expect(done).toBe(true);
      expect(calls.length).toBe(0);
    });
  });

  // -------------------------------------------------------------------------
  // #452 — Suppression d'un indicateur de réponse (saved + pending).
  // -------------------------------------------------------------------------
  describe('#452 suppression d\'indicateur de réponse', () => {
    it('removeResponseIndicator : supprime l\'indicateur et le retire de l\'action', () => {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).operationId = signal(2653);
      (c as any).existingOperation = signal({
        id_operation: 2653,
        metriques: [
          { id_metrique: 5, indicateur_id: 50, indicateur_type: 'REPONSE' },
          { id_metrique: 6, indicateur_id: 60, indicateur_type: 'REPONSE' },
        ],
      });
      const deleted: number[] = [];
      (c as any).enjeuService = {
        deleteIndicateur: (id: number) => { deleted.push(id); return of(null); },
      };
      c.removeResponseIndicator(5);
      expect(deleted).toEqual([50]); // supprime l'indicateur (cascade métrique)
      const remaining = (c as any).existingOperation().metriques.map((m: any) => m.id_metrique);
      expect(remaining).toEqual([6]); // retiré localement
    });

    it('removePendingResponseIndicator : retire l\'élément à l\'index donné', () => {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).pendingResponseIndicators = [
        { nom_indicateur: 'A' }, { nom_indicateur: 'B' }, { nom_indicateur: 'C' },
      ];
      c.removePendingResponseIndicator(1);
      expect((c as any).pendingResponseIndicators.map((p: any) => p.nom_indicateur)).toEqual(['A', 'C']);
    });
  });
});
