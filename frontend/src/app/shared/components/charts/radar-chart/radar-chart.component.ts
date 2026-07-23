import {
  ChangeDetectionStrategy, Component, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { RadarAxis, nextChartUid } from '../chart.types';

interface RadarPoint { x: number; y: number; color: string; value: number; label: string; }
interface RadarAxisVm { x2: number; y2: number; labelX: number; labelY: number; anchor: string; label: string; }

interface RadarVm {
  size: number;
  cx: number;
  gradId: string;
  rings: number[];
  ringLabels: { x: number; y: number; label: string }[];
  axes: RadarAxisVm[];
  polygon: string;
  points: RadarPoint[];
  outer: number;
}

/**
 * Graphe radar du kit UI — moyennes des résultats par enjeu / FCR.
 * Fond en dégradé radial arc-en-ciel (centre chaud → extérieur froid), grille
 * concentrique graduée 1..max, polygone des valeurs et points colorés par score.
 */
@Component({
  selector: 'app-radar-chart',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm) {
      <svg [attr.viewBox]="'0 0 ' + vm.size + ' ' + vm.size" class="radar-svg" preserveAspectRatio="xMidYMid meet">
        <svg:defs>
          <svg:radialGradient [attr.id]="vm.gradId" cx="50%" cy="50%" r="50%">
            <svg:stop offset="0%" stop-color="#FF7579" stop-opacity="0.55"></svg:stop>
            <svg:stop offset="30%" stop-color="#FA9965" stop-opacity="0.45"></svg:stop>
            <svg:stop offset="55%" stop-color="#F7D35C" stop-opacity="0.42"></svg:stop>
            <svg:stop offset="78%" stop-color="#82DB8A" stop-opacity="0.45"></svg:stop>
            <svg:stop offset="100%" stop-color="#81C9D8" stop-opacity="0.5"></svg:stop>
          </svg:radialGradient>
        </svg:defs>

        @if (rainbow) {
          <svg:circle [attr.cx]="vm.cx" [attr.cy]="vm.cx" [attr.r]="vm.outer" [attr.fill]="'url(#' + vm.gradId + ')'"></svg:circle>
        }

        <!-- Grille concentrique -->
        @for (r of vm.rings; track r) {
          <svg:circle [attr.cx]="vm.cx" [attr.cy]="vm.cx" [attr.r]="r" class="radar-ring"></svg:circle>
        }
        @for (rl of vm.ringLabels; track rl.label) {
          <svg:text [attr.x]="rl.x" [attr.y]="rl.y" text-anchor="middle" class="radar-ring-label">{{ rl.label }}</svg:text>
        }

        <!-- Axes + libellés -->
        @for (a of vm.axes; track a.label) {
          <svg:line [attr.x1]="vm.cx" [attr.y1]="vm.cx" [attr.x2]="a.x2" [attr.y2]="a.y2" class="radar-axis"></svg:line>
          <svg:text [attr.x]="a.labelX" [attr.y]="a.labelY" [attr.text-anchor]="a.anchor" class="radar-axis-label">{{ a.label }}</svg:text>
        }

        <!-- Polygone des valeurs -->
        <svg:polygon [attr.points]="vm.polygon" class="radar-shape"></svg:polygon>

        <!-- Points -->
        @for (p of vm.points; track p.label) {
          <svg:circle [attr.cx]="p.x" [attr.cy]="p.y" r="5" [attr.fill]="p.color" class="radar-point"></svg:circle>
        }
      </svg>
    }
  `,
  styleUrl: './radar-chart.component.scss',
})
export class RadarChartComponent implements OnChanges {
  @Input() axes: RadarAxis[] = [];
  @Input() max = 5;
  @Input() rainbow = true;
  @Input() size = 280;

  vm: RadarVm | null = null;
  private readonly uid = nextChartUid('radar');

  ngOnChanges(): void {
    const data = this.axes || [];
    if (data.length < 3) { this.vm = null; return; }

    const cx = this.size / 2;
    const outer = cx - 34; // marge pour les libellés
    const n = data.length;
    const step = (2 * Math.PI) / n;
    const offset = -Math.PI / 2;

    const rings: number[] = [];
    const ringLabels: { x: number; y: number; label: string }[] = [];
    for (let s = 1; s <= this.max; s++) {
      const r = (s / this.max) * outer;
      rings.push(r);
      ringLabels.push({ x: cx - 4, y: cx - r + 3, label: String(s) });
    }

    const axes: RadarAxisVm[] = data.map((d, i) => {
      const a = offset + i * step;
      const cos = Math.cos(a), sin = Math.sin(a);
      const anchor = Math.abs(cos) < 0.3 ? 'middle' : cos > 0 ? 'start' : 'end';
      return {
        x2: cx + outer * cos,
        y2: cx + outer * sin,
        labelX: cx + (outer + 14) * cos,
        labelY: cx + (outer + 14) * sin + 4,
        anchor,
        label: d.label,
      };
    });

    const points: RadarPoint[] = data.map((d, i) => {
      const a = offset + i * step;
      const r = (Math.max(0, Math.min(this.max, d.value)) / this.max) * outer;
      return {
        x: cx + r * Math.cos(a),
        y: cx + r * Math.sin(a),
        color: d.color ?? '#025359',
        value: d.value,
        label: d.label,
      };
    });

    this.vm = {
      size: this.size, cx, outer,
      gradId: `${this.uid}-grad`,
      rings, ringLabels, axes,
      polygon: points.map(p => `${p.x},${p.y}`).join(' '),
      points,
    };
  }
}
