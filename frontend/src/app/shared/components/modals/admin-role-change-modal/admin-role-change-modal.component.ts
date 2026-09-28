import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormFieldComponent } from '../../form-field/form-field.component';

export type AdminRoleChangeType = 'promotion' | 'demotion';

export interface AdminRoleChangeModalData {
  type: AdminRoleChangeType;
  userName: string;
  userEmail: string;
  /**
   * Changement appliqué immédiatement (#655) : le super administrateur est le
   * validateur final, il n'a pas de demande à déposer. Le motif devient alors
   * facultatif.
   */
  direct?: boolean;
}

export interface AdminRoleChangeModalResult {
  confirmed: boolean;
  justification?: string;
}

@Component({
  selector: 'app-admin-role-change-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './admin-role-change-modal.component.html',
  styleUrl: './admin-role-change-modal.component.scss'
})
export class AdminRoleChangeModalComponent {
  private readonly dialogRef = inject(MatDialogRef<AdminRoleChangeModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<AdminRoleChangeModalData>(MAT_DIALOG_DATA);

  justification = '';
  errorMessage = signal<string | null>(null);

  get isPromotion(): boolean {
    return this.data.type === 'promotion';
  }

  /** Le super administrateur applique le changement, il ne le demande pas (#655). */
  get isDirect(): boolean {
    return this.data.direct === true;
  }

  get titleKey(): string {
    const base = this.isPromotion
      ? 'modals.adminRoleChange.promotion.title'
      : 'modals.adminRoleChange.demotion.title';
    return this.isDirect ? `${base}Direct` : base;
  }

  get noticeKey(): string {
    return this.isDirect
      ? 'modals.adminRoleChange.directNotice'
      : 'modals.adminRoleChange.superAdminNotice';
  }

  get justificationHintKey(): string {
    return this.isDirect
      ? 'modals.adminRoleChange.justification.hintOptional'
      : 'modals.adminRoleChange.justification.hint';
  }

  get warningMessageKey(): string {
    return this.isPromotion
      ? 'modals.adminRoleChange.promotion.warning'
      : 'modals.adminRoleChange.demotion.warning';
  }

  get confirmButtonKey(): string {
    const base = this.isPromotion
      ? 'modals.adminRoleChange.promotion.confirm'
      : 'modals.adminRoleChange.demotion.confirm';
    return this.isDirect ? `${base}Direct` : base;
  }

  get isValid(): boolean {
    if (this.isDirect) return true; // motif facultatif (#655)
    return this.justification.trim().length >= 10; // Minimum 10 characters
  }

  onConfirm(): void {
    if (!this.isValid) {
      this.errorMessage.set(this.translate.instant('modals.adminRoleChange.validation.minLength'));
      return;
    }

    this.dialogRef.close({
      confirmed: true,
      justification: this.justification.trim()
    } as AdminRoleChangeModalResult);
  }

  onCancel(): void {
    this.dialogRef.close({ confirmed: false } as AdminRoleChangeModalResult);
  }
}
