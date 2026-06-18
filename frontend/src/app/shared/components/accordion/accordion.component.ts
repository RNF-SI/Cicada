import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

export type AccordionVariant = 'default' | 'enjeu' | 'fcr' | 'subtle' | 'section';
export type AccordionSize = 'sm' | 'md' | 'lg';

/**
 * Accordion - Composant accordéon réutilisable (issue #303)
 *
 * Bloc collapsible avec header (titre + icône optionnelle + actions) et body projeté.
 *
 * - Chevron haut/bas conforme #297 (replié → bas, déplié → haut)
 * - 5 variantes visuelles : default, enjeu (terra-cotta), fcr (saumon), subtle (gris clair),
 *   section (en-tête de section « DÉTAILS » : titre sombre en majuscules, icône colorée
 *   projetée, sans bande latérale — cf. #334)
 * - Slots : `[accordionIcon]` (icône à gauche), `[accordionActions]` (boutons à droite), corps par défaut
 * - Compatible avec contrôle externe (input `expanded`) ou interne (toggle)
 *
 * @example Simple (auto-toggle)
 * <app-accordion title="Détails du protocole">
 *   <p>Contenu déplié...</p>
 * </app-accordion>
 *
 * @example Pour enjeu (variant + actions)
 * <app-accordion
 *   variant="enjeu"
 *   title="Enjeu 3 : Préservation de la qualité des eaux"
 *   [expanded]="isOpen()"
 *   (expandedChange)="isOpen.set($event)">
 *   <ng-container accordionIcon>
 *     <i class="fi fi-rr-mountains"></i>
 *   </ng-container>
 *   <button accordionActions class="icon-btn-flat" (click)="onEdit()">
 *     <i class="fi fi-rr-pencil"></i>
 *   </button>
 *   <!-- Corps du bloc -->
 *   <p>Détails de l'enjeu...</p>
 * </app-accordion>
 */
@Component({
  selector: 'app-accordion',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './accordion.component.html',
  styleUrl: './accordion.component.scss',
})
export class AccordionComponent {
  /** Titre affiché dans le header */
  @Input() title: string = '';

  /** Variante visuelle */
  @Input() variant: AccordionVariant = 'default';

  /** Taille (espacement et tailles d'icônes) */
  @Input() size: AccordionSize = 'md';

  /** Contrôle externe de l'état déplié (sinon géré en interne) */
  @Input()
  get expanded(): boolean {
    return this.internalExpanded();
  }
  set expanded(value: boolean) {
    this.internalExpanded.set(value);
  }
  @Output() expandedChange = new EventEmitter<boolean>();

  /** Désactive le toggle (header non cliquable) */
  @Input() disabled: boolean = false;

  protected internalExpanded = signal(false);

  toggle(): void {
    if (this.disabled) {
      return;
    }
    const next = !this.internalExpanded();
    this.internalExpanded.set(next);
    this.expandedChange.emit(next);
  }
}
