import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { PlanSuiviActionsComponent } from './plan-suivi-actions.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';

/**
 * #540 — Les actions rattachées directement à un indicateur (sans métrique)
 * doivent aussi apparaître dans le suivi des actions.
 */
describe('PlanSuiviActionsComponent — extraction des actions (#540)', () => {
  let component: PlanSuiviActionsComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    // Pas de detectChanges() : on évite ngOnInit et on teste la méthode d'extraction.
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
  });

  function extract(indicateurs: any[], enjeu: any) {
    const result: any[] = [];
    (component as any).extractOpsFromIndicateurs(indicateurs, enjeu, result, new Set<number>());
    return result;
  }

  const enjeu = { id_enjeu: 1, libelle: 'Enjeu 1', intitule_court: 'E1' };

  it('inclut les actions liées via une métrique', () => {
    const result = extract(
      [{ id_indicateur: 10, metriques: [{ id_metrique: 100, operations: [{ id_operation: 1000 }] }], operations: [] }],
      enjeu,
    );
    expect(result.map(r => r.operation.id_operation)).toEqual([1000]);
  });

  it('inclut les actions rattachées directement à l\'indicateur (sans métrique)', () => {
    const result = extract(
      [{ id_indicateur: 10, metriques: [], operations: [{ id_operation: 2000 }] }],
      enjeu,
    );
    expect(result.map(r => r.operation.id_operation)).toEqual([2000]);
    expect(result[0].enjeuId).toBe(1);
  });

  it('ne duplique pas une action présente à la fois via métrique et via l\'indicateur', () => {
    const result = extract(
      [{
        id_indicateur: 10,
        metriques: [{ id_metrique: 100, operations: [{ id_operation: 3000 }] }],
        operations: [{ id_operation: 3000 }],
      }],
      enjeu,
    );
    expect(result.map(r => r.operation.id_operation)).toEqual([3000]);
  });
});

/**
 * #569 — La RH saisie dans le suivi (lignes rh_lignes, depuis #560) doit se
 * répercuter dans le tableau de synthèse RH. Le champ scalaire etp/etp_realise
 * n'étant plus alimenté, l'agrégation doit sommer rh_lignes[].jours.
 */
describe('PlanSuiviActionsComponent — agrégation RH (#569)', () => {
  let component: PlanSuiviActionsComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
    component.currentYear.set(2026);
  });

  it('somme les jours prévisionnels des lignes RH (rh_lignes) pour l\'année en cours', () => {
    const op: any = {
      ventilation_mode: 'none',
      operation_annees: [
        { annee: 2026, rh_lignes: [{ jours: 5, finance: true }, { jours: 3, finance: false }] },
      ],
    };
    const cell = component.aggregateEtp(op, 'current');
    expect(cell.previsionnel).toBe(8);
  });

  it('somme les jours réalisés des lignes RH de la réalisation', () => {
    const op: any = {
      ventilation_mode: 'none',
      operation_annees: [
        {
          annee: 2026,
          rh_lignes: [{ jours: 10, finance: true }],
          realisation: { rh_lignes: [{ jours: 4, finance: true }, { jours: 2, finance: true }] },
        },
      ],
    };
    const cell = component.aggregateEtp(op, 'current');
    expect(cell.previsionnel).toBe(10);
    expect(cell.realise).toBe(6);
    expect(cell.hasRealise).toBe(true);
  });

  it('répercute la RH sur la période écoulée (années < année en cours)', () => {
    const op: any = {
      ventilation_mode: 'none',
      operation_annees: [
        { annee: 2024, rh_lignes: [{ jours: 7, finance: true }] },
        { annee: 2026, rh_lignes: [{ jours: 9, finance: true }] },
      ],
    };
    expect(component.aggregateEtp(op, 'past').previsionnel).toBe(7);
    expect(component.aggregateEtp(op, 'total').previsionnel).toBe(16);
  });

  it('conserve le repli sur l\'ancien champ etp quand aucune ligne RH n\'existe', () => {
    const op: any = {
      ventilation_mode: 'none',
      operation_annees: [
        { annee: 2026, etp: 4, realisation: { etp_realise: 3 } },
      ],
    };
    const cell = component.aggregateEtp(op, 'current');
    expect(cell.previsionnel).toBe(4);
    expect(cell.realise).toBe(3);
  });
});

