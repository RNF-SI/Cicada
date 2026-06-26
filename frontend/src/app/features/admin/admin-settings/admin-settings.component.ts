import { Component, inject, OnInit, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SettingsService, SiteConfiguration, ImagePosition } from '../../../core/services/settings.service';

@Component({
  selector: 'app-admin-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatButtonToggleModule,
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

  // Image position
  selectedPosition = signal<ImagePosition>('center');

  // #448 — Personnalisation : couleur du bandeau + logo structure.
  // Bandeau blanc par défaut (comportement historique).
  readonly headerColor = signal<string>('#FFFFFF');
  /** Couleurs prédéfinies du kit UI (blanc/beige en tête : défaut historique). */
  readonly presetColors: { label: string; value: string }[] = [
    { label: 'Blanc (défaut)', value: '#FFFFFF' },
    { label: 'Beige', value: '#F8F5F1' },
    { label: 'Primary (bleu-vert)', value: '#025359' },
    { label: 'Terra cotta', value: '#B74D5D' },
    { label: 'Succès (vert)', value: '#04854B' },
    { label: 'Info (bleu)', value: '#81C9D8' },
    { label: 'Jaune', value: '#FEC180' },
    { label: 'Orange saumon', value: '#F5B399' },
    { label: 'Vert pâle', value: '#C0E3CF' },
  ];
  readonly logoPreview = signal<string | null>(null);
  readonly selectedLogo = signal<File | null>(null);

  constructor() {
    // Sync position from config when it loads
    effect(() => {
      const config = this.config();
      if (config?.homepage_image_position) {
        this.selectedPosition.set(config.homepage_image_position);
      }
      if (config?.header_color) {
        this.headerColor.set(config.header_color);
      }
    });
  }

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

  // ============================================================
  // #448 — Couleur du bandeau
  // ============================================================

  /** Sélection d'une couleur (preset ou color input). */
  onColorInput(value: string): void {
    this.headerColor.set(value);
  }

  /**
   * #448 — Couleur de texte lisible (blanc ou noir) au-dessus d'une couleur de
   * fond donnée. Même logique de luminance que le header, pour que l'aperçu
   * reflète fidèlement le rendu réel (texte clair sur fond foncé et inversement).
   */
  contrastTextColor(hex: string): string {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
    if (!m) return '#FFFFFF';
    const n = parseInt(m[1], 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance < 0.6 ? '#FFFFFF' : '#343433';
  }

  /** Couleur de texte de l'aperçu du bandeau (lisible sur la couleur choisie). */
  get bannerTextColor(): string {
    return this.contrastTextColor(this.headerColor());
  }

  /** Enregistre la couleur du bandeau. */
  saveHeaderColor(): void {
    this.isSaving.set(true);
    const formData = new FormData();
    formData.append('header_color', this.headerColor());
    this.settingsService.updateSettings(formData).subscribe({
      next: () => {
        this.isSaving.set(false);
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

  // ============================================================
  // #448 — Logo de la structure
  // ============================================================

  get currentLogoUrl(): string | null {
    return this.logoPreview() || this.config()?.structure_logo_url || null;
  }

  get hasStructureLogo(): boolean {
    return !!this.config()?.structure_logo;
  }

  onLogoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    const file = input.files[0];
    if (!file.type.startsWith('image/')) {
      this.snackBar.open('Veuillez sélectionner une image valide', 'Fermer', { duration: 3000 });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.snackBar.open('Le logo ne doit pas dépasser 5 Mo', 'Fermer', { duration: 3000 });
      return;
    }
    this.selectedLogo.set(file);
    const reader = new FileReader();
    reader.onload = (e) => this.logoPreview.set(e.target?.result as string);
    reader.readAsDataURL(file);
  }

  uploadLogo(): void {
    const file = this.selectedLogo();
    if (!file) return;
    this.isSaving.set(true);
    const formData = new FormData();
    formData.append('structure_logo', file);
    this.settingsService.updateSettings(formData).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.logoPreview.set(null);
        this.selectedLogo.set(null);
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

  cancelLogoSelection(): void {
    this.logoPreview.set(null);
    this.selectedLogo.set(null);
  }

  resetLogo(): void {
    this.isSaving.set(true);
    this.settingsService.resetStructureLogo().subscribe({
      next: () => {
        this.isSaving.set(false);
        this.logoPreview.set(null);
        this.selectedLogo.set(null);
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

  /**
   * Update image position
   */
  onPositionChange(position: ImagePosition): void {
    this.selectedPosition.set(position);
    this.isSaving.set(true);

    const formData = new FormData();
    formData.append('homepage_image_position', position);

    this.settingsService.updateSettings(formData).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.snackBar.open(
          this.translate.instant('admin.settings.messages.positionSaved'),
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
   * Get CSS object-position value from position setting
   */
  get imageObjectPosition(): string {
    const position = this.selectedPosition();
    switch (position) {
      case 'top': return 'center top';
      case 'bottom': return 'center bottom';
      default: return 'center center';
    }
  }
}
