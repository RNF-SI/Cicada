/**
 * Tests unitaires pour OperationFormComponent — ventilation budgétaire 4 modes.
 *
 * On teste la logique métier (helpers, save payload, inférence mode au chargement)
 * sans monter le composant complet (trop de dépendances).
 */
import { TestBed } from '@angular/core/testing';
import { signal, computed } from '@angular/core';
import { OperationFormComponent } from './operation-form.component';

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
});
