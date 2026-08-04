import { ElementRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { PlanBilanComponent } from './plan-bilan.component';
import { AdminService } from '../../../core/services/admin.service';
import {
  RealisationService, BilanResponse, BilanIndicateursResponse, BilanSeriesResponse,
} from '../../../core/services/realisation.service';
import * as chartImageExport from '../../../shared/utils/chart-image-export';

// La rasterisation (`<canvas>`) et le téléchargement n'existent pas en jsdom :
// seule la composition de la planche est vérifiée ici.
jest.mock('../../../shared/utils/chart-image-export', () => ({
  ...jest.requireActual('../../../shared/utils/chart-image-export'),
  svgToJpeg: jest.fn(() => Promise.resolve(new Blob())),
  downloadBlob: jest.fn(),
}));

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

  // `termine` (niveau de nomenclature) et `planifiee_realisee` (croisé prévu ×
  // réalisé) décrivent les mêmes actions : les graphiques et l'export lisent le
  // second, les deux doivent donc rester cohérents dans le jeu d'essai.
  const counts = (termine: number, total: number) => ({
    non_demarre: 0, en_cours: 0, partiel: 0, termine,
    abandonne: 0, reporte: 0, inconnu: 0, total,
    planifiee_realisee: termine, planifiee_partielle: 0,
    planifiee_non_realisee: total - termine,
    non_planifiee_realisee: 0, non_planifiee_partielle: 0,
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
      statuts: {
        planifiee_realisee: [1, 2], planifiee_partielle: [0, 0],
        planifiee_non_realisee: [0, 0],
        non_planifiee_realisee: [0, 0], non_planifiee_partielle: [0, 0],
      },
    },
  } as unknown as BilanSeriesResponse;

  let hostElement: HTMLElement;
  let snackBar: { open: jest.Mock };

  beforeEach(() => {
    jest.clearAllMocks();
    realisationService = {
      bilan: jest.fn().mockReturnValue(of(bilan)),
      bilanIndicateurs: jest.fn().mockReturnValue(of(indicateurs)),
      bilanSeries: jest.fn().mockReturnValue(of(series)),
    };
    hostElement = document.createElement('div');
    hostElement.innerHTML = '<section class="content-section"></section>';
    snackBar = { open: jest.fn() };
    TestBed.configureTestingModule({
      providers: [
        { provide: ActivatedRoute, useValue: { paramMap: of({ get: () => null }) } },
        { provide: AdminService, useValue: { getPlanBySlug: () => of(null) } },
        { provide: RealisationService, useValue: realisationService },
        { provide: TranslateService, useValue: { instant: (k: string) => k } },
        { provide: ElementRef, useValue: new ElementRef(hostElement) },
        { provide: MatSnackBar, useValue: snackBar },
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

  // ===========================================================================
  // Retour recette : les chiffres s'exportaient, pas les graphiques
  // ===========================================================================

  describe('export JPG des graphiques', () => {
    const renderChart = () => {
      hostElement.querySelector('.content-section')!.innerHTML = `
        <article class="chart-card">
          <header class="chart-card__head"><h3 class="chart-card__title">Taux de réalisation</h3></header>
          <div class="chart-card__body"><svg viewBox="0 0 400 200"></svg></div>
        </article>`;
    };

    const exportedSvg = () =>
      (chartImageExport.svgToJpeg as jest.Mock).mock.calls[0][0] as SVGSVGElement;

    const exportedTexts = () =>
      Array.from(exportedSvg().querySelectorAll('text')).map(t => t.textContent);

    it('télécharge une planche JPG nommée d’après l’onglet et la portée', async () => {
      renderChart();
      component.planSlug.set('plan-test');
      await component.exportCharts();

      expect(chartImageExport.downloadBlob).toHaveBeenCalledWith(
        expect.stringMatching(/^bilan_graphiques_indicateurs_global_plan-test_\d{4}-\d{2}-\d{2}\.jpg$/),
        expect.any(Blob),
      );
    });

    it('rappelle les filtres en cours sur l’image', async () => {
      renderChart();
      component.selectedYear.set(2027);
      component.setScope('annuel');
      component.onEnjeuFilterChange([7]);
      await component.exportCharts();

      expect(exportedTexts()).toEqual(expect.arrayContaining([
        'plans.suivis.bilan.export.portee : plans.suivis.bilan.scope.annuel',
        'plans.suivis.bilan.export.annee : 2027',
        'plans.suivis.bilan.filterEnjeu : Enjeu 7',
        'plans.suivis.bilan.export.onglet : plans.suivis.bilan.tabs.indicateurs',
      ]));
      expect(exportedTexts()).toContain('Taux de réalisation');
    });

    it('prévient au lieu de télécharger un fichier vide quand rien n’est affiché', async () => {
      await component.exportCharts();

      expect(chartImageExport.downloadBlob).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledWith(
        'plans.suivis.bilan.export.noCharts', expect.anything(), expect.anything(),
      );
    });
  });
});