/**
 * #568 — Pagination des tableaux (actions à plat + tableaux groupés budget/RH).
 */
describe('PlanSuiviActionsComponent — pagination (#568)', () => {
  let component: PlanSuiviActionsComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
  });

  function seed(n: number) {
    const ops = Array.from({ length: n }, (_, i) => ({
      operation: { id_operation: i + 1, libelle: `Op ${i + 1}` },
      enjeuLibelle: 'E1',
      enjeuId: 1,
    }));
    component.allOperations.set(ops as any);
  }

  it('découpe la liste à plat des actions par page (pageSize=20)', () => {
    seed(25);
    expect(component.pageSize).toBe(20);
    component.page.set(1);
    expect(component.pagedOperations().length).toBe(20);
    expect(component.pagedOperations()[0].operation.id_operation).toBe(1);
    component.page.set(2);
    expect(component.pagedOperations().length).toBe(5);
    expect(component.pagedOperations()[0].operation.id_operation).toBe(21);
  });

  it('pagine les tableaux groupés en conservant le groupe complet pour les sous-totaux', () => {
    seed(25); // actions non ventilées → un seul groupe « plan général »
    expect(component.orgGroupsRowCount()).toBe(25);
    component.page.set(1);
    let groups = component.pagedOrgGroups();
    expect(groups.length).toBe(1);
    expect(groups[0].operations.length).toBe(20);       // lignes de la page
    expect(groups[0].fullOperations.length).toBe(25);   // total pour le sous-total
    component.page.set(2);
    groups = component.pagedOrgGroups();
    expect(groups[0].operations.length).toBe(5);
    expect(groups[0].fullOperations.length).toBe(25);
  });
});

/**
 * #570 — Le choix de l'année de référence (setCurrentYear) déplace la frontière
 * « Année en cours » / « Période écoulée » du tableau de synthèse.
 */
describe('PlanSuiviActionsComponent — choix de l\'année de synthèse (#570)', () => {
  let component: PlanSuiviActionsComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
  });

  it('réajuste la période écoulée à l\'année sélectionnée', () => {
    const op: any = {
      ventilation_mode: 'none',
      operation_annees: [
        { annee: 2024, budget: 100 },
        { annee: 2026, budget: 200 },
        { annee: 2028, budget: 300 },
      ],
    };
    component.setCurrentYear(2028);
    expect(component.currentYear()).toBe(2028);
    // Année en cours = 2028 ; période écoulée = 2024 + 2026.
    expect(component.aggregateBudget(op, 'current').previsionnel).toBe(300);
    expect(component.aggregateBudget(op, 'past').previsionnel).toBe(300);

    component.setCurrentYear(2026);
    expect(component.aggregateBudget(op, 'current').previsionnel).toBe(200);
    expect(component.aggregateBudget(op, 'past').previsionnel).toBe(100);
  });
});

/**
 * #616 — la vue globale du budget restait à 0 € : elle ne lisait que les
 * enveloppes `budget_fonctionnement` / `_investissement`, jamais alimentées
 * dans les modes « + type de poste » (le budget y est dérivé des coûts).
 */
