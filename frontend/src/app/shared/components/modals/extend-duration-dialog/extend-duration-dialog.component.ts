import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface ExtendDurationDialogData {
  /** Nom complet du plan affiché dans la modale. */
  planName: string;
  /** Année de fin d'origine du plan (sert au calcul de la nouvelle échéance). */
  anneeFin: number;
  /** Extension déjà acquise sur le plan source (0 ou 1). Défaut : 0.
   *  Limite le choix : si déjà à 1 an, seule la reconduction +1 an est possible
   *  (cumul max 2 ans). */
  currentExtension?: number;
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

  /** Extension déjà acquise (0 ou 1). */
  get currentExtension(): number {
    return this.data.currentExtension ?? 0;
  }

  /** Nombre d'années encore ajoutables (cumul max 2 ans). */
  get remaining(): number {
    return Math.max(0, 2 - this.currentExtension);
  }

  /** Vrai si une reconduction (extension déjà partielle) — pas une 1re prolongation. */
  get isReconduction(): boolean {
    return this.currentExtension > 0;
  }

  /** Échéance effective une fois `years` ajoutées (annee_fin + extension cumulée). */
  newEnd(years: number): number {
    return this.data.anneeFin + this.currentExtension + years;
  }

  choose(years: 1 | 2): void {
    this.dialogRef.close({ years });
  }

  cancel(): void {
    this.dialogRef.close({ years: null });
  }
}
