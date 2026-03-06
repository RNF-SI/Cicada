import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatChipsModule } from '@angular/material/chips';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem, PlanStatut } from '../../../core/models/admin.model';

@Component({
  selector: 'app-plan-version-timeline',
  standalone: true,
  imports: [CommonModule, RouterModule, MatChipsModule, TranslateModule],
  templateUrl: './plan-version-timeline.component.html',
  styleUrl: './plan-version-timeline.component.scss',
})
export class PlanVersionTimelineComponent {
  @Input() chain: PlanVersionChainItem[] = [];
  @Input() currentStatus: PlanStatut = 'draft';
  /** L'utilisateur peut gérer le cycle de vie (référent du plan, admin_og, super_admin) */
  @Input() canManage = false;

  @Output() statusChange = new EventEmitter<PlanStatut>();
  @Output() createEvaluation = new EventEmitter<void>();

  get visible(): boolean {
    return this.chain.length > 1;
  }

  /** Le plan courant est une évaluation mi-parcours (pas un plan initial/révisé) */
  get isEvaluation(): boolean {
    const current = this.chain.find(item => item.is_current);
    return current?.type_document_mnemonique === 'EVAL_MI_PARCOURS';
  }

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
      archive: 'status-neutre',
    };
    return classes[item.statut] || '';
  }

  getNodeClass(item: PlanVersionChainItem): string {
    const classes = ['timeline-node'];
    if (item.is_current) classes.push('current');
    classes.push(`node-${item.statut}`);
    return classes.join(' ');
  }

  onValidate(): void {
    this.statusChange.emit('valide');
  }

  onArchive(): void {
    this.statusChange.emit('archive');
  }

  onCreateEvaluation(): void {
    this.createEvaluation.emit();
  }

  onToDraft(): void {
    this.statusChange.emit('draft');
  }

  onReactivate(): void {
    this.statusChange.emit('valide');
  }
}
