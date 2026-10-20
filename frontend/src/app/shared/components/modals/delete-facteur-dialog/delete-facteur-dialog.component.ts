import { Component, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface DeleteFacteurDialogData {
  /** Libellé du facteur d'influence. */
  libelle: string;
  /** Libellé de l'enjeu (ou FCR) affiché, dont on peut retirer le facteur. */
  enjeuLibelle: string;
  /** Nombre d'enjeux sous lesquels le facteur est partagé (≥ 2). */
  nbEnjeux: number;
}

export interface DeleteFacteurDialogResult {
  action: 'delete' | 'unlink' | 'cancel';
}

/**
 * #730 — Choix à la suppression d'un facteur d'influence partagé entre
 * plusieurs enjeux (#552) :
 *   - « Retirer de cet enjeu » → unlink (le facteur et ses pressions restent
 *     sous les autres enjeux),
 *   - « Supprimer partout » → DELETE du facteur et de tout son sous-arbre.
 */
@Component({
  selector: 'app-delete-facteur-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, TranslateModule],
  templateUrl: './delete-facteur-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  // Même présentation que le choix de suppression d'une action (#457).
  styleUrl: '../delete-operation-dialog/delete-operation-dialog.component.scss',
})
export class DeleteFacteurDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<DeleteFacteurDialogComponent>);
  readonly data: DeleteFacteurDialogData = inject(MAT_DIALOG_DATA);

  /** Par défaut : l'option non destructive. */
  mode = signal<'delete' | 'unlink'>('unlink');

  setMode(mode: 'delete' | 'unlink'): void {
    this.mode.set(mode);
  }

  confirm(): void {
    this.dialogRef.close({ action: this.mode() } as DeleteFacteurDialogResult);
  }

  cancel(): void {
    this.dialogRef.close({ action: 'cancel' } as DeleteFacteurDialogResult);
  }
}
