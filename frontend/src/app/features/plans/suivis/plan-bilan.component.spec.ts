import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { PlanBilanComponent } from './plan-bilan.component';
import { AdminService } from '../../../core/services/admin.service';
import {
  RealisationService, BilanResponse, BilanIndicateursResponse, BilanSeriesResponse,
} from '../../../core/services/realisation.service';

/**
 * #639 — L'export des résultats du bilan doit sérialiser les agrégations
 * chargées avec les filtres en cours (portée, année, enjeu), et le filtre
 * « Enjeux/FCR » doit aussi scoper l'onglet Indicateurs.
 */
describe('PlanBilanComponent — export des résultats (#639)', () => {
  let component: PlanBilanComponent;
  let realisationService: {
    bilan: jest.Mock;
    bilanIndicateurs: jest.Mock;
    bilanSeries: jest.Mock;
  };

  const counts = (termine: number, total: number) => ({
    non_demarre: 0, en_cours: 0, partiel: 0, termine,
    abandonne: 0, reporte: 0, inconnu: 0, total,
  });

  const bilan = {
    plan_id: 1, plan_nom: 'Plan test', annee_min: 2026, annee_max: 2027,
    taux_realisation: counts(3, 5),
    by_categorie_action: [{ ...counts(1, 2), code: 'CS', label: 'Connaissance et suivi' }],
    by_enjeu: [{ ...counts(2, 3), enjeu_id: 7, libelle: 'Enjeu 7' }],
    budget: {
      fonctionnement: { previsionnel: 1000, realise: 800 },
      investissement: { previsionnel: 500, realise: 0 },
      total: { previsionnel: 1500, realise: 800 },
    },
    rh: {
      previsionnel: 20, realise: 12,
      previsionnel_finance: 15, previsionnel_non_finance: 5,
      realise_finance: 10, realise_non_finance: 2,
    },
  } as BilanResponse;

  const indicateurs = {
    plan_id: 1, plan_nom: 'Plan test',
    total_indicateurs: 4, indicateurs_evalues: 3, taux_evaluation_pct: 75,
    score_distribution: [{ score: 4, label: 'Bon', count: 3 }],
    by_enjeu: [{ enjeu_id: 7, libelle: 'Enjeu 7', moyenne: 4, count: 3 }],
  } as BilanIndicateursResponse;

  const series = {
    plan_id: 1, plan_nom: 'Plan test', years: [2026, 2027],
    indicateurs_evolution: { mean: [3, 4], min: [2, 3], max: [4, 5], std: [0.5, 0.5] },
    rh_par_annee: { previsionnel: [10, 10], realise: [6, 6] },
    actions_par_annee: {
      niveaux: {
        termine: [1, 2], partiel: [0, 0], en_cours: [0, 0],
        reporte: [0, 0], non_demarre: [0, 0], abandonne: [0, 0],
      },
    },
  } as unknown as BilanSeriesResponse;

  beforeEach(() => {
    realisationService = {
      bilan: jest.fn().mockReturnValue(of(bilan)),
      bilanIndicateurs: jest.fn().mockReturnValue(of(indicateurs)),
      bilanSeries: jest.fn().mockReturnValue(of(series)),
    };
    TestBed.configureTestingModule({
      providers: [
        { provide: ActivatedRoute, useValue: { paramMap: of({ get: () => null }) } },
        { provide: AdminService, useValue: { getPlanBySlug: () => of(null) } },
        { provide: RealisationService, useValue: realisationService },
        { provide: TranslateService, useValue: { instant: (k: string) => k } },
      ],
    });
    component = TestBed.runInInjectionContext(() => new PlanBilanComponent());
    component.planId.set(1);
    component.planNom.set('Plan test');
    component.bilan.set(bilan);
    component.bilanIndicateurs.set(indicateurs);
    component.bilanSeries.set(series);
  });

  const rows = () => (component as any).buildExportRows() as any[][];
  const cell = (label: string) => rows().find(r => r[0] === label);

  it('rappelle la portée et le filtre enjeu en tête de fichier', () => {
    expect(cell('plans.suivis.bilan.export.portee')?.[1]).toBe('plans.suivis.bilan.scope.global');
    expect(cell('plans.suivis.bilan.filterEnjeu')?.[1]).toBe('plans.suivis.bilan.allEnjeux');
  });

  it('exporte l’année sélectionnée en portée annuelle', () => {
    component.selectedYear.set(2027);
    component.setScope('annuel');
    expect(cell('plans.suivis.bilan.export.annee')?.[1]).toBe(2027);
  });

  it('nomme l’enjeu filtré plutôt que « tous les enjeux »', () => {
    component.onEnjeuFilterChange([7]);
    expect(cell('plans.suivis.bilan.filterEnjeu')?.[1]).toBe('Enjeu 7');
  });

  it('exporte les résultats des indicateurs et des actions dans le même fichier', () => {
    const flat = rows().map(r => r[0]);
    expect(flat).toContain('plans.suivis.bilan.tabs.indicateurs');
    expect(flat).toContain('plans.suivis.bilan.tabs.actions');
    expect(cell('plans.suivis.bilan.export.totalIndicateurs')?.[1]).toBe(4);
    expect(cell('plans.suivis.bilan.summary.fonctionnement')).toEqual([
      'plans.suivis.bilan.summary.fonctionnement', 1000, 800,
    ]);
  });

  it('omet les sections « par année » en portée annuelle, comme à l’écran', () => {
    expect(rows().map(r => r[0])).toContain('plans.suivis.bilan.actionsChart.evolutionTitle');
    component.setScope('annuel');
    expect(rows().map(r => r[0])).not.toContain('plans.suivis.bilan.actionsChart.evolutionTitle');
  });

  it('applique le filtre enjeu à l’onglet Indicateurs (#639)', () => {
    component.onEnjeuFilterChange([7]);
    expect(realisationService.bilanIndicateurs).toHaveBeenCalledWith(1, { enjeu_id: 7 });
  });

  it('recharge les indicateurs sans filtre à la réinitialisation', () => {
    component.onEnjeuFilterChange([7]);
    realisationService.bilanIndicateurs.mockClear();
    component.filters.reset();
    expect(realisationService.bilanIndicateurs).toHaveBeenCalledWith(1, undefined);
  });
});
