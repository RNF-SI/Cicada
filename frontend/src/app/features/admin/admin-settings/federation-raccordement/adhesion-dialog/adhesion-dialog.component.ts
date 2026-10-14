import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

import {
  CleErreurRaccordement,
  EtatRaccordement,
  FederationRaccordementService,
  cleErreurRaccordement,
} from '../../../../../core/services/federation-raccordement.service';
import { FormFieldComponent } from '../../../../../shared/components/form-field/form-field.component';

export interface AdhesionDialogData {
  instance_id: string;
  libelle: string;
  /** Défauts proposés : l'utilisateur connecté, modifiables. */
  contact_nom: string;
  contact_email: string;
}

/**
 * #696 v2 — Demande d'adhésion à l'exploration nationale.
 *
 * RNF ne décide plus sur un code calculé : il prend contact avec la personne
 * indiquée ici, puis lui envoie un code de confirmation par e-mail. Le nom et
 * l'adresse sont donc ce que la demande a de plus important — d'où le
 * formulaire plutôt qu'une simple confirmation.
 *
 * Le dialogue envoie lui-même la demande : en cas d'erreur il reste ouvert,
 * la saisie n'est pas perdue. Il se ferme sur l'état renvoyé par le serveur.
 */
@Component({
  selector: 'app-adhesion-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './adhesion-dialog.component.html',
  styleUrl: '../raccordement-dialog.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class AdhesionDialogComponent {
  private readonly dialogRef = inject<MatDialogRef<AdhesionDialogComponent, EtatRaccordement>>(MatDialogRef);
  private readonly service = inject(FederationRaccordementService);
  readonly data = inject<AdhesionDialogData>(MAT_DIALOG_DATA);

  readonly form = inject(FormBuilder).nonNullable.group({
    contact_nom: [this.data.contact_nom ?? '', [Validators.required, Validators.maxLength(200)]],
    contact_email: [this.data.contact_email ?? '', [Validators.required, Validators.email]],
    contact_telephone: ['', [Validators.maxLength(50)]],
    message: ['', [Validators.maxLength(2000)]],
  });

  readonly envoiEnCours = signal(false);
  readonly erreur = signal<CleErreurRaccordement | null>(null);

  /** Clé i18n de l'erreur d'un champ, affichée une fois le champ touché. */
  erreurChamp(champ: 'contact_nom' | 'contact_email'): string | null {
    const controle = this.form.controls[champ];
    if (!controle.touched || controle.valid) {
      return null;
    }
    return controle.hasError('required')
      ? 'admin.settings.federation.etat.formulaire.requis'
      : 'admin.settings.federation.etat.formulaire.emailInvalide';
  }

  envoyer(): void {
    if (this.envoiEnCours()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const valeur = this.form.getRawValue();
    this.envoiEnCours.set(true);
    this.erreur.set(null);
    this.service
      .demanderAdhesion({
        contact_nom: valeur.contact_nom.trim(),
        contact_email: valeur.contact_email.trim(),
        contact_telephone: valeur.contact_telephone.trim(),
        message: valeur.message.trim(),
      })
      .subscribe({
        next: etat => {
          this.envoiEnCours.set(false);
          this.dialogRef.close(etat);
        },
        error: err => {
          this.envoiEnCours.set(false);
          this.erreur.set(cleErreurRaccordement(err));
        },
      });
  }

  annuler(): void {
    this.dialogRef.close();
  }
}
