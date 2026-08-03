/**
 * Page « Bilan de la gestion » (Suivis).
 *
 * Route : /plans/:slug/bilan
 *
 * Refonte kit UI (Figma 4515-73893 / 74450 / 74948) : onglets Indicateurs /
 * Actions, sélecteur de portée Global / Mi-parcours / Annuel, et graphiques
 * construits avec la bibliothèque `shared/components/charts` (donut, barres,
 * courbes, radar). Les agrégations viennent de `RealisationService`.
 *
 * NB : les graphiques « par année » (évolution des indicateurs, jours RH par
 * année, niveau de réalisation par année) nécessitent une agrégation temporelle
 * côté serveur qui n'existe pas encore — leur tuile affiche un message dédié.
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  FilterBarComponent,
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
  FilterOption,
} from '../../../shared/components/filters';
import {
  ChartCardComponent, ChartLegendComponent, DonutChartComponent,
  BarChartComponent, LineChartComponent, RadarChartComponent,
  DonutSlice, BarDatum, BarSegment, RadarAxis, LegendItem, LineSeries, LineBand, scoreColor,
} from '../../../shared/components/charts';
import { createFilterSet } from '../../../shared/utils/filter-set';
import { CsvCell, csvFilename, downloadCsv } from '../../../shared/utils/csv-export';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import {
  RealisationService, BilanResponse, BilanCounts, BilanIndicateursResponse,
  BilanSeriesResponse,
} from '../../../core/services/realisation.service';

/** Niveaux de réalisation (barres empilées) — couleurs du design system. */
const NIVEAUX: Array<{ key: keyof BilanCounts; color: string; i18n: string }> = [
  { key: 'termine',     color: '#04854B', i18n: 'plans.suivis.bilan.niveau.termine' },
  { key: 'partiel',     color: '#82DB8A', i18n: 'plans.suivis.bilan.niveau.partiel' },
  { key: 'en_cours',    color: '#025359', i18n: 'plans.suivis.bilan.niveau.enCours' },
  { key: 'reporte',     color: '#F7D35C', i18n: 'plans.suivis.bilan.niveau.reporte' },
  { key: 'non_demarre', color: '#E4E4E4', i18n: 'plans.suivis.bilan.niveau.nonDemarre' },
  { key: 'abandonne',   color: '#E12329', i18n: 'plans.suivis.bilan.niveau.abandonne' },
];

type Scope = 'global' | 'mi_parcours' | 'annuel';

