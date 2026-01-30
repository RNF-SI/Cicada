/**
 * Dialog pour afficher le detail d'une demande de validation.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';

import { ValidationService } from '../../../core/services/validation.service';
import { ValidationRequest, ValidationStatus, ValidationRequestType } from '../../../core/models/notification.model';

interface DialogData {
  validationId: number;
}

@Component({
  selector: 'app-validation-detail-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslateModule
  ],
  template: `
    <h2 mat-dialog-title>
      <i class="fi" [ngClass]="getTypeIcon(validation()?.request_type)"></i>
      Detail de la demande
    </h2>

    <mat-dialog-content>
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (validation()) {
        <div class="detail-content">
          <!-- Type et statut -->
          <div class="detail-row">
            <span class="detail-label">Type</span>
            <span class="detail-value">
              <span class="type-badge">
                <i class="fi" [ngClass]="getTypeIcon(validation()!.request_type)"></i>
                {{ validation()!.request_type_display }}
              </span>
            </span>
          </div>

          <div class="detail-row">
            <span class="detail-label">Statut</span>
            <span class="detail-value">
              <mat-chip [ngClass]="getStatusClass(validation()!.status)">
                {{ validation()!.status_display }}
              </mat-chip>
            </span>
          </div>

          <!-- Demandeur -->
          @if (validation()!.requester) {
            <div class="detail-row">
              <span class="detail-label">Demandeur</span>
              <span class="detail-value">
                {{ validation()!.requester!.nom_complet }}
                <span class="email">({{ validation()!.requester!.email }})</span>
              </span>
            </div>
          }

          <!-- Cible selon le type -->
          @if (validation()!.target_site) {
            <div class="detail-row">
              <span class="detail-label">Site</span>
              <span class="detail-value">{{ validation()!.target_site!.nom_site }}</span>
            </div>
          }

          <!-- Avertissement pour les demandes de creation de site -->
          @if (validation()!.request_type === 'site_creation') {
            <div class="duplicate-warning">
              <i class="fi fi-rr-exclamation-triangle"></i>
              <span>{{ 'admin.validations.warnings.checkDuplicateSite' | translate }}</span>
            </div>
          }

          @if (validation()!.target_plan) {
            <div class="detail-row">
              <span class="detail-label">Plan</span>
              <span class="detail-value">{{ validation()!.target_plan!.nom }}</span>
            </div>
          }

          @if (validation()!.target_user) {
            <div class="detail-row">
              <span class="detail-label">Utilisateur cible</span>
              <span class="detail-value">
                {{ validation()!.target_user!.nom_complet }}
                <span class="email">({{ validation()!.target_user!.email }})</span>
              </span>
            </div>
          }

          @if (validation()!.requested_organisme) {
            <div class="detail-row">
              <span class="detail-label">Organisme demande</span>
              <span class="detail-value">{{ validation()!.requested_organisme!.nom_organisme }}</span>
            </div>
          }

          <!-- Justification -->
          @if (validation()!.justification) {
            <div class="detail-row full-width">
              <span class="detail-label">Justification</span>
              <span class="detail-value justification">{{ validation()!.justification }}</span>
            </div>
          }

          <!-- Dates -->
          <div class="detail-row">
            <span class="detail-label">Date de demande</span>
            <span class="detail-value">{{ formatDate(validation()!.created_at) }}</span>
          </div>

          @if (validation()!.validated_at) {
            <div class="detail-row">
              <span class="detail-label">Date de traitement</span>
              <span class="detail-value">{{ formatDate(validation()!.validated_at!) }}</span>
            </div>
          }

          @if (validation()!.validator) {
            <div class="detail-row">
              <span class="detail-label">Traite par</span>
              <span class="detail-value">
                {{ validation()!.validator!.nom_complet }}
              </span>
            </div>
          }

          @if (validation()!.validation_comment) {
            <div class="detail-row full-width">
              <span class="detail-label">Commentaire</span>
              <span class="detail-value justification">{{ validation()!.validation_comment }}</span>
            </div>
          }

          <!-- Info sur la demande de référent -->
          @if (showApproveAsUserOption()) {
            <div class="referent-request-info">
              <i class="fi fi-rr-info"></i>
              <div class="info-content">
                <strong>Demande :</strong> souhaite devenir <strong>referent</strong> du site
              </div>
            </div>
          }

          <!-- Avertissement: site_access bloqué par site_org_link -->
          @if (validation()!.blocked_by_org_link) {
            <div class="blocked-warning">
              <i class="fi fi-rr-exclamation-triangle"></i>
              <span>{{ 'admin.validations.warnings.blockedByOrgLink' | translate }}</span>
            </div>
          }

          <!-- Formulaire action si en attente -->
          @if (validation()!.status === 'pending' && !actionSuccess()) {
            <div class="action-section">
              <h3>Traiter la demande</h3>

              @if (processing()) {
                <div class="processing-overlay">
                  <mat-spinner diameter="32"></mat-spinner>
                  <span>Traitement en cours...</span>
                </div>
              } @else {
                <mat-form-field appearance="outline" class="comment-field">
                  <mat-label>Commentaire (optionnel pour approbation, requis pour rejet)</mat-label>
                  <textarea
                    matInput
                    [(ngModel)]="comment"
                    rows="3"
                    placeholder="Ajoutez un commentaire..."
                  ></textarea>
                </mat-form-field>

                <div class="action-buttons">
                  @if (showApproveAsUserOption()) {
                    <!-- Demande avec demande de référent: deux options d'approbation -->
                    <button
                      mat-raised-button
                      color="primary"
                      (click)="approveWithReferent(true)"
                      [disabled]="processing() || validation()!.blocked_by_org_link"
                    >
                      <i class="fi fi-rr-user-check"></i>
                      Approuver (référent)
                    </button>
                    <button
                      mat-stroked-button
                      (click)="approveWithReferent(false)"
                      [disabled]="processing() || validation()!.blocked_by_org_link"
                    >
                      <i class="fi fi-rr-user"></i>
                      Approuver (utilisateur)
                    </button>
                  } @else {
                    <!-- Demande standard: un seul bouton d'approbation -->
                    <button
                      mat-raised-button
                      color="primary"
                      (click)="approve()"
                      [disabled]="processing() || validation()!.blocked_by_org_link"
                    >
                      <i class="fi fi-rr-check"></i>
                      Approuver
                    </button>
                  }
                  <button
                    mat-raised-button
                    color="warn"
                    (click)="reject()"
                    [disabled]="processing() || !comment.trim()"
                    matTooltip="Un commentaire est requis pour rejeter une demande"
                  >
                    <i class="fi fi-rr-cross"></i>
                    Rejeter
                  </button>
                </div>
              }
            </div>
          }

          <!-- Message de succes -->
          @if (actionSuccess()) {
            <div class="success-message">
              <i class="fi fi-rr-check-circle"></i>
              <span>{{ actionSuccess() }}</span>
            </div>
          }
        </div>
      } @else {
        <div class="error-state">
          <i class="fi fi-rr-exclamation error-icon"></i>
          <p>Impossible de charger les details de cette demande.</p>
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="close()">Fermer</button>
    </mat-dialog-actions>
  `,
  styles: [`
    @use '../admin-validations.component.scss' as v;

    h2 {
      display: flex;
      align-items: center;
      gap: 12px;

      i {
        font-size: 20px;
        color: v.$primary-color;
      }
    }

    mat-dialog-content {
      min-width: 420px;
      max-height: 65vh;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .detail-content {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .detail-row {
      display: flex;
      align-items: flex-start;

      &.full-width {
        flex-direction: column;
        gap: 8px;
      }

      .detail-label {
        flex: 0 0 150px;
        font-weight: 600;
        color: #666;
      }

      .detail-value {
        flex: 1;

        .email {
          color: v.$gray;
          font-size: 13px;
        }

        &.justification {
          background: v.$gray-light;
          padding: 6px 10px;
          border-radius: 6px;
          white-space: pre-wrap;
          font-size: 12px;
          max-height: 50px;
          overflow-y: auto;
        }
      }
    }

    .type-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      background-color: v.$gray-light;
      border-radius: 4px;
      font-size: 13px;

      i {
        font-size: 14px;
        color: v.$primary-color;
      }
    }

    .action-section {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid v.$gray-light;

      h3 {
        margin: 0 0 12px 0;
        font-size: 15px;
        color: v.$primary-color;
      }

      .comment-field {
        width: 100%;
      }

      .action-buttons {
        display: flex;
        gap: 12px;

        button {
          display: flex;
          align-items: center;
          gap: 8px;

          i {
            font-size: 14px;
          }
        }
      }

      .processing-overlay {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        padding: 32px;
        background: rgba(v.$primary-color, 0.05);
        border-radius: 8px;

        span {
          color: v.$primary-color;
          font-weight: 500;
        }
      }
    }

    .success-message {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 24px;
      margin-top: 24px;
      background: rgba(v.$success-color, 0.1);
      border: 1px solid rgba(v.$success-color, 0.3);
      border-radius: 8px;
      color: v.$success-color;

      i {
        font-size: 24px;
      }

      span {
        font-size: 16px;
        font-weight: 600;
      }
    }

    .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      text-align: center;

      .error-icon {
        font-size: 48px;
        color: v.$error-color;
        margin-bottom: 16px;
      }

      p {
        color: v.$gray;
      }
    }

    // Status classes from parent
    .status-success {
      background-color: rgba(v.$success-color, 0.15) !important;
      color: v.$success-color !important;
    }

    .status-error {
      background-color: rgba(v.$error-color, 0.15) !important;
      color: v.$error-color !important;
    }

    .status-warning {
      background-color: rgba(v.$warning-color, 0.15) !important;
      color: darken(v.$warning-color, 15%) !important;
    }

    .status-neutre {
      background-color: v.$gray-light !important;
      color: v.$gray !important;
    }

    .referent-request-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      margin-top: 8px;
      background: rgba(v.$info-color, 0.1);
      border: 1px solid rgba(v.$info-color, 0.3);
      border-radius: 6px;
      font-size: 13px;

      > i {
        font-size: 16px;
        color: v.$info-color;
        flex-shrink: 0;
      }

      .info-content {
        strong {
          color: v.$primary-color;
        }
      }
    }

    .blocked-warning {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 12px 14px;
      margin-top: 8px;
      background: rgba(v.$warning-color, 0.12);
      border: 1px solid rgba(v.$warning-color, 0.4);
      border-radius: 6px;
      font-size: 14px;
      line-height: 1.5;

      > i {
        font-size: 18px;
        color: darken(v.$warning-color, 10%);
        flex-shrink: 0;
        margin-top: 2px;
      }

      > span {
        color: darken(v.$warning-color, 20%);
        font-weight: 700;
      }
    }

    .duplicate-warning {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 10px 12px;
      margin-top: 8px;
      background: rgba(v.$warning-color, 0.12);
      border: 1px solid rgba(v.$warning-color, 0.4);
      border-radius: 6px;
      font-size: 12px;
      line-height: 1.4;

      > i {
        font-size: 16px;
        color: darken(v.$warning-color, 10%);
        flex-shrink: 0;
      }

      > span {
        color: darken(v.$warning-color, 20%);
        font-weight: 500;
      }
    }
  `]
})
export class ValidationDetailDialogComponent implements OnInit {
  private readonly validationService = inject(ValidationService);
  private readonly dialogRef = inject(MatDialogRef<ValidationDetailDialogComponent>);
  private readonly data: DialogData = inject(MAT_DIALOG_DATA);
  private readonly snackBar = inject(MatSnackBar);

  readonly loading = signal(false);
  readonly processing = signal(false);
  readonly validation = signal<ValidationRequest | null>(null);
  readonly actionSuccess = signal<string | null>(null);

  comment = '';

  ngOnInit(): void {
    this.loadValidation();
  }

  /**
   * Charge les details de la demande.
   */
  loadValidation(): void {
    this.loading.set(true);

    this.validationService.getValidationRequest(this.data.validationId).subscribe({
      next: (validation: ValidationRequest) => {
        this.validation.set(validation);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        console.error('Erreur chargement validation:', error);
        this.loading.set(false);
      }
    });
  }

  /**
   * Vérifie si l'option d'approbation avec choix référent/utilisateur doit être affichée.
   * Affiche les deux boutons si c'est une demande de création ou d'accès site avec request_as_referent=true.
   */
  showApproveAsUserOption(): boolean {
    const v = this.validation();
    if (!v) return false;
    // Afficher l'option si c'est une demande de création ou d'accès site avec request_as_referent
    return (v.request_type === 'site_creation' || v.request_type === 'site_access')
           && v.request_as_referent === true;
  }

  /**
   * Approuve la demande (version standard sans choix de référent).
   */
  approve(): void {
    this.processing.set(true);

    const data = this.comment ? { comment: this.comment } : undefined;

    this.validationService.approveRequest(this.data.validationId, data).subscribe({
      next: () => {
        this.processing.set(false);
        this.actionSuccess.set('Demande approuvee avec succes !');
        // Fermer le dialog apres un court delai pour montrer le succes
        setTimeout(() => {
          this.dialogRef.close(true);
        }, 1500);
      },
      error: (error: { error?: { error?: string } }) => {
        this.snackBar.open(error.error?.error || 'Erreur lors de l\'approbation', 'Fermer', {
          duration: 5000
        });
        this.processing.set(false);
      }
    });
  }

  /**
   * Approuve la demande avec choix explicite du statut référent.
   * @param asReferent true pour approuver comme référent, false pour utilisateur simple
   */
  approveWithReferent(asReferent: boolean): void {
    this.processing.set(true);

    const data: { comment?: string; approve_as_referent?: boolean } = {};
    if (this.comment) data.comment = this.comment;
    data.approve_as_referent = asReferent;

    this.validationService.approveRequest(this.data.validationId, data).subscribe({
      next: () => {
        this.processing.set(false);
        const roleText = asReferent ? 'comme référent' : 'comme utilisateur';
        this.actionSuccess.set(`Demande approuvee ${roleText} !`);
        // Fermer le dialog apres un court delai pour montrer le succes
        setTimeout(() => {
          this.dialogRef.close(true);
        }, 1500);
      },
      error: (error: { error?: { error?: string } }) => {
        this.snackBar.open(error.error?.error || 'Erreur lors de l\'approbation', 'Fermer', {
          duration: 5000
        });
        this.processing.set(false);
      }
    });
  }

  /**
   * Rejette la demande.
   */
  reject(): void {
    if (!this.comment.trim()) {
      this.snackBar.open('Un commentaire est requis pour rejeter une demande', 'OK', {
        duration: 3000
      });
      return;
    }

    this.processing.set(true);

    this.validationService.rejectRequest(this.data.validationId, { comment: this.comment }).subscribe({
      next: () => {
        this.processing.set(false);
        this.actionSuccess.set('Demande rejetee.');
        // Fermer le dialog apres un court delai pour montrer le succes
        setTimeout(() => {
          this.dialogRef.close(true);
        }, 1500);
      },
      error: (error: { error?: { error?: string } }) => {
        this.snackBar.open(error.error?.error || 'Erreur lors du rejet', 'Fermer', {
          duration: 5000
        });
        this.processing.set(false);
      }
    });
  }

  /**
   * Ferme le dialog. Renvoie true si une action a ete effectuee pour rafraichir la liste.
   */
  close(): void {
    this.dialogRef.close(!!this.actionSuccess());
  }

  /**
   * Obtient la classe CSS du statut.
   */
  getStatusClass(status: ValidationStatus): string {
    const classes: Record<string, string> = {
      'pending': 'status-warning',
      'approved': 'status-success',
      'rejected': 'status-error',
      'cancelled': 'status-neutre',
      'expired': 'status-neutre',
    };
    return classes[status] || 'status-neutre';
  }

  /**
   * Obtient l'icone du type de demande.
   */
  getTypeIcon(type?: ValidationRequestType): string {
    if (!type) return 'fi-rr-check-circle';

    const icons: Record<string, string> = {
      'user_registration': 'fi-rr-user-add',
      'site_creation': 'fi-rr-marker-plus',
      'site_access': 'fi-rr-marker',
      'plan_access': 'fi-rr-document',
      'module_access': 'fi-rr-apps',
      'admin_deactivation': 'fi-rr-user-slash',
      'admin_promotion': 'fi-rr-user-crown',
      'admin_demotion': 'fi-rr-user-minus',
      'referent_validation': 'fi-rr-badge-check',
      'site_org_link': 'fi-rr-link',
      'invite_org_to_site': 'fi-rr-building',
      'invite_user_to_site': 'fi-rr-user-add',
    };
    return icons[type] || 'fi-rr-check-circle';
  }

  /**
   * Formate la date.
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
