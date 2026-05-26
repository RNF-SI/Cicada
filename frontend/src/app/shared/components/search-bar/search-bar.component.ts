import { Component, EventEmitter, Input, Output, ViewChild, ElementRef, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

export type SearchBarMode = 'auto' | 'manual';

/**
 * SearchBar - Composant de recherche unifié (issue #298)
 *
 * 2 variantes :
 * - `mode="auto"` : la saisie filtre instantanément (émet `valueChange` à chaque caractère)
 * - `mode="manual"` : champ + bouton "Rechercher" qui déclenche `search` (utile pour API distantes)
 *
 * Texte d'aide placé AVANT le champ (accessibilité — lecteurs d'écran).
 *
 * @example Auto-filtre
 * <app-search-bar
 *   [(value)]="query"
 *   placeholder="Rechercher un site...">
 * </app-search-bar>
 *
 * @example Manuel (avec bouton)
 * <app-search-bar
 *   mode="manual"
 *   placeholder="Rechercher un plan..."
 *   helpText="Entrez au moins 2 caractères"
 *   (search)="onSearch($event)">
 * </app-search-bar>
 */
@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.scss',
})
export class SearchBarComponent {
  /** Mode de la barre : 'auto' (filtre instantané) ou 'manual' (avec bouton) */
  @Input() mode: SearchBarMode = 'auto';

  /** Valeur courante du champ (two-way binding) */
  @Input() value: string = '';
  @Output() valueChange = new EventEmitter<string>();

  /** Placeholder affiché dans le champ */
  @Input() placeholder: string = '';

  /** Texte d'aide affiché AU-DESSUS du champ (accessibilité) */
  @Input() helpText?: string;

  /** Label visuellement caché mais lu par les lecteurs d'écran si pas de helpText */
  @Input() ariaLabel: string = 'Rechercher';

  /** Désactive le champ */
  @Input() disabled: boolean = false;

  /** Émis en mode 'manual' quand l'utilisateur clique sur "Rechercher" ou appuie sur Enter */
  @Output() search = new EventEmitter<string>();

  /** Émis quand l'utilisateur efface le champ via le bouton x */
  @Output() cleared = new EventEmitter<void>();

  @ViewChild('input') input?: ElementRef<HTMLInputElement>;

  protected hasFocus = signal(false);

  onInput(newValue: string): void {
    this.value = newValue;
    if (this.mode === 'auto') {
      this.valueChange.emit(newValue);
    }
  }

  onEnter(): void {
    if (this.mode === 'manual' && this.value.trim()) {
      this.search.emit(this.value.trim());
    }
  }

  onSearchClick(): void {
    if (this.value.trim()) {
      this.search.emit(this.value.trim());
    }
  }

  clear(): void {
    this.value = '';
    this.valueChange.emit('');
    this.cleared.emit();
    this.input?.nativeElement.focus();
  }

  onFocus(): void {
    this.hasFocus.set(true);
  }

  onBlur(): void {
    this.hasFocus.set(false);
  }
}
