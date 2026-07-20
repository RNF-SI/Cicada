/**
 * Page Bilan de gestion (Phase 4 - Suivis).
 *
 * Route : /plans/:slug/bilan
 *
 * MVP : cartes synthèse (taux de réalisation, budget, RH) + tableaux par
 * catégorie d'action et par enjeu avec barres horizontales empilées en CSS.
 * Les graphiques (camembert, barres D3) viendront en itération suivante.
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
import { createFilterSet } from '../../../shared/utils/filter-set';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import {
  RealisationService, BilanResponse, BilanCounts, BilanIndicateursResponse,
} from '../../../core/services/realisation.service';

/** Niveaux affichables dans les barres empilées, dans l'ordre. */
const NIVEAUX: Array<{ key: keyof BilanCounts; cssClass: string; i18n: string }> = [
  { key: 'termine',     cssClass: 'bar-termine',     i18n: 'plans.suivis.bilan.niveau.termine' },
  { key: 'partiel',     cssClass: 'bar-partiel',     i18n: 'plans.suivis.bilan.niveau.partiel' },
  { key: 'en_cours',    cssClass: 'bar-en-cours',    i18n: 'plans.suivis.bilan.niveau.enCours' },
  { key: 'reporte',     cssClass: 'bar-reporte',     i18n: 'plans.suivis.bilan.niveau.reporte' },
  { key: 'non_demarre', cssClass: 'bar-non-demarre', i18n: 'plans.suivis.bilan.niveau.nonDemarre' },
  { key: 'abandonne',   cssClass: 'bar-abandonne',   i18n: 'plans.suivis.bilan.niveau.abandonne' },
];

