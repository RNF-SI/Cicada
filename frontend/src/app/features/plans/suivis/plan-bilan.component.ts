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
 * Portée : les trois endpoints (`bilan`, `bilan-indicateurs`, `bilan-series`)
 * reçoivent la MÊME fenêtre d'années — voir `periode()`. Auparavant seule la
 * requête « actions » recevait l'année : sur l'onglet Indicateurs (celui par
 * défaut), changer de portée ou d'année ne changeait donc rien à l'écran, et
 * « Mi-parcours » n'envoyait aucun filtre du tout.
 */
import { Component, ElementRef, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
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
  DonutSlice, BarDatum, BarSegment, RadarAxis, LegendItem, LineSeries, LineBand,
  ChartPattern, scoreColor,
} from '../../../shared/components/charts';
import { createFilterSet } from '../../../shared/utils/filter-set';
import { CsvCell, csvFilename, downloadCsv, exportFilename } from '../../../shared/utils/csv-export';
import {
  buildChartsSvg, collectChartCards, downloadBlob, svgToJpeg,
} from '../../../shared/utils/chart-image-export';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import {
  RealisationService, BilanResponse, BilanCounts, BilanIndicateursResponse,
  BilanSeriesResponse, BilanFilters, BilanPeriode,
} from '../../../core/services/realisation.service';

/**
 * Séries des barres empilées du Bilan — croisé planifiée × réalisée (kit UI).
 *
 * Deux couleurs seulement : la **couleur** dit qui (planifiée `$primary-color`
 * / non planifiée `$secondary-terra-cotta`), le **motif** dit l'issue (plein =
 * réalisée, hachures = partiellement, croix = non réalisée). Six teintes
 * distinctes seraient illisibles en impression noir et blanc, et ne diraient
 * plus que « planifiée » et « non planifiée » sont deux familles.
 * Voir docs/DESIGN_SYSTEM.md « Graphiques ».
 */
const PLANIFIE_COLOR = '#025359';
const NON_PLANIFIE_COLOR = '#B74D5D';
/** Couleur unique des donuts d'avancement (indicateurs et actions). */
const AVANCEMENT_COLOR = '#FEC180';

