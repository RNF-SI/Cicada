import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface AnchorNavItem {
  /** ID de l'ancre (correspondant à l'id de la section à scroller) */
  id: string;
  /** Label affiché */
  label: string;
  /** Optionnel : icône Flaticon à gauche du label */
  icon?: string;
}

/**
 * AnchorNav - Navigation interne par ancres (issue #304)
 *
 * Boutons tertiaires séparés par `/` qui scrollent dans la page vers une section.
 * Conçu pour les pages de détail comportant plusieurs sections (Détail site, etc.).
 *
 * - Item actif détecté automatiquement via IntersectionObserver (à venir si besoin)
 * - Au clic : scroll smooth vers la section, émet `itemClick`
 * - Aspect visuel : 5 boutons tertiaires séparés par `/`, style ancre
 *
 * @example
 * <app-anchor-nav
 *   [items]="[
 *     { id: 'overview', label: 'Vue d\'ensemble' },
 *     { id: 'info', label: 'Informations' },
 *     { id: 'organismes', label: 'Organismes' },
 *     { id: 'users', label: 'Utilisateurs' },
 *     { id: 'plans', label: 'Plans de gestion' }
 *   ]"
 *   [activeId]="currentSection()"
 *   (itemClick)="onScrollTo($event)">
 * </app-anchor-nav>
 */
@Component({
  selector: 'app-anchor-nav',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './anchor-nav.component.html',
  styleUrl: './anchor-nav.component.scss',
})
export class AnchorNavComponent {
  /** Liste des sections / ancres */
  @Input() items: AnchorNavItem[] = [];

  /** ID de l'item actif (mise en évidence visuelle) */
  @Input() activeId?: string;

  /** Si true (défaut), scroll smooth vers l'ID au clic */
  @Input() scrollOnClick: boolean = true;

  /** Émis au clic sur un item */
  @Output() itemClick = new EventEmitter<AnchorNavItem>();

  onClick(item: AnchorNavItem, event: MouseEvent): void {
    event.preventDefault();
    if (this.scrollOnClick) {
      const target = document.getElementById(item.id);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
    this.itemClick.emit(item);
  }

  isActive(item: AnchorNavItem): boolean {
    return this.activeId === item.id;
  }
}
