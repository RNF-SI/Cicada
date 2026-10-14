import { Component, inject, ChangeDetectionStrategy } from '@angular/core';

import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface MiParcoursPromptDialogData {
  /** Nom du plan en cours de validation (affiché dans la pop-up). */
  planName: string;
}

export interface MiParcoursPromptDialogResult {
  /** `true` si l'utilisateur déclare cette modification comme l'évaluation
   *  mi-parcours (statut résultant `mi_parcours`). `false` pour `modifie`.
   *  `null` si l'utilisateur a fermé sans choisir. */
  isMiParcours: boolean | null;
}

/**
 * Pop-up affichée à la validation d'un brouillon enfant d'un plan déjà validé,
 * **uniquement si aucune version `mi_parcours` n'existe encore dans la chaîne**.
 * Cf. #276 et note interne *Cycle de vie d'un plan de gestion*.
 */
@Component({
  selector: 'app-mi-parcours-prompt-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, TranslateModule],
  templateUrl: './mi-parcours-prompt-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './mi-parcours-prompt-dialog.component.scss',
})
export class MiParcoursPromptDialogComponent {
  private readonly dialogRef = inject(
    MatDialogRef<MiParcoursPromptDialogComponent, MiParcoursPromptDialogResult>
  );
  readonly data: MiParcoursPromptDialogData = inject(MAT_DIALOG_DATA);

  pickModifie(): void {
    this.dialogRef.close({ isMiParcours: false });
  }

  pickMiParcours(): void {
    this.dialogRef.close({ isMiParcours: true });
  }

  cancel(): void {
    this.dialogRef.close({ isMiParcours: null });
  }
}
