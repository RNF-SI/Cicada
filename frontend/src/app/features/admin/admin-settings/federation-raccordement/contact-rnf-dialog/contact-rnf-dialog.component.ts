import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

import {
  CleErreurRaccordement,
  FederationRaccordementService,
  cleErreurRaccordement,
} from '../../../../../core/services/federation-raccordement.service';
import { FormFieldComponent } from '../../../../../shared/components/form-field/form-field.component';

/**
 * #696 v2 — Écrire à RNF depuis la page du raccordement, à tout moment
 * (question sur l'adhésion, code non reçu, changement d'adresse…).
 *
 * Le nom et l'adresse de l'expéditeur ne sont pas saisis : le serveur prend
 * ceux de l'utilisateur connecté, auxquels RNF répondra. Le dialogue se ferme
 * sur `true` une fois le message accepté ; une erreur le laisse ouvert.
 */
@Component({
  selector: 'app-contact-rnf-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './contact-rnf-dialog.component.html',
  styleUrl: '../raccordement-dialog.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ContactRnfDialogComponent {
  private readonly dialogRef = inject<MatDialogRef<ContactRnfDialogComponent, boolean>>(MatDialogRef);
  private readonly service = inject(FederationRaccordementService);

  readonly form = inject(FormBuilder).nonNullable.group({
    sujet: ['', [Validators.required, Validators.maxLength(200)]],
    message: ['', [Validators.required, Validators.maxLength(5000)]],
  });

  readonly envoiEnCours = signal(false);
  readonly erreur = signal<CleErreurRaccordement | null>(null);

  champInvalide(champ: 'sujet' | 'message'): boolean {
    const controle = this.form.controls[champ];
    return controle.touched && controle.invalid;
  }

  envoyer(): void {
    if (this.envoiEnCours()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { sujet, message } = this.form.getRawValue();
    this.envoiEnCours.set(true);
    this.erreur.set(null);
    this.service.contacterRnf({ sujet: sujet.trim(), message: message.trim() }).subscribe({
      next: () => {
        this.envoiEnCours.set(false);
        this.dialogRef.close(true);
      },
      error: err => {
        this.envoiEnCours.set(false);
        this.erreur.set(cleErreurRaccordement(err));
      },
    });
  }

  annuler(): void {
    this.dialogRef.close(false);
  }
}
