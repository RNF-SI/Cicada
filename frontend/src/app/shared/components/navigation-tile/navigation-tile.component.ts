import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

export type TileColor = 'primary' | 'salmon' | 'terra-cotta' | 'yellow';

/**
 * NavigationTileComponent - Tuile de navigation réutilisable
 *
 * Composant de tuile avec:
 * - Zone colorée avec vagues décoratives
 * - Forme de coin arrondi avec icône en superposition
 * - Titre et flèche en bas
 *
 * @example
 * <app-navigation-tile
 *   title="Mes plans de gestion"
 *   uicon="fi-rr-document"
 *   link="/plans"
 *   color="primary"
 * ></app-navigation-tile>
 */
@Component({
  selector: 'app-navigation-tile',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navigation-tile.component.html',
  styleUrl: './navigation-tile.component.scss'
})
export class NavigationTileComponent {
  /** Titre affiché en bas de la tuile */
  @Input() title: string = '';

  /** Icône Flaticon pour le coin (ex: 'fi-rr-document') ou chemin vers SVG custom (ex: 'custom:icon-auction') */
  @Input() uicon: string = 'fi-rr-folder';

  /** Lien de navigation au clic */
  @Input() link: string = '/';

  /** Couleur de la tuile (détermine l'overlay et la couleur du coin) */
  @Input() color: TileColor = 'primary';

  /** Vérifie si l'icône est une icône SVG custom */
  isCustomIcon(): boolean {
    return this.uicon.startsWith('custom:');
  }

  /** Retourne le chemin vers l'icône SVG custom */
  getCustomIconPath(): string {
    const iconName = this.uicon.replace('custom:', '');
    return `assets/images/icons/${iconName}.svg`;
  }

  /** Retourne la classe Flaticon */
  getFlatIconClass(): string {
    return `fi ${this.uicon}`;
  }

  /** Retourne le chemin vers l'image de fond complète (couleur + vagues + découpage) */
  getBackgroundImagePath(): string {
    return `assets/images/tile-backgrounds/bg-${this.color}.png`;
  }

  /** Retourne le chemin vers la forme de coin PNG */
  getCornerShapePath(): string {
    return `assets/images/corner-shapes/corner-${this.color}.png`;
  }
}
