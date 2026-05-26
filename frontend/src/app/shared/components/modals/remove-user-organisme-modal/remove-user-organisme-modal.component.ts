import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormFieldComponent } from '../../form-field/form-field.component';

export interface RemoveUserOrganismeModalData {
  userName: string;
  userEmail: string;
  organismeName: string;
}

export interface RemoveUserOrganismeModalResult {
  confirmed: boolean;
  reason?: string;
}

@Component({
  selector: 'app-remove-user-organisme-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './remove-user-organisme-modal.component.html',
  styleUrl: './remove-user-organisme-modal.component.scss'
})
export class RemoveUserOrganismeModalComponent {
  private readonly dialogRef = inject(MatDialogRef<RemoveUserOrganismeModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<RemoveUserOrganismeModalData>(MAT_DIALOG_DATA);

  reason = '';
  errorMessage = signal<string | null>(null);

  get isValid(): boolean {
    return this.reason.trim().length >= 10; // Minimum 10 characters
  }

  onConfirm(): void {
    if (!this.isValid) {
      this.errorMessage.set(this.translate.instant('modals.removeUserOrganisme.validation.minLength'));
      return;
    }

    this.dialogRef.close({
      confirmed: true,
      reason: this.reason.trim()
    } as RemoveUserOrganismeModalResult);
  }

  onCancel(): void {
    this.dialogRef.close({ confirmed: false } as RemoveUserOrganismeModalResult);
  }
}
