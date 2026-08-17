import {
  ChangeDetectionStrategy, Component, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  BarDatum, PatternDef, PatternRegistry, nextChartUid,
} from '../chart.types';
import { ChartDefsComponent } from '../chart-defs.component';

interface BarRect {
  /** Tracé de la barre : coins hauts arrondis seulement au sommet de la pile. */
  d: string;
  fill: string;
  title: string;
}

interface BarColumn {
  label: string;
  labelX: number;
  rects: BarRect[];
  topLabel?: string;
  topLabelX: number;
  topLabelY: number;
}

interface GridLine { y: number; label: string; }

interface BarVm {
  width: number;
  height: number;
  plotBottom: number;
  plotLeft: number;
  plotRight: number;
  grid: GridLine[];
  columns: BarColumn[];
  defs: PatternDef[];
  hasData: boolean;
}

/**
 * Graphe en barres du kit UI. Trois modes :
 *  - `simple`  : une barre par catégorie (+ valeur au-dessus)
 *  - `stacked` : segments empilés (niveaux de réalisation)
 *  - `grouped` : segments côte à côte (prévi vs réel)
 *
 * Motifs hachurés/croix supportés par segment (planifiée partiellement réalisée…).
 */
@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [CommonModule, ChartDefsComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm && vm.hasData) {
      <svg [attr.viewBox]="'0 0 ' + vm.width + ' ' + vm.height" class="bar-svg"
           [style.max-width.px]="vm.width" preserveAspectRatio="xMidYMid meet">
        <svg:g ccdChartDefs [defs]="vm.defs"></svg:g>

        @if (yLabel) {
          <svg:text [attr.x]="vm.plotLeft" y="14" class="bar-axis-title">{{ yLabel }}</svg:text>
        }

        <!-- Grille + graduations Y -->
        @for (g of vm.grid; track g.y) {
          <svg:line [attr.x1]="vm.plotLeft" [attr.x2]="vm.plotRight" [attr.y1]="g.y" [attr.y2]="g.y"
                    class="bar-grid"></svg:line>
          <svg:text [attr.x]="vm.plotLeft - 6" [attr.y]="g.y + 3" text-anchor="end" class="bar-tick">{{ g.label }}</svg:text>
        }

        <!-- Barres -->
        @for (col of vm.columns; track col.label) {
          @for (r of col.rects; track $index) {
            <svg:path [attr.d]="r.d" [attr.fill]="r.fill"
                      class="bar-rect" [class.bar-rect--stacked]="mode === 'stacked'">
              <svg:title>{{ r.title }}</svg:title>
            </svg:path>
          }
          @if (col.topLabel) {
            <svg:text [attr.x]="col.topLabelX" [attr.y]="col.topLabelY" text-anchor="middle" class="bar-value">{{ col.topLabel }}</svg:text>
          }
          <svg:text [attr.x]="col.labelX" [attr.y]="vm.plotBottom + 16" text-anchor="middle" class="bar-xlabel">{{ col.label }}</svg:text>
        }

        @if (xLabel) {
          <svg:text [attr.x]="(vm.plotLeft + vm.plotRight) / 2" [attr.y]="vm.height - 2" text-anchor="middle" class="bar-axis-title">{{ xLabel }}</svg:text>
        }
      </svg>
    }
  `,
  styleUrl: './bar-chart.component.scss',
})
export class BarChartComponent implements OnChanges {
  @Input() data: BarDatum[] = [];
  @Input() mode: 'simple' | 'stacked' | 'grouped' = 'stacked';
  @Input() maxY?: number;
  @Input() yTicks = 5;
  @Input() yLabel?: string;
  @Input() xLabel?: string;
  @Input() height = 250;
  /**
   * Largeur cible du tracé, en px. Le SVG ne dépasse jamais cette largeur : les
   * bandes se resserrent quand il y a beaucoup de colonnes, au lieu de laisser
   * le navigateur réduire tout le dessin — ce qui rapetisserait aussi les
   * libellés d'axes, censés rester à 13 px (kit UI).
   */
  @Input() maxWidth = 560;
  /** Affiche la valeur au-dessus des barres (mode simple). */
  @Input() showValues = false;

  vm: BarVm | null = null;
  private readonly uid = nextChartUid('bar');

  private static readonly PAD_LEFT = 38;
  private static readonly PAD_RIGHT = 14;
  private static readonly PAD_TOP = 22;
  private static readonly BAND = 74;
  private static readonly BAND_MIN = 34;

  ngOnChanges(): void {
    const data = this.data || [];
    const registry = new PatternRegistry(this.uid);
    const padBottom = this.xLabel ? 40 : 26;
    const plotTop = BarChartComponent.PAD_TOP;
    const plotBottom = this.height - padBottom;
    const plotLeft = BarChartComponent.PAD_LEFT;
    const available = this.maxWidth - plotLeft - BarChartComponent.PAD_RIGHT;
    const band = data.length
      ? Math.max(
          BarChartComponent.BAND_MIN,
          Math.min(BarChartComponent.BAND, available / data.length),
        )
      : BarChartComponent.BAND;
    const width = plotLeft + data.length * band + BarChartComponent.PAD_RIGHT;
    const plotRight = width - BarChartComponent.PAD_RIGHT;
    const plotH = plotBottom - plotTop;

    // Valeur max de l'axe Y.
    const rawMax = this.maxY ?? this.computeMax(data);
    const maxY = this.niceMax(rawMax);
    const yToPx = (v: number) => plotBottom - (v / maxY) * plotH;

    // Grille Y.
    const grid: GridLine[] = [];
    for (let i = 0; i <= this.yTicks; i++) {
      const v = (maxY / this.yTicks) * i;
      grid.push({ y: yToPx(v), label: this.formatTick(v) });
    }

    // Colonnes.
    const columns: BarColumn[] = data.map((d, i) => {
      const bandX = plotLeft + i * band;
      const center = bandX + band / 2;
      const rects: BarRect[] = [];
      let top: number | undefined;

      if (this.mode === 'grouped') {
        const segs = d.segments.filter(s => s.value !== 0);
        const groupW = band * 0.62;
        const barW = segs.length ? groupW / segs.length : groupW;
        const startX = center - groupW / 2;
        segs.forEach((s, si) => {
          const h = (Math.abs(s.value) / maxY) * plotH;
          rects.push({
            d: this.barPath(startX + si * barW + 1, plotBottom - h, barW - 2, h, true),
            fill: registry.ref(s.color, s.pattern),
            title: `${s.seriesLabel ?? d.label} : ${s.value}`,
          });
        });
      } else if (this.mode === 'simple') {
        const s = d.segments[0];
        const barW = band * 0.5;
        const h = s ? (Math.abs(s.value) / maxY) * plotH : 0;
        if (s) {
          rects.push({
            d: this.barPath(center - barW / 2, plotBottom - h, barW, h, true),
            fill: registry.ref(s.color, s.pattern),
            title: `${d.label} : ${s.value}`,
          });
          top = plotBottom - h - 6;
        }
      } else {
        // stacked — empilé du bas vers le haut : seul le dernier segment posé
        // est au sommet et porte les coins arrondis (kit UI).
        const barW = band * 0.5;
        const segs = d.segments.filter(s => s.value > 0);
        let acc = 0;
        segs.forEach((s, si) => {
          const h = (s.value / maxY) * plotH;
          const y = plotBottom - (acc / maxY) * plotH - h;
          rects.push({
            d: this.barPath(center - barW / 2, y, barW, h, si === segs.length - 1),
            fill: registry.ref(s.color, s.pattern),
            title: `${s.seriesLabel ?? d.label} : ${s.value}`,
          });
          acc += s.value;
        });
      }

      return {
        label: d.label,
        labelX: center,
        rects,
        topLabel: this.showValues && top !== undefined ? this.formatTick(d.segments[0]?.value ?? 0) : undefined,
        topLabelX: center,
        topLabelY: top ?? 0,
      };
    });

    this.vm = {
      width, height: this.height, plotBottom, plotLeft, plotRight,
      grid, columns, defs: registry.defs(),
      hasData: data.length > 0 && columns.some(c => c.rects.length > 0),
    };
  }

  /**
   * Rectangle de barre, coins hauts arrondis de 4 px si `roundTop`.
   * Le rayon est bridé par la hauteur et la demi-largeur pour qu'un segment
   * très fin ne devienne pas une pastille.
   */
  private barPath(x: number, y: number, w: number, h: number, roundTop: boolean): string {
    const r = roundTop ? Math.max(0, Math.min(4, h, w / 2)) : 0;
    if (r <= 0) return `M${x} ${y}h${w}v${h}h${-w}Z`;
    return `M${x} ${y + r}a${r} ${r} 0 0 1 ${r} ${-r}h${w - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}v${h - r}h${-w}Z`;
  }

  private computeMax(data: BarDatum[]): number {
    let max = 0;
    for (const d of data) {
      if (this.mode === 'stacked') {
        max = Math.max(max, d.segments.reduce((a, s) => a + Math.max(s.value, 0), 0));
      } else {
        max = Math.max(max, ...d.segments.map(s => Math.abs(s.value)));
      }
    }
    return max;
  }

  /** Arrondit le max à une graduation « propre ». */
  private niceMax(v: number): number {
    if (v <= 0) return this.yTicks;
    const step = v / this.yTicks;
    const mag = Math.pow(10, Math.floor(Math.log10(step)));
    const norm = step / mag;
    const niceStep = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
    return niceStep * this.yTicks;
  }

  private formatTick(v: number): string {
    if (Number.isInteger(v)) return String(v);
    return v.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
  }
}
