import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

// Toutes les couleurs disponibles pour l'ellipse
export type EllipseColor =
  | 'primary'       // #025359 - Bleu-vert
  | 'salmon'        // #F5B399 - Orange saumon
  | 'terra-cotta'   // #B74D5D - Terra cotta
  | 'yellow'        // #FEC180 - Jaune
  | 'pale-green'    // #C0E3CF - Vert pâle
  | 'white'         // #FFFFFF - Blanc
  | 'beige'         // #F8F5F1 - Beige
  | 'gray'          // #949494 - Gris
  | 'gray-light';   // #DADADA - Gris clair

// Couleur de l'icône
export type IconColor = 'white' | 'primary';

// Tailles disponibles
export type EllipseSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

/**
 * EllipseIconButton - Composant ellipse réutilisable avec icône
 *
 * @example
 * <!-- Ellipse primaire avec icône blanche (défaut) -->
 * <app-ellipse-icon-button icon="fi-rr-document"></app-ellipse-icon-button>
 *
 * @example
 * <!-- Ellipse blanche avec icône primaire -->
 * <app-ellipse-icon-button
 *   icon="fi-rr-search"
 *   ellipseColor="white"
 *   iconColor="primary"
 * ></app-ellipse-icon-button>
 *
 * @example
 * <!-- Ellipse jaune, grande taille -->
 * <app-ellipse-icon-button
 *   icon="fi-rr-star"
 *   ellipseColor="yellow"
 *   size="lg"
 * ></app-ellipse-icon-button>
 */
@Component({
  selector: 'app-ellipse-icon-button',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ellipse-icon-button.component.html',
  styleUrl: './ellipse-icon-button.component.scss'
})
export class EllipseIconButtonComponent {
  /** Classe d'icône Flaticon (ex: 'fi-rr-document', 'fi-rr-search') */
  @Input() icon: string = 'fi-rr-document';

  /** Couleur de fond de l'ellipse */
  @Input() ellipseColor: EllipseColor = 'primary';

  /** @deprecated Utiliser ellipseColor à la place */
  @Input() set color(value: EllipseColor) {
    this.ellipseColor = value;
  }

  /** Couleur de l'icône */
  @Input() iconColor: IconColor = 'white';

  /** Taille de l'ellipse */
  @Input() size: EllipseSize = 'md';

  /** Afficher ou non la bordure blanche */
  @Input() showBorder: boolean = true;

  /** Afficher ou non l'ombre */
  @Input() showShadow: boolean = true;
}
