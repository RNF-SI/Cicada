import { Component, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { interval, Subscription } from 'rxjs';
import { takeWhile } from 'rxjs/operators';

import { AdminService } from '../../../../core/services/admin.service';
import {
  BulkImportFieldMapping,
  BulkImportSiteRow,
  BulkImportValidationResult,
  BulkImportResult,
  BulkImportDetailItem,
  BulkImportJobStatus,
} from '../../../../core/models/admin.model';

export interface BulkSiteImportModalResult {
  imported: boolean;
  created: number;
}

const TARGET_FIELDS = [
  { value: 'nom_site', label: 'modals.bulkImport.mapping.fields.nom_site' },
  { value: 'id_inpn', label: 'modals.bulkImport.mapping.fields.id_inpn' },
  { value: 'id_local', label: 'modals.bulkImport.mapping.fields.id_local' },
  { value: 'type_site_id', label: 'modals.bulkImport.mapping.fields.type_site_id' },
  { value: 'surf_off', label: 'modals.bulkImport.mapping.fields.surf_off' },
  { value: 'marin', label: 'modals.bulkImport.mapping.fields.marin' },
  { value: 'outre_mer', label: 'modals.bulkImport.mapping.fields.outre_mer' },
];

@Component({
  selector: 'app-bulk-site-import-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatStepperModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatTableModule,
    MatCheckboxModule,
    MatChipsModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatTooltipModule,
    TranslateModule,
  ],
  templateUrl: './bulk-site-import-modal.component.html',
  styleUrl: './bulk-site-import-modal.component.scss',
})
export class BulkSiteImportModalComponent {
  private readonly dialogRef = inject(MatDialogRef<BulkSiteImportModalComponent>);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);

  @ViewChild('stepper') stepper!: MatStepper;

  // Step state
  readonly currentStep = signal(0);

  // Step 1: Upload
  readonly selectedFile = signal<File | null>(null);
  readonly uploading = signal(false);
  readonly uploadError = signal('');

  // Step 2: Mapping
  readonly detectedProperties = signal<string[]>([]);
  readonly fieldMapping = signal<Record<string, string>>({});
  readonly suggestedMapping = signal<Record<string, string>>({});
  readonly validating = signal(false);

  // Step 3: Preview
  readonly validationResult = signal<BulkImportValidationResult | null>(null);
  readonly sites = signal<BulkImportSiteRow[]>([]);

  // Step 4: Results
  readonly importing = signal(false);
  readonly importResult = signal<BulkImportResult | null>(null);
  readonly importDetails = signal<BulkImportDetailItem[]>([]);
  readonly jobStatus = signal<BulkImportJobStatus | null>(null);
  private pollSubscription: Subscription | null = null;

  // Constants
  readonly targetFields = TARGET_FIELDS;
  readonly previewColumns = ['select', 'row', 'name', 'inpn', 'local', 'surface', 'geometry', 'status'];

  // Computed
  readonly totalValid = computed(() => {
    const result = this.validationResult();
    return result ? result.valid : 0;
  });

  readonly totalErrors = computed(() => {
    const result = this.validationResult();
    return result ? result.errors : 0;
  });

  readonly totalDuplicates = computed(() => {
    const result = this.validationResult();
    return result ? result.duplicates : 0;
  });

  readonly selectedCount = computed(() => {
    return this.sites().filter(s => s.selected).length;
  });

  readonly allSelected = computed(() => {
    const selectableSites = this.sites().filter(s => s.errors.length === 0);
    return selectableSites.length > 0 && selectableSites.every(s => s.selected);
  });

  readonly canImport = computed(() => {
    return this.selectedCount() > 0 && !this.importing();
  });

  readonly importProgress = computed(() => {
    const status = this.jobStatus();
    if (!status || status.total_sites === 0) return 0;
    return Math.round((status.processed_sites / status.total_sites) * 100);
  });

  // Step 1: File selection
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.selectFile(input.files[0]);
    }
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer?.files.length) {
      this.selectFile(event.dataTransfer.files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  private selectFile(file: File): void {
    const name = file.name.toLowerCase();
    if (!name.endsWith('.geojson') && !name.endsWith('.json') && !name.endsWith('.csv')) {
      this.uploadError.set(this.translate.instant('modals.bulkImport.upload.errors.invalidFormat'));
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.uploadError.set(this.translate.instant('modals.bulkImport.upload.errors.tooLarge'));
      return;
    }
    this.selectedFile.set(file);
    this.uploadError.set('');
    this.uploadAndValidate();
  }

  private uploadAndValidate(mapping?: BulkImportFieldMapping): void {
    const file = this.selectedFile();
    if (!file) return;

    this.uploading.set(true);
    this.uploadError.set('');

    this.adminService.bulkImportValidate(file, mapping).subscribe({
      next: (result) => {
        this.uploading.set(false);
        this.validationResult.set(result);
        this.detectedProperties.set(result.detected_properties);
        this.suggestedMapping.set(result.suggested_mapping);

        // Initialize field mapping with suggested or applied mapping
        const currentMapping = mapping || result.suggested_mapping;
        this.fieldMapping.set({ ...currentMapping });

        // Initialize sites with selection state
        const sitesWithSelection = result.sites.map(site => ({
          ...site,
          selected: site.errors.length === 0 && !site.duplicate_info,
        }));
        this.sites.set(sitesWithSelection);

        // Auto-advance to mapping step if not already there
        if (this.currentStep() === 0) {
          this.currentStep.set(1);
        }
      },
      error: (err) => {
        this.uploading.set(false);
        this.uploadError.set(err.message || this.translate.instant('modals.bulkImport.upload.errors.parseError'));
      },
    });
  }

  // Step 2: Mapping
  onMappingChange(sourceProperty: string, targetField: string): void {
    const mapping = { ...this.fieldMapping() };
    if (targetField === '') {
      delete mapping[sourceProperty];
    } else {
      mapping[sourceProperty] = targetField;
    }
    this.fieldMapping.set(mapping);
  }

  revalidate(): void {
    this.validating.set(true);
    this.uploadAndValidate(this.fieldMapping());
    this.validating.set(false);
  }

  getExampleValues(property: string): string[] {
    const allSites = this.sites();
    const examples: string[] = [];
    for (const site of allSites.slice(0, 3)) {
      const val = site.original_properties?.[property];
      if (val !== undefined && val !== null && val !== '') {
        examples.push(String(val));
      }
    }
    return examples;
  }

  goToPreview(): void {
    this.stepNext();
  }

  stepNext(): void {
    this.stepper.next();
    this.currentStep.set(this.stepper.selectedIndex);
  }

  stepPrevious(): void {
    this.stepper.previous();
    this.currentStep.set(this.stepper.selectedIndex);
  }

  // Step 3: Preview
  toggleSite(index: number): void {
    const updated = [...this.sites()];
    if (updated[index].errors.length === 0) {
      updated[index] = { ...updated[index], selected: !updated[index].selected };
      this.sites.set(updated);
    }
  }

  toggleAll(): void {
    const allSel = this.allSelected();
    const updated = this.sites().map(site => ({
      ...site,
      selected: site.errors.length === 0 ? !allSel : false,
    }));
    this.sites.set(updated);
  }

  getSiteStatus(site: BulkImportSiteRow): string {
    if (site.errors.length > 0) return 'error';
    if (site.duplicate_info) return 'duplicate';
    if (site.warnings.length > 0) return 'warning';
    return 'valid';
  }

  // Step 4: Import
  startImport(): void {
    const selectedSites = this.sites().filter(s => s.selected);
    const selectedIndices = selectedSites.map(s => s.row_index);

    if (selectedIndices.length === 0) return;

    this.importing.set(true);
    this.stepNext();

    // Build sites payload (strip local 'selected' field)
    const sitesPayload = selectedSites.map(s => ({
      row_index: s.row_index,
      original_properties: s.original_properties,
      mapped_data: s.mapped_data,
      geometry: s.geometry || null,
    }));

    this.adminService.bulkImportExecute(sitesPayload, selectedIndices).subscribe({
      next: (result) => {
        this.importResult.set(result);

        if (result.async && result.job_id) {
          // Poll for status
          this.pollJobStatus(result.job_id);
        } else {
          // Sync import completed
          this.importing.set(false);
          this.importDetails.set(result.details || []);
        }
      },
      error: (err) => {
        this.importing.set(false);
        this.importResult.set({
          async: false,
          created: 0,
          failed: 0,
          validation_pending: 0,
          details: [{
            row_index: -1,
            nom_site: '',
            status: 'failed',
            error: err.message,
          }],
        });
        this.importDetails.set([{
          row_index: -1,
          nom_site: 'Erreur globale',
          status: 'failed',
          error: err.message,
        }]);
      },
    });
  }

  private pollJobStatus(jobId: number): void {
    this.pollSubscription = interval(2000)
      .pipe(takeWhile(() => this.importing()))
      .subscribe(() => {
        this.adminService.bulkImportStatus(jobId).subscribe({
          next: (status) => {
            this.jobStatus.set(status);

            if (status.status === 'completed' || status.status === 'failed') {
              this.importing.set(false);
              this.importDetails.set(status.result_data?.details || []);
              this.importResult.set({
                async: true,
                job_id: jobId,
                created: status.created_sites,
                failed: status.failed_sites,
                validation_pending: status.validation_pending_sites,
                details: status.result_data?.details || [],
              });
              this.pollSubscription?.unsubscribe();
            }
          },
          error: () => {
            // Continue polling on error
          },
        });
      });
  }

  // Dialog actions
  close(): void {
    this.pollSubscription?.unsubscribe();
    const result = this.importResult();
    if (result && (result.created || 0) > 0) {
      this.dialogRef.close({
        imported: true,
        created: result.created || 0,
      } as BulkSiteImportModalResult);
    } else {
      this.dialogRef.close(null);
    }
  }
}
