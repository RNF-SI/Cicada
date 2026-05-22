import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';
import { PlanDuplicateOptions } from '../../../../core/models/admin.model';
import { CheckboxComponent } from '../../checkbox/checkbox.component';

export interface DuplicatePlanDialogData {
  planId: number;
  planName: string;
  planPeriod: string;
  planStatus: string;
  nbSites: number;
}

export interface DuplicatePlanDialogResult {
  confirmed: boolean;
  options?: PlanDuplicateOptions;
}

@Component({
  selector: 'app-duplicate-plan-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    CheckboxComponent,
  ],
  templateUrl: './duplicate-plan-dialog.component.html',
  styleUrl: './duplicate-plan-dialog.component.scss',
})
export class DuplicatePlanDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<DuplicatePlanDialogComponent>);
  readonly data = inject<DuplicatePlanDialogData>(MAT_DIALOG_DATA);

  copySites = signal(true);
  copyReferents = signal(true);
  copyFichiers = signal(false);
  copyEnjeux = signal(true);
  copySubElements = signal(true);

  loading = signal(false);

  subElementsDisabled = computed(() => !this.copyEnjeux());

  onEnjeuxChange(checked: boolean): void {
    this.copyEnjeux.set(checked);
    if (!checked) {
      this.copySubElements.set(false);
    }
  }

  onConfirm(): void {
    const options: PlanDuplicateOptions = {
      copy_sites: this.copySites(),
      copy_referents: this.copyReferents(),
      copy_fichiers: this.copyFichiers(),
      copy_enjeux: this.copyEnjeux(),
      copy_sub_elements: this.copySubElements(),
    };
    this.dialogRef.close({ confirmed: true, options } as DuplicatePlanDialogResult);
  }

  onCancel(): void {
    this.dialogRef.close({ confirmed: false } as DuplicatePlanDialogResult);
  }
}
