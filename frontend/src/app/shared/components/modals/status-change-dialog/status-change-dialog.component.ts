import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { PlanStatut } from '../../../../core/models/admin.model';

export interface StatusChangeDialogData {
  planId: number;
  planName: string;
  currentStatus: PlanStatut;
  period: string;
  isSuperAdmin: boolean;
}

export interface StatusChangeDialogResult {
  action: 'change_status' | 'create_evaluation' | 'cancel';
  newStatus?: PlanStatut;
}

interface StatusAction {
  action: 'change_status' | 'create_evaluation';
  label: string;
  description: string;
  icon: string;
  colorClass: string;
  newStatus?: PlanStatut;
}

@Component({
  selector: 'app-status-change-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatChipsModule,
    TranslateModule,
  ],
  templateUrl: './status-change-dialog.component.html',
  styleUrl: './status-change-dialog.component.scss',
})
export class StatusChangeDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<StatusChangeDialogComponent>);
  readonly data: StatusChangeDialogData = inject(MAT_DIALOG_DATA);
  private readonly translate = inject(TranslateService);

  get availableActions(): StatusAction[] {
    const actions: StatusAction[] = [];

    switch (this.data.currentStatus) {
      case 'draft':
        actions.push({
          action: 'change_status',
          label: this.translate.instant('plans.lifecycle.actions.validate'),
          description: this.translate.instant('plans.lifecycle.actions.validateDesc'),
          icon: 'fi-rr-check',
          colorClass: 'action-success',
          newStatus: 'valide',
        });
        break;

      case 'valide':
        actions.push({
          action: 'change_status',
          label: this.translate.instant('plans.lifecycle.actions.toDraft'),
          description: this.translate.instant('plans.lifecycle.actions.toDraftDesc'),
          icon: 'fi-rr-undo',
          colorClass: 'action-warning',
          newStatus: 'draft',
        });
        actions.push({
          action: 'change_status',
          label: this.translate.instant('plans.lifecycle.actions.archive'),
          description: this.translate.instant('plans.lifecycle.actions.archiveDesc'),
          icon: 'fi-rr-box',
          colorClass: 'action-neutral',
          newStatus: 'archive',
        });
        actions.push({
          action: 'create_evaluation',
          label: this.translate.instant('plans.lifecycle.actions.createEvaluation'),
          description: this.translate.instant('plans.lifecycle.actions.createEvaluationDesc'),
          icon: 'fi-rr-time-forward',
          colorClass: 'action-terra-cotta',
        });
        break;

      case 'archive':
        actions.push({
          action: 'change_status',
          label: this.translate.instant('plans.lifecycle.actions.reactivate'),
          description: this.translate.instant('plans.lifecycle.actions.reactivateHint'),
          icon: 'fi-rr-undo',
          colorClass: 'action-success',
          newStatus: 'valide',
        });
        break;
    }

    return actions;
  }

  get statusLabel(): string {
    return this.translate.instant(`plans.status.${this.data.currentStatus}`);
  }

  get statusClass(): string {
    const classes: Record<string, string> = {
      draft: 'status-warning',
      valide: 'status-success',
      archive: 'status-neutre',
    };
    return classes[this.data.currentStatus] || '';
  }

  selectAction(action: StatusAction): void {
    this.dialogRef.close({
      action: action.action,
      newStatus: action.newStatus,
    } as StatusChangeDialogResult);
  }

  cancel(): void {
    this.dialogRef.close({ action: 'cancel' } as StatusChangeDialogResult);
  }
}
