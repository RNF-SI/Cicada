import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

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
  imports: [CommonModule],
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

  /** Si true, ajoute curseur et hover */
  @Input() clickable: boolean = false;

  /** Émis au clic si clickable */
  @Output() tileClick = new EventEmitter<void>();

  onClick(): void {
    if (this.clickable) {
      this.tileClick.emit();
    }
  }
}
