import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';
import { CheckboxComponent } from '../../checkbox/checkbox.component';

/** Formats proposés pour une fiche action (#642). */
export type FicheActionExportFormat = 'print' | 'xlsx';

/** Section facultative de la fiche (#532), incluable ou non à l'impression. */
export interface FicheActionExportSection {
  key: string;
  labelKey: string;
}

export interface ExportFicheActionDialogData {
  /** Code / libellé de l'action, rappelé dans l'en-tête de la modale. */
  actionLabel?: string;
  /** Sections facultatives de la fiche, dans l'ordre d'affichage. */
  sections: readonly FicheActionExportSection[];
  /** Visibilité courante de chaque section (clé → affichée). */
  sectionVisibility: Record<string, boolean>;
}

export interface ExportFicheActionDialogResult {
  format: FicheActionExportFormat;
  /** Sections retenues — ne s'applique qu'à l'impression / PDF. */
  sections: Record<string, boolean>;
}

/**
 * #642 — Modale « Exporter ou imprimer » de la fiche action.
 *
 * Regroupe en un seul bouton de la barre d'actions le choix du format
 * (impression / PDF via le navigateur, ou classeur Excel au modèle CICADA) et
 * le choix des sections à inclure (#532), qui ne concerne que l'impression :
 * le classeur Excel suit le modèle CICADA, dont la structure est fixe.
 */
@Component({
  selector: 'app-export-fiche-action-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TranslateModule, CheckboxComponent],
  templateUrl: './export-fiche-action-dialog.component.html',
  styleUrl: './export-fiche-action-dialog.component.scss',
})
export class ExportFicheActionDialogComponent {
  private readonly dialogRef = inject(
    MatDialogRef<ExportFicheActionDialogComponent, ExportFicheActionDialogResult>
  );
  readonly data: ExportFicheActionDialogData = inject(MAT_DIALOG_DATA);

  /** Format sélectionné (impression par défaut, comportement historique). */
  readonly format = signal<FicheActionExportFormat>('print');

  /** Sections retenues, initialisées sur l'affichage courant de la fiche. */
  readonly sections = signal<Record<string, boolean>>({ ...this.data.sectionVisibility });

  selectFormat(format: FicheActionExportFormat): void {
    this.format.set(format);
  }

  isSelected(format: FicheActionExportFormat): boolean {
    return this.format() === format;
  }

  sectionVisible(key: string): boolean {
    return this.sections()[key] !== false;
  }

  setSectionVisible(key: string, visible: boolean): void {
    this.sections.update(cur => ({ ...cur, [key]: visible }));
  }

  confirm(): void {
    this.dialogRef.close({ format: this.format(), sections: this.sections() });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