@Component({
  selector: 'app-plan-bilan',
  standalone: true,
  imports: [
    CommonModule, RouterModule, FormsModule, TranslateModule,
    MatProgressSpinnerModule, MatMenuModule,
    HeaderComponent, PlanSidebarComponent,
    FilterBarComponent, FilterDropdownComponent, FilterOptionListComponent,
    FilterPanelDirective,
    ChartCardComponent, ChartLegendComponent, DonutChartComponent,
    BarChartComponent, LineChartComponent, RadarChartComponent,
  ],
  templateUrl: './plan-bilan.component.html',
  styleUrl: './plan-bilan.component.scss',
})
export class PlanBilanComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly realisationService = inject(RealisationService);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  bilan = signal<BilanResponse | null>(null);
  bilanIndicateurs = signal<BilanIndicateursResponse | null>(null);
  bilanSeries = signal<BilanSeriesResponse | null>(null);
  isLoadingIndicateurs = signal(false);

  scope = signal<Scope>('global');
  contentTab = signal<'indicateurs' | 'actions'>('indicateurs');
  selectedYear = signal<number>(new Date().getFullYear());

  /** Filtres (#592) — enjeu implémenté serveur, organisme/indicateur = jalons. */
  readonly filters = createFilterSet({
    enjeu: [] as number[],
    organisme: [] as number[],
  }, {
    onReset: () => {
      this.reloadWithFilter();
      this.loadBilanSeries();
      this.loadBilanIndicateurs();
    },
  });

  /** Légende des 6 niveaux de réalisation (barres empilées). */
  niveauLegend = computed<LegendItem[]>(() =>
    NIVEAUX.map(n => ({ label: this.translate.instant(n.i18n), color: n.color })),
  );

  /** Années du plan pour le sélecteur timeline. */
  planYears = computed<number[]>(() => {
    const b = this.bilan();
    if (!b?.annee_min || !b?.annee_max) return [];
    const out: number[] = [];
    for (let y = b.annee_min; y <= b.annee_max; y++) out.push(y);
    return out;
  });

  enjeuOptions = computed(() => this.bilan()?.by_enjeu || []);

  enjeuFilterOptions = computed<FilterOption<number>[]>(() =>
    this.enjeuOptions().map((e) => ({ value: e.enjeu_id, label: e.libelle })),
  );

  /** Sous-titre du hero : évite « Plan de gestion Plan de gestion … ». */
  heroSubtitle = computed<string>(() => {
    const prefix = this.translate.instant('plans.suivis.bilan.subtitlePrefix');
    const nom = this.planNom();
    if (!nom) return prefix;
    return nom.toLowerCase().startsWith(prefix.toLowerCase()) ? nom : `${prefix} ${nom}`;
  });

  // ===========================================================================
  // Indicateurs — modèles de données pour les composants graphiques
  // ===========================================================================

  /** Donut « Taux de réalisation des indicateurs » : distribution des scores 1..5. */
  indicTauxSlices = computed<DonutSlice[]>(() => {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    return bi.score_distribution
      .filter(s => s.score > 0 && s.count > 0)
      .map(s => ({ label: s.label, value: s.count, color: scoreColor(s.score) }));
  });

  /** Donut « Évaluation des indicateurs » : Fait vs Pas fait (hachuré). */
  indicEvalSlices = computed<DonutSlice[]>(() => {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    const fait = bi.indicateurs_evalues;
    const pasFait = Math.max(bi.total_indicateurs - bi.indicateurs_evalues, 0);
    return [
      { label: this.translate.instant('plans.suivis.bilan.indic.fait'), value: fait, color: '#FEC180' },
      { label: this.translate.instant('plans.suivis.bilan.indic.pasFait'), value: pasFait, color: '#746F6E', pattern: 'cross' },
    ];
  });

  /** Radar : moyenne des résultats par enjeu/FCR, point coloré selon le score. */
  radarAxes = computed<RadarAxis[]>(() => {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    return bi.by_enjeu.map(e => ({ label: this.truncate(e.libelle, 26), value: e.moyenne, color: scoreColor(e.moyenne) }));
  });

  // ===========================================================================
  // Actions — modèles de données pour les composants graphiques
  // ===========================================================================

  /** Donut « Taux de réalisation des actions » : réalisée / partielle / non réalisée. */
  actionsTauxSlices = computed<DonutSlice[]>(() => {
    const b = this.bilan();
    if (!b) return [];
    const t = b.taux_realisation;
    const nonRealisee = t.total - t.termine - t.partiel;
    return [
      { label: this.translate.instant('plans.suivis.bilan.actionsChart.realisee'), value: t.termine, color: '#FA9965' },
      { label: this.translate.instant('plans.suivis.bilan.actionsChart.partielle'), value: t.partiel, color: '#FEC180', pattern: 'hatch' },
      { label: this.translate.instant('plans.suivis.bilan.actionsChart.nonRealisee'), value: Math.max(nonRealisee, 0), color: '#746F6E', pattern: 'cross' },
    ];
  });

  /** Barres empilées « par catégorie d'action ». */
  niveauByCategorieBars = computed<BarDatum[]>(() =>
    (this.bilan()?.by_categorie_action || []).map(cat => ({
      label: cat.code || cat.label,
      segments: this.buildNiveauSegments(cat),
    })),
  );

  /** Barres empilées « par enjeu / FCR ». */
  niveauByEnjeuBars = computed<BarDatum[]>(() =>
    (this.bilan()?.by_enjeu || []).map(e => ({
      label: this.truncate(e.libelle, 11),
      segments: this.buildNiveauSegments(e),
    })),
  );

  private buildNiveauSegments(counts: BilanCounts): BarSegment[] {
    return NIVEAUX.map(n => ({
      value: counts[n.key] as number,
      color: n.color,
      seriesLabel: this.translate.instant(n.i18n),
    })).filter(s => s.value > 0);
  }

  private truncate(label: string, max: number): string {
    return label.length > max ? label.slice(0, max - 1).trimEnd() + '…' : label;
  }

  // ===========================================================================
  // Séries par année (graphiques « évolution »)
  // ===========================================================================

  seriesYears = computed<number[]>(() => this.bilanSeries()?.years ?? []);

  /** Courbe « évolution de la moyenne des indicateurs » (série moyenne). */
  indicEvolutionSeries = computed<LineSeries[]>(() => {
    const s = this.bilanSeries();
    if (!s) return [];
    return [{
      label: this.translate.instant('plans.suivis.bilan.indic.legendMoyenne'),
      color: '#B74D5D',
      points: s.indicateurs_evolution.mean,
      showPoints: true,
    }];
  });

  /** Bande de confiance : enveloppe min–max + bande écart-type autour de la moyenne. */
  indicEvolutionBand = computed<LineBand | undefined>(() => {
    const s = this.bilanSeries();
    if (!s) return undefined;
    const ev = s.indicateurs_evolution;
    const innerLower = ev.mean.map((m, i) => (m === null || ev.std[i] === null) ? null : m - (ev.std[i] as number));
    const innerUpper = ev.mean.map((m, i) => (m === null || ev.std[i] === null) ? null : m + (ev.std[i] as number));
    return { lower: ev.min, upper: ev.max, innerLower, innerUpper, color: '#B74D5D' };
  });

  indicEvolutionLegend = computed<LegendItem[]>(() => [
    { label: this.translate.instant('plans.suivis.bilan.indic.legendMoyenne'), color: '#B74D5D' },
    { label: this.translate.instant('plans.suivis.bilan.indic.legendMinMax'), color: '#CE8E99' },
    { label: this.translate.instant('plans.suivis.bilan.indic.legendEcartType'), color: '#EDD3D8' },
  ]);

  hasIndicEvolution = computed<boolean>(() =>
    (this.bilanSeries()?.indicateurs_evolution.mean ?? []).some(v => v !== null),
  );

  /** Barres groupées « évolution jours RH par année » (prévisionnel vs réel). */
  rhParAnneeBars = computed<BarDatum[]>(() => {
    const s = this.bilanSeries();
    if (!s) return [];
    const prevLabel = this.translate.instant('plans.suivis.bilan.actionsChart.rhPrevisionnelLegend');
    const reelLabel = this.translate.instant('plans.suivis.bilan.actionsChart.rhReelLegend');
    return s.years.map((y, i) => ({
      label: String(y),
      segments: [
        { value: s.rh_par_annee.previsionnel[i] ?? 0, color: '#FEC180', seriesLabel: prevLabel },
        { value: s.rh_par_annee.realise[i] ?? 0, color: '#B74D5D', seriesLabel: reelLabel },
      ],
    }));
  });

  rhParAnneeLegend = computed<LegendItem[]>(() => [
    { label: this.translate.instant('plans.suivis.bilan.actionsChart.rhPrevisionnelLegend'), color: '#FEC180' },
    { label: this.translate.instant('plans.suivis.bilan.actionsChart.rhReelLegend'), color: '#B74D5D' },
  ]);

  hasRhSeries = computed<boolean>(() => {
    const rh = this.bilanSeries()?.rh_par_annee;
    return !!rh && [...rh.previsionnel, ...rh.realise].some(v => v > 0);
  });

  /** Barres empilées « évolution du niveau de réalisation des actions par année ». */
  actionsParAnneeBars = computed<BarDatum[]>(() => {
    const s = this.bilanSeries();
    if (!s) return [];
    const niv = s.actions_par_annee.niveaux;
    return s.years.map((y, i) => ({
      label: String(y),
      segments: NIVEAUX.map(n => ({
        value: niv[n.key]?.[i] ?? 0,
        color: n.color,
        seriesLabel: this.translate.instant(n.i18n),
      })).filter(seg => seg.value > 0),
    }));
  });

  hasActionsSeries = computed<boolean>(() => {
    const niv = this.bilanSeries()?.actions_par_annee.niveaux;
    if (!niv) return false;
    return NIVEAUX.some(n => (niv[n.key] ?? []).some(v => v > 0));
  });

  // ===========================================================================
  // Interactions
  // ===========================================================================

  setScope(s: Scope): void {
    this.scope.set(s);
    this.reloadWithFilter();
  }

  setContentTab(t: 'indicateurs' | 'actions'): void {
    this.contentTab.set(t);
    if (t === 'indicateurs' && !this.bilanIndicateurs() && !this.isLoadingIndicateurs()) {
      this.loadBilanIndicateurs();
    }
  }

  selectYear(y: number): void {
    this.selectedYear.set(y);
    if (this.scope() === 'annuel') this.reloadWithFilter();
  }

  onEnjeuFilterChange(values: number[]): void {
    this.filters.enjeu.set(values);
    this.reloadWithFilter();
    this.loadBilanSeries();
    this.loadBilanIndicateurs();
  }

  // ===========================================================================
  // #639 — Export CSV des résultats du bilan, filtres en cours inclus
  // ===========================================================================

  /**
   * Exporte les résultats affichés en CSV. Les agrégations exportées sont celles
   * chargées avec les filtres courants (portée Global / Mi-parcours / Annuel,
   * année sélectionnée, enjeu) : l'export ne recalcule rien, il sérialise ce que
   * les graphiques affichent. Les deux volets (Indicateurs, Actions) sont
   * exportés dans le même fichier — le bilan est un tout, l'onglet n'est qu'un
   * découpage de lecture. Les sections « par année » sont omises en portée
   * Annuel, comme à l'écran.
   */
  exportResults(): void {
    downloadCsv(
      csvFilename(['bilan', this.scope(), this.planSlug()]),
      this.buildExportRows(),
    );
  }

  private t(key: string): string {
    return this.translate.instant(key);
  }

  private buildExportRows(): CsvCell[][] {
    const rows: CsvCell[][] = [];
    const enjeuId = this.filters.enjeu()[0];
    const enjeuLabel = enjeuId
      ? (this.enjeuOptions().find(e => e.enjeu_id === enjeuId)?.libelle ?? String(enjeuId))
      : this.t('plans.suivis.bilan.allEnjeux');

    rows.push([this.t('plans.suivis.bilan.title'), this.planNom()]);
    rows.push([this.t('plans.suivis.bilan.export.portee'), this.t(`plans.suivis.bilan.scope.${
      this.scope() === 'mi_parcours' ? 'miParcours' : this.scope()}`)]);
    if (this.scope() === 'annuel') {
      rows.push([this.t('plans.suivis.bilan.export.annee'), this.selectedYear()]);
    }
    rows.push([this.t('plans.suivis.bilan.filterEnjeu'), enjeuLabel]);

    this.appendIndicateursSection(rows);
    this.appendActionsSection(rows);
    return rows;
  }

  private appendIndicateursSection(rows: CsvCell[][]): void {
    const bi = this.bilanIndicateurs();
    if (!bi) return;
    rows.push([], [this.t('plans.suivis.bilan.tabs.indicateurs')]);
    rows.push([this.t('plans.suivis.bilan.export.totalIndicateurs'), bi.total_indicateurs]);
    rows.push([this.t('plans.suivis.bilan.indic.evalues'), bi.indicateurs_evalues]);
    rows.push([this.t('plans.suivis.bilan.export.tauxEvaluation'), bi.taux_evaluation_pct]);

    rows.push([], [this.t('plans.suivis.bilan.indic.tauxTitle')]);
    rows.push([
      this.t('plans.suivis.bilan.indic.score'),
      this.t('plans.suivis.bilan.export.libelle'),
      this.t('plans.suivis.bilan.export.nombre'),
    ]);
    for (const s of bi.score_distribution) rows.push([s.score, s.label, s.count]);

    rows.push([], [this.t('plans.suivis.bilan.indic.radarTitle')]);
    rows.push([
      this.t('plans.suivis.bilan.filterEnjeu'),
      this.t('plans.suivis.bilan.indic.legendMoyenne'),
      this.t('plans.suivis.bilan.export.nbIndicateurs'),
    ]);
    for (const e of bi.by_enjeu) rows.push([e.libelle, e.moyenne, e.count]);

    const series = this.bilanSeries();
    if (this.scope() !== 'annuel' && series && this.hasIndicEvolution()) {
      const ev = series.indicateurs_evolution;
      rows.push([], [this.t('plans.suivis.bilan.indic.evolutionTitle')]);
      rows.push([
        this.t('plans.suivis.bilan.export.annee'),
        this.t('plans.suivis.bilan.indic.legendMoyenne'),
        this.t('plans.suivis.bilan.export.min'),
        this.t('plans.suivis.bilan.export.max'),
        this.t('plans.suivis.bilan.indic.legendEcartType'),
      ]);
      series.years.forEach((y, i) =>
        rows.push([y, ev.mean[i], ev.min[i], ev.max[i], ev.std[i]]));
    }
  }

  private appendActionsSection(rows: CsvCell[][]): void {
    const b = this.bilan();
    if (!b) return;
    rows.push([], [this.t('plans.suivis.bilan.tabs.actions')]);

    rows.push([this.t('plans.suivis.bilan.actionsChart.tauxTitle')]);
    rows.push([this.t('plans.suivis.bilan.export.niveau'), this.t('plans.suivis.bilan.export.nombre')]);
    for (const n of NIVEAUX) rows.push([this.t(n.i18n), b.taux_realisation[n.key]]);
    rows.push([this.t('plans.suivis.bilan.summary.total'), b.taux_realisation.total]);

    const prev = this.t('plans.suivis.bilan.actionsChart.budgetPrevisionnel');
    const reel = this.t('plans.suivis.bilan.actionsChart.budgetReel');
    rows.push([], [this.t('plans.suivis.bilan.summary.budgetTitle')]);
    rows.push(['', `${prev} (€)`, `${reel} (€)`]);
    rows.push([this.t('plans.suivis.bilan.summary.fonctionnement'),
      b.budget.fonctionnement.previsionnel, b.budget.fonctionnement.realise]);
    rows.push([this.t('plans.suivis.bilan.summary.investissement'),
      b.budget.investissement.previsionnel, b.budget.investissement.realise]);
    rows.push([this.t('plans.suivis.bilan.summary.total'),
      b.budget.total.previsionnel, b.budget.total.realise]);

    const jours = this.t('plans.suivis.bilan.actionsChart.jours');
    rows.push([], [this.t('plans.suivis.bilan.summary.rhTitle')]);
    rows.push([this.t('plans.suivis.bilan.actionsChart.rhPrevisionnelle'), `${b.rh.previsionnel} ${jours}`]);
    rows.push([this.t('plans.suivis.bilan.actionsChart.rhReelle'), `${b.rh.realise} ${jours}`]);

    const niveauHeaders = NIVEAUX.map(n => this.t(n.i18n));
    rows.push([], [this.t('plans.suivis.bilan.actionsChart.byCategorieTitle')]);
    rows.push([this.t('plans.suivis.bilan.actionsChart.categorieAxis'), ...niveauHeaders,
      this.t('plans.suivis.bilan.summary.total')]);
    for (const c of b.by_categorie_action) {
      rows.push([c.label || c.code, ...NIVEAUX.map(n => c[n.key]), c.total]);
    }

    rows.push([], [this.t('plans.suivis.bilan.actionsChart.byEnjeuTitle')]);
    rows.push([this.t('plans.suivis.bilan.filterEnjeu'), ...niveauHeaders,
      this.t('plans.suivis.bilan.summary.total')]);
    for (const e of b.by_enjeu) {
      rows.push([e.libelle, ...NIVEAUX.map(n => e[n.key]), e.total]);
    }

    const series = this.bilanSeries();
    if (this.scope() === 'annuel' || !series) return;

    if (this.hasRhSeries()) {
      rows.push([], [this.t('plans.suivis.bilan.actionsChart.rhEvolutionTitle')]);
      rows.push([
        this.t('plans.suivis.bilan.export.annee'),
        `${this.t('plans.suivis.bilan.actionsChart.rhPrevisionnelLegend')} (${jours})`,
        `${this.t('plans.suivis.bilan.actionsChart.rhReelLegend')} (${jours})`,
      ]);
      series.years.forEach((y, i) => rows.push([
        y, series.rh_par_annee.previsionnel[i] ?? 0, series.rh_par_annee.realise[i] ?? 0,
      ]));
    }

    if (this.hasActionsSeries()) {
      const niv = series.actions_par_annee.niveaux;
      rows.push([], [this.t('plans.suivis.bilan.actionsChart.evolutionTitle')]);
      rows.push([this.t('plans.suivis.bilan.export.annee'), ...niveauHeaders]);
      series.years.forEach((y, i) =>
        rows.push([y, ...NIVEAUX.map(n => niv[n.key]?.[i] ?? 0)]));
    }
  }

  /** Écart en % entre prévi et réalisé (négatif = sous-consommation). */
  ecartPct(previsionnel: number, realise: number): number | null {
    if (!previsionnel) return null;
    return ((realise - previsionnel) / previsionnel) * 100;
  }

  private loadBilanIndicateurs(): void {
    const id = this.planId();
    if (!id) return;
    this.isLoadingIndicateurs.set(true);
    // #639 — le filtre « Enjeux/FCR » scope aussi l'onglet Indicateurs, sinon
    // ses graphiques (et leur export) restent sur le plan entier.
    const enjeuId = this.filters.enjeu()[0];
    this.realisationService.bilanIndicateurs(id, enjeuId ? { enjeu_id: enjeuId } : undefined).subscribe({
      next: (data) => { this.bilanIndicateurs.set(data); this.isLoadingIndicateurs.set(false); },
      error: () => this.isLoadingIndicateurs.set(false),
    });
  }

  private loadBilanSeries(): void {
    const id = this.planId();
    if (!id) return;
    const enjeuId = this.filters.enjeu()[0];
    this.realisationService.bilanSeries(id, enjeuId ? { enjeu_id: enjeuId } : undefined).subscribe({
      next: (data) => this.bilanSeries.set(data),
      error: () => this.bilanSeries.set(null),
    });
  }

  private reloadWithFilter(): void {
    const id = this.planId();
    if (!id) return;
    const filters: { enjeu_id?: number; organisme_id?: number; annee?: number } = {};
    const enjeuId = this.filters.enjeu()[0];
    const organismeId = this.filters.organisme()[0];
    if (enjeuId) filters.enjeu_id = enjeuId;
    if (organismeId) filters.organisme_id = organismeId;
    // Seule la portée « annuel » scope les agrégations à une année (#101).
    if (this.scope() === 'annuel') filters.annee = this.selectedYear();
    this.realisationService.bilan(id, filters).subscribe({
      next: (data) => this.bilan.set(data),
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      this.planSlug.set(slug);
      if (!slug) return;

      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.loadBilan(plan.id_pg);
          // Onglet Indicateurs par défaut (Figma) → précharger les agrégations.
          this.loadBilanIndicateurs();
          this.loadBilanSeries();
        },
        error: () => {
          this.errorMessage.set(this.translate.instant('plans.suivis.saisie.errors.planNotFound'));
          this.isLoading.set(false);
        },
      });
    });
  }

  private loadBilan(planId: number): void {
    this.realisationService.bilan(planId).subscribe({
      next: (data) => { this.bilan.set(data); this.isLoading.set(false); },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.bilan.errors.loadFailed'));
        this.isLoading.set(false);
      },
    });
  }
}