const STATUTS: Array<{
  key: keyof BilanCounts; color: string; pattern?: ChartPattern; i18n: string;
}> = [
  { key: 'planifiee_realisee',      color: PLANIFIE_COLOR,                        i18n: 'plans.suivis.bilan.statut.planifieeRealisee' },
  { key: 'planifiee_partielle',     color: PLANIFIE_COLOR,     pattern: 'hatch',  i18n: 'plans.suivis.bilan.statut.planifieePartielle' },
  { key: 'planifiee_non_realisee',  color: PLANIFIE_COLOR,     pattern: 'cross',  i18n: 'plans.suivis.bilan.statut.planifieeNonRealisee' },
  { key: 'non_planifiee_realisee',  color: NON_PLANIFIE_COLOR,                    i18n: 'plans.suivis.bilan.statut.nonPlanifieeRealisee' },
  { key: 'non_planifiee_partielle', color: NON_PLANIFIE_COLOR, pattern: 'hatch',  i18n: 'plans.suivis.bilan.statut.nonPlanifieePartielle' },
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
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly snackBar = inject(MatSnackBar);

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
    onReset: () => this.reloadAll(),
  });

  /** Légende des barres empilées : croisé planifiée × réalisée (5 séries). */
  niveauLegend = computed<LegendItem[]>(() =>
    STATUTS.map(s => ({
      label: this.translate.instant(s.i18n),
      color: s.color,
      pattern: s.pattern,
    })),
  );

  /** Années du plan pour le sélecteur timeline. */
  planYears = computed<number[]>(() => {
    const b = this.bilan();
    if (!b?.annee_min || !b?.annee_max) return [];
    const out: number[] = [];
    for (let y = b.annee_min; y <= b.annee_max; y++) out.push(y);
    return out;
  });

  /**
   * Période « Mi-parcours » : la **première moitié** de la durée du plan,
   * arrondie au supérieur (un plan 2020-2029 → 2020-2024, un plan 2020-2030 →
   * 2020-2025). C'est la période que couvre l'évaluation à mi-parcours ; le
   * bilan y répond donc à « où en est-on à la moitié du plan ? » sans compter
   * les années suivantes, encore vides.
   */
  miParcoursRange = computed<{ min: number; max: number } | null>(() => {
    const b = this.bilan();
    if (!b?.annee_min || !b?.annee_max || b.annee_max < b.annee_min) return null;
    const n = b.annee_max - b.annee_min + 1;
    return { min: b.annee_min, max: b.annee_min + Math.ceil(n / 2) - 1 };
  });

  /**
   * Fenêtre d'années de la portée courante, envoyée telle quelle aux trois
   * endpoints du bilan. Global = aucune borne (toute la durée du plan).
   */
  periode = computed<BilanPeriode>(() => {
    if (this.scope() === 'annuel') return { annee: this.selectedYear() };
    if (this.scope() === 'mi_parcours') {
      const range = this.miParcoursRange();
      if (range) return { annee_min: range.min, annee_max: range.max };
    }
    return {};
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
      { label: this.translate.instant('plans.suivis.bilan.indic.fait'), value: fait, color: AVANCEMENT_COLOR },
      { label: this.translate.instant('plans.suivis.bilan.indic.pasFait'), value: pasFait, color: AVANCEMENT_COLOR, pattern: 'cross' },
    ];
  });

  /** Radar : moyenne des résultats par enjeu/FCR, point coloré selon le score. */
  radarAxes = computed<RadarAxis[]>(() => {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    return bi.by_enjeu.map(e => ({ label: this.truncate(e.libelle, 16), value: e.moyenne, color: scoreColor(e.moyenne) }));
  });

  // ===========================================================================
  // Actions — modèles de données pour les composants graphiques
  // ===========================================================================

  /**
   * Donut « Taux de réalisation des actions » : réalisée / partielle / non réalisée.
   * Actions planifiées ET non planifiées confondues (le donut mesure l'issue,
   * pas l'origine) : c'est la répartition par motif d'une couleur unique.
   */
  actionsTauxSlices = computed<DonutSlice[]>(() => {
    const b = this.bilan();
    if (!b) return [];
    const t = b.taux_realisation;
    return [
      {
        label: this.translate.instant('plans.suivis.bilan.actionsChart.realisee'),
        value: t.planifiee_realisee + t.non_planifiee_realisee,
        color: AVANCEMENT_COLOR,
      },
      {
        label: this.translate.instant('plans.suivis.bilan.actionsChart.partielle'),
        value: t.planifiee_partielle + t.non_planifiee_partielle,
        color: AVANCEMENT_COLOR, pattern: 'hatch',
      },
      {
        label: this.translate.instant('plans.suivis.bilan.actionsChart.nonRealisee'),
        value: t.planifiee_non_realisee,
        color: AVANCEMENT_COLOR, pattern: 'cross',
      },
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
      label: this.truncate(e.libelle, 9),
      segments: this.buildNiveauSegments(e),
    })),
  );

  private buildNiveauSegments(counts: BilanCounts): BarSegment[] {
    return STATUTS.map(s => ({
      value: (counts[s.key] as number) ?? 0,
      color: s.color,
      pattern: s.pattern,
      seriesLabel: this.translate.instant(s.i18n),
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
      color: NON_PLANIFIE_COLOR,
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
    return { lower: ev.min, upper: ev.max, innerLower, innerUpper, color: NON_PLANIFIE_COLOR };
  });

  /**
   * Légende du graphe courbes : chaque série est annoncée par **son** symbole
   * (kit UI) — trait plein et point pour la moyenne, pointillé pour
   * l'enveloppe min–max, aplat transparent pour la bande d'écart-type. Trois
   * carrés de teintes différentes ne disaient pas lequel était lequel.
   */
  indicEvolutionLegend = computed<LegendItem[]>(() => [
    { label: this.translate.instant('plans.suivis.bilan.indic.legendMoyenne'), color: NON_PLANIFIE_COLOR, shape: 'line' },
    { label: this.translate.instant('plans.suivis.bilan.indic.legendMinMax'), color: NON_PLANIFIE_COLOR, shape: 'dashed' },
    { label: this.translate.instant('plans.suivis.bilan.indic.legendEcartType'), color: NON_PLANIFIE_COLOR, opacity: 0.2 },
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
        { value: s.rh_par_annee.previsionnel[i] ?? 0, color: AVANCEMENT_COLOR, seriesLabel: prevLabel },
        { value: s.rh_par_annee.realise[i] ?? 0, color: NON_PLANIFIE_COLOR, seriesLabel: reelLabel },
      ],
    }));
  });

  rhParAnneeLegend = computed<LegendItem[]>(() => [
    { label: this.translate.instant('plans.suivis.bilan.actionsChart.rhPrevisionnelLegend'), color: AVANCEMENT_COLOR },
    { label: this.translate.instant('plans.suivis.bilan.actionsChart.rhReelLegend'), color: NON_PLANIFIE_COLOR },
  ]);

  hasRhSeries = computed<boolean>(() => {
    const rh = this.bilanSeries()?.rh_par_annee;
    return !!rh && [...rh.previsionnel, ...rh.realise].some(v => v > 0);
  });

  /** Barres empilées « évolution du niveau de réalisation des actions par année ». */
  actionsParAnneeBars = computed<BarDatum[]>(() => {
    const s = this.bilanSeries();
    if (!s) return [];
    const st = s.actions_par_annee.statuts ?? {};
    return s.years.map((y, i) => ({
      label: String(y),
      segments: STATUTS.map(n => ({
        value: st[n.key]?.[i] ?? 0,
        color: n.color,
        pattern: n.pattern,
        seriesLabel: this.translate.instant(n.i18n),
      })).filter(seg => seg.value > 0),
    }));
  });

  hasActionsSeries = computed<boolean>(() => {
    const st = this.bilanSeries()?.actions_par_annee.statuts;
    if (!st) return false;
    return STATUTS.some(n => (st[n.key] ?? []).some(v => v > 0));
  });

  // ===========================================================================
  // Interactions
  // ===========================================================================

  setScope(s: Scope): void {
    if (this.scope() === s) return;
    this.scope.set(s);
    this.reloadAll();
  }

  setContentTab(t: 'indicateurs' | 'actions'): void {
    this.contentTab.set(t);
    if (t === 'indicateurs' && !this.bilanIndicateurs() && !this.isLoadingIndicateurs()) {
      this.loadBilanIndicateurs();
    }
  }

  selectYear(y: number): void {
    if (this.selectedYear() === y) return;
    this.selectedYear.set(y);
    // Les agrégations ne sont scopées à l'année qu'en portée « Annuel » :
    // ailleurs, l'année sélectionnée n'entre dans aucune requête.
    if (this.scope() === 'annuel') this.reloadAll();
  }

  onEnjeuFilterChange(values: number[]): void {
    this.filters.enjeu.set(values);
    this.reloadAll();
  }

  // ===========================================================================
  // #639 — Export des résultats du bilan (CSV) et des graphiques (JPG),
  //        filtres en cours inclus
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

  /**
   * Exporte les graphiques affichés en une planche JPG (#639, retour recette).
   *
   * Le CSV ne rend que les chiffres : pour un rapport de gestion, il faut aussi
   * l'image. On exporte **les graphiques de l'onglet affiché** — seul lui est
   * dans le DOM, et c'est aussi ce que l'utilisateur voit au moment du clic. Un
   * seul fichier plutôt qu'un par graphique : les navigateurs bloquent les
   * téléchargements multiples déclenchés par un même clic.
   */
  async exportCharts(): Promise<void> {
    const cards = collectChartCards(this.host.nativeElement.querySelector('.content-section'));
    if (!cards.length) {
      this.notify('plans.suivis.bilan.export.noCharts');
      return;
    }
    try {
      const svg = buildChartsSvg(cards, {
        title: `${this.t('plans.suivis.bilan.title')} — ${this.planNom()}`,
        lines: this.exportFilterLines(),
      });
      downloadBlob(
        exportFilename(['bilan', 'graphiques', this.contentTab(), this.scope(), this.planSlug()], 'jpg'),
        await svgToJpeg(svg),
      );
    } catch {
      this.notify('plans.suivis.bilan.export.chartsFailed');
    }
  }

  private notify(key: string): void {
    this.snackBar.open(this.t(key), this.t('common.actions.close'), { duration: 4000 });
  }

  private t(key: string): string {
    return this.translate.instant(key);
  }

  /** Portée courante, libellée comme dans le sélecteur. */
  private scopeLabel(): string {
    const s = this.scope();
    return this.t(`plans.suivis.bilan.scope.${s === 'mi_parcours' ? 'miParcours' : s}`);
  }

  /** Enjeu/FCR filtré, ou « tous les enjeux » si le filtre est vide. */
  private enjeuLabel(): string {
    const enjeuId = this.filters.enjeu()[0];
    if (!enjeuId) return this.t('plans.suivis.bilan.allEnjeux');
    return this.enjeuOptions().find(e => e.enjeu_id === enjeuId)?.libelle ?? String(enjeuId);
  }

  /**
   * Rappel des filtres en tête de la planche JPG — mêmes informations que
   * l'en-tête du CSV, pour qu'une image détachée du fichier reste lisible.
   */
  private exportFilterLines(): string[] {
    const lines = [
      `${this.t('plans.suivis.bilan.export.portee')} : ${this.scopeLabel()}`,
      `${this.t('plans.suivis.bilan.filterEnjeu')} : ${this.enjeuLabel()}`,
      `${this.t('plans.suivis.bilan.export.onglet')} : ${this.t(`plans.suivis.bilan.tabs.${this.contentTab()}`)}`,
    ];
    const periode = this.periodeLabel();
    if (periode) lines.splice(1, 0, periode);
    return lines;
  }

  /**
   * « Année : 2027 » ou « Période : 2020 – 2024 » selon la portée, ou null au
   * global. L'export doit dire sur quelles années portent les chiffres.
   */
  private periodeLabel(): string | null {
    if (this.scope() === 'annuel') {
      return `${this.t('plans.suivis.bilan.export.annee')} : ${this.selectedYear()}`;
    }
    const range = this.scope() === 'mi_parcours' ? this.miParcoursRange() : null;
    if (!range) return null;
    return `${this.t('plans.suivis.bilan.export.periode')} : ${range.min} – ${range.max}`;
  }

  private buildExportRows(): CsvCell[][] {
    const rows: CsvCell[][] = [];

    rows.push([this.t('plans.suivis.bilan.title'), this.planNom()]);
    rows.push([this.t('plans.suivis.bilan.export.portee'), this.scopeLabel()]);
    if (this.scope() === 'annuel') {
      rows.push([this.t('plans.suivis.bilan.export.annee'), this.selectedYear()]);
    } else if (this.scope() === 'mi_parcours') {
      const range = this.miParcoursRange();
      if (range) {
        rows.push([this.t('plans.suivis.bilan.export.periode'), `${range.min} – ${range.max}`]);
      }
    }
    rows.push([this.t('plans.suivis.bilan.filterEnjeu'), this.enjeuLabel()]);

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

    // L'export reprend les séries **affichées** (#639) : il est lu à côté du
    // graphique, des catégories différentes le rendraient incomparable.
    rows.push([this.t('plans.suivis.bilan.actionsChart.tauxTitle')]);
    rows.push([this.t('plans.suivis.bilan.export.niveau'), this.t('plans.suivis.bilan.export.nombre')]);
    for (const s of this.actionsTauxSlices()) rows.push([s.label, s.value]);
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

    const statutHeaders = STATUTS.map(s => this.t(s.i18n));
    rows.push([], [this.t('plans.suivis.bilan.actionsChart.byCategorieTitle')]);
    rows.push([this.t('plans.suivis.bilan.actionsChart.categorieAxis'), ...statutHeaders,
      this.t('plans.suivis.bilan.summary.total')]);
    for (const c of b.by_categorie_action) {
      rows.push([c.label || c.code, ...STATUTS.map(s => c[s.key]), c.total]);
    }

    rows.push([], [this.t('plans.suivis.bilan.actionsChart.byEnjeuTitle')]);
    rows.push([this.t('plans.suivis.bilan.filterEnjeu'), ...statutHeaders,
      this.t('plans.suivis.bilan.summary.total')]);
    for (const e of b.by_enjeu) {
      rows.push([e.libelle, ...STATUTS.map(s => e[s.key]), e.total]);
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
      const st = series.actions_par_annee.statuts ?? {};
      rows.push([], [this.t('plans.suivis.bilan.actionsChart.evolutionTitle')]);
      rows.push([this.t('plans.suivis.bilan.export.annee'), ...statutHeaders]);
      series.years.forEach((y, i) =>
        rows.push([y, ...STATUTS.map(s => st[s.key]?.[i] ?? 0)]));
    }
  }

  /** Écart en % entre prévi et réalisé (négatif = sous-consommation). */
  ecartPct(previsionnel: number, realise: number): number | null {
    if (!previsionnel) return null;
    return ((realise - previsionnel) / previsionnel) * 100;
  }

  /**
   * Paramètres communs aux trois requêtes : filtres métier + fenêtre d'années
   * de la portée. Un seul point de vérité, sinon les onglets se désynchronisent.
   */
  private bilanFilters(): BilanFilters {
    const filters: BilanFilters = { ...this.periode() };
    const enjeuId = this.filters.enjeu()[0];
    const organismeId = this.filters.organisme()[0];
    if (enjeuId) filters.enjeu_id = enjeuId;
    if (organismeId) filters.organisme_id = organismeId;
    return filters;
  }

  /** Recharge les trois agrégations avec la portée et les filtres courants. */
  private reloadAll(): void {
    this.reloadBilan();
    this.loadBilanIndicateurs();
    this.loadBilanSeries();
  }

  private loadBilanIndicateurs(): void {
    const id = this.planId();
    if (!id) return;
    this.isLoadingIndicateurs.set(true);
    // #639 — le filtre « Enjeux/FCR » scope aussi l'onglet Indicateurs, sinon
    // ses graphiques (et leur export) restent sur le plan entier. Idem pour la
    // portée : sans elle, cet onglet ignorait « Annuel » et « Mi-parcours ».
    this.realisationService.bilanIndicateurs(id, this.bilanFilters()).subscribe({
      next: (data) => { this.bilanIndicateurs.set(data); this.isLoadingIndicateurs.set(false); },
      error: () => this.isLoadingIndicateurs.set(false),
    });
  }

  private loadBilanSeries(): void {
    const id = this.planId();
    if (!id) return;
    // Les graphiques par année sont masqués en portée « Annuel » (une seule
    // année ne fait pas une série) : inutile de les recharger.
    if (this.scope() === 'annuel') return;
    this.realisationService.bilanSeries(id, this.bilanFilters()).subscribe({
      next: (data) => this.bilanSeries.set(data),
      error: () => this.bilanSeries.set(null),
    });
  }

  private reloadBilan(): void {
    const id = this.planId();
    if (!id) return;
    this.realisationService.bilan(id, this.bilanFilters()).subscribe({
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
      next: (data) => {
        this.bilan.set(data);
        this.clampSelectedYear(data);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.bilan.errors.loadFailed'));
        this.isLoading.set(false);
      },
    });
  }

  /**
   * Ramène l'année sélectionnée dans la durée du plan. Sans cela, un plan
   * 2015-2024 ouvrait la portée « Annuel » sur l'année en cours (hors plan) :
   * tout était vide, et le sélecteur d'années semblait sans effet.
   */
  private clampSelectedYear(b: BilanResponse): void {
    const min = b.annee_min;
    const max = b.annee_max;
    if (!min || !max || max < min) return;
    this.selectedYear.set(Math.min(Math.max(this.selectedYear(), min), max));
  }
}
