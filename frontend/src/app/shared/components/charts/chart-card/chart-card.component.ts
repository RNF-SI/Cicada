import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Tuile graphique du kit UI (« Format d'une tuile graphe »).
 *
 * Carte blanche arrondie : titre en capitales bleu-vert + sous-titre mention
 * optionnel + contenu projeté (graphique, tableau…). Un en-tête d'actions peut
 * être projeté via le slot `[cardActions]` (ex. sélecteur d'enjeu).
 */
@Component({
  selector: 'app-chart-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article class="chart-card" [class.chart-card--accent]="accent">
      <header class="chart-card__head">
        <div class="chart-card__titles">
          <h3 class="chart-card__title">{{ title }}</h3>
          @if (subtitle) {
            <p class="chart-card__subtitle">{{ subtitle }}</p>
          }
        </div>
        <div class="chart-card__actions">
          <ng-content select="[cardActions]"></ng-content>
        </div>
      </header>
      <div class="chart-card__body">
        <ng-content></ng-content>
      </div>
    </article>
  `,
  styleUrl: './chart-card.component.scss',
})
export class ChartCardComponent {
  @Input() title = '';
  @Input() subtitle?: string;
  /** Variante fond vert pâle (ex. carte budget). */
  @Input() accent = false;
}
