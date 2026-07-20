import { Component, booleanAttribute, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { FilterTheme } from '../filter.types';

/**
 * Barre de filtres horizontale (#592, famille B du Figma node 4487:31534).
 *
 * Remplace les cinq conventions de conteneur qui coexistaient : `.filters-bar`,
 * `.filter-bar` / `.filter-bar-left`, `.filter-row` / `.filter-pill`, `.logs-toolbar`
 * et `.toolbar` — et les quatorze blocs SCSS dupliqués qui allaient avec.
 *
 * Le responsive est **intégré ici** volontairement : la construction « bordure gauche +
 * séparateur après le dernier bouton » ne se replie pas gracieusement, et laissée aux pages
 * elle ferait renaître les sept blocs `@media` que cette consolidation supprime.
 *
 * @example
 * ```html
 * <app-filter-bar [showReset]="filters.hasActive()" (reset)="filters.reset()">
 *   <app-filter-dropdown label="Enjeu" [activeCount]="filters.enjeux().length">
 *     <ng-template appFilterPanel>…</ng-template>
 *   </app-filter-dropdown>
 * </app-filter-bar>
 * ```
 */
@Component({
  selector: 'app-filter-bar',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './filter-bar.component.html',
  styleUrl: './filter-bar.component.scss',
  host: {
    '[class.theme-dark]': "theme() === 'dark'",
  },
})
export class FilterBarComponent {
  /** Libellé de la pastille. Par défaut « Filtrer » (clé `common.filters.label`). */
  readonly label = input<string>('');

  readonly showReset = input(false, { transform: booleanAttribute });
  readonly theme = input<FilterTheme>('light');
  readonly testId = input<string>('');

  readonly reset = output<void>();
}
