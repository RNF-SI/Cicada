import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ActionStatus =
  | 'planned'           // Action prévue (cercle vide)
  | 'planned-realized'  // Action prévue et réalisée (cercle plein)
  | 'planned-partial'   // Action prévue et partiellement réalisée (demi-cercle)
  | 'realized-unplanned' // Action réalisée non prévue (cercle plein + croix)
  | 'partial-unplanned'; // Action partiellement réalisée non prévue (demi-cercle + croix)

@Component({
  selector: 'app-action-icon',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './action-icon.component.html',
  styleUrl: './action-icon.component.scss'
})
export class ActionIconComponent {
  @Input() status: ActionStatus = 'planned';
  @Input() size: number = 28;

  getLabel(): string {
    const labels: Record<ActionStatus, string> = {
      'planned': 'Action prévue',
      'planned-realized': 'Action prévue et réalisée',
      'planned-partial': 'Action prévue et partiellement réalisée',
      'realized-unplanned': 'Action réalisée non prévue',
      'partial-unplanned': 'Action partiellement réalisée non prévue'
    };
    return labels[this.status];
  }
}
