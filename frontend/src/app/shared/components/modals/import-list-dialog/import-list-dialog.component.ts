import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule } from '@ngx-translate/core';
import { TaxonomyService, BulkValidationFoundItem, BulkValidationNotFoundItem } from '../../../../core/services/taxonomy.service';
import { HabitatService, HabitatBulkFoundItem, HabitatBulkNotFoundItem } from '../../../../core/services/habitat.service';
import { GeologyService, InpgBulkFoundItem, InpgBulkNotFoundItem } from '../../../../core/services/geology.service';

export interface ImportListDialogData {
  type: 'taxon' | 'habitat' | 'geology';
  existingCodes: (number | string)[];
}

export interface ImportListDialogResult {
  items: ImportedItem[];
}

export interface ImportedItem {
  code: number | string;
  label: string;
  secondaryLabel?: string;
  input: string;
  valid: boolean;
}

export interface NotFoundEntry {
  input: string;
  candidates: { label: string; secondary?: string }[];
}

@Component({
  selector: 'app-import-list-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    TranslateModule,
  ],
  templateUrl: './import-list-dialog.component.html',
  styleUrl: './import-list-dialog.component.scss',
})
export class ImportListDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<ImportListDialogComponent>);
  private readonly data: ImportListDialogData = inject(MAT_DIALOG_DATA);
  private readonly taxonomyService = inject(TaxonomyService);
  private readonly habitatService = inject(HabitatService);
  private readonly geologyService = inject(GeologyService);

  readonly type = this.data.type;
  readonly codesInput = signal('');
  readonly isValidating = signal(false);
  readonly validationDone = signal(false);
  readonly foundItems = signal<ImportedItem[]>([]);
  readonly notFoundEntries = signal<NotFoundEntry[]>([]);

  get hasInput(): boolean {
    return this.codesInput().trim().length > 0;
  }

  onFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.readFile(file);
  }

  private readFile(file: File): void {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (text) {
        this.codesInput.set(text);
      }
    };
    reader.readAsText(file);
  }

  onValidate(): void {
    const lines = this.codesInput()
      .split(/[\n\r]+/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (lines.length === 0) return;

    // Filtrer les doublons avec les éléments déjà présents
    const existingSet = new Set(this.data.existingCodes.map((c) => String(c)));
    const newItems = lines.filter((l) => {
      // Pour les codes numériques, comparer directement
      try {
        if (!isNaN(Number(l)) && existingSet.has(l)) return false;
      } catch { /* ignore */ }
      return true;
    });
    if (newItems.length === 0) return;

    this.isValidating.set(true);

    if (this.type === 'taxon') {
      this.taxonomyService.validateBulk(newItems).subscribe({
        next: (result) => this.handleTaxonResult(result.found, result.not_found),
        error: () => this.isValidating.set(false),
      });
    } else if (this.type === 'habitat') {
      this.habitatService.validateBulk(newItems).subscribe({
        next: (result) => this.handleHabitatResult(result.found, result.not_found),
        error: () => this.isValidating.set(false),
      });
    } else {
      this.geologyService.validateBulk(newItems).subscribe({
        next: (result) => this.handleGeologyResult(result.found, result.not_found),
        error: () => this.isValidating.set(false),
      });
    }
  }

  private handleTaxonResult(
    found: BulkValidationFoundItem[],
    notFound: BulkValidationNotFoundItem[]
  ): void {
    const items: ImportedItem[] = found.map((item) => ({
      code: item.cd_nom,
      label: item.nom_complet || item.nom_valide,
      secondaryLabel: item.nom_vern || undefined,
      input: item.input,
      valid: true,
    }));
    const entries: NotFoundEntry[] = notFound.map((nf) => ({
      input: nf.input,
      candidates: nf.candidates.map((c) => ({
        label: c.nom_valide,
        secondary: c.nom_vern || undefined,
      })),
    }));
    this.foundItems.set(items);
    this.notFoundEntries.set(entries);
    this.validationDone.set(true);
    this.isValidating.set(false);
  }

  private handleHabitatResult(
    found: HabitatBulkFoundItem[],
    notFound: HabitatBulkNotFoundItem[]
  ): void {
    const items: ImportedItem[] = found.map((item) => ({
      code: item.cd_hab,
      label: item.lb_hab_fr || item.lb_hab_fr_complet || '',
      secondaryLabel: item.lb_code || undefined,
      input: item.input,
      valid: true,
    }));
    const entries: NotFoundEntry[] = notFound.map((nf) => ({
      input: nf.input,
      candidates: nf.candidates.map((c) => ({
        label: c.lb_hab_fr || '',
        secondary: c.lb_code || undefined,
      })),
    }));
    this.foundItems.set(items);
    this.notFoundEntries.set(entries);
    this.validationDone.set(true);
    this.isValidating.set(false);
  }

  private handleGeologyResult(
    found: InpgBulkFoundItem[],
    notFound: InpgBulkNotFoundItem[]
  ): void {
    const items: ImportedItem[] = found.map((item) => ({
      code: item.id_inpg,
      label: item.lb_site || item.id_metier || '',
      secondaryLabel: item.id_metier || undefined,
      input: item.input,
      valid: true,
    }));
    const entries: NotFoundEntry[] = notFound.map((nf) => ({
      input: nf.input,
      candidates: nf.candidates.map((c) => ({
        label: c.lb_site || '',
        secondary: c.id_metier || undefined,
      })),
    }));
    this.foundItems.set(items);
    this.notFoundEntries.set(entries);
    this.validationDone.set(true);
    this.isValidating.set(false);
  }

  onConfirm(): void {
    this.dialogRef.close({ items: this.foundItems() } as ImportListDialogResult);
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
