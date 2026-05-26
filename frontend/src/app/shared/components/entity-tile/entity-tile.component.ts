import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

/**
 * EntityTile - Tuile compacte pour site / utilisateur / organisme (issue #302)
 *
 * Utilisée dans :
 * - Vue d'ensemble plan (sections Sites + Utilisateurs)
 * - Modales Gérer sites / utilisateurs
 *
 * - Icône à gauche (Flaticon class)
 * - Nom (titre) + sous-info (organisme, email…)
 * - Action ou tag à droite (slot via `<ng-content select="[tileAction]">`)
 * - Pas de hover ni cursor si non cliquable
 *
 * @example Site
 * <app-entity-tile
 *   icon="fi-rr-marker"
 *   name="Réserve Naturelle du Lac de Remoray"
 *   subtitle="Réserves Naturelles de France">
 *   <button tileAction class="link-default">Demander l'accès</button>
 * </app-entity-tile>
 *
 * @example Utilisateur cliquable
 * <app-entity-tile
 *   icon="fi-rr-user"
 *   name="Marie Dupont"
 *   subtitle="admin.rnf@test.fr"
 *   [clickable]="true"
 *   (click)="goToUser()">
 *   <app-tag tileAction variant="warning" label="Référent" />
 * </app-entity-tile>
 */
@Component({
  selector: 'app-entity-tile',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './entity-tile.component.html',
  styleUrl: './entity-tile.component.scss',
})
export class EntityTileComponent {
  /** Classe Flaticon pour l'icône à gauche (ex: 'fi-rr-marker') */
  @Input() icon: string = 'fi-rr-document';

  /** Nom principal (ligne 1, bold) */
  @Input() name: string = '';

  /** Sous-info (ligne 2, gris foncé) */
  @Input() subtitle?: string;

  /** Si fourni, la tuile devient un lien (navigateur ou Router). Auto-active clickable. */
  @Input() routerLink?: string | unknown[];

  /** Si fourni (alternative à routerLink), URL externe via <a href> */
  @Input() href?: string;

  /** État verrouillé (icône lock, opacité réduite) — pour sites sans accès */
  @Input() locked: boolean = false;

  /** Active curseur + hover sans navigation (utilise tileClick) */
  @Input() clickable: boolean = false;

  /** Émis au clic (utile sans routerLink ni href) */
  @Output() tileClick = new EventEmitter<void>();

  get isInteractive(): boolean {
    return this.clickable || !!this.routerLink || !!this.href;
  }

  onClick(): void {
    if (this.clickable && !this.locked) {
      this.tileClick.emit();
    }
  }
}
