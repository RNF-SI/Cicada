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
