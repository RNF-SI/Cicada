import { Component, Input } from '@angular/core';
import { getPrioriteLevel, PrioriteLevel } from '../../utils/tag-icons';

/**
 * PriorityBadge — Affichage de la priorité d'une action de gestion (#566).
 *
 * Format conforme au kit UI Figma « 🧩 Tags » → « Priorité d'un enjeu »
 * (nodes 4487:30880 / 30907 / 30934) : le libellé « Priorité » en gris suivi
 * d'une **pastille ronde** portant le chiffre, colorée selon le niveau :
 *   - Priorité 1 → rouge  #FF7579 (score-very-bad)
 *   - Priorité 2 → jaune  #F7D35C (score-neutral)
 *   - Priorité 3 → bleu   #81C9D8 (score-very-good)
 * Chiffre en noir #343433 (WCAG AA sur les fonds scores).
 *
 * Remplace l'ancien pill « Priorité N » (palette et format non conformes,
 * cf. retour issue #566).
 *
 * @example
 * <app-priority-badge [label]="op.priorite_label"></app-priority-badge>
 *
 * @example Pastille seule (tableaux denses)
 * <app-priority-badge [label]="op.priorite_label" [showLabel]="false"></app-priority-badge>
 */
@Component({
  selector: 'app-priority-badge',
  standalone: true,
  imports: [],
  template: `
    @if (level(); as lvl) {
      <span class="priority-badge" [title]="title ?? label ?? ''">
        @if (showLabel && word()) {
          <span class="priority-badge__label">{{ word() }}</span>
        }
        <span class="priority-badge__circle" [class]="'priority-badge__circle--' + lvl">{{ lvl }}</span>
      </span>
    }
  `,
  styleUrl: './priority-badge.component.scss',
})
export class PriorityBadgeComponent {
  /** Libellé de priorité fourni par l'API (ex. « Priorité 1 »). */
  @Input() label: string | null | undefined;

  /** Afficher le mot « Priorité » avant la pastille (false = pastille seule). */
  @Input() showLabel = true;

  /** Tooltip optionnel (défaut : le libellé complet). */
  @Input() title?: string;

  /** Niveau 1/2/3 déduit du libellé, ou null (rien n'est rendu). */
  level(): PrioriteLevel | null {
    return getPrioriteLevel(this.label);
  }

  /** Partie texte du libellé, sans le chiffre (ex. « Priorité 1 » → « Priorité »). */
  word(): string {
    return (this.label ?? '').replace(/\s*\d+\s*$/, '').trim();
  }
}
