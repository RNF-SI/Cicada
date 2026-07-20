import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface ToDraftChoiceDialogData {
  /** Nom du plan validé sur lequel on veut revenir en écriture. */
  planName: string;
  /** Faux si un brouillon enfant existe déjà : l'option « nouvelle version » est alors indisponible. */
  canCreateNewVersion: boolean;
}

export type ToDraftChoice = 'new-version' | 'to-draft' | 'cancel';

export interface ToDraftChoiceDialogResult {
  choice: ToDraftChoice;
}

/**
 * #436 — Pop-up affichée au clic sur « Remettre en brouillon » depuis un plan
 * validé. Au lieu de dégrader directement la version validée, on propose
 * d'abord de **créer une nouvelle version** (option recommandée) en détaillant
 * les implications de chaque choix.
 */
@Component({
  selector: 'app-to-draft-choice-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TranslateModule],
  templateUrl: './to-draft-choice-dialog.component.html',
  styleUrl: './to-draft-choice-dialog.component.scss',
})
export class ToDraftChoiceDialogComponent {
  private readonly dialogRef = inject(
    MatDialogRef<ToDraftChoiceDialogComponent, ToDraftChoiceDialogResult>
  );
  readonly data: ToDraftChoiceDialogData = inject(MAT_DIALOG_DATA);

  pickNewVersion(): void {
    this.dialogRef.close({ choice: 'new-version' });
  }

  pickToDraft(): void {
    this.dialogRef.close({ choice: 'to-draft' });
  }

  cancel(): void {
    this.dialogRef.close({ choice: 'cancel' });
  }
}
