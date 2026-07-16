import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type TagVariant =
  // Palette pastel — texte toujours noir #343433 (AA)
  | 'success'      // Vert #CFF1D3 — Validé, Approuvé, Actif
  | 'error'        // Rouge #FFC7C9 — Rejeté, Annulé, Expiré, Inactif, Erreur
  | 'info'         // Cyan #C1E5EC — Modifié, Utilisateur
  | 'primary'      // Cyan (alias info)
  | 'warning'      // Orange #FFE6CC — En attente, Avertissement, Référent
  | 'draft'        // Orange #FFE6CC — Brouillon (alias warning)
  | 'neutral'      // Saumon #F9CFBE — libellé neutre, sans icône
  | 'muted'        // Gris #E4E4E4 — Archivé
  // Scores (palette des scores, texte noir)
  | 'score-very-bad'   // #FF7579
  | 'score-bad'        // #FA9965
  | 'score-neutral'    // #F7D35C
  | 'score-good'       // #82DB8A
  | 'score-very-good'; // #81C9D8

export type TagSize = 'sm' | 'md';

/**
 * Tag - Composant de tag unifié (issue #296)
 *
 * Remplace les anciennes classes `.status-*`, `.score-*`, `.priority-*`, et les `mat-chip`.
 * Style : pill, sans bordure, padding compact, pas de hover si non cliquable.
 *
 * Palette pastel + texte noir d'après Figma « 🧩 Tags » (node 4487:30877).
 * Règle de la maquette : icône seulement sur les statuts principaux où couleur
 * et icône font sens ; sinon variante `neutral` sans icône. Les icônes des
 * statuts connus sont centralisées dans `shared/utils/tag-icons.ts`.
 *
 * @example Statut simple
 * <app-tag variant="success" label="Validé" icon="fi-rr-check"></app-tag>
 *
 * @example Sans icône (libellé neutre)
 * <app-tag variant="neutral" label="Prolongé +1 an"></app-tag>
 *
 * @example Cliquable (peut être édité)
 * <app-tag variant="draft" label="Brouillon" [clickable]="true" (click)="onEdit()"></app-tag>
 */
@Component({
  selector: 'app-tag',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="app-tag"
      [class]="'app-tag--' + variant + ' app-tag--' + size"
      [class.app-tag--clickable]="clickable">
      @if (icon) {
        <i class="fi" [class]="icon"></i>
      }
      <span class="app-tag__label">{{ label }}</span>
    </span>
  `,
  styleUrl: './tag.component.scss',
})
export class TagComponent {
  /** Variante de couleur du tag */
  @Input() variant: TagVariant = 'neutral';

  /** Texte affiché dans le tag */
  @Input() label: string = '';

  /** Icône Flaticon optionnelle (ex: 'fi-rr-check') */
  @Input() icon?: string;

  /** Taille du tag */
  @Input() size: TagSize = 'md';

  /** Si true, ajoute le curseur pointer et un effet hover léger */
  @Input() clickable: boolean = false;
}
