import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { LegendItem } from '../chart.types';

/**
 * Légende réutilisable pour les graphiques (kit UI).
 *
 * Affiche une pastille (aplat ou motif hachuré/croix/points) + un libellé et,
 * optionnellement, une valeur en gras. Deux dispositions : colonne (défaut) ou
 * en ligne (`inline`).
 */
@Component({
  selector: 'app-chart-legend',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="legend" [class.legend--inline]="inline">
      @for (it of items; track it.label) {
        <li class="legend__item">
          <span
            class="legend__swatch"
            [ngClass]="'is-' + (it.pattern || 'solid')"
            [style.--swatch-color]="it.color">
          </span>
          <span class="legend__label">{{ it.label }}</span>
          @if (it.value !== undefined && it.value !== null) {
            <strong class="legend__value">{{ it.value }}</strong>
          }
        </li>
      }
    </ul>
  `,
  styleUrl: './chart-legend.component.scss',
})
export class ChartLegendComponent {
  @Input() items: LegendItem[] = [];
  /** Disposition horizontale (wrap) plutôt qu'en colonne. */
  @Input() inline = false;
}
