import { Component, ContentChild, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgControl } from '@angular/forms';

/**
 * FormField - Wrapper compact pour champs de formulaire (issue #300)
 *
 * Style "label au-dessus du champ" (vs Material Design qui place le label dans le champ).
 * Beaucoup plus dense pour les applications métier avec beaucoup de champs.
 *
 * Le composant est un wrapper visuel : il fournit la structure label + helpText + input + erreur,
 * mais le contrôle de formulaire reste dans le `<input>`, `<textarea>` ou `<select>` projeté.
 *
 * @example Basique
 * <app-form-field label="Nom du site" required>
 *   <input type="text" formControlName="name" />
 * </app-form-field>
 *
 * @example Avec aide et erreur
 * <app-form-field
 *   label="Surface (ha)"
 *   helpText="Saisissez un nombre entier"
 *   [error]="form.controls.surface.touched && form.controls.surface.errors?.['min'] ? 'La surface doit être ≥ 0' : null">
 *   <input type="number" formControlName="surface" min="0" />
 * </app-form-field>
 */
@Component({
  selector: 'app-form-field',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './form-field.component.html',
  styleUrl: './form-field.component.scss',
})
export class FormFieldComponent {
  /** Label affiché au-dessus du champ */
  @Input() label: string = '';

  /** Marque le champ comme requis (ajoute l'astérisque rouge) */
  @Input() required: boolean = false;

  /** Texte d'aide affiché ENTRE le label et le champ (accessibilité) */
  @Input() helpText?: string;

  /** Message d'erreur — quand renseigné, le champ passe en état erreur */
  @Input() error?: string | null;

  /** Suffixe affiché à droite du champ (ex: 'ha', '€', 'j') */
  @Input() suffix?: string;

  /** ID unique pour l'association label/input (auto-généré sinon) */
  @Input() fieldId: string = `app-field-${Math.random().toString(36).slice(2, 9)}`;

  /** Détecte le contrôle projeté pour propager focus/error via [class] */
  @ContentChild(NgControl) protected control?: NgControl;

  get hasError(): boolean {
    return !!this.error;
  }
}
