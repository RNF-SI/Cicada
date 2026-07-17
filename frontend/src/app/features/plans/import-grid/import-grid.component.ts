import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../core/services/admin.service';
import {
  ArborescenceImportReport,
  ImportSheet,
  ParsedData,
  ParsedRow,
} from '../../../core/models/admin.model';

/**
 * Grille de correction interactive (#9) : édite les données parsées d'un import
 * d'arborescence, revalide sans repasser par Excel, puis importe.
 */
@Component({
  selector: 'app-import-grid',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
  ],
  templateUrl: './import-grid.component.html',
  styleUrls: ['./import-grid.component.scss'],
})
export class ImportGridComponent {
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly planId = input.required<number>();
  readonly sheets = input.required<ImportSheet[]>();
  /** Données initiales (issues de la validation fichier). */
  readonly initialData = input.required<ParsedData>();
  readonly initialReport = input.required<ArborescenceImportReport>();

  readonly imported = output<number>();
  readonly cancelled = output<void>();

  readonly data = signal<ParsedData>({});
  readonly report = signal<ArborescenceImportReport | null>(null);
  readonly validating = signal(false);
  readonly importing = signal(false);

  private initialised = false;

  ngOnInit(): void {
    // Copie éditable des données initiales.
    this.data.set(structuredClone(this.initialData()));
    this.report.set(this.initialReport());
    this.initialised = true;
  }

  /** Onglets à afficher : ceux qui portent des lignes. */
  readonly visibleSheets = computed<ImportSheet[]>(() => {
    const d = this.data();
    return this.sheets().filter(s => (d[s.key]?.length ?? 0) > 0);
  });

  /** Index des anomalies par « onglet|ligne|colonne » (erreurs) et messages. */
  private readonly errorIndex = computed<Map<string, string>>(() => {
    const map = new Map<string, string>();
    for (const issue of this.report()?.issues ?? []) {
      if (issue.level !== 'error') continue;
      map.set(`${issue.sheet}|${issue.row}|${issue.column}`, issue.message);
    }
    return map;
  });

  readonly canImport = computed(() => this.report()?.can_import === true);
  readonly errorCount = computed(() => this.report()?.n_errors ?? 0);
  readonly warningCount = computed(() => this.report()?.n_warnings ?? 0);

  rowsOf(sheetKey: string): ParsedRow[] {
    return this.data()[sheetKey] ?? [];
  }

  cellError(sheetName: string, row: ParsedRow, colKey: string): string | null {
    return this.errorIndex().get(`${sheetName}|${row['_row']}|${colKey}`) ?? null;
  }

  cellValue(row: ParsedRow, colKey: string): string {
    const v = row[colKey];
    return v === null || v === undefined ? '' : String(v);
  }

  onCellInput(row: ParsedRow, colKey: string, value: string): void {
    row[colKey] = value;
  }

  removeRow(sheetKey: string, index: number): void {
    const d = { ...this.data() };
    d[sheetKey] = (d[sheetKey] ?? []).filter((_, i) => i !== index);
    this.data.set(d);
  }

  revalidate(): void {
    this.validating.set(true);
    this.adminService.validateArborescenceData(this.planId(), this.data()).subscribe({
      next: report => {
        this.validating.set(false);
        this.report.set(report);
        if (report.data) this.data.set(report.data);
        const key = report.can_import
          ? 'plans.import.grid.revalidateOk'
          : 'plans.import.grid.revalidateErrors';
        this.snackBar.open(
          this.translate.instant(key, { count: report.n_errors }),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
      },
      error: () => {
        this.validating.set(false);
        this.snackBar.open(
          this.translate.instant('plans.import.validateError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  runImport(): void {
    if (!this.canImport()) return;
    this.importing.set(true);
    this.adminService.importArborescenceData(this.planId(), this.data()).subscribe({
      next: result => {
        this.importing.set(false);
        this.imported.emit(result.total);
      },
      error: err => {
        this.importing.set(false);
        const body = err?.error as ArborescenceImportReport | undefined;
        if (body && 'issues' in body) {
          this.report.set(body);
          if (body.data) this.data.set(body.data);
        }
        this.snackBar.open(
          this.translate.instant('plans.import.importError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  cancel(): void {
    this.cancelled.emit();
  }
}
