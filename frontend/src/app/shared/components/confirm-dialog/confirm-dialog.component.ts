/**
 * Composant de dialogue de confirmation réutilisable.
 *
 * Supporte une liste d'impact pour les suppressions en cascade (revue design Amandine) :
 * passer `impactList` pour afficher explicitement les entités qui seront supprimées.
 */
import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';

export interface CascadeImpactGroup {
  /** Nom du type d'entité au pluriel (ex: "Pressions", "Objectifs à long terme") */
  label: string;
  /** Nombre d'entités impactées de ce type */
  count: number;
  /** Icône Flaticon (ex: "fi-rr-mountains") */
  icon?: string;
}

export interface ConfirmDialogData {
  title: string;
  message: string;
  /** Liste structurée des entités qui seront supprimées en cascade */
  impactList?: CascadeImpactGroup[];
  /** Texte d'avertissement complémentaire (ex: "Cette action est irréversible") */
  warningText?: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: 'primary' | 'accent' | 'warn';
  /** Variante destructive : icône d'alerte + couleur rouge */
  destructive?: boolean;
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
    <h2 mat-dialog-title>
      @if (data.destructive) {
        <i class="fi fi-rr-exclamation title-icon"></i>
      }
      {{ data.title }}
    </h2>
    <mat-dialog-content>
      <p class="message">{{ data.message }}</p>

      @if (data.impactList && data.impactList.length > 0) {
        <div class="impact-block">
          <p class="impact-title">{{ 'common.cascadeDelete.impactTitle' | translate }}</p>
          <ul class="impact-list">
            @for (group of data.impactList; track group.label) {
              <li class="impact-item">
                @if (group.icon) {
                  <i class="fi" [class]="group.icon"></i>
                }
                <span class="impact-count">{{ group.count }}</span>
                <span class="impact-label">{{ group.label }}</span>
              </li>
            }
          </ul>
        </div>
      }

      @if (data.warningText) {
        <p class="warning-text">
          <i class="fi fi-rr-triangle-warning"></i>
          {{ data.warningText }}
        </p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="onCancel()">
        {{ data.cancelText || ('common.actions.cancel' | translate) }}
      </button>
      <button mat-flat-button
              [color]="data.confirmColor || (data.destructive ? 'warn' : 'primary')"
              (click)="onConfirm()">
        {{ data.confirmText || ('common.actions.confirm' | translate) }}
      </button>
    </mat-dialog-actions>
  `,
  styleUrl: './confirm-dialog.component.scss'
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
