import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatChipsModule } from '@angular/material/chips';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem } from '../../../core/models/admin.model';

@Component({
  selector: 'app-plan-version-timeline',
  standalone: true,
  imports: [CommonModule, RouterModule, MatChipsModule, TranslateModule],
  templateUrl: './plan-version-timeline.component.html',
  styleUrl: './plan-version-timeline.component.scss',
})
export class PlanVersionTimelineComponent {
  @Input() chain: PlanVersionChainItem[] = [];
  @Input() currentStatus = 'draft';

  getNodeIcon(item: PlanVersionChainItem): string {
    switch (item.type_document_mnemonique) {
      case 'EVAL_MI_PARCOURS':
        return 'fi-rr-time-forward';
      case 'PLAN_REVISE':
        return 'fi-rr-refresh';
      default:
        return 'fi-rr-document';
    }
  }

  getStatusClass(item: PlanVersionChainItem): string {
    const classes: Record<string, string> = {
      draft: 'status-warning',
      valide: 'status-success',
      etendu: 'status-info',
      archive: 'status-neutre',
    };
    return classes[item.statut] || '';
  }
}