@Component({
  selector: 'app-plan-bilan',
  standalone: true,
  imports: [
    CommonModule, RouterModule, FormsModule, TranslateModule,
    MatProgressSpinnerModule, MatMenuModule,
    HeaderComponent, PlanSidebarComponent,
    FilterBarComponent, FilterDropdownComponent, FilterOptionListComponent,
    FilterPanelDirective,
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
  isLoadingIndicateurs = signal(false);

  // Toggles UI (Phase 4 - maquette Figma #4043)
  scope = signal<'annuel' | 'global'>('global');
  contentTab = signal<'indicateurs' | 'actions'>('actions');
  selectedYear = signal<number>(new Date().getFullYear());

  // Palette pour les scores (5 niveaux + sans donnée)
  scorePalette: Record<number, string> = {
    0: '#DADADA',  // sans donnée
    1: '#FF7579',  // très mauvais
    2: '#FA9965',  // mauvais
    3: '#F7D35C',  // moyen
    4: '#82DB8A',  // bon
    5: '#81C9D8',  // très bon
  };

  // Filtres (#592 — état porté par `createFilterSet`, mono-sélection stockée en tableau).
  // Le filtre « organisme » reste un jalon non implémenté côté API (cf. template).
  readonly filters = createFilterSet({
    enjeu: [] as number[],
    organisme: [] as number[],
  }, {
    // Réinitialiser doit aussi relancer la requête serveur du bilan.
    onReset: () => this.reloadWithFilter(),
  });

  legendItems = NIVEAUX.map(n => ({ cssClass: n.cssClass, i18n: n.i18n, key: n.key }));

  /** Liste d'années du plan pour le sélecteur timeline. */
  planYears = computed<number[]>(() => {
    const b = this.bilan();
    if (!b?.annee_min || !b?.annee_max) return [];
    const out: number[] = [];
    for (let y = b.annee_min; y <= b.annee_max; y++) out.push(y);
    return out;
  });

  /** Liste des enjeux disponibles pour filtrer. */
  enjeuOptions = computed(() => {
    return this.bilan()?.by_enjeu || [];
  });

  setScope(s: 'annuel' | 'global'): void {
    this.scope.set(s);
    // La vue « annuel » doit recharger le bilan filtré sur l'année sélectionnée
    // (sinon les comptages globaux s'affichent pour chaque année — #101).
    this.reloadWithFilter();
  }
  setContentTab(t: 'indicateurs' | 'actions'): void {
    this.contentTab.set(t);
    if (t === 'indicateurs' && !this.bilanIndicateurs() && !this.isLoadingIndicateurs()) {
      this.loadBilanIndicateurs();
    }
  }

  private loadBilanIndicateurs(): void {
    const id = this.planId();
    if (!id) return;
    this.isLoadingIndicateurs.set(true);
    this.realisationService.bilanIndicateurs(id).subscribe({
      next: (data) => {
        this.bilanIndicateurs.set(data);
        this.isLoadingIndicateurs.set(false);
      },
      error: () => this.isLoadingIndicateurs.set(false),
    });
  }

  // ===========================================================================
  // SVG helpers — graphiques de l'onglet Indicateurs (camembert + radar)
  // ===========================================================================

  /**
   * Génère les chemins SVG d'un camembert depuis une liste de slices.
   * Retourne pour chaque slice : { d (path), color, label, count, pct, midAngle }.
   */
  buildPieSlices(
    data: { count: number; label: string; score?: number }[],
    radius: number,
    cx: number,
    cy: number,
  ): { d: string; color: string; label: string; count: number; pct: number; midAngle: number }[] {
    const total = data.reduce((a, b) => a + b.count, 0);
    if (!total) return [];
    let startAngle = -Math.PI / 2;
    return data.filter(d => d.count > 0).map(d => {
      const pct = d.count / total;
      const endAngle = startAngle + pct * Math.PI * 2;
      const largeArc = pct > 0.5 ? 1 : 0;
      const x1 = cx + radius * Math.cos(startAngle);
      const y1 = cy + radius * Math.sin(startAngle);
      const x2 = cx + radius * Math.cos(endAngle);
      const y2 = cy + radius * Math.sin(endAngle);
      const path = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
      const midAngle = (startAngle + endAngle) / 2;
      const color = d.score !== undefined ? this.scorePalette[d.score] : '#999';
      startAngle = endAngle;
      return { d: path, color, label: d.label, count: d.count, pct: pct * 100, midAngle };
    });
  }

  /** Slices pour le 1er camembert : évalués vs non évalués. */
  getEvalSlices() {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    return this.buildPieSlices(
      [
        {
          count: bi.indicateurs_evalues,
          label: this.translate.instant('plans.suivis.bilan.indic.evalues'),
          score: 4,
        },
        {
          count: Math.max(bi.total_indicateurs - bi.indicateurs_evalues, 0),
          label: this.translate.instant('plans.suivis.bilan.indic.nonEvalues'),
          score: 0,
        },
      ],
      90, 110, 110,
    );
  }

  /** Slices pour le 2e camembert : distribution des scores. */
  getScoreSlices() {
    const bi = this.bilanIndicateurs();
    if (!bi) return [];
    return this.buildPieSlices(bi.score_distribution, 90, 110, 110);
  }

  /** Données radar (lit le signal directement). */
  getRadar() {
    const bi = this.bilanIndicateurs();
    if (!bi || bi.by_enjeu.length < 3) {
      return { axes: [], polygon: '', grid: [], points: [] };
    }
    return this.buildRadar(bi.by_enjeu, 80, 150, 130);
  }

  /** Position d'un label centré dans une part de camembert. */
  pieLabelPos(midAngle: number, radius: number, cx: number, cy: number): { x: number; y: number } {
    const r = radius * 0.65;
    return { x: cx + r * Math.cos(midAngle), y: cy + r * Math.sin(midAngle) };
  }

  /**
   * Construit un radar chart : points sur un polygone régulier, valeurs 0..5.
   * Retourne axes (rayons + labels), polygon (valeurs), grid (cercles concentriques).
   */
  buildRadar(
    data: { libelle: string; moyenne: number }[],
    radius: number,
    cx: number,
    cy: number,
  ): {
    axes: { x1: number; y1: number; x2: number; y2: number; labelX: number; labelY: number; label: string }[];
    polygon: string;
    grid: number[];
    points: { x: number; y: number; value: number; libelle: string }[];
  } {
    const n = data.length;
    if (n < 3) {
      return { axes: [], polygon: '', grid: [], points: [] };
    }
    const angleStep = (2 * Math.PI) / n;
    const offset = -Math.PI / 2; // démarre en haut

    const axes = data.map((d, i) => {
      const a = offset + i * angleStep;
      const x2 = cx + radius * Math.cos(a);
      const y2 = cy + radius * Math.sin(a);
      const labelX = cx + (radius + 18) * Math.cos(a);
      const labelY = cy + (radius + 18) * Math.sin(a);
      return { x1: cx, y1: cy, x2, y2, labelX, labelY, label: d.libelle };
    });

    const pts = data.map((d, i) => {
      const a = offset + i * angleStep;
      const r = (d.moyenne / 5) * radius;
      return {
        x: cx + r * Math.cos(a),
        y: cy + r * Math.sin(a),
        value: d.moyenne,
        libelle: d.libelle,
      };
    });
    const polygon = pts.map(p => `${p.x},${p.y}`).join(' ');
    // Grille : 5 cercles concentriques aux niveaux de score
    const grid = [1, 2, 3, 4, 5].map(s => (s / 5) * radius);

    return { axes, polygon, grid, points: pts };
  }
  selectYear(y: number): void {
    this.selectedYear.set(y);
    if (this.scope() === 'annuel') {
      this.reloadWithFilter();
    }
  }
  /** #592 — options du filtre « enjeu » au format du kit UI. */
  enjeuFilterOptions = computed<FilterOption<number>[]>(() =>
    this.enjeuOptions().map((e) => ({ value: e.enjeu_id, label: e.libelle })),
  );

  /** Le bilan est calculé côté serveur : tout changement relance la requête. */
  onEnjeuFilterChange(values: number[]): void {
    this.filters.enjeu.set(values);
    this.reloadWithFilter();
  }

  private reloadWithFilter(): void {
    const id = this.planId();
    if (!id) return;
    const filters: any = {};
    const enjeuId = this.filters.enjeu()[0];
    const organismeId = this.filters.organisme()[0];
    if (enjeuId) filters.enjeu_id = enjeuId;
    if (organismeId) filters.organisme_id = organismeId;
    // En vue « annuel », scoper les agrégations à l'année sélectionnée (#101).
    if (this.scope() === 'annuel') filters.annee = this.selectedYear();
    this.realisationService.bilan(id, filters).subscribe({
      next: (data) => this.bilan.set(data),
    });
  }

  /** Segments d'une barre empilée (% du total). */
  buildBarSegments(counts: BilanCounts): { cssClass: string; pct: number; count: number; label: string }[] {
    const total = counts.total || 0;
    if (!total) return [];
    return NIVEAUX
      .map(n => ({
        cssClass: n.cssClass,
        pct: (counts[n.key] as number) / total * 100,
        count: counts[n.key] as number,
        label: this.translate.instant(n.i18n),
      }))
      .filter(s => s.count > 0);
  }

  /** Écart en % entre prévi et réalisé (négatif = sous-consommation). */
  ecartPct(previsionnel: number, realise: number): number | null {
    if (!previsionnel) return null;
    return ((realise - previsionnel) / previsionnel) * 100;
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
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.bilan.errors.loadFailed'));
        this.isLoading.set(false);
      },
    });
  }
}
