import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type TagVariant =
  // Statuts sémantiques (texte sur fond coloré, AA)
  | 'success'      // Vert succès #04854B - blanc
  | 'error'        // Rouge erreur #E12329 - blanc
  | 'info'         // Bleu-vert principal #025359 - blanc
  | 'primary'      // Bleu-vert principal (alias info)
  // Statuts décoratifs (texte noir/primary sur fond pastel, AA)
  | 'warning'      // Orange saumon #F5B399 - noir
  | 'draft'        // Jaune #FEC180 - noir
  | 'neutral'      // Vert pâle #C0E3CF - noir
  | 'muted'        // Gris très clair #E4E4E4 - noir
  // Scores
  | 'score-very-bad'   // #FF7579 - noir
  | 'score-bad'        // #FA9965 - noir
  | 'score-neutral'    // #F7D35C - noir
  | 'score-good'       // #82DB8A - noir
  | 'score-very-good'; // #81C9D8 - noir

export type TagSize = 'sm' | 'md';

/**
 * Tag - Composant de tag unifié (issue #296)
 *
 * Remplace les anciennes classes `.status-*`, `.score-*`, `.priority-*`, et les `mat-chip`.
 * Style : pill, sans bordure, padding compact, pas de hover si non cliquable.
 *
 * @example Statut simple
 * <app-tag variant="success" label="Validé"></app-tag>
 *
 * @example Avec icône
 * <app-tag variant="warning" label="En attente" icon="fi-rr-clock"></app-tag>
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
