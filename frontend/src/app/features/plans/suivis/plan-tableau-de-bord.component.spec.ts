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

  // #549 — une métrique grille TEXTE (valeur = libellé) doit scorer via le
  // libellé, pas retomber sur « no-data » (rond gris) faute de parseFloat.
  it('score une métrique grille TEXTE via son libellé (plus de rond gris)', () => {
    const metriqueTexte = {
      id_metrique: 2,
      id_indicateur: 2,
      score_4_label: 'Bon',
      mesures: [{ id_mesure: 2, valeur: 'Bon', date_mesure: '2024-12-31' }],
    } as unknown as Metrique;
    const row = {
      subId: 1, subLabel: 'NE1', expanded: false,
      indicateur: { id_indicateur: 2 } as unknown as Indicateur,
      metriques: [metriqueTexte],
    };
    expect(component.getScoreForYear(row, 2024)).toBe('good');
  });

  // #551 — l'état de l'année est la MOYENNE PONDÉRÉE des scores de toutes les
  // métriques, pas le score de la première : deux métriques 1 et 5 → moyenne 3
  // (« moyen »), et non « très mauvais ».
  it('score l’année via la moyenne pondérée de toutes les métriques (#551)', () => {
    const mVeryBad = {
      id_metrique: 10, id_indicateur: 5,
      score_1_inf: 0, score_1_sup: 20,
      mesures: [{ id_mesure: 10, valeur: '10', date_mesure: '2024-12-31' }],
    } as unknown as Metrique;
    const mVeryGood = {
      id_metrique: 11, id_indicateur: 5,
      score_5_inf: 80, score_5_sup: 100,
      mesures: [{ id_mesure: 11, valeur: '90', date_mesure: '2024-12-31' }],
    } as unknown as Metrique;
    const row = {
      subId: 1, subLabel: 'NE1', expanded: false,
      indicateur: { id_indicateur: 5 } as unknown as Indicateur,
      metriques: [mVeryBad, mVeryGood],
    };
    expect(component.getScoreForYear(row, 2024)).toBe('neutral'); // (1+5)/2 = 3
  });

  it('pondère la moyenne des métriques selon `ponderation` (#551)', () => {
    const mVeryBad = {
      id_metrique: 20, id_indicateur: 6, ponderation: 4,
      score_1_inf: 0, score_1_sup: 20,
      mesures: [{ id_mesure: 20, valeur: '10', date_mesure: '2024-12-31' }],
    } as unknown as Metrique;
    const mVeryGood = {
      id_metrique: 21, id_indicateur: 6, ponderation: 1,
      score_5_inf: 80, score_5_sup: 100,
      mesures: [{ id_mesure: 21, valeur: '90', date_mesure: '2024-12-31' }],
    } as unknown as Metrique;
    const row = {
      subId: 1, subLabel: 'NE1', expanded: false,
      indicateur: { id_indicateur: 6 } as unknown as Indicateur,
      metriques: [mVeryBad, mVeryGood],
    };
    // (1×4 + 5×1) / 5 = 1.8 → arrondi 2 → « mauvais »
    expect(component.getScoreForYear(row, 2024)).toBe('bad');
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

  // #518 (2e retour) — la colonne « Global » doit refléter l'évaluation globale
  // forcée manuellement depuis la page globale de l'indicateur (#356), qui prime
  // sur le calcul « état courant » (dernière année). C'est ce cas précis qui
  // restait KO : seul le calcul automatique s'affichait dans la colonne Global.
  it('affiche l’évaluation globale forcée manuellement dans la colonne Global', () => {
    const indicateur = {
      id_indicateur: 1,
      // Auto (métrique) = very-bad, mais évaluation globale forcée « good » (4).
      global_score_override: 4,
    } as unknown as Indicateur;
    const spy = jest.spyOn(component, 'yearColumns').mockReturnValue([2024] as any);
    expect(component.getGlobalScoreForRow(makeRow(indicateur))).toBe('good');
    spy.mockRestore();
  });

  it('retombe sur le calcul automatique si l’évaluation globale n’est pas forcée', () => {
    const indicateur = {
      id_indicateur: 1,
      global_score_override: null,
    } as unknown as Indicateur;
    const spy = jest.spyOn(component, 'yearColumns').mockReturnValue([2024] as any);
    expect(component.getGlobalScoreForRow(makeRow(indicateur))).toBe('very-bad');
    spy.mockRestore();
  });

  // #518 (3e retour) — au retour d'une saisie de suivi, le tableau de bord doit
  // recharger depuis le serveur (forceRefresh=true) et non servir le cache, sinon
  // les scores fraîchement saisis n'apparaissent qu'après un rafraîchissement manuel.
  it('recharge les données depuis le serveur (forceRefresh) au chargement', () => {
    const svc = (component as unknown as { enjeuService: EnjeuService }).enjeuService;
    const spy = jest
      .spyOn(svc, 'getPlanEnjeux')
      .mockReturnValue(of({ enjeux: [], fcr: [] }) as any);
    (component as unknown as { loadData: (id: number) => void }).loadData(42);
    expect(spy).toHaveBeenCalledWith(42, true);
  });
});

