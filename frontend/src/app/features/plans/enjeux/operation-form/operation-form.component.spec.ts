/**
 * Tests unitaires pour OperationFormComponent — ventilation budgétaire 4 modes.
 *
 * On teste la logique métier (helpers, save payload, inférence mode au chargement)
 * sans monter le composant complet (trop de dépendances).
 */
import { TestBed } from '@angular/core/testing';
import { signal, computed } from '@angular/core';
import { Subject, of, throwError } from 'rxjs';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
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
  // #560 — lignes RH (dérivées des postes ou des organismes selon le mode)
  comp.rhLines = [];

  // Signals (reproduits manuellement car pas d'injection Angular)
  (comp as any).ventilationMode = signal<'none' | 'by_org' | 'by_type' | 'by_org_type'>('none');
  (comp as any).declinaisonParPoste = signal(false);
  (comp as any).postes = signal<any[]>([]);
  (comp as any).rhMode = computed(() => {
    if ((comp as any).declinaisonParPoste()) return 'postes';
    const mode = (comp as any).ventilationMode();
    return mode === 'by_org' || mode === 'by_org_type' ? 'organismes' : 'global';
  });
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
  // #486 — code complet affiché AVANT enregistrement : le backend fournit le
  // rang ; tant qu'il n'a pas répondu on montre le préfixe suivi de « … », pour
  // ne jamais vider le bloc pendant la frappe.
  // -------------------------------------------------------------------------
  describe('#486 displayCode (aperçu avant enregistrement)', () => {
    function makeDisplay() {
      const resolvedCode = signal<string | null>(null);
      const previewCode = signal<string | null>(null);
      const displayCode = computed<string | null>(() => {
        const full = resolvedCode();
        if (full) return full;
        const prefix = previewCode();
        return prefix ? `${prefix}…` : null;
      });
      return { resolvedCode, previewCode, displayCode };
    }

    it('affiche le code complet dès que le backend a répondu', () => {
      const d = makeDisplay();
      d.previewCode.set('CS');
      d.resolvedCode.set('CS3');
      expect(d.displayCode()).toBe('CS3');
    });

    it('affiche le préfixe suivi de « … » tant que le rang est inconnu', () => {
      const d = makeDisplay();
      d.previewCode.set('IP');
      expect(d.displayCode()).toBe('IP…');
    });

    it('repasse en préfixe seul si le backend ne sait pas situer l\'action', () => {
      const d = makeDisplay();
      d.previewCode.set('CS');
      d.resolvedCode.set('CS2');
      d.resolvedCode.set(null); // ex. plan non résolu / erreur réseau
      expect(d.displayCode()).toBe('CS…');
    });

    it('n\'affiche rien tant qu\'aucun type ni catégorie n\'est choisi', () => {
      const d = makeDisplay();
      expect(d.displayCode()).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // #485 — numéro fixé manuellement dans le code : normalisation du payload.
  // Reproduit l'expression de buildPayload : vide/0/négatif → null (retour à la
  // numérotation automatique), positif → entier.
  // -------------------------------------------------------------------------
  describe('#485 normalisation du numéro fixé (numero_manuel)', () => {
    const normalize = (raw: number | null): number | null =>
      raw != null && raw > 0 ? Math.floor(raw) : null;

    it('null (champ vide) → null (numérotation automatique)', () => {
      expect(normalize(null)).toBeNull();
    });

    it('0 → null (retour à la numérotation automatique)', () => {
      expect(normalize(0)).toBeNull();
    });

    it('valeur négative → null', () => {
      expect(normalize(-3)).toBeNull();
    });

    it('entier positif → conservé', () => {
      expect(normalize(4)).toBe(4);
    });

    it('décimal positif → tronqué à l\'entier', () => {
      expect(normalize(2.9)).toBe(2);
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
    function comp(fail = false) {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).typeMetriqueOptions = signal([
        { id_nomenclature: 1351, mnemonique: 'CHIFFRE', label: 'Chiffre' },
      ]);
      (c as any).formatMetriqueOptions = signal([
        { id_nomenclature: 1371, mnemonique: 'GRILLE', label: 'Grille' },
      ]);
      const calls: { id: number; p: any }[] = [];
      (c as any).enjeuService = {
        updateMetrique: (id: number, p: any) => {
          calls.push({ id, p });
          return fail ? throwError(() => ({ status: 400 })) : of(p);
        },
      };
      (c as any).latestGridData = new Map();
      return { c, calls };
    }

    it('PATCHe le dernier état CHIFFRE de chaque grille en attente', () => {
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
    });

    it('sans grille en attente : ne déclenche aucun PATCH', () => {
      const { c, calls } = comp();
      let done = false;
      (c as any).flushResponseGrids().subscribe(() => { done = true; });
      expect(done).toBe(true);
      expect(calls.length).toBe(0);
    });

    it('mode strict : propage l\'erreur si une grille est rejetée (400)', () => {
      const { c } = comp(true);
      (c as any).latestGridData.set(5, { nom_metrique: '', type_metrique: 1351, scores: {}, _inactiveLevels: [] });
      let errored = false, completed = false;
      (c as any).flushResponseGrids(true).subscribe({ next: () => { completed = true; }, error: () => { errored = true; } });
      expect(errored).toBe(true);   // bloque la validation
      expect(completed).toBe(false);
    });

    it('mode tolérant (brouillon) : absorbe l\'erreur (ne bloque pas)', () => {
      const { c } = comp(true);
      (c as any).latestGridData.set(5, { nom_metrique: '', type_metrique: 1351, scores: {}, _inactiveLevels: [] });
      let errored = false, completed = false;
      (c as any).flushResponseGrids(false).subscribe({ next: () => { completed = true; }, error: () => { errored = true; } });
      expect(errored).toBe(false);
      expect(completed).toBe(true);
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
      (c as any).latestGridData = new Map();
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

  // -------------------------------------------------------------------------
  // #452 — Intitulé d'indicateur de réponse obligatoire pour valider l'action.
  // -------------------------------------------------------------------------
  describe('#452 hasMissingResponseTitle', () => {
    const DEFAULT_NAME = 'Nouvel indicateur de réponse';
    function comp(saved: any[], pending: any[]): OperationFormComponent {
      const c = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (c as any).responseIndicators = () => saved;
      (c as any).pendingResponseIndicators = pending;
      (c as any).translate = {
        instant: (k: string) => k === 'enjeux.operations.newIndicatorDefault' ? DEFAULT_NAME : k,
      };
      return c;
    }

    it('vrai si un indicateur enregistré n\'a pas d\'intitulé (vide ou espaces)', () => {
      expect(comp([{ indicateur_nom: '' }], []).hasMissingResponseTitle()).toBe(true);
      expect(comp([{ indicateur_nom: '   ' }], []).hasMissingResponseTitle()).toBe(true);
    });

    it('vrai si l\'intitulé est resté le nom par défaut (non renommé)', () => {
      expect(comp([{ indicateur_nom: DEFAULT_NAME }], []).hasMissingResponseTitle()).toBe(true);
      expect(comp([], [{ nom_indicateur: DEFAULT_NAME }]).hasMissingResponseTitle()).toBe(true);
    });

    it('vrai si un indicateur en attente n\'a pas d\'intitulé', () => {
      expect(comp([], [{ nom_indicateur: '' }]).hasMissingResponseTitle()).toBe(true);
    });

    it('faux si tous les indicateurs ont un intitulé renseigné', () => {
      expect(comp([{ indicateur_nom: 'État du lac' }], [{ nom_indicateur: 'Suivi' }]).hasMissingResponseTitle()).toBe(false);
    });

    it('faux s\'il n\'y a aucun indicateur de réponse', () => {
      expect(comp([], []).hasMissingResponseTitle()).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // #520 — Bascule du choix « protocole dans CAMPanule ? »
  // -------------------------------------------------------------------------
  describe('#520 — onProtocoleCampanuleChange', () => {
    function makeComp(): OperationFormComponent {
      const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (comp as any).selectedCampanule = signal<unknown>({ cd_protocole: 42, lb_protocole_court: 'Proto X' });
      (comp as any).campanuleSearchCtrl = new FormControl('Proto X');
      (comp as any).form = new FormGroup({
        protocole_dans_campanule: new FormControl(false),
        protocole_campanule_nom: new FormControl('Proto X'),
        cd_protocole_campanule: new FormControl(42),
        description_protocole: new FormControl('Description issue de CAMPanule'),
        objectif_protocole: new FormControl('Objectif CAMPanule'),
        periode_echantillonnage: new FormControl('Mai; Juin'),
      });
      return comp;
    }

    it('vide les champs auto-remplis et la sélection CAMPanule au changement de choix', () => {
      const c = makeComp();
      c.onProtocoleCampanuleChange();
      const form = (c as any).form as FormGroup;
      expect(form.get('description_protocole')?.value).toBe('');
      expect(form.get('objectif_protocole')?.value).toBe('');
      expect(form.get('periode_echantillonnage')?.value).toBe('');
      expect(form.get('protocole_campanule_nom')?.value).toBe('');
      expect(form.get('cd_protocole_campanule')?.value).toBeNull();
      expect((c as any).selectedCampanule()).toBeNull();
      expect((c as any).campanuleSearchCtrl.value).toBe('');
    });

    // Retour de test #520 : un aller-retour du choix ne doit pas perdre les données.
    function makeEmptyComp(): OperationFormComponent {
      const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (comp as any).selectedCampanule = signal<unknown>(null);
      (comp as any).campanuleSearchCtrl = new FormControl('');
      (comp as any).form = new FormGroup({
        protocole_dans_campanule: new FormControl(false),
        protocole_campanule_nom: new FormControl(''),
        cd_protocole_campanule: new FormControl(null),
        description_protocole: new FormControl(''),
        objectif_protocole: new FormControl(''),
        periode_echantillonnage: new FormControl(''),
      });
      return comp;
    }

    it('préserve la saisie manuelle après un aller-retour Non → Oui → Non', () => {
      const c = makeEmptyComp();
      const form = (c as any).form as FormGroup;

      // L'utilisateur saisit manuellement en mode « Non »
      form.patchValue({
        description_protocole: 'Ma description perso',
        objectif_protocole: 'Mon objectif perso',
        periode_echantillonnage: 'Avril; Mai',
      });

      // Non → Oui
      form.get('protocole_dans_campanule')?.setValue(true);
      c.onProtocoleCampanuleChange();
      expect(form.get('description_protocole')?.value).toBe('');

      // Oui → Non : la saisie manuelle est restaurée
      form.get('protocole_dans_campanule')?.setValue(false);
      c.onProtocoleCampanuleChange();
      expect(form.get('description_protocole')?.value).toBe('Ma description perso');
      expect(form.get('objectif_protocole')?.value).toBe('Mon objectif perso');
      expect(form.get('periode_echantillonnage')?.value).toBe('Avril; Mai');
    });

    it('restaure la sélection CAMPanule après un aller-retour Oui → Non → Oui', () => {
      const c = makeComp(); // démarre avec un protocole CAMPanule sélectionné
      const form = (c as any).form as FormGroup;
      form.get('protocole_dans_campanule')?.setValue(true);

      // Oui → Non : la sélection est archivée, les champs éditables vidés
      form.get('protocole_dans_campanule')?.setValue(false);
      c.onProtocoleCampanuleChange();
      expect(form.get('cd_protocole_campanule')?.value).toBeNull();
      expect((c as any).selectedCampanule()).toBeNull();

      // Non → Oui : la sélection CAMPanule précédente est restaurée
      form.get('protocole_dans_campanule')?.setValue(true);
      c.onProtocoleCampanuleChange();
      expect(form.get('cd_protocole_campanule')?.value).toBe(42);
      expect(form.get('protocole_campanule_nom')?.value).toBe('Proto X');
      expect(form.get('description_protocole')?.value).toBe('Description issue de CAMPanule');
      expect((c as any).selectedCampanule()).toEqual({ cd_protocole: 42, lb_protocole_court: 'Proto X' });
    });
  });

  // -------------------------------------------------------------------------
  // #483 — changer le type d'action ne doit effacer aucune saisie
  // -------------------------------------------------------------------------
  describe('#483 — onTypeActionSelected conserve les saisies', () => {
    function makeComp(): OperationFormComponent {
      const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      const selected = signal<any>(null);
      (comp as any).selectedTypeAction = selected;
      (comp as any).isCSAction = computed(() => {
        const s = selected();
        return !!s && String(s.cd_nomenclature || '').startsWith('CS');
      });
      (comp as any).estSuiviExistant = signal(false);
      (comp as any).availableInventaires = signal<any[]>([]);
      (comp as any).libelleDisplay = signal('');
      (comp as any).loadInventairesByTypeAction = jest.fn();
      (comp as any).syncConditionalValidators = jest.fn();
      (comp as any).setSuiviFieldsEnabled = jest.fn();
      (comp as any).form = new FormGroup({
        id_type_action: new FormControl(null),
        libelle: new FormControl(''),
        intitule_suivi: new FormControl(''),
        id_suivi: new FormControl(null),
        objectif_principal: new FormControl(''),
      });
      return comp;
    }

    const GA = { id_nomenclature: 1, cd_nomenclature: 'GA1' } as any;
    const CS1 = { id_nomenclature: 2, cd_nomenclature: 'CS1' } as any;
    const CS2 = { id_nomenclature: 3, cd_nomenclature: 'CS2' } as any;

    it('non-CS → CS : le libellé saisi devient l\'intitulé du suivi', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      c.onTypeActionSelected(GA);
      form.get('libelle')?.setValue('Comptage des oiseaux nicheurs');

      c.onTypeActionSelected(CS1);

      expect(form.get('intitule_suivi')?.value).toBe('Comptage des oiseaux nicheurs');
      expect(form.getRawValue().libelle).toBe('Comptage des oiseaux nicheurs');
      expect((c as any).libelleDisplay()).toBe('Comptage des oiseaux nicheurs');
    });

    it('CS → CS : ne réécrit pas l\'intitulé déjà saisi', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      c.onTypeActionSelected(CS1);
      form.get('intitule_suivi')?.setValue('Suivi avifaune');
      form.get('libelle')?.setValue('Suivi avifaune');
      form.get('objectif_principal')?.setValue('Évaluer la population');

      c.onTypeActionSelected(CS2);

      expect(form.get('intitule_suivi')?.value).toBe('Suivi avifaune');
      expect(form.get('objectif_principal')?.value).toBe('Évaluer la population');
    });

    it('CS → non-CS : l\'intitulé du suivi est conservé comme libellé', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      c.onTypeActionSelected(CS1);
      form.get('intitule_suivi')?.setValue('Suivi avifaune');

      c.onTypeActionSelected(GA);

      expect(form.get('libelle')?.value).toBe('Suivi avifaune');
      expect(form.get('intitule_suivi')?.value).toBe('Suivi avifaune');
    });

    it('aller-retour non-CS → CS → non-CS : aucune perte', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      c.onTypeActionSelected(GA);
      form.get('libelle')?.setValue('Comptage des oiseaux nicheurs');

      c.onTypeActionSelected(CS1);
      c.onTypeActionSelected(GA);

      expect(form.get('libelle')?.value).toBe('Comptage des oiseaux nicheurs');
    });

    it('abandonne un suivi existant absent du nouveau type, sans vider les champs', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      (c as any).estSuiviExistant.set(true);
      form.get('id_suivi')?.setValue(42);
      form.get('objectif_principal')?.setValue('Évaluer la population');

      (c as any).dropStaleSuiviSelection([{ id_suivi_inventaire: 99 }]);

      expect(form.get('id_suivi')?.value).toBeNull();
      expect((c as any).estSuiviExistant()).toBe(false);
      expect(form.get('objectif_principal')?.value).toBe('Évaluer la population');
    });

    it('conserve la sélection si le suivi existe toujours pour le nouveau type', () => {
      const c = makeComp();
      const form = (c as any).form as FormGroup;
      (c as any).estSuiviExistant.set(true);
      form.get('id_suivi')?.setValue(42);

      (c as any).dropStaleSuiviSelection([{ id_suivi_inventaire: 42 }]);

      expect(form.get('id_suivi')?.value).toBe(42);
      expect((c as any).estSuiviExistant()).toBe(true);
    });
  });

  describe('#561 — « Respectez-vous strictement le protocole ? » facultatif', () => {
    function makeComp(campanule: boolean): OperationFormComponent {
      const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (comp as any).isCSAction = () => true;
      (comp as any).estSuiviExistant = () => false;
      (comp as any).form = new FormGroup({
        intitule_suivi: new FormControl(''),
        objectif_principal: new FormControl(''),
        cibles_principales: new FormControl(null),
        protocole_dans_campanule: new FormControl(campanule),
        respect_protocole: new FormControl(null),
        cd_protocole_campanule: new FormControl(null),
        nom_protocole: new FormControl(''),
      });
      return comp;
    }

    it('ne rend jamais respect_protocole obligatoire, même en mode CAMPanule', () => {
      const c = makeComp(true);
      (c as any).syncConditionalValidators();
      const ctrl = (c as any).form.get('respect_protocole');
      expect(ctrl.hasValidator(Validators.required)).toBe(false);
      expect(ctrl.valid).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // #588 — Le type d'action est obligatoire (et doit être marqué par une *)
  // -------------------------------------------------------------------------

  describe("#588 — type d'action obligatoire", () => {
    function makeForm(): FormGroup {
      const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
      (comp as any).fb = new FormBuilder();
      (comp as any).initForm();
      return (comp as any).form as FormGroup;
    }

    it('applique Validators.required sur id_type_action', () => {
      const ctrl = makeForm().get('id_type_action')!;
      expect(ctrl.hasValidator(Validators.required)).toBe(true);
    });

    it('rend le formulaire invalide tant que le type d\'action est vide', () => {
      const form = makeForm();
      expect(form.get('id_type_action')!.valid).toBe(false);
      form.get('id_type_action')!.setValue(42);
      expect(form.get('id_type_action')!.valid).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // #560 — Tableau RH dérivé (déclinaison par poste / ventilation par organisme)
  // -------------------------------------------------------------------------

  describe('lignes RH dérivées (#560)', () => {
    beforeEach(() => {
      comp.rhLines = [];
      (comp as any).declinaisonParPoste.set(false);
      (comp as any).ventilationMode.set('none');
      (comp as any).postes.set([
        { id_poste: 1, libelle: 'Conservateur', organisme_nom: 'RNF', finance_par_defaut: true },
        { id_poste: 2, libelle: 'Bénévole', organisme_nom: 'RNF', finance_par_defaut: false },
      ]);
    });

    it('affiche une saisie globale sans déclinaison ni ventilation par organisme (#580)', () => {
      expect((comp as any).rhMode()).toBe('global');
    });

    it('propose une ligne de temps total sans cible en mode global (#580)', () => {
      (comp as any).syncRhLines();
      expect(comp.rhLines.length).toBe(1);
      const [line] = comp.rhLines;
      expect(line.id_poste).toBeNull();
      expect(line.id_organisme).toBeNull();
      expect(line.derived).toBe(true);
    });

    it('préserve le temps total saisi lors d\'une resynchronisation en mode global (#580)', () => {
      (comp as any).syncRhLines();
      comp.setRhJours(0, 0, '12');
      // Une resynchronisation (ex. cibles rechargées) est idempotente : la ligne
      // globale et ses jours doivent subsister.
      (comp as any).syncRhLines();
      const global = comp.rhLines.find(l => l.id_poste == null && l.id_organisme == null);
      expect(global).toBeDefined();
      expect(global!.jours[0]).toBe(12);
      expect(comp.rhLines.length).toBe(1);
    });

    it('décline une ligne par poste quand la case est cochée', () => {
      comp.toggleDeclinaisonParPoste(true);
      expect((comp as any).rhMode()).toBe('postes');
      expect(comp.rhLines.map(l => l.id_poste)).toEqual([1, 2]);
      expect(comp.rhLines.every(l => l.derived)).toBe(true);
    });

    it('hérite du financement des fonctions du poste', () => {
      comp.toggleDeclinaisonParPoste(true);
      expect(comp.rhLines.find(l => l.id_poste === 1)!.finance).toBe(true);
      expect(comp.rhLines.find(l => l.id_poste === 2)!.finance).toBe(false);
    });

    it('décline une ligne par organisme quand le budget est ventilé par organisme', () => {
      comp.onModeToggle('by_org');
      expect((comp as any).rhMode()).toBe('organismes');
      expect(comp.rhLines.map(l => l.id_organisme)).toEqual([100, 101]);
      expect(comp.rhLines.every(l => l.id_poste === null)).toBe(true);
    });

    it('préserve les jours déjà saisis en reconstruisant les lignes', () => {
      comp.toggleDeclinaisonParPoste(true);
      comp.setRhJours(0, 0, '8');
      // Une nouvelle synchronisation (ex. postes rechargés) ne doit rien perdre.
      comp.toggleDeclinaisonParPoste(true);
      expect(comp.getRhJours(0, 0)).toBe(8);
    });

    it('écarte les lignes qui ne correspondent plus au mode', () => {
      comp.toggleDeclinaisonParPoste(true);
      comp.setRhJours(0, 0, '8');
      // Passage en ventilation par organisme : les lignes par poste n'ont plus
      // de sens, seules les lignes par organisme subsistent.
      comp.toggleDeclinaisonParPoste(false);
      comp.onModeToggle('by_org');
      expect(comp.rhLines.every(l => l.id_poste === null)).toBe(true);
      expect(comp.rhLines.map(l => l.id_organisme)).toEqual([100, 101]);
    });

    it('conserve un lot ajouté à la main sur une cible déjà listée', () => {
      comp.toggleDeclinaisonParPoste(true);
      comp.addRhLine();
      comp.setRhTarget(2, 1); // second lot sur le poste 1
      comp.rhLines[2].finance = false;
      comp.toggleDeclinaisonParPoste(true); // resynchronisation
      expect(comp.rhLines.length).toBe(3);
      const lots = comp.rhLines.filter(l => l.id_poste === 1);
      expect(lots.length).toBe(2);
      expect(lots.filter(l => l.derived).length).toBe(1);
    });

    it('totalise les jours par année, financé et non financé séparément', () => {
      comp.toggleDeclinaisonParPoste(true);
      comp.setRhJours(0, 0, '8');   // Conservateur, financé
      comp.setRhJours(1, 0, '5');   // Bénévole, non financé
      expect(comp.getRhYearTotal(0)).toBe(13);
      expect(comp.getRhYearTotalByFinance(0, true)).toBe(8);
      expect(comp.getRhYearTotalByFinance(0, false)).toBe(5);
      expect(comp.hasRhNonFinance()).toBe(true);
    });

    it('affiche l\'organisme sous le libellé du poste', () => {
      comp.toggleDeclinaisonParPoste(true);
      expect(comp.rhLineLabel(comp.rhLines[0])).toBe('Conservateur');
      expect(comp.rhLineSubLabel(comp.rhLines[0])).toBe('RNF');
    });
  });
});

// ===========================================================================
// #531 — Lien « Voir le suivi de l'action » depuis la page de modification
// ===========================================================================

describe('OperationFormComponent — lien vers le suivi de l\'action (#531)', () => {
  function makeInstance(router: { navigate: jest.Mock }): OperationFormComponent {
    const comp = Object.create(OperationFormComponent.prototype) as OperationFormComponent;
    (comp as any).router = router;
    (comp as any).planSlug = signal<string | null>(null);
    (comp as any).operationId = signal<number | null>(null);
    return comp;
  }

  it('navigue vers la page globale de suivi de l\'action en édition', () => {
    const router = { navigate: jest.fn() };
    const c = makeInstance(router);
    (c as any).planSlug.set('plan-x');
    (c as any).operationId.set(42);

    c.goToSuivi();

    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'suivi-actions', 'action', 42]);
  });

  it('ne navigue pas en création (aucune action enregistrée)', () => {
    const router = { navigate: jest.fn() };
    const c = makeInstance(router);
    (c as any).planSlug.set('plan-x');
    (c as any).operationId.set(null);

    c.goToSuivi();

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('navigue vers la fiche synthétique de l\'action en édition', () => {
    const router = { navigate: jest.fn() };
    const c = makeInstance(router);
    (c as any).planSlug.set('plan-x');
    (c as any).operationId.set(42);

    c.goToFiche();

    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'enjeux', 'operations', 42, 'fiche']);
  });

  it('ne navigue pas vers la fiche en création', () => {
    const router = { navigate: jest.fn() };
    const c = makeInstance(router);
    (c as any).planSlug.set('plan-x');
    (c as any).operationId.set(null);

    c.goToFiche();

    expect(router.navigate).not.toHaveBeenCalled();
  });

});
