import {
  ChangeDetectionStrategy, Component, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { ChartPoint, LineSeries, LineBand, LegendItem, smoothPath } from '../chart.types';
import { ChartLegendComponent } from '../chart-legend/chart-legend.component';

interface SeriesVm { path: string; color: string; dashed: boolean; showPoints: boolean; points: { x: number; y: number }[]; }
interface GridLine { y: number; label: string; }

interface LineVm {
  width: number;
  height: number;
  plotLeft: number;
  plotRight: number;
  plotBottom: number;
  grid: GridLine[];
  xticks: { x: number; label: string }[];
  /** Enveloppe min–max : deux courbes **ouvertes**, tracées en pointillés. */
  bandEdges: string[];
  /** Bande d'écart-type : surface fermée, peinte. */
  innerBandPath?: string;
  bandColor: string;
  series: SeriesVm[];
  hasData: boolean;
}

/**
 * Graphe courbes du kit UI. Une ou plusieurs séries + bande de confiance
 * optionnelle (enveloppe min–max en pointillés + bande écart-type ombrée),
 * comme « Évolution de la moyenne des indicateurs ».
 */
@Component({
  selector: 'app-line-chart',
  standalone: true,
  imports: [CommonModule, ChartLegendComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm && vm.hasData) {
      <svg [attr.viewBox]="'0 0 ' + vm.width + ' ' + vm.height" class="line-svg"
           [style.max-width.px]="vm.width" preserveAspectRatio="xMidYMid meet">
        @if (yLabel) {
          <svg:text [attr.x]="vm.plotLeft" y="12" class="line-axis-title">{{ yLabel }}</svg:text>
        }
        <!-- Grille Y -->
        @for (g of vm.grid; track g.y) {
          <svg:line [attr.x1]="vm.plotLeft" [attr.x2]="vm.plotRight" [attr.y1]="g.y" [attr.y2]="g.y" class="line-grid"></svg:line>
          <svg:text [attr.x]="vm.plotLeft - 6" [attr.y]="g.y + 3" text-anchor="end" class="line-tick">{{ g.label }}</svg:text>
        }
        <!-- Bande d'écart-type (aplat), puis enveloppe min–max (pointillés) -->
        @if (vm.innerBandPath) {
          <svg:path [attr.d]="vm.innerBandPath" [attr.fill]="vm.bandColor" fill-opacity="0.2" stroke="none"></svg:path>
        }
        <!--
          Enveloppe min–max : deux courbes pointillées distinctes, sans
          remplissage. Un contour fermé ajouterait un trait vertical à chaque
          extrémité, là où le minimum rejoindrait le maximum — une variation
          que la donnée ne décrit pas.
        -->
        @for (edge of vm.bandEdges; track $index) {
          <svg:path [attr.d]="edge" fill="none" [attr.stroke]="vm.bandColor"
                    stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3 6"></svg:path>
        }
        <!-- Séries -->
        @for (s of vm.series; track $index) {
          <svg:path [attr.d]="s.path" fill="none" [attr.stroke]="s.color" stroke-width="2"
                    [attr.stroke-dasharray]="s.dashed ? '5 4' : null"
                    stroke-linecap="round" stroke-linejoin="round"></svg:path>
          @if (s.showPoints) {
            @for (p of s.points; track $index) {
              <svg:circle [attr.cx]="p.x" [attr.cy]="p.y" r="4" [attr.fill]="s.color"></svg:circle>
            }
          }
        }
        <!-- Libellés X -->
        @for (t of vm.xticks; track t.label) {
          <svg:text [attr.x]="t.x" [attr.y]="vm.plotBottom + 16" text-anchor="middle" class="line-xlabel">{{ t.label }}</svg:text>
        }
      </svg>
      @if (legend?.length) {
        <app-chart-legend [items]="legend!" [inline]="true"></app-chart-legend>
      }
    }
  `,
  styleUrl: './line-chart.component.scss',
})
export class LineChartComponent implements OnChanges {
  @Input() xLabels: (string | number)[] = [];
  @Input() series: LineSeries[] = [];
  @Input() band?: LineBand;
  @Input() yMin = 0;
  @Input() yMax = 5;
  @Input() yTicks = 5;
  @Input() height = 240;
  @Input() yLabel?: string;
  /** Largeur du tracé, en px — voir `BarChartComponent.maxWidth`. */
  @Input() maxWidth = 640;
  @Input() legend?: LegendItem[];

  vm: LineVm | null = null;

  ngOnChanges(): void {
    const n = this.xLabels.length;
    if (n === 0 || this.series.length === 0) { this.vm = null; return; }

    const width = this.maxWidth;
    const plotLeft = 34, plotRight = width - 14, plotTop = 18, plotBottom = this.height - 26;
    const plotW = plotRight - plotLeft;
    const plotH = plotBottom - plotTop;
    const span = this.yMax - this.yMin || 1;

    const xAt = (i: number) => n === 1 ? (plotLeft + plotRight) / 2 : plotLeft + (i / (n - 1)) * plotW;
    const yAt = (v: number) => plotBottom - ((v - this.yMin) / span) * plotH;

    const grid: GridLine[] = [];
    for (let i = 0; i <= this.yTicks; i++) {
      const v = this.yMin + (span / this.yTicks) * i;
      grid.push({ y: yAt(v), label: this.formatTick(v) });
    }

    const xticks = this.xLabels.map((label, i) => ({ x: xAt(i), label: String(label) }));

    const series: SeriesVm[] = this.series.map((s) => {
      const points = s.points.map((v, i) => v === null ? null : { x: xAt(i), y: yAt(v) });
      return {
        color: s.color,
        dashed: !!s.dashed,
        showPoints: s.showPoints !== false,
        path: this.toPath(points),
        points: points.filter((p): p is { x: number; y: number } => p !== null),
      };
    });

    let bandEdges: string[] = [];
    let innerBandPath: string | undefined;
    if (this.band) {
      bandEdges = [this.band.upper, this.band.lower]
        .map(vals => this.toEdgePath(vals, xAt, yAt))
        .filter((d): d is string => !!d);
      if (this.band.innerLower && this.band.innerUpper) {
        innerBandPath = this.toBandPath(this.band.innerLower, this.band.innerUpper, xAt, yAt);
      }
    }

    this.vm = {
      width, height: this.height, plotLeft, plotRight, plotBottom,
      grid, xticks, bandEdges, innerBandPath,
      bandColor: this.band?.color ?? '#B74D5D',
      series,
      hasData: series.some(s => s.points.length > 0),
    };
  }

  /**
   * Tracé lissé d'une série, en sautant les points manquants : chaque suite de
   * points consécutifs forme sa propre courbe, sinon un trou d'une année
   * relierait deux mesures distantes par une courbe inventée.
   */
  private toPath(points: (ChartPoint | null)[]): string {
    const morceaux: ChartPoint[][] = [];
    let courant: ChartPoint[] = [];
    for (const p of points) {
      if (p === null) {
        if (courant.length) morceaux.push(courant);
        courant = [];
      } else {
        courant.push(p);
      }
    }
    if (courant.length) morceaux.push(courant);
    return morceaux.map(m => smoothPath(m)).join(' ').trim();
  }

  /** Une bordure de l'enveloppe (min ou max), lissée et laissée ouverte. */
  private toEdgePath(
    values: (number | null)[],
    xAt: (i: number) => number, yAt: (v: number) => number,
  ): string | undefined {
    const pts = values
      .map((v, i) => v === null ? null : { x: xAt(i), y: yAt(v) })
      .filter((p): p is ChartPoint => p !== null);
    return pts.length ? smoothPath(pts) : undefined;
  }

  private toBandPath(
    lower: (number | null)[], upper: (number | null)[],
    xAt: (i: number) => number, yAt: (v: number) => number,
  ): string | undefined {
    // La bande suit les mêmes courbes que la moyenne qu'elle entoure : lissée
    // à l'aller (bord haut) et au retour (bord bas), refermée entre les deux.
    const up: ChartPoint[] = [];
    const down: ChartPoint[] = [];
    for (let i = 0; i < upper.length; i++) {
      if (upper[i] === null) continue;
      up.push({ x: xAt(i), y: yAt(upper[i] as number) });
    }
    for (let i = lower.length - 1; i >= 0; i--) {
      if (lower[i] === null) continue;
      down.push({ x: xAt(i), y: yAt(lower[i] as number) });
    }
    if (!up.length || !down.length) return undefined;
    const haut = smoothPath(up);
    const bas = smoothPath(down).replace(/^M/, 'L');
    return `${haut} ${bas} Z`;
  }

  private formatTick(v: number): string {
    return Number.isInteger(v) ? String(v) : v.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
  }
}
