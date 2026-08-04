import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { PatternDef } from './chart.types';

/**
 * Rend les `<pattern>` SVG (hachures, croix, points) d'un graphique.
 *
 * Utilisation (à l'intérieur d'un `<svg>`) :
 *   <svg:g ccdChartDefs [defs]="vm.defs"></svg:g>
 *
 * Chaque motif est un **fond de la couleur de série à 8 % d'opacité**, surchargé
 * de traits de cette même couleur (kit UI, cf. docs/DESIGN_SYSTEM.md « Graphiques »).
 * L'aplat blanc utilisé auparavant donnait la teinte inverse de la maquette :
 * c'est la couleur de la série qui doit teinter le segment, pas le blanc.
 *
 * Géométrie relevée sur les SVG Figma (donuts et barres du Bilan) :
 *  - hachures : traits à 45°, épaisseur ~0,9 px, espacés de ~5,3 px
 *  - croix    : glyphe de 4,5 px au pas de 9 px, épaisseur 1 px — les croix ne
 *               se touchent pas (#640), contrairement au treillis continu
 *               produit par des diagonales pleine largeur.
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
              width="5.3" height="5.3"
              patternTransform="rotate(-45)">
              <svg:rect width="5.3" height="5.3" [attr.fill]="d.color" fill-opacity="0.08"></svg:rect>
              <svg:line x1="0" y1="0" x2="0" y2="5.3" [attr.stroke]="d.color" stroke-width="0.9"></svg:line>
            </svg:pattern>
          }
          @case ('cross') {
            <svg:pattern
              [attr.id]="d.id"
              patternUnits="userSpaceOnUse"
              width="9" height="9">
              <svg:rect width="9" height="9" [attr.fill]="d.color" fill-opacity="0.08"></svg:rect>
              <svg:path d="M2.25 2.25 L6.75 6.75 M6.75 2.25 L2.25 6.75"
                        fill="none" [attr.stroke]="d.color" stroke-width="1"></svg:path>
            </svg:pattern>
          }
          @case ('dots') {
            <svg:pattern
              [attr.id]="d.id"
              patternUnits="userSpaceOnUse"
              width="7" height="7">
              <svg:rect width="7" height="7" [attr.fill]="d.color" fill-opacity="0.08"></svg:rect>
              <svg:circle cx="3.5" cy="3.5" r="1.2" [attr.fill]="d.color"></svg:circle>
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
