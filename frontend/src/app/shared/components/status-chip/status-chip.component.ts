import { ChangeDetectionStrategy, Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MatTooltipModule } from '@angular/material/tooltip';

import { PlanStatut } from '../../../core/models/admin.model';
import {
  getPlanStatusKey,
  getPlanStatusTooltipKey,
} from '../../utils/plan-status.utils';
import { TagComponent, TagSize, TagVariant } from '../tag/tag.component';
import { getPlanStatusTag } from '../../utils/tag-icons';

/**
 * Source de vérité unique pour l'affichage d'un chip statut de plan de
 * gestion dans toute l'application (Mes plans, Plan détail, Site associé,
 * Admin plans, etc.).
 *
 * Wrapper du composant Kit UI `<app-tag>` : couleur et icône du statut prises
 * dans `tag-icons.ts` (source Figma), label/tooltip i18n centralisés via
 * `plan-status.utils.ts`.
 *
 * @example
 * <app-status-chip [statut]="plan.statut" />
 * <app-status-chip [statut]="plan.statut" size="sm" />
 */
@Component({
  selector: 'app-status-chip',
  standalone: true,
  imports: [CommonModule, TranslateModule, MatTooltipModule, TagComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="app-status-chip-wrapper has-tooltip"
      [matTooltip]="showTooltip ? (tooltipKey() | translate) : ''"
      matTooltipPosition="above">
      <app-tag
        [variant]="variant()"
        [icon]="icon()"
        [label]="labelKey() | translate"
        [size]="size">
      </app-tag>
    </span>
  `,
  styles: [`
    .app-status-chip-wrapper {
      display: inline-flex;
      cursor: help;
    }
  `],
})
export class StatusChipComponent {
  /** Statut du plan (draft / valide / modifie / archive). */
  @Input({ required: true }) set statut(value: PlanStatut | string | null | undefined) {
    this._statut.set(value ?? 'draft');
  }
  get statut(): PlanStatut | string {
    return this._statut();
  }

  /** Taille du chip Kit UI (md par défaut, sm pour tableaux denses). */
  @Input() size: TagSize = 'md';

  /** Désactiver le tooltip pédagogique (par défaut activé). */
  @Input() showTooltip = true;

  private readonly _statut = signal<PlanStatut | string>('draft');

  readonly labelKey = computed(() => getPlanStatusKey(this._statut()));
  readonly tooltipKey = computed(() => getPlanStatusTooltipKey(this._statut()));
  readonly variant = computed<TagVariant>(() => getPlanStatusTag(this._statut()).variant);
  readonly icon = computed<string | undefined>(() => getPlanStatusTag(this._statut()).icon);
}
