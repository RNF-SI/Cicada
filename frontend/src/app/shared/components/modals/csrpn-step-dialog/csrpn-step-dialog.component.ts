import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { TranslateModule } from '@ngx-translate/core';

/** Type d'étape CSRPN à saisir (#277). */
export type CsrpnStep = 'csrpn' | 'comite' | 'arrete';

export interface CsrpnStepDialogData {
  step: CsrpnStep;
  planName: string;
  /** `true` si le site principal est une RNN — détermine le routage final
   *  (`arrete_pref` requis) et la présence du toggle mi-parcours. */
  isRnn: boolean;
  /** `true` si le plan est une modification dont la chaîne ne contient pas
   *  encore de `mi_parcours`. Permet d'afficher la case mi-parcours dans le
   *  dialog `arrete` (RNN) ou `comite` (non-RNN). */
  canDeclareMiParcours: boolean;
}

export interface CsrpnStepDialogResult {
  date: string; // ISO yyyy-mm-dd
  /** Renseigné uniquement pour step='arrete'. */
  numeroArrete?: string;
  /** Saisi via la case à cocher dans le dialog terminal. */
  isMiParcours?: boolean;
}

@Component({
  selector: 'app-csrpn-step-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatCheckboxModule,
    TranslateModule,
  ],
  templateUrl: './csrpn-step-dialog.component.html',
  styleUrl: './csrpn-step-dialog.component.scss',
})
export class CsrpnStepDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(
    MatDialogRef<CsrpnStepDialogComponent, CsrpnStepDialogResult | null>
  );
  readonly data: CsrpnStepDialogData = inject(MAT_DIALOG_DATA);

  form: FormGroup;

  constructor() {
    this.form = this.fb.group({
      date: [null, Validators.required],
      numeroArrete: [''],
      isMiParcours: [false],
    });
    if (this.data.step === 'arrete') {
      this.form.get('numeroArrete')?.addValidators(Validators.required);
    }
  }

  /** Vrai si l'étape déclenchera la validation finale du plan (transition
   *  vers `valide`/`modifie`/`mi_parcours`). On expose alors la case mi-parcours
   *  si la chaîne autorise encore une déclaration mi-parcours. */
  get isTerminalStep(): boolean {
    if (this.data.step === 'arrete') return true;            // RNN : arrête → valide
    if (this.data.step === 'comite' && !this.data.isRnn) return true; // non-RNN : comité → valide
    return false;
  }

  get showMiParcoursToggle(): boolean {
    return this.isTerminalStep && this.data.canDeclareMiParcours;
  }

  submit(): void {
    if (this.form.invalid) return;
    const value = this.form.value;
    const date: Date = value.date;
    const iso = date.toISOString().slice(0, 10);
    const result: CsrpnStepDialogResult = { date: iso };
    if (this.data.step === 'arrete') {
      result.numeroArrete = value.numeroArrete;
    }
    if (this.showMiParcoursToggle && value.isMiParcours) {
      result.isMiParcours = true;
    }
    this.dialogRef.close(result);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