describe('PlanSuiviActionsComponent — agrégation budget / RH (#616)', () => {
  let component: PlanSuiviActionsComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
    component.currentYear.set(2027);
  });

  /** Action en ventilation maximale : coûts par organisme + lignes RH. */
  const action: any = {
    id_operation: 1, ventilation_mode: 'by_org_type_poste',
    operation_annees: [{
      annee: 2027,
      budget: null, etp: null, budget_fonctionnement: null, budget_investissement: null,
      organismes: [{
        id_organisme: 100, budget_fonctionnement: null, budget_investissement: null,
        cout_stage: '200.00', cout_prestataire: '1000.00', autre_cout: '500.00',
        realisation: { cout_prestataire_realise: '800.00' },
      }],
      rh_lignes: [
        { id_poste: 1, jours: '10.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
      ],
      realisation: {
        rh_lignes: [
          { id_poste: 1, jours: '8.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
        ],
      },
    }],
  };

  it('agrège le budget dérivé des coûts saisis, prévu et réalisé', () => {
    const cell = component.aggregateBudget(action, 'total');
    expect(cell.previsionnel).toBe(4700);   // 3000 salarial + 200 + 1000 + 500
    expect(cell.realise).toBe(3200);        // 2400 salarial réalisé + 800
    expect(cell.hasRealise).toBe(true);
  });

  it('agrège les jours depuis les lignes RH', () => {
    const cell = component.aggregateEtp(action, 'total');
    expect(cell.previsionnel).toBe(10);
    expect(cell.realise).toBe(8);
    expect(cell.hasRealise).toBe(true);
  });

  it('restreint l\'agrégation à la période demandée', () => {
    expect(component.aggregateBudget(action, 'current').previsionnel).toBe(4700);
    // 2027 n'est pas une année écoulée : rien à agréger.
    expect(component.aggregateBudget(action, 'past').previsionnel).toBe(0);
  });

  it('n\'affiche aucun réalisé tant qu\'aucun suivi n\'est saisi', () => {
    const sansSuivi = {
      ...action,
      operation_annees: [{ ...action.operation_annees[0], realisation: null, organismes: [{ id_organisme: 100, cout_prestataire: '1000.00' }] }],
    };
    const cell = component.aggregateBudget(sansSuivi as any, 'total');
    expect(cell.previsionnel).toBe(4000);   // 3000 salarial + 1000
    expect(cell.hasRealise).toBe(false);
  });

  it('conserve le mode « totaux directs »', () => {
    const directe: any = {
      id_operation: 2, ventilation_mode: 'none',
      operation_annees: [{
        annee: 2027, budget: '1500.00', etp: '3.00', rh_lignes: [],
        realisation: { budget_realise: '1200.00', rh_lignes: [] },
      }],
    };
    expect(component.aggregateBudget(directe, 'total').previsionnel).toBe(1500);
    expect(component.aggregateBudget(directe, 'total').realise).toBe(1200);
    // Repli sur l'ancien champ `etp` pour les données antérieures à #560.
    expect(component.aggregateEtp(directe, 'total').previsionnel).toBe(3);
  });
});

/**
 * #637 — L'export du tableau doit refléter l'onglet actif ET les filtres en
 * cours, sans se limiter à la page affichée.
 */
