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
