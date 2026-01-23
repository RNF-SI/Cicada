import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SettingsService, SiteConfiguration } from '../../../core/services/settings.service';

@Component({
  selector: 'app-admin-settings',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    TranslateModule
  ],
  templateUrl: './admin-settings.component.html',
  styleUrl: './admin-settings.component.scss'
})
export class AdminSettingsComponent implements OnInit {
  private readonly settingsService = inject(SettingsService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  // State
  readonly config = this.settingsService.config;
  readonly isLoading = this.settingsService.isLoading;
  readonly isSaving = signal(false);

  // Preview image (for file selection before upload)
  readonly previewImage = signal<string | null>(null);
  readonly selectedFile = signal<File | null>(null);

  ngOnInit(): void {
    this.settingsService.loadSettings().subscribe();
  }

  /**
   * Get the current homepage image URL for display
   */
  get currentImageUrl(): string {
    const preview = this.previewImage();
    if (preview) return preview;

    const config = this.config();
    if (config?.homepage_image_url) return config.homepage_image_url;

    return this.settingsService.defaultHomepageImage;
  }

  /**
   * Check if using custom image (not default)
   */
  get hasCustomImage(): boolean {
    const config = this.config();
    return !!config?.homepage_image;
  }

  /**
   * Handle file selection
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const file = input.files[0];

    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.snackBar.open('Veuillez sélectionner une image valide', 'Fermer', { duration: 3000 });
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      this.snackBar.open('L\'image ne doit pas dépasser 10 Mo', 'Fermer', { duration: 3000 });
      return;
    }

    this.selectedFile.set(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      this.previewImage.set(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }

  /**
   * Upload the selected image
   */
  uploadImage(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.isSaving.set(true);

    const formData = new FormData();
    formData.append('homepage_image', file);

    this.settingsService.updateSettings(formData).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.previewImage.set(null);
        this.selectedFile.set(null);
        this.snackBar.open(
          this.translate.instant('admin.settings.messages.saved'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      },
      error: () => {
        this.isSaving.set(false);
        this.snackBar.open(
          this.translate.instant('admin.settings.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  /**
   * Cancel file selection
   */
  cancelSelection(): void {
    this.previewImage.set(null);
    this.selectedFile.set(null);
  }

  /**
   * Reset to default image
   */
  resetToDefault(): void {
    this.isSaving.set(true);

    this.settingsService.resetHomepageImage().subscribe({
      next: () => {
        this.isSaving.set(false);
        this.previewImage.set(null);
        this.selectedFile.set(null);
        this.snackBar.open(
          this.translate.instant('admin.settings.messages.restored'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      },
      error: () => {
        this.isSaving.set(false);
        this.snackBar.open(
          this.translate.instant('admin.settings.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string | undefined): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
