import {
  ChangeDetectionStrategy, Component, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  DonutSlice, LegendItem, PatternDef, PatternRegistry, nextChartUid,
} from '../chart.types';
import { ChartDefsComponent } from '../chart-defs.component';
import { ChartLegendComponent } from '../chart-legend/chart-legend.component';

interface DonutArc {
  slice: DonutSlice;
  fill: string;
  dashArray: string;
  dashOffset: number;
  pct: number;
  tipX: number;
  tipY: number;
}

interface DonutVm {
  arcs: DonutArc[];
  defs: PatternDef[];
  legend: LegendItem[];
  cx: number;
  r: number;
  circumference: number;
  total: number;
}

/**
 * Donut (camembert évidé) du kit UI — parts, motifs hachurés, infobulle au
 * survol et légende. Les couleurs proviennent de la palette du design system
 * (fournies par l'appelant dans `slices`).
 */
@Component({
  selector: 'app-donut-chart',
  standalone: true,
  imports: [CommonModule, ChartDefsComponent, ChartLegendComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm && vm.total > 0) {
      <div class="donut" [class.donut--row]="legendPosition === 'side'">
        <div class="donut__plot" [style.max-width.px]="size">
          <svg [attr.viewBox]="'0 0 ' + size + ' ' + size" class="donut__svg">
            <svg:g ccdChartDefs [defs]="vm.defs"></svg:g>
            <svg:g [attr.transform]="'rotate(-90 ' + vm.cx + ' ' + vm.cx + ')'">
              @for (a of vm.arcs; track a.slice.label; let i = $index) {
                <svg:circle
                  class="donut__arc"
                  [class.is-dim]="hovered !== null && hovered !== i"
                  [attr.cx]="vm.cx"
                  [attr.cy]="vm.cx"
                  [attr.r]="vm.r"
                  fill="none"
                  [attr.stroke]="a.fill"
                  [attr.stroke-width]="thickness"
                  [attr.stroke-dasharray]="a.dashArray"
                  [attr.stroke-dashoffset]="a.dashOffset"
                  (mouseenter)="hovered = i"
                  (mouseleave)="hovered = null">
                </svg:circle>
              }
            </svg:g>
            @if (centerValue) {
              <svg:text [attr.x]="vm.cx" [attr.y]="vm.cx - 2" text-anchor="middle" class="donut__center-value">{{ centerValue }}</svg:text>
              <svg:text [attr.x]="vm.cx" [attr.y]="vm.cx + 16" text-anchor="middle" class="donut__center-label">{{ centerLabel }}</svg:text>
            }
          </svg>

          @if (hovered !== null) {
            @let a = vm.arcs[hovered];
            <div
              class="donut__tip"
              [style.left.%]="a.tipX / size * 100"
              [style.top.%]="a.tipY / size * 100">
              {{ a.slice.label }} : <strong>{{ a.pct | number:'1.0-0':'fr-FR' }}%</strong>
            </div>
          }
        </div>

        @if (legendPosition !== 'none') {
          <app-chart-legend [items]="vm.legend" [inline]="legendPosition === 'bottom'"></app-chart-legend>
        }
      </div>
    }
  `,
  styleUrl: './donut-chart.component.scss',
})
export class DonutChartComponent implements OnChanges {
  @Input() slices: DonutSlice[] = [];
  @Input() size = 200;
  @Input() thickness = 34;
  /** 'bottom' (défaut), 'side', ou 'none'. */
  @Input() legendPosition: 'bottom' | 'side' | 'none' = 'bottom';
  /** Valeur affichée dans la légende : pourcentage, effectif, ou les deux. */
  @Input() legendValue: 'percent' | 'count' | 'both' | 'none' = 'both';
  @Input() centerValue?: string | number;
  @Input() centerLabel = '';

  hovered: number | null = null;
  vm: DonutVm | null = null;

  private readonly uid = nextChartUid('donut');

  ngOnChanges(): void {
    this.hovered = null;
    const slices = (this.slices || []).filter(s => s.value > 0);
    const total = slices.reduce((a, s) => a + s.value, 0);
    const cx = this.size / 2;
    const r = (this.size - this.thickness) / 2;
    const circumference = 2 * Math.PI * r;
    const registry = new PatternRegistry(this.uid);

    let cumulative = 0;
    const arcs: DonutArc[] = slices.map((slice) => {
      const pct = (slice.value / total) * 100;
      const len = (slice.value / total) * circumference;
      const midLen = cumulative + len / 2;
      // Angle depuis le haut (repère tourné de -90°).
      const midAngle = (midLen / circumference) * 2 * Math.PI - Math.PI / 2;
      const arc: DonutArc = {
        slice,
        fill: registry.ref(slice.color, slice.pattern),
        dashArray: `${len} ${circumference - len}`,
        dashOffset: -cumulative,
        pct,
        tipX: cx + r * Math.cos(midAngle),
        tipY: cx + r * Math.sin(midAngle),
      };
      cumulative += len;
      return arc;
    });

    const legend: LegendItem[] = slices.map((s) => ({
      label: s.label,
      color: s.color,
      pattern: s.pattern,
      value: this.legendLabel(s.value, total),
    }));

    this.vm = { arcs, defs: registry.defs(), legend, cx, r, circumference, total };
  }

  private legendLabel(value: number, total: number): string | number | undefined {
    const pct = Math.round((value / total) * 100);
    switch (this.legendValue) {
      case 'percent': return `${pct}%`;
      case 'count': return value;
      case 'both': return `${value} · ${pct}%`;
      default: return undefined;
    }
  }
}
