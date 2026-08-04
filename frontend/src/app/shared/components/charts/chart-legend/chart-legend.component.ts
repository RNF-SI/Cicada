import { ChangeDetectionStrategy, Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

import { LegendItem, PatternDef, PatternRegistry, nextChartUid } from '../chart.types';
import { ChartDefsComponent } from '../chart-defs.component';

interface SwatchVm { item: LegendItem; fill: string; }

/**
 * Légende réutilisable pour les graphiques (kit UI).
 *
 * Affiche une pastille (aplat ou motif hachuré/croix/points) + un libellé et,
 * optionnellement, une valeur en gras. Deux dispositions : colonne (défaut) ou
 * en ligne (`inline`).
 *
 * La pastille est un SVG de 16 px qui réutilise les `<pattern>` des graphiques
 * (`ChartDefsComponent`) : une série à motif est ainsi rendue **exactement**
 * comme son segment, sans réimplémenter les hachures en CSS — sinon les deux
 * définitions divergent au premier ajustement.
 */
@Component({
  selector: 'app-chart-legend',
  standalone: true,
  imports: [CommonModule, ChartDefsComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="legend" [class.legend--inline]="inline">
      @for (s of vm; track s.item.label) {
        <li class="legend__item">
          <svg class="legend__swatch" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <svg:g ccdChartDefs [defs]="defs"></svg:g>
            <svg:rect width="16" height="16" rx="4" [attr.fill]="s.fill"></svg:rect>
          </svg>
          <span class="legend__label">{{ s.item.label }}</span>
          @if (s.item.value !== undefined && s.item.value !== null) {
            <strong class="legend__value">{{ s.item.value }}</strong>
          }
        </li>
      }
    </ul>
  `,
  styleUrl: './chart-legend.component.scss',
})
export class ChartLegendComponent implements OnChanges {
  @Input() items: LegendItem[] = [];
  /** Disposition horizontale (wrap) plutôt qu'en colonne. */
  @Input() inline = false;

  vm: SwatchVm[] = [];
  defs: PatternDef[] = [];

  private readonly uid = nextChartUid('legend');

  ngOnChanges(): void {
    const registry = new PatternRegistry(this.uid);
    this.vm = (this.items || []).map(item => ({
      item,
      fill: registry.ref(item.color, item.pattern),
    }));
    this.defs = registry.defs();
  }
}
