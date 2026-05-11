import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface ExtendDurationDialogData {
  /** Nom complet du plan affiché dans la modale. */
  planName: string;
  /** Année de fin actuelle du plan (sert au calcul de la nouvelle échéance). */
  anneeFin: number;
}

export interface ExtendDurationDialogResult {
  /** Nombre d'années choisi (1 ou 2), ou null si l'utilisateur annule. */
  years: 1 | 2 | null;
}

@Component({
  selector: 'app-extend-duration-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TranslateModule],
  templateUrl: './extend-duration-dialog.component.html',
  styleUrl: './extend-duration-dialog.component.scss',
})
export class ExtendDurationDialogComponent {
  private readonly dialogRef = inject(
    MatDialogRef<ExtendDurationDialogComponent, ExtendDurationDialogResult>
  );
  readonly data: ExtendDurationDialogData = inject(MAT_DIALOG_DATA);

  choose(years: 1 | 2): void {
    this.dialogRef.close({ years });
  }

  cancel(): void {
    this.dialogRef.close({ years: null });
  }
}