/**
 * #638 — L'export du tableau de bord doit refléter l'onglet actif et les
 * filtres en cours (objectif, enjeu, recherche).
 */
describe('PlanTableauDeBordComponent — export du tableau (#638)', () => {
  let component: PlanTableauDeBordComponent;

  const makeGroup = (kind: 'olt' | 'oo', id: number, label: string, enjeuId: number) => ({
    kind, id, index: id, label,
    enjeuId, enjeuLibelle: `Enjeu ${enjeuId}`, enjeuSlug: `enjeu-${enjeuId}`,
    rows: [{
      subId: id,
      subLabel: `Sous-entité ${id}`,
      indicateur: { id_indicateur: id, nom_indicateur: `Indicateur ${id}` } as unknown as Indicateur,
      expanded: false,
      metriques: [{ id_metrique: id, nom_metrique: `Métrique ${id}`, unite: 'ha', mesures: [] } as unknown as Metrique],
    }],
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
    component = TestBed.runInInjectionContext(() => new PlanTableauDeBordComponent());
    component.planYearStart.set(2026);
    component.planYearEnd.set(2027);
    component.dashboardGroups.set([
      makeGroup('olt', 1, 'Objectif A', 1),
      makeGroup('oo', 2, 'Objectif B', 2),
    ] as any);
  });

  const rows = () => (component as any).buildExportRows() as any[][];

  it('exporte une colonne par année du plan', () => {
    const header = rows()[0];
    expect(header).toContain(2026);
    expect(header).toContain(2027);
  });

  it('n’exporte que les groupes de l’onglet actif', () => {
    component.setTab('etat');
    expect(rows().map(r => r[1])).toEqual(['plans.suivis.tableauDeBord.nomObjectif', 'OLT 1 : Objectif A', 'OLT 1 : Objectif A']);

    component.setTab('pression');
    expect(rows().map(r => r[1])).toEqual(['plans.suivis.tableauDeBord.nomObjectif', 'OO 2 : Objectif B', 'OO 2 : Objectif B']);
  });

  it('applique le filtre par nom d’objectif', () => {
    component.setTab('ensemble');
    component.filters.objectifs.set(['Objectif B']);
    const out = rows();
    expect(out).toHaveLength(3); // en-tête + indicateur + métrique
    expect(out[1][1]).toBe('OO 2 : Objectif B');
  });

  it('applique la recherche textuelle', () => {
    component.setTab('ensemble');
    component.filters.name.set('Indicateur 1');
    expect(rows().map(r => r[3])).toEqual(['plans.suivis.tableauDeBord.indicateurs', 'Indicateur 1', 'Indicateur 1']);
  });

  it('détaille les métriques sous leur indicateur, indépendamment du pliage', () => {
    component.setTab('etat');
    const out = rows();
    expect(out[1][4]).toBe('');                 // ligne indicateur
    expect(out[2][4]).toBe('Métrique 1 (ha)');  // ligne métrique
  });
});
