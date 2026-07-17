import { CommonModule } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../core/services/admin.service';
import {
  ArborescenceImportReport,
  ForeignSheet,
  ImportSheet,
  ParsedData,
  ParsedRow,
} from '../../../core/models/admin.model';
import { ImportGridComponent } from '../import-grid/import-grid.component';

/** Mapping d'un onglet cible : quel onglet source, et quelle colonne source par colonne cible. */
interface SheetMapping {
  source: string;
  columns: Record<string, string>;
}

/**
 * Import « mapping » (#10) : téléverse un classeur Excel quelconque, associe ses
 * colonnes au format cible, puis réutilise la grille de correction pour vérifier
 * et importer.
 */
@Component({
  selector: 'app-import-mapping',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    ImportGridComponent,
  ],
  templateUrl: './import-mapping.component.html',
  styleUrls: ['./import-mapping.component.scss'],
})
export class ImportMappingComponent {
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly planId = input.required<number>();
  readonly imported = output<number>();
  readonly cancelled = output<void>();

  readonly reading = signal(false);
  readonly preparing = signal(false);
  readonly foreignSheets = signal<ForeignSheet[]>([]);
  readonly targetSheets = signal<ImportSheet[]>([]);
  readonly fileName = signal('');

  /** Résultat préparé (données + rapport) → affiche la grille de correction. */
  readonly prepared = signal<{ data: ParsedData; report: ArborescenceImportReport } | null>(null);

  /** Mapping courant, par clé d'onglet cible. */
  mapping: Record<string, SheetMapping> = {};

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (!file) return;
    this.fileName.set(file.name);
    this.prepared.set(null);
    this.reading.set(true);
    // Charge en parallèle le schéma cible (si pas déjà) et lit le fichier source.
    if (!this.targetSheets().length) {
      this.adminService.getImportSchema().subscribe({
        next: res => this.targetSheets.set(res.sheets),
      });
    }
    this.adminService.readForeignXlsx(file).subscribe({
      next: res => {
        this.reading.set(false);
        this.foreignSheets.set(res.sheets);
        this.initMapping();
      },
      error: () => {
        this.reading.set(false);
        this.snackBar.open(
          this.translate.instant('plans.import.mapping.readError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  private initMapping(): void {
    const map: Record<string, SheetMapping> = {};
    for (const sheet of this.targetSheets()) {
      map[sheet.key] = { source: '', columns: {} };
    }
    this.mapping = map;
  }

  headersOf(sourceName: string): string[] {
    return this.foreignSheets().find(s => s.name === sourceName)?.headers ?? [];
  }

  /** Construit les données cibles à partir du mapping, valide, puis affiche la grille. */
  prepare(): void {
    const data = this.buildParsedData();
    const total = Object.values(data).reduce((n, rows) => n + rows.length, 0);
    if (total === 0) {
      this.snackBar.open(
        this.translate.instant('plans.import.mapping.nothingMapped'),
        this.translate.instant('common.actions.close'),
        { duration: 5000 },
      );
      return;
    }
    this.preparing.set(true);
    this.adminService.validateArborescenceData(this.planId(), data).subscribe({
      next: report => {
        this.preparing.set(false);
        this.prepared.set({ data: report.data ?? data, report });
      },
      error: () => {
        this.preparing.set(false);
        this.snackBar.open(
          this.translate.instant('plans.import.validateError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  private buildParsedData(): ParsedData {
    const data: ParsedData = {};
    for (const sheet of this.targetSheets()) {
      const m = this.mapping[sheet.key];
      data[sheet.key] = [];
      if (!m?.source) continue;
      const foreign = this.foreignSheets().find(s => s.name === m.source);
      if (!foreign) continue;
      const idx: Record<string, number> = {};
      for (const col of sheet.columns) {
        const header = m.columns[col.key];
        if (header) idx[col.key] = foreign.headers.indexOf(header);
      }
      foreign.rows.forEach((row, i) => {
        const built: ParsedRow = { _row: i + 3 };
        let hasValue = false;
        for (const col of sheet.columns) {
          const j = idx[col.key];
          if (j !== undefined && j >= 0) {
            const v = row[j] ?? '';
            built[col.key] = v;
            if (String(v).trim()) hasValue = true;
          }
        }
        if (hasValue) data[sheet.key].push(built);
      });
    }
    return data;
  }

  onGridImported(total: number): void {
    this.imported.emit(total);
  }

  onGridCancelled(): void {
    this.prepared.set(null);
  }

  cancel(): void {
    this.cancelled.emit();
  }
}
