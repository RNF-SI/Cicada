import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

export type AdminRoleChangeType = 'promotion' | 'demotion';

export interface AdminRoleChangeModalData {
  type: AdminRoleChangeType;
  userName: string;
  userEmail: string;
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
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    TranslateModule
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

  get titleKey(): string {
    return this.isPromotion
      ? 'modals.adminRoleChange.promotion.title'
      : 'modals.adminRoleChange.demotion.title';
  }

  get warningMessageKey(): string {
    return this.isPromotion
      ? 'modals.adminRoleChange.promotion.warning'
      : 'modals.adminRoleChange.demotion.warning';
  }

  get confirmButtonKey(): string {
    return this.isPromotion
      ? 'modals.adminRoleChange.promotion.confirm'
      : 'modals.adminRoleChange.demotion.confirm';
  }

  get isValid(): boolean {
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
