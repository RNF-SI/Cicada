import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { PlanTableauDeBordComponent } from './plan-tableau-de-bord.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import { Indicateur, Metrique } from '../../../core/models/enjeu.model';

/**
 * #518 — Le tableau de bord doit afficher le score saisi manuellement (override
 * au niveau indicateur) en priorité sur le score automatique calculé à partir
 * des mesures des métriques.
 */
describe('PlanTableauDeBordComponent — score manuel (#518)', () => {
  let component: PlanTableauDeBordComponent;

  // Métrique numérique : valeur 10 → score automatique « very-bad » (palier 1).
  const metrique = {
    id_metrique: 1,
    id_indicateur: 1,
    score_1_inf: 0, score_1_sup: 20,
    mesures: [{ id_mesure: 1, valeur: '10', date_mesure: '2024-12-31' }],
  } as unknown as Metrique;

  const makeRow = (indicateur: Indicateur) => ({
    subId: 1,
    subLabel: 'NE1',
    indicateur,
    expanded: false,
    metriques: [metrique],
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null } } } },
        { provide: AdminService, useValue: { getPlanBySlug: () => of(null) } },
        { provide: EnjeuService, useValue: { getPlanEnjeux: () => of(null) } },
        { provide: TranslateService, useValue: { instant: (k: string) => k } },
      ],
    });
    // On instancie la classe dans un contexte d'injection sans rendre le
    // template : les méthodes testées (scoring) sont pures et n'en dépendent pas.
    component = TestBed.runInInjectionContext(() => new PlanTableauDeBordComponent());
  });

  it('affiche le score automatique quand aucun override n’est saisi', () => {
    const indicateur = { id_indicateur: 1 } as unknown as Indicateur;
    expect(component.getScoreForYear(makeRow(indicateur), 2024)).toBe('very-bad');
  });

  it('affiche le score forcé manuellement à la place du score automatique', () => {
    // Override « very-good » (5) pour 2024, alors que l'auto vaut « very-bad ».
    const indicateur = {
      id_indicateur: 1,
      score_overrides: { '2024': 5 },
    } as unknown as Indicateur;
    expect(component.getScoreForYear(makeRow(indicateur), 2024)).toBe('very-good');
  });

  it('n’applique l’override qu’à l’année concernée', () => {
    const indicateur = {
      id_indicateur: 1,
      score_overrides: { '2023': 4 },
    } as unknown as Indicateur;
    // 2024 n'est pas surchargée → score automatique conservé.
    expect(component.getScoreForYear(makeRow(indicateur), 2024)).toBe('very-bad');
  });

  it('reflète l’override dans le score global de la ligne', () => {
    const indicateur = {
      id_indicateur: 1,
      score_overrides: { '2024': 5 },
    } as unknown as Indicateur;
    const spy = jest.spyOn(component, 'yearColumns').mockReturnValue([2024] as any);
    expect(component.getGlobalScoreForRow(makeRow(indicateur))).toBe('very-good');
    spy.mockRestore();
  });
});
