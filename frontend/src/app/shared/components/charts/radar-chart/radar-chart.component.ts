import {
  ChangeDetectionStrategy, Component, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { RadarAxis, nextChartUid, smoothPath } from '../chart.types';

interface RadarPoint { x: number; y: number; color: string; value: number; label: string; }
interface RadarAxisVm { x2: number; y2: number; labelX: number; labelY: number; anchor: string; label: string; }

interface RadarVm {
  /** Largeur du viewBox : disque + couronne de libellés de part et d'autre. */
  vbWidth: number;
  size: number;
  cx: number;
  cy: number;
  gradId: string;
  rings: number[];
  ringLabels: { x: number; y: number; label: string }[];
  axes: RadarAxisVm[];
  /** Tracé fermé et lissé des valeurs. */
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
      <svg [attr.viewBox]="'0 0 ' + vm.vbWidth + ' ' + vm.size" class="radar-svg"
           [style.max-width.px]="vm.vbWidth" preserveAspectRatio="xMidYMid meet">
        <svg:defs>
          <!--
            Arrêts et opacité relevés sur la maquette : l'opacité est portée par
            le disque (0.5 uniforme), pas par chaque arrêt — sinon le dégradé
            change de saturation en même temps que de teinte.
          -->
          <svg:radialGradient [attr.id]="vm.gradId" cx="50%" cy="50%" r="50%">
            <svg:stop offset="0%" stop-color="#FF7579"></svg:stop>
            <svg:stop offset="35%" stop-color="#FA9965"></svg:stop>
            <svg:stop offset="60%" stop-color="#F7D35C"></svg:stop>
            <svg:stop offset="85%" stop-color="#82DB8A"></svg:stop>
            <svg:stop offset="100%" stop-color="#81C9D8"></svg:stop>
          </svg:radialGradient>
        </svg:defs>

        @if (rainbow) {
          <svg:circle [attr.cx]="vm.cx" [attr.cy]="vm.cy" [attr.r]="vm.outer"
                      [attr.fill]="'url(#' + vm.gradId + ')'" fill-opacity="0.5"></svg:circle>
        }

        <!-- Grille concentrique -->
        @for (r of vm.rings; track r) {
          <svg:circle [attr.cx]="vm.cx" [attr.cy]="vm.cy" [attr.r]="r" class="radar-ring"></svg:circle>
        }
        @for (rl of vm.ringLabels; track rl.label) {
          <svg:text [attr.x]="rl.x" [attr.y]="rl.y" text-anchor="middle" class="radar-ring-label">{{ rl.label }}</svg:text>
        }

        <!-- Axes + libellés -->
        @for (a of vm.axes; track a.label) {
          <svg:line [attr.x1]="vm.cx" [attr.y1]="vm.cy" [attr.x2]="a.x2" [attr.y2]="a.y2" class="radar-axis"></svg:line>
          <svg:text [attr.x]="a.labelX" [attr.y]="a.labelY" [attr.text-anchor]="a.anchor" class="radar-axis-label">{{ a.label }}</svg:text>
        }

        <!-- Polygone des valeurs -->
        <svg:path [attr.d]="vm.polygon" class="radar-shape"></svg:path>

        <!-- Points -->
        @for (p of vm.points; track p.label) {
          <svg:circle [attr.cx]="p.x" [attr.cy]="p.y" r="6" [attr.fill]="p.color" class="radar-point"></svg:circle>
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
  /** Kit UI : disque de 328 px + couronne de libellés. */
  @Input() size = 340;

  vm: RadarVm | null = null;
  private readonly uid = nextChartUid('radar');

  /** Place horizontale reservee aux libelles d'axes, de chaque cote du disque. */
  private static readonly LABEL_ROOM = 110;

  ngOnChanges(): void {
    const data = this.axes || [];
    if (data.length < 3) { this.vm = null; return; }

    // Les libellés d'axes sortent du disque : le viewBox est élargi de
    // `LABEL_ROOM` de chaque côté pour les contenir. Sans cette couronne, un
    // libellé d'enjeu un peu long est rogné par le bord de la carte.
    const vbWidth = this.size + 2 * RadarChartComponent.LABEL_ROOM;
    const cx = vbWidth / 2;
    const cy = this.size / 2;
    const outer = cy - 22;
    const n = data.length;
    const step = (2 * Math.PI) / n;
    const offset = -Math.PI / 2;

    // Les graduations suivent la bissectrice entre le premier et le dernier
    // axe (kit UI) : posées sur un axe, elles passeraient sous les sommets du
    // polygone et sous les points, qui s'y trouvent par construction.
    const gradAngle = offset - step / 2;
    const gradCos = Math.cos(gradAngle), gradSin = Math.sin(gradAngle);

    const rings: number[] = [];
    const ringLabels: { x: number; y: number; label: string }[] = [];
    for (let s = 1; s <= this.max; s++) {
      const r = (s / this.max) * outer;
      rings.push(r);
      ringLabels.push({ x: cx + r * gradCos, y: cy + r * gradSin + 4, label: String(s) });
    }

    const axes: RadarAxisVm[] = data.map((d, i) => {
      const a = offset + i * step;
      const cos = Math.cos(a), sin = Math.sin(a);
      const anchor = Math.abs(cos) < 0.3 ? 'middle' : cos > 0 ? 'start' : 'end';
      return {
        x2: cx + outer * cos,
        y2: cy + outer * sin,
        labelX: cx + (outer + 14) * cos,
        labelY: cy + (outer + 14) * sin + 4,
        anchor,
        label: d.label,
      };
    });

    const points: RadarPoint[] = data.map((d, i) => {
      const a = offset + i * step;
      const r = (Math.max(0, Math.min(this.max, d.value)) / this.max) * outer;
      return {
        x: cx + r * Math.cos(a),
        y: cy + r * Math.sin(a),
        color: d.color ?? '#025359',
        value: d.value,
        label: d.label,
      };
    });

    this.vm = {
      vbWidth, size: this.size, cx, cy, outer,
      gradId: `${this.uid}-grad`,
      rings, ringLabels, axes,
      // Courbe fermée, comme la maquette : un radar à cinq axes tracé en
      // segments droits donne une étoile anguleuse, pas la forme du kit.
      polygon: smoothPath(points, 0.5, true),
      points,
    };
  }
}
