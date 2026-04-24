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
import { forkJoin } from 'rxjs';
import { ValidationService } from '../../../core/services/validation.service';

export interface SelectableSite {
  id_site: number;
  slug: string;
  nom_site: string;
}

export interface AccessRequestDialogData {
  type: 'site' | 'plan';
  // Mode 1: Site/Plan unique (existant)
  targetId?: number;  // Utilisé pour les plans
  targetSlug?: string;  // Utilisé pour les sites
  targetName?: string;
  // Mode 2: Selection parmi une liste (nouveau)
  selectableSites?: SelectableSite[];
  // Mode plan: accès via site ou combiné
  hasAccessViaSite?: boolean;       // true = demande directe, false = besoin site
  sitesNeedingAccess?: SelectableSite[];  // Sites du plan où demander le lien
  // Mode site : demande personnelle (CorRoleSite) ou rattachement d'organisme (CorOgSite)
  siteMode?: 'personal' | 'organisme';
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
      @if (data.type === 'site' && isOrganismeMode) {
        {{ 'accessRequest.dialog.titleSiteOrg' | translate }}
      } @else if (data.type === 'site') {
        {{ 'accessRequest.dialog.titleSite' | translate }}
      } @else if (isCombinedPlanMode) {
        {{ 'accessRequest.dialog.titlePlanWithSite' | translate }}
      } @else {
        {{ 'accessRequest.dialog.titlePlan' | translate }}
      }
    </h2>

