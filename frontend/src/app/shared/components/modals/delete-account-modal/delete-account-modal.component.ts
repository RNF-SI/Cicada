import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';
import { FormFieldComponent } from '../../form-field/form-field.component';

export interface DeleteAccountModalData {
  userEmail: string;
}

export interface DeleteAccountModalResult {
  confirmed: boolean;
}

@Component({
  selector: 'app-delete-account-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './delete-account-modal.component.html',
  styleUrl: './delete-account-modal.component.scss'
})
export class DeleteAccountModalComponent {
  private readonly dialogRef = inject(MatDialogRef<DeleteAccountModalComponent>);
  readonly data = inject<DeleteAccountModalData>(MAT_DIALOG_DATA);

  confirmEmail = '';
  isLoading = signal(false);

  get isValid(): boolean {
    return this.confirmEmail.toLowerCase().trim() === this.data.userEmail.toLowerCase().trim();
  }

  onConfirm(): void {
    if (!this.isValid) {
      return;
    }
    this.dialogRef.close({ confirmed: true } as DeleteAccountModalResult);
  }

  onCancel(): void {
    this.dialogRef.close({ confirmed: false } as DeleteAccountModalResult);
  }
}
