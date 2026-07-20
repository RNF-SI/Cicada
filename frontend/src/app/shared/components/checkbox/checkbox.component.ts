import { Component, EventEmitter, forwardRef, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

/**
 * Checkbox - Composant checkbox custom (issue #299)
 *
 * Remplace `<mat-checkbox>` qui a un cercle ripple non-conforme au kit UI.
 *
 * - Carré arrondi 16x16, sans cercle ripple
 * - Bordure bleu-vert + fond blanc quand non coché
 * - Fond bleu-vert + icône check blanche quand coché
 * - Variante avec mention sous le label principal
 * - Compatible Reactive Forms via ControlValueAccessor
 *
 * @example Simple
 * <app-checkbox [(checked)]="agreed" label="J'accepte les conditions"></app-checkbox>
 *
 * @example Avec mention
 * <app-checkbox [(checked)]="copy" label="Sites associés" mention="Copie les associations site-plan"></app-checkbox>
 *
 * @example Avec Reactive Forms
 * <app-checkbox formControlName="active" label="Site actif"></app-checkbox>
 */
@Component({
  selector: 'app-checkbox',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './checkbox.component.html',
  styleUrl: './checkbox.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CheckboxComponent),
      multi: true,
    },
  ],
})
export class CheckboxComponent implements ControlValueAccessor {
  /** État coché */
  @Input() checked: boolean = false;
  @Output() checkedChange = new EventEmitter<boolean>();

  /** Label principal à côté de la case */
  @Input() label: string = '';

  /** Texte mention affiché sous le label (variant avec description) */
  @Input() mention?: string;

  /** Désactive la checkbox */
  @Input() disabled: boolean = false;

  /** ID unique pour l'association label/input (auto-généré sinon) */
  @Input() inputId: string = `app-checkbox-${Math.random().toString(36).slice(2, 9)}`;

  /**
   * État indéterminé (case maître / parent d'arbre à sélection partielle).
   * Ignoré quand `checked` est vrai. Rend un tiret et expose `aria-checked="mixed"`.
   */
  @Input() indeterminate: boolean = false;

  /**
   * Taille de la case.
   * - `sm` (défaut) : 18px, bordure 1.5px — rendu historique, ne pas modifier.
   * - `md` : 20px, bordure 1px, radius 6px — spec kit UI des filtres (#592).
   */
  @Input() size: 'sm' | 'md' = 'sm';

  /**
   * Contexte de rendu. `dark` = sur carte primary #025359 (sidebar filtres).
   * Les couleurs sont résolues via les custom properties `--checkbox-*`.
   */
  @Input() theme: 'light' | 'dark' = 'light';

  /** Callbacks ControlValueAccessor */
  private onChange: (value: boolean) => void = () => {};
  private onTouched: () => void = () => {};

  toggle(event?: Event): void {
    if (this.disabled) {
      return;
    }
    event?.preventDefault();
    // Un clic sur une case indéterminée coche (convention usuelle), il ne décoche pas.
    this.checked = this.indeterminate ? true : !this.checked;
    this.indeterminate = false;
    this.checkedChange.emit(this.checked);
    this.onChange(this.checked);
    this.onTouched();
  }

  // ControlValueAccessor
  writeValue(value: boolean): void {
    this.checked = !!value;
  }

  registerOnChange(fn: (value: boolean) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }
}
