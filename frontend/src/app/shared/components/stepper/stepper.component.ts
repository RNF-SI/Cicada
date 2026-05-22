import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface StepperStep {
  /** Identifiant unique de l'étape */
  id: string | number;
  /** Label de l'étape (ex: "Fichier", "Correspondance") */
  label: string;
  /** Optionnel : étape terminée avec succès */
  completed?: boolean;
}

/**
 * Stepper - Composant étapes numérotées (issue #301)
 *
 * Utilisé pour les processus multi-étapes (ex: Import en masse de sites).
 *
 * - Étapes numérotées avec cercle
 * - Ligne de progression entre étapes
 * - État `completed` (check) / `current` (mise en avant) / `pending` (numéro)
 * - Cliquable pour revenir en arrière sur étapes complétées
 *
 * @example
 * <app-stepper
 *   [steps]="[
 *     { id: 1, label: 'Fichier', completed: true },
 *     { id: 2, label: 'Correspondance', completed: true },
 *     { id: 3, label: 'Vérification' },
 *     { id: 4, label: 'Résultats' }
 *   ]"
 *   [currentStep]="3"
 *   (stepClick)="goToStep($event)">
 * </app-stepper>
 */
@Component({
  selector: 'app-stepper',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './stepper.component.html',
  styleUrl: './stepper.component.scss',
})
export class StepperComponent {
  /** Liste des étapes */
  @Input() steps: StepperStep[] = [];

  /** Index (1-based) ou ID de l'étape courante */
  @Input() currentStep: string | number = 1;

  /** Si true, les étapes complétées sont cliquables (retour en arrière) */
  @Input() allowGoBack: boolean = true;

  /** Émis au clic sur une étape complétée */
  @Output() stepClick = new EventEmitter<StepperStep>();

  isCompleted(step: StepperStep, index: number): boolean {
    if (step.completed !== undefined) {
      return step.completed;
    }
    // Fallback: si pas explicite, complétée = avant l'étape courante
    return this.indexOfStep(this.currentStep) > index;
  }

  isCurrent(step: StepperStep): boolean {
    return step.id === this.currentStep || this.steps.indexOf(step) + 1 === this.currentStep;
  }

  isClickable(step: StepperStep, index: number): boolean {
    return this.allowGoBack && this.isCompleted(step, index) && !this.isCurrent(step);
  }

  onClick(step: StepperStep, index: number): void {
    if (this.isClickable(step, index)) {
      this.stepClick.emit(step);
    }
  }

  protected indexOfStep(stepIdOrIndex: string | number): number {
    const byId = this.steps.findIndex((s) => s.id === stepIdOrIndex);
    if (byId !== -1) {
      return byId;
    }
    return typeof stepIdOrIndex === 'number' ? stepIdOrIndex - 1 : -1;
  }
}