describe('PlanSuiviActionsComponent — export du tableau (#637)', () => {
  let component: PlanSuiviActionsComponent;

  const makeOp = (id: number, libelle: string, annees: any[] = []) => ({
    id_operation: id,
    libelle,
    code_affichage: `CS${id}`,
    priorite_label: 'Priorité 1',
    ventilation_mode: 'none',
    operation_annees: annees,
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanSuiviActionsComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigate: jest.fn(), events: of(), createUrlTree: jest.fn(), serializeUrl: jest.fn() } },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]), getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of({ enjeux: [], fcr: [] }) } },
      ],
    });
    component = TestBed.createComponent(PlanSuiviActionsComponent).componentInstance;
    component.planYearStart.set(2026);
    component.planYearEnd.set(2027);
    component.allOperations.set([
      {
        operation: makeOp(1, 'Action A', [
          { annee: 2026, periodicite: true, periodicite_mensuelle: { '3': true, '5': true } },
        ]) as any,
        enjeuLibelle: 'Enjeu 1', enjeuId: 1,
      },
      {
        operation: makeOp(2, 'Action B', [
          { annee: 2027, periodicite: true, periodicite_mensuelle: {} },
        ]) as any,
        enjeuLibelle: 'Enjeu 2', enjeuId: 2,
      },
    ]);
  });

  const grid = (name: string, ...args: any[]) =>
    (component as any)[name](...args) as { entetes: string[]; lignes: any[] };
  /** Vue « matrice » (en-tête + lignes), indépendante de la mise en forme. */
  const rows = (name: string, ...args: any[]): any[][] => {
    const g = grid(name, ...args);
    const text = (c: any) => (c && typeof c === 'object' ? c.t : c);
    return [g.entetes, ...g.lignes.map(l => l.cellules.map(text))];
  };

  it('exporte une ligne par action filtrée, avec une colonne par année', () => {
    const out = rows('buildRealisationGrid');
    expect(out).toHaveLength(3); // en-tête + 2 actions
    expect(out[0]).toContain('2026');
    expect(out[0]).toContain('2027');
    expect(out[1][2]).toBe('Action A');
    expect(out[2][2]).toBe('Action B');
  });

  it('n\'exporte que les actions retenues par les filtres', () => {
    component.filters.enjeu.set([2]);
    const out = rows('buildRealisationGrid');
    expect(out).toHaveLength(2);
    expect(out[1][2]).toBe('Action B');
  });

  it('exporte toutes les lignes filtrées, pas seulement la page courante', () => {
    component.allOperations.set(
      Array.from({ length: 25 }, (_, i) => ({
        operation: makeOp(i + 1, `Action ${i + 1}`) as any,
        enjeuLibelle: 'Enjeu 1', enjeuId: 1,
      })),
    );
    expect(component.pagedOperations().length).toBe(component.pageSize);
    expect(rows('buildRealisationGrid')).toHaveLength(26);
  });

  it('exporte la planification mois par mois, année par année', () => {
    const out = rows('buildPlanificationGrid');
    expect(out).toHaveLength(3);
    expect(out[1][6]).toBe(2026);
    // monthsShort n'est pas traduit dans le test : repli sur les numéros de mois.
    expect(String(out[1][7]).split(' ')).toHaveLength(2);
    expect(out[2][6]).toBe(2027);
    expect(out[2][7]).toBe('');
  });

  // ===========================================================================
  // Retour recette : colonne Code surchargée, totaux mal placés, aucun visuel
  // ===========================================================================

  it('sépare le code d’affichage du code d’opération en deux colonnes', () => {
    component.allOperations.set([{
      operation: { ...makeOp(1, 'Action A'), code_operation: 'CAM-SE01' } as any,
      enjeuLibelle: 'Enjeu 1', enjeuId: 1,
    }]);
    const out = rows('buildRealisationGrid');

    expect(out[0][0]).toBe('plans.suivis.actions.export.code');
    expect(out[0][1]).toBe('plans.suivis.actions.export.codeOperation');
    expect(out[1][0]).toBe('CS1');        // code d'affichage calculé par CICADA
    expect(out[1][1]).toBe('CAM-SE01');   // code saisi par la structure
    // Aucune cellule ne recolle les deux identifiants.
    expect(out[1].some((c: any) => String(c).includes('·'))).toBe(false);
  });

  it('clôt chaque groupe par sa ligne de total, hors de la colonne Code', () => {
    const g = grid('buildAggregationGrid', 'budget');
    expect(g.entetes[0]).toBe('plans.suivis.actions.organisme');

    // Bucket « Plan général » : 2 actions puis le total du groupe.
    expect(g.lignes).toHaveLength(3);
    expect(g.lignes[0].type).toBeUndefined();
    const total = g.lignes[2];
    expect(total.type).toBe('total');
    // Le libellé du total est dans la colonne « Organisme »…
    expect(String(total.cellules[0])).toContain('plans.suivis.actions.planGeneral');
    // … et les colonnes d'identification de l'action restent vides.
    expect(total.cellules.slice(1, 7)).toEqual(['', '', '', '', '', '']);
  });

  it('annonce l’onglet et les filtres actifs en tête de classeur', () => {
    component.setTab('realisation');
    component.filters.enjeu.set([2]);
    component.filters.text.set('Balbuzard');

    const payload = (component as any).buildExportPayload();
    expect(payload.onglet).toBe('plans.suivis.actions.tabs.realisation');
    expect(payload.meta).toContainEqual([
      'plans.suivis.actions.export.onglet', 'plans.suivis.actions.tabs.realisation',
    ]);
    expect(payload.meta).toContainEqual(['common.actions.search', 'Balbuzard']);
    // Les colonnes d'identification restent visibles au défilement.
    expect(payload.gel).toBe(6);
  });

  it('marque les colonnes de montants pour que le tableur affiche « € » (#644)', () => {
    component.setTab('budget');
    const payload = (component as any).buildExportPayload();

    // Identification (organisme + 6 colonnes d'action) : aucun format imposé.
    expect(payload.formats.slice(0, 7)).toEqual([null, null, null, null, null, null, null]);
    // Colonnes chiffrées prévi/réalisé des 3 périodes : toutes en euros.
    expect(payload.formats.slice(7)).toEqual(Array(6).fill('euro'));
    expect(payload.formats).toHaveLength(payload.entetes.length);
  });

  it('n’ajoute pas de « € » aux colonnes de jours de l’onglet RH (#644)', () => {
    component.setTab('rh');
    const payload = (component as any).buildExportPayload();
    expect(payload.formats.every((f: any) => f === null)).toBe(true);
  });
});
