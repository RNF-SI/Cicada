/**
 * Dialog reutilisable pour les demandes d'acces aux sites et plans de gestion.
 * Supporte deux modes:
 * - Mode site unique: targetId et targetName fournis
 * - Mode selection: selectableSites fournis (liste de sites a choisir)
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ValidationService } from '../../../core/services/validation.service';

export interface SelectableSite {
  id_site: number;
  nom_site: string;
}

export interface AccessRequestDialogData {
  type: 'site' | 'plan';
  // Mode 1: Site/Plan unique (existant)
  targetId?: number;
  targetName?: string;
  // Mode 2: Selection parmi une liste (nouveau)
  selectableSites?: SelectableSite[];
}

@Component({
  selector: 'app-access-request-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    TranslateModule
  ],
  template: `
    <h2 mat-dialog-title>
      @if (data.type === 'site') {
        {{ 'accessRequest.dialog.titleSite' | translate }}
      } @else {
        {{ 'accessRequest.dialog.titlePlan' | translate }}
      }
    </h2>

    <mat-dialog-content>
      <!-- Mode selection: liste de sites -->
      @if (isSelectionMode) {
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ 'accessRequest.dialog.selectSite' | translate }}</mat-label>
          <mat-select [(ngModel)]="selectedSiteId" required>
            @for (site of data.selectableSites; track site.id_site) {
              <mat-option [value]="site.id_site">{{ site.nom_site }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
      } @else {
        <!-- Mode site unique -->
        <div class="target-info">
          <span class="target-label">{{ 'accessRequest.dialog.targetLabel' | translate }}</span>
          <span class="target-name">{{ data.targetName }}</span>
        </div>
      }

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>{{ 'accessRequest.dialog.justificationLabel' | translate }}</mat-label>
        <textarea
          matInput
          [(ngModel)]="justification"
          [placeholder]="'accessRequest.dialog.justificationPlaceholder' | translate"
          rows="4"
        ></textarea>
        <mat-hint>{{ 'accessRequest.dialog.justificationHint' | translate }}</mat-hint>
      </mat-form-field>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close [disabled]="submitting">
        {{ 'accessRequest.dialog.cancel' | translate }}
      </button>
      <button
        mat-flat-button
        color="primary"
        (click)="submit()"
        [disabled]="submitting || !canSubmit"
      >
        @if (submitting) {
          <mat-spinner diameter="20"></mat-spinner>
        } @else {
          {{ 'accessRequest.dialog.submit' | translate }}
        }
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .target-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 24px;
      padding: 16px;
      background-color: #F8F5F1;
      border-radius: 8px;
    }

    .target-label {
      font-family: 'Nunito', sans-serif;
      font-size: 12px;
      font-weight: 600;
      color: #949494;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .target-name {
      font-family: 'Nunito', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #025359;
    }

    .full-width {
      width: 100%;
    }

    mat-dialog-content {
      min-width: 400px;
    }

    mat-dialog-actions button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
  `]
})
export class AccessRequestDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<AccessRequestDialogComponent>);
  readonly data: AccessRequestDialogData = inject(MAT_DIALOG_DATA);
  private readonly validationService = inject(ValidationService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  justification = '';
  submitting = false;
  selectedSiteId: number | null = null;

  /** Verifie si on est en mode selection */
  get isSelectionMode(): boolean {
    return !!(this.data.selectableSites && this.data.selectableSites.length > 0);
  }

  /** Verifie si le formulaire peut etre soumis */
  get canSubmit(): boolean {
    if (this.isSelectionMode) {
      return this.selectedSiteId !== null;
    }
    return this.data.targetId !== undefined;
  }

  /** Obtient l'ID cible (soit de la selection, soit du data) */
  private getTargetId(): number {
    if (this.isSelectionMode && this.selectedSiteId !== null) {
      return this.selectedSiteId;
    }
    return this.data.targetId!;
  }

  submit(): void {
    if (!this.canSubmit) return;

    this.submitting = true;

    const requestData = this.justification ? { justification: this.justification } : undefined;
    const targetId = this.getTargetId();

    const request$ = this.data.type === 'site'
      ? this.validationService.requestSiteAccess(targetId, requestData)
      : this.validationService.requestPlanAccess(targetId, requestData);

    request$.subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('accessRequest.success'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        this.dialogRef.close(true);
      },
      error: (error) => {
        console.error('Erreur demande acces:', error);

        let errorMessage = this.translate.instant('accessRequest.error');
        if (error.status === 409 || error.error?.detail?.includes('deja')) {
          errorMessage = this.translate.instant('accessRequest.alreadyPending');
        }

        this.snackBar.open(
          errorMessage,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        this.submitting = false;
      }
    });
  }
}
