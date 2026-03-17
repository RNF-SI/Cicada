import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { EllipseIconButtonComponent, EllipseColor } from '../ellipse-icon-button/ellipse-icon-button.component';

/**
 * SectionTitle - Composant de titre de section avec icône ellipse
 *
 * Utilisé pour les titres de sections dans les pages de détail (plans, sites, etc.)
 * Combine une ellipse colorée avec icône et un titre, avec optionnellement un lien.
 *
 * @example
 * <!-- Titre simple -->
 * <app-section-title
 *   title="Synthèse"
 *   icon="fi-rr-list-check"
 *   ellipseColor="salmon">
 * </app-section-title>
 *
 * @example
 * <!-- Titre avec lien -->
 * <app-section-title
 *   title="Site"
 *   icon="fi-rr-marker"
 *   ellipseColor="primary"
 *   linkText="Voir en détails"
 *   linkUrl="/sites/123">
 * </app-section-title>
 */
@Component({
  selector: 'app-section-title',
  standalone: true,
  imports: [CommonModule, RouterModule, EllipseIconButtonComponent],
  templateUrl: './section-title.component.html',
  styleUrl: './section-title.component.scss'
})
export class SectionTitleComponent {
  /** Titre de la section */
  @Input() title: string = '';

  /** Classe d'icône Flaticon (ex: 'fi-rr-list-check') ou custom SVG (ex: 'custom:mindmap') */
  @Input() icon: string = 'fi-rr-document';

  /** Vérifie si l'icône est une icône custom SVG */
  get isCustomIcon(): boolean {
    return this.icon.startsWith('custom:');
  }

  /** Retourne le nom de l'icône custom (sans le préfixe 'custom:') */
  get customIconName(): string {
    return this.icon.replace('custom:', '');
  }

  /** Retourne le chemin vers l'icône custom SVG */
  get customIconPath(): string {
    return `assets/images/icons/${this.customIconName}.svg`;
  }

  /** Couleur de l'ellipse */
  @Input() ellipseColor: EllipseColor = 'primary';

  /** Couleur de l'icône */
  @Input() iconColor: 'white' | 'primary' = 'white';

  /** Taille de l'ellipse */
  @Input() size: 'xs' | 'sm' | 'md' | 'lg' | 'xl' = 'md';

  /** Taille du titre */
  @Input() titleSize: 'normal' | 'small' = 'normal';

  /** Couleur du titre (par défaut primary) */
  @Input() titleColor: 'primary' | 'terra-cotta' | 'salmon' | 'yellow' = 'primary';

  /** Afficher la bordure de l'ellipse */
  @Input() showBorder: boolean = false;

  /** Afficher l'ombre de l'ellipse */
  @Input() showShadow: boolean = false;

  /** Texte du lien (optionnel) */
  @Input() linkText: string = '';

  /** URL du lien (optionnel) */
  @Input() linkUrl: string = '';

  /** Afficher la ligne de séparation sous le titre */
  @Input() showLine: boolean = true;

  /** Retourne le chemin vers l'image ellipse selon la couleur (sans bordure blanche) */
  getCornerShapePath(): string {
    // Mapping des couleurs vers les noms de fichiers
    const colorMap: Record<string, string> = {
      'primary': 'primary',
      'salmon': 'salmon',
      'orange': 'salmon', // orange utilise salmon
      'terra-cotta': 'terra-cotta',
      'yellow': 'yellow',
      'pale-green': 'pale-green',
      'white': 'pale-green', // fallback
      'beige': 'pale-green', // fallback
      'gray': 'pale-green', // fallback
      'gray-light': 'pale-green' // fallback
    };
    const colorName = colorMap[this.ellipseColor] || 'primary';
    // Utilise les ellipses sans bordure pour les titres de section
    return `assets/images/ellipses/ellipse-${colorName}.png`;
  }
}
