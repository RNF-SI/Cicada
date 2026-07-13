import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface DeleteOperationDialogMetrique {
  id_metrique: number;
  nom_metrique: string;
}

export interface DeleteOperationDialogData {
  /** Libellé de l'action (affiché dans le titre / le message). */
  libelle: string;
  /** Métriques auxquelles l'action est actuellement liée (≥ 2 attendu). */
  metriques: DeleteOperationDialogMetrique[];
}

export interface DeleteOperationDialogResult {
  action: 'delete' | 'unlink' | 'cancel';
  /** Renseigné uniquement quand action === 'unlink'. Une ou plusieurs métriques
   *  peuvent être déliées en une seule opération (#538). */
  metriqueIds?: number[];
}

/**
 * #457 — Choix à la suppression d'une action liée à plusieurs métriques :
 *   - « Supprimer l'action entièrement » → DELETE de l'opération,
 *   - « Retirer le lien à une métrique » → remove-metrique (l'action reste
 *      accessible depuis les autres métriques).
 */
@Component({
  selector: 'app-delete-operation-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    TranslateModule,
  ],
  templateUrl: './delete-operation-dialog.component.html',
  styleUrl: './delete-operation-dialog.component.scss',
})
export class DeleteOperationDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<DeleteOperationDialogComponent>);
  readonly data: DeleteOperationDialogData = inject(MAT_DIALOG_DATA);

  /** Mode sélectionné. Par défaut : retrait du lien (option non destructive). */
  mode = signal<'delete' | 'unlink'>('unlink');
  /** Métriques cochées pour le retrait de lien (multi-sélection, #538).
   *  Par défaut : la première métrique est cochée. */
  selectedMetriqueIds = signal<Set<number>>(
    new Set(this.data.metriques?.[0] ? [this.data.metriques[0].id_metrique] : []),
  );

  readonly metriques = computed(() => this.data.metriques ?? []);

  setMode(mode: 'delete' | 'unlink'): void {
    this.mode.set(mode);
  }

  isMetriqueSelected(id: number): boolean {
    return this.selectedMetriqueIds().has(id);
  }

  toggleMetrique(id: number): void {
    this.selectedMetriqueIds.update(set => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  confirm(): void {
    if (this.mode() === 'delete') {
      this.dialogRef.close({ action: 'delete' } as DeleteOperationDialogResult);
      return;
    }
    const metriqueIds = [...this.selectedMetriqueIds()];
    if (metriqueIds.length > 0) {
      this.dialogRef.close({ action: 'unlink', metriqueIds } as DeleteOperationDialogResult);
    }
  }

  cancel(): void {
    this.dialogRef.close({ action: 'cancel' } as DeleteOperationDialogResult);
  }
}
