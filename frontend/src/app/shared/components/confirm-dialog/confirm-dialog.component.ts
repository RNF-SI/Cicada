/**
 * Composant de dialogue de confirmation réutilisable.
 */
import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: 'primary' | 'accent' | 'warn';
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    TranslateModule
  ],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content>
      <p>{{ data.message }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="onCancel()">
        {{ data.cancelText || ('common.actions.cancel' | translate) }}
      </button>
      <button mat-flat-button
              [color]="data.confirmColor || 'primary'"
              (click)="onConfirm()">
        {{ data.confirmText || ('common.actions.confirm' | translate) }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2 {
      margin: 0;
      font-weight: 600;
    }

    mat-dialog-content {
      padding: 16px 0;

      p {
        margin: 0;
        color: #746F6E;
      }
    }

    mat-dialog-actions {
      padding-top: 16px;
      gap: 8px;
    }
  `]
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData
  ) {}

  onCancel(): void {
    this.dialogRef.close(false);
  }

  onConfirm(): void {
    this.dialogRef.close(true);
  }
}
