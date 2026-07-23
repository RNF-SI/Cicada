import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { PatternDef } from './chart.types';

/**
 * Rend les `<pattern>` SVG (hachures, croix, points) d'un graphique.
 *
 * Utilisation (à l'intérieur d'un `<svg>`) :
 *   <svg:g ccdChartDefs [defs]="vm.defs"></svg:g>
 *
 * Chaque motif est un aplat blanc surchargé de traits de la couleur demandée,
 * afin de rester lisible sur fond de carte (kit UI). L'aplat blanc garantit le
 * contraste des hachures quelle que soit la couleur de série.
 */
@Component({
  selector: 'g[ccdChartDefs]',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg:defs>
      @for (d of defs; track d.id) {
        @switch (d.kind) {
          @case ('hatch') {
            <svg:pattern
              [attr.id]="d.id"
              patternUnits="userSpaceOnUse"
              width="7" height="7"
              patternTransform="rotate(45)">
              <svg:rect width="7" height="7" fill="#ffffff"></svg:rect>
              <svg:line x1="0" y1="0" x2="0" y2="7" [attr.stroke]="d.color" stroke-width="3.2"></svg:line>
            </svg:pattern>
          }
          @case ('cross') {
            <svg:pattern
              [attr.id]="d.id"
              patternUnits="userSpaceOnUse"
              width="8" height="8">
              <svg:rect width="8" height="8" fill="#ffffff"></svg:rect>
              <svg:path d="M0 0 L8 8 M8 0 L0 8" [attr.stroke]="d.color" stroke-width="1.3"></svg:path>
            </svg:pattern>
          }
          @case ('dots') {
            <svg:pattern
              [attr.id]="d.id"
              patternUnits="userSpaceOnUse"
              width="7" height="7">
              <svg:rect width="7" height="7" fill="#ffffff"></svg:rect>
              <svg:circle cx="3.5" cy="3.5" r="1.35" [attr.fill]="d.color"></svg:circle>
            </svg:pattern>
          }
        }
      }
    </svg:defs>
  `,
})
export class ChartDefsComponent {
  @Input() defs: PatternDef[] = [];
}
