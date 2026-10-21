import { Component, computed, inject, signal, ChangeDetectionStrategy } from '@angular/core';

import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../../core/services/admin.service';
import { SettingsService } from '../../../../core/services/settings.service';
import { FichierType } from '../../../../core/models/admin.model';
import { FormFieldComponent } from '../../form-field/form-field.component';

export interface UploadDocumentDialogData {
  planId: number;
}

@Component({
  selector: 'app-upload-document-modal',
  standalone: true,
  imports: [
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FormFieldComponent
],
  templateUrl: './upload-document-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './upload-document-modal.component.scss',
})
export class UploadDocumentModalComponent {
  private readonly dialogRef = inject(MatDialogRef<UploadDocumentModalComponent>);
  private readonly data: UploadDocumentDialogData = inject(MAT_DIALOG_DATA);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  private readonly settingsService = inject(SettingsService);

  /** #745 — Taille maximale d'un document, réglée par l'administrateur de l'instance. */
  readonly tailleMaxMo = computed(() => this.settingsService.config()?.taille_max_document_mo ?? 20);

  selectedFile = signal<File | null>(null);
  uploading = signal(false);
  errorMessage = signal<string | null>(null);

  typeFichier: FichierType = 'document';
  titre = '';
  description = '';
  auteur = '';
  dateDocument: Date | null = null;

  readonly fichierTypes: { value: FichierType; labelKey: string }[] = [
    { value: 'document', labelKey: 'plans.detail.documents.upload.types.document' },
    { value: 'annexe', labelKey: 'plans.detail.documents.upload.types.annexe' },
    { value: 'carte', labelKey: 'plans.detail.documents.upload.types.carte' },
    { value: 'photo', labelKey: 'plans.detail.documents.upload.types.photo' },
    { value: 'rapport', labelKey: 'plans.detail.documents.upload.types.rapport' },
    { value: 'autre', labelKey: 'plans.detail.documents.upload.types.autre' },
  ];

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      // #745 — Prévenir avant l'envoi plutôt qu'après un long téléversement
      // refusé par le serveur (qui contrôle de toute façon).
      if (file.size > this.tailleMaxMo() * 1024 * 1024) {
        this.selectedFile.set(null);
        this.errorMessage.set(this.translate.instant(
          'plans.detail.documents.upload.tooLarge', { max: this.tailleMaxMo() }));
        input.value = '';
        return;
      }
      this.selectedFile.set(file);
      this.errorMessage.set(null);
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  submit(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.uploading.set(true);
    this.errorMessage.set(null);

    const metadata: any = {
      type_fichier: this.typeFichier,
    };
    if (this.titre.trim()) metadata.titre = this.titre.trim();
    if (this.description.trim()) metadata.description = this.description.trim();
    if (this.auteur.trim()) metadata.auteur = this.auteur.trim();
    if (this.dateDocument) {
      metadata.date_document = this.dateDocument.toISOString().split('T')[0];
    }

    this.adminService.uploadFichier(this.data.planId, file, metadata).subscribe({
      next: (fichier) => {
        this.uploading.set(false);
        this.dialogRef.close(fichier);
      },
      error: (err) => {
        this.uploading.set(false);
        this.errorMessage.set(err.message || 'Erreur lors de l\'upload');
      },
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