    <mat-dialog-content>
      <!-- Mode selection de sites (existant) -->
      @if (isSelectionMode) {
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ 'accessRequest.dialog.selectSite' | translate }}</mat-label>
          <mat-select [(ngModel)]="selectedSiteSlug" required>
            @for (site of data.selectableSites; track site.slug) {
              <mat-option [value]="site.slug">{{ site.nom_site }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
      } @else if (isCombinedPlanMode) {
        <!-- Mode combiné plan : besoin de lien site + accès plan -->
        <div class="target-info">
          <span class="target-label">{{ 'accessRequest.dialog.targetLabel' | translate }}</span>
          <span class="target-name">{{ data.targetName }}</span>
        </div>

        <div class="site-access-note">
          <i class="fi fi-rr-info"></i>
          <span>{{ 'accessRequest.dialog.siteAccessNote' | translate }}</span>
        </div>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ 'accessRequest.dialog.selectSiteForPlan' | translate }}</mat-label>
          <mat-select [(ngModel)]="selectedSiteSlug" required>
            @for (site of data.sitesNeedingAccess; track site.slug) {
              <mat-option [value]="site.slug">{{ site.nom_site }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
      } @else {
        <!-- Mode direct : site unique ou plan direct -->
        <div class="target-info">
          <span class="target-label">{{ 'accessRequest.dialog.targetLabel' | translate }}</span>
          <span class="target-name">{{ data.targetName }}</span>
        </div>

        @if (data.type === 'site' && isOrganismeMode) {
          <div class="site-access-note">
            <i class="fi fi-rr-info"></i>
            <span>{{ 'accessRequest.dialog.siteOrgNote' | translate }}</span>
          </div>
        }
      }

      @if (data.type === 'plan') {
        <div class="role-choice">
          <label class="role-label">{{ 'accessRequest.dialog.roleLabel' | translate }}</label>
          <div class="role-options">
            <label class="role-option" [class.selected]="!requestAsReferent">
              <input type="radio" name="role" [value]="false" [(ngModel)]="requestAsReferent">
              <div class="role-option-content">
                <span class="role-option-title">{{ 'accessRequest.dialog.roleMember' | translate }}</span>
                <span class="role-option-desc">{{ 'accessRequest.dialog.roleMemberDesc' | translate }}</span>
              </div>
            </label>
            <label class="role-option" [class.selected]="requestAsReferent">
              <input type="radio" name="role" [value]="true" [(ngModel)]="requestAsReferent">
              <div class="role-option-content">
                <span class="role-option-title">{{ 'accessRequest.dialog.roleReferent' | translate }}</span>
                <span class="role-option-desc">{{ 'accessRequest.dialog.roleReferentDesc' | translate }}</span>
              </div>
            </label>
          </div>
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

    .site-access-note {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 16px;
      padding: 12px 16px;
      background-color: #FFF8E1;
      border-radius: 8px;
      font-family: 'Nunito', sans-serif;
      font-size: 13px;
      color: #343433;
      line-height: 1.4;
    }

    .site-access-note i {
      color: #FA9965;
      margin-top: 2px;
      flex-shrink: 0;
    }

    mat-dialog-actions button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .role-choice {
      margin-bottom: 16px;
    }

    .role-label {
      display: block;
      font-family: 'Nunito', sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: #343433;
      margin-bottom: 8px;
    }

    .role-options {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .role-option {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px 16px;
      border: 1px solid #E0E0E0;
      border-radius: 8px;
      cursor: pointer;
      transition: border-color 0.2s, background-color 0.2s;
    }

    .role-option:hover {
      border-color: #025359;
    }

    .role-option.selected {
      border-color: #025359;
      background-color: #F0F7F7;
    }

    .role-option input[type="radio"] {
      margin-top: 2px;
      accent-color: #025359;
    }

    .role-option-content {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .role-option-title {
      font-family: 'Nunito', sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: #343433;
    }

    .role-option-desc {
      font-family: 'Nunito', sans-serif;
      font-size: 12px;
      color: #746F6E;
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
  selectedSiteSlug: string | null = null;
  requestAsReferent = false;

  /** Verifie si on est en mode selection de sites (existant) */
  get isSelectionMode(): boolean {
    return !!(this.data.selectableSites && this.data.selectableSites.length > 0);
  }

  /** Verifie si on est en mode combine plan (besoin site + plan) */
  get isCombinedPlanMode(): boolean {
    return this.data.type === 'plan' &&
           this.data.hasAccessViaSite === false &&
           !!(this.data.sitesNeedingAccess && this.data.sitesNeedingAccess.length > 0);
  }

  /** Mode de demande site : rattachement d'organisme (CorOgSite) vs personnel (CorRoleSite). */
  get isOrganismeMode(): boolean {
    return this.data.type === 'site' && this.data.siteMode === 'organisme';
  }

  /** Verifie si le formulaire peut etre soumis */
  get canSubmit(): boolean {
    if (this.isSelectionMode) {
      return this.selectedSiteSlug !== null;
    }
    if (this.isCombinedPlanMode) {
      return this.selectedSiteSlug !== null;
    }
    if (this.data.type === 'site') {
      return this.data.targetSlug !== undefined;
    }
    return this.data.targetId !== undefined;
  }

  /** Obtient le slug cible pour les sites (soit de la selection, soit du data) */
  private getTargetSlug(): string {
    if (this.isSelectionMode && this.selectedSiteSlug !== null) {
      return this.selectedSiteSlug;
    }
    return this.data.targetSlug!;
  }

  submit(): void {
    if (!this.canSubmit) return;

    this.submitting = true;

    const requestData = this.justification ? { justification: this.justification } : undefined;

    if (this.data.type === 'plan') {
      const planRequestData = {
        ...(requestData || {}),
        request_as_referent: this.requestAsReferent,
      };
      if (this.isCombinedPlanMode) {
        // Cas 2 : Demande site + plan en parallele
        forkJoin({
          siteRequest: this.validationService.requestSiteAccess(this.selectedSiteSlug!, requestData),
          planRequest: this.validationService.requestPlanAccess(this.data.targetId!, planRequestData)
        }).subscribe({
          next: () => this.onSuccess('accessRequest.successBoth'),
          error: (e) => this.onError(e)
        });
      } else {
        // Cas 1 : Demande directe plan uniquement
        this.validationService.requestPlanAccess(this.data.targetId!, planRequestData)
          .subscribe({
            next: () => this.onSuccess('accessRequest.success'),
            error: (e) => this.onError(e)
          });
      }
    } else {
      // Sites (existant)
      const slug = this.getTargetSlug();
      const obs = this.isOrganismeMode
        ? this.validationService.requestSiteOrgLink(slug, requestData)
        : this.validationService.requestSiteAccess(slug, requestData);
      obs.subscribe({
        next: () => this.onSuccess('accessRequest.success'),
        error: (e) => this.onError(e)
      });
    }
  }

  private onSuccess(messageKey: string): void {
    this.snackBar.open(
      this.translate.instant(messageKey),
      this.translate.instant('common.actions.close'),
      { duration: 5000 }
    );
    this.dialogRef.close(true);
  }

  private onError(error: any): void {
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
}
