import { Component, booleanAttribute, computed, input, model, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { CheckboxComponent } from '../../checkbox/checkbox.component';
import { HighlightMatchPipe } from '../highlight-match.pipe';
import { matchesQuery } from '../filter-search.util';
import { FilterOption, FilterTheme, FilterValue, TriState } from '../filter.types';

/**
 * Corps de panneau d'un filtre à liste plate (#592).
 *
 * Couvre trois cas du Figma sans composant supplémentaire :
 * - **A1** multiselect avec recherche (`searchable`) ;
 * - **A2** multiselect avec case maître « Toutes les données » (`masterLabel`) ;
 * - **C** mono-sélection (`multiple=false`) — mêmes recherche, surlignage et « Voir plus »,
 *   seules les lignes changent (pas de case à cocher).
 *
 * Utilisable dans un `app-filter-dropdown` (via `ng-template appFilterPanel`) ou directement
 * dans une carte de sidebar.
 */
@Component({
  selector: 'app-filter-option-list',
  standalone: true,
  imports: [CommonModule, TranslateModule, CheckboxComponent, HighlightMatchPipe],
  templateUrl: './filter-option-list.component.html',
  styleUrl: './filter-option-list.component.scss',
  host: {
    '[class.theme-dark]': "theme() === 'dark'",
  },
})
export class FilterOptionListComponent<T extends FilterValue = FilterValue> {
  readonly options = input.required<FilterOption<T>[]>();

  /** Valeurs sélectionnées. Bidirectionnel — ce composant les met à jour lui-même. */
  readonly selected = model<T[]>([]);

  /** `false` bascule en mono-sélection : lignes sans case, fermeture attendue par l'appelant. */
  readonly multiple = input(true, { transform: booleanAttribute });

  readonly searchable = input(false, { transform: booleanAttribute });
  readonly searchPlaceholder = input<string>('');

  /** Libellé de la case maître (« Toutes les données »). `null` = pas de case maître. */
  readonly masterLabel = input<string | null>(null);

  /**
   * Libellé de la ligne « tout » d'un filtre mono-sélection (« Toutes », « Tous les
   * organismes »…). Vider la sélection équivaut à ne pas filtrer, d'où une simple ligne
   * de remise à zéro plutôt qu'une option porteuse d'une valeur sentinelle.
   */
  readonly allLabel = input<string | null>(null);

  /** Au-delà de N options, tronque et affiche « Voir plus ». */
  readonly maxVisible = input<number | null>(null);

  readonly theme = input<FilterTheme>('light');
  readonly emptyLabel = input<string>('');

  /** Racine des `data-testid` des options, propagée par le dropdown parent. */
  readonly testId = input<string>('');

  /**
   * Émis à chaque choix — utile en mono-sélection pour refermer le panneau.
   * `null` correspond à la ligne « tout » (sélection vidée).
   */
  readonly optionPicked = output<T | null>();

  protected readonly query = signal('');
  protected readonly expanded = signal(false);

  /** Options correspondant à la recherche courante. */
  private readonly matching = computed(() => {
    const q = this.query().trim();
    return q ? this.options().filter((o) => matchesQuery(o.label, q)) : this.options();
  });

  /** Options réellement affichées (troncature « Voir plus » appliquée). */
  protected readonly visible = computed(() => {
    const max = this.maxVisible();
    const all = this.matching();
    return max !== null && !this.expanded() ? all.slice(0, max) : all;
  });

  protected readonly hiddenCount = computed(() =>
    Math.max(0, this.matching().length - this.visible().length),
  );

  protected readonly isEmpty = computed(() => this.matching().length === 0);

  /** État de la case maître : tout / rien / partiel, sur les options non désactivées. */
  protected readonly masterState = computed<TriState>(() => {
    const selectable = this.options().filter((o) => !o.disabled);
    if (!selectable.length) {
      return 'unchecked';
    }
    const set = new Set(this.selected());
    const count = selectable.filter((o) => set.has(o.value)).length;
    if (count === 0) {
      return 'unchecked';
    }
    return count === selectable.length ? 'checked' : 'indeterminate';
  });

  protected isSelected(value: T): boolean {
    return this.selected().includes(value);
  }

  protected toggle(option: FilterOption<T>): void {
    if (option.disabled) {
      return;
    }

    if (!this.multiple()) {
      this.selected.set([option.value]);
      this.optionPicked.emit(option.value);
      return;
    }

    const current = this.selected();
    this.selected.set(
      current.includes(option.value)
        ? current.filter((v) => v !== option.value)
        : [...current, option.value],
    );
    this.optionPicked.emit(option.value);
  }

  /**
   * Bascule la case maître. Un état partiel se résout en « tout sélectionner »,
   * convention usuelle des cases à trois états.
   */
  protected toggleMaster(): void {
    const selectable = this.options().filter((o) => !o.disabled);
    this.selected.set(
      this.masterState() === 'checked' ? [] : selectable.map((o) => o.value),
    );
  }

  /** Vide la sélection depuis la ligne « tout » (mono-sélection). */
  protected selectAllNone(): void {
    this.selected.set([]);
    this.optionPicked.emit(null);
  }

  protected clearSearch(): void {
    this.query.set('');
  }

  protected onSearchInput(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  protected optionTestId(option: FilterOption<T>): string | null {
    return this.testId() ? `${this.testId()}-option-${option.value}` : null;
  }
}
