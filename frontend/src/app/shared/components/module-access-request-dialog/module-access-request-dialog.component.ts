/**
 * Dialog pour demander l'acces a un module.
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ValidationService } from '../../../core/services/validation.service';
import { ModuleCode } from '../../../core/models/notification.model';

export interface ModuleAccessRequestDialogData {
  moduleCode: ModuleCode;
  moduleName: string;
}

@Component({
  selector: 'app-module-access-request-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
    TranslateModule
  ],
  template: `
    <h2 mat-dialog-title>
      <i class="fi fi-rr-lock title-icon"></i>
      {{ 'moduleAccess.dialog.title' | translate }}
    </h2>

    <mat-dialog-content>
      <div class="module-info">
        <span class="module-label">{{ 'moduleAccess.dialog.moduleLabel' | translate }}</span>
        <span class="module-name">{{ data.moduleName }}</span>
      </div>

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>{{ 'moduleAccess.dialog.justificationLabel' | translate }}</mat-label>
        <textarea
          matInput
          [(ngModel)]="justification"
          [placeholder]="'moduleAccess.dialog.justificationPlaceholder' | translate"
          rows="4"
        ></textarea>
        <mat-hint>{{ 'moduleAccess.dialog.justificationHint' | translate }}</mat-hint>
      </mat-form-field>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>
        {{ 'common.actions.cancel' | translate }}
      </button>
      <button
        mat-flat-button
        color="primary"
        [disabled]="submitting"
        (click)="submit()"
      >
        @if (submitting) {
          <span>{{ 'common.loading' | translate }}</span>
        } @else {
          <i class="fi fi-rr-paper-plane"></i>
          <span>{{ 'moduleAccess.dialog.submit' | translate }}</span>
        }
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .title-icon {
      margin-right: 8px;
      color: #025359;
    }

    .module-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 12px 16px;
      background-color: #F8F5F1;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .module-label {
      font-size: 12px;
      color: #746F6E;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .module-name {
      font-size: 16px;
      font-weight: 600;
      color: #025359;
    }

    .full-width {
      width: 100%;
    }

    mat-dialog-actions button {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
  `]
})
export class ModuleAccessRequestDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<ModuleAccessRequestDialogComponent>);
  readonly data = inject<ModuleAccessRequestDialogData>(MAT_DIALOG_DATA);
  private readonly validationService = inject(ValidationService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  justification = '';
  submitting = false;

  submit(): void {
    this.submitting = true;

    this.validationService.requestModuleAccess({
      module_code: this.data.moduleCode,
      justification: this.justification || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('moduleAccess.success'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.dialogRef.close(true);
      },
      error: (error) => {
        console.error('Erreur demande acces module:', error);
        const message = error.error?.detail || this.translate.instant('moduleAccess.error');
        this.snackBar.open(
          message,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        this.submitting = false;
      }
    });
  }
}
