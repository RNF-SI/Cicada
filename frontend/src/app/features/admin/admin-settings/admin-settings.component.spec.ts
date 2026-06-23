import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';

import { AdminSettingsComponent } from './admin-settings.component';
import { SettingsService, SiteConfiguration } from '../../../core/services/settings.service';

// Fake translate loader for tests
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'admin.settings.title': 'Paramètres',
      'admin.settings.homepage.title': 'Image de la page d\'accueil',
      'admin.settings.homepage.description': 'Description',
      'admin.settings.homepage.currentImage': 'Image actuelle',
      'admin.settings.homepage.selectImage': 'Choisir une image',
      'admin.settings.homepage.uploadHint': 'Aide',
      'admin.settings.homepage.resetToDefault': 'Réinitialiser',
      'admin.settings.messages.saved': 'Paramètres enregistrés',
      'admin.settings.messages.restored': 'Image réinitialisée',
      'admin.settings.messages.error': 'Erreur',
      'common.actions.save': 'Enregistrer',
      'common.actions.cancel': 'Annuler',
      'common.actions.close': 'Fermer'
    });
  }
}

describe('AdminSettingsComponent', () => {
  let component: AdminSettingsComponent;
  let fixture: ComponentFixture<AdminSettingsComponent>;
  let mockSettingsService: Partial<SettingsService>;
  let mockSnackBar: { open: jest.Mock };
  let translateService: TranslateService;

  // Writable signals for mocking
  let configSignal: WritableSignal<SiteConfiguration | null>;
  let isLoadingSignal: WritableSignal<boolean>;

  const mockConfig: SiteConfiguration = {
    homepage_image: 'settings/homepage/image.jpg',
    homepage_image_url: 'http://localhost:8000/media/settings/homepage/image.jpg',
    homepage_image_position: 'center',
    header_color: '#025359',
    structure_logo: null,
    structure_logo_url: null,
    updated_at: '2024-01-15T10:30:00Z',
    updated_by: 1,
    updated_by_name: 'Admin User'
  };

  beforeEach(async () => {
    // Create writable signals for the mock
    configSignal = signal<SiteConfiguration | null>(mockConfig);
    isLoadingSignal = signal<boolean>(false);

    mockSettingsService = {
      config: configSignal.asReadonly(),
      isLoading: isLoadingSignal.asReadonly(),
      defaultHomepageImage: 'assets/images/homepage-default.jpg',
      loadSettings: jest.fn().mockReturnValue(of(mockConfig)),
      updateSettings: jest.fn().mockReturnValue(of(mockConfig)),
      resetHomepageImage: jest.fn().mockReturnValue(of({
        ...mockConfig,
        homepage_image: null,
        homepage_image_url: null
      }))
    };

    mockSnackBar = {
      open: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [
        AdminSettingsComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr'
        })
      ],
      providers: [
        { provide: SettingsService, useValue: mockSettingsService },
        { provide: MatSnackBar, useValue: mockSnackBar }
      ]
    });

    // Override provider for standalone component (must be before compileComponents)
    TestBed.overrideProvider(MatSnackBar, { useValue: mockSnackBar });

    await TestBed.compileComponents();

    translateService = TestBed.inject(TranslateService);
    translateService.use('fr');

    fixture = TestBed.createComponent(AdminSettingsComponent);
    component = fixture.componentInstance;
  });

  // =============================================================================
  // INITIALIZATION TESTS
  // =============================================================================

  describe('Initialization', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should load settings on init', () => {
      fixture.detectChanges();
      expect(mockSettingsService.loadSettings).toHaveBeenCalled();
    });

    it('should have no preview image initially', () => {
      fixture.detectChanges();
      expect(component.previewImage()).toBeNull();
    });

    it('should have no selected file initially', () => {
      fixture.detectChanges();
      expect(component.selectedFile()).toBeNull();
    });

    it('should not be saving initially', () => {
      fixture.detectChanges();
      expect(component.isSaving()).toBe(false);
    });
  });

  // =============================================================================
  // currentImageUrl TESTS
  // =============================================================================

  describe('currentImageUrl', () => {
    it('should return preview image when set', () => {
      fixture.detectChanges();
      component.previewImage.set('data:image/jpeg;base64,preview');
      expect(component.currentImageUrl).toBe('data:image/jpeg;base64,preview');
    });

    it('should return config URL when no preview', () => {
      fixture.detectChanges();
      expect(component.currentImageUrl).toBe(mockConfig.homepage_image_url);
    });

    it('should return default image when no config URL', () => {
      // Reset config to no image
      configSignal.set({
        ...mockConfig,
        homepage_image: null,
        homepage_image_url: null
      });
      fixture.detectChanges();
      expect(component.currentImageUrl).toBe('assets/images/homepage-default.jpg');
    });
  });

  // =============================================================================
  // hasCustomImage TESTS
  // =============================================================================

  describe('hasCustomImage', () => {
    it('should return true when config has image', () => {
      fixture.detectChanges();
      expect(component.hasCustomImage).toBe(true);
    });

    it('should return false when config has no image', () => {
      configSignal.set({
        ...mockConfig,
        homepage_image: null
      });
      fixture.detectChanges();
      expect(component.hasCustomImage).toBe(false);
    });

    it('should return false when config is null', () => {
      configSignal.set(null);
      fixture.detectChanges();
      expect(component.hasCustomImage).toBe(false);
    });
  });

  // =============================================================================
  // onFileSelected TESTS
  // =============================================================================

  describe('onFileSelected', () => {
    it('should reject non-image files', () => {
      fixture.detectChanges();

      const file = new File(['test'], 'test.txt', { type: 'text/plain' });
      const event = {
        target: {
          files: [file]
        }
      } as unknown as Event;

      component.onFileSelected(event);

      expect(component.selectedFile()).toBeNull();
      expect(mockSnackBar.open).toHaveBeenCalled();
    });

    it('should handle empty file list', () => {
      fixture.detectChanges();

      const event = {
        target: {
          files: []
        }
      } as unknown as Event;

      component.onFileSelected(event);

      expect(component.selectedFile()).toBeNull();
    });
  });

  // =============================================================================
  // uploadImage TESTS
  // =============================================================================

  describe('uploadImage', () => {
    it('should not upload if no file selected', () => {
      fixture.detectChanges();
      component.uploadImage();
      expect(mockSettingsService.updateSettings).not.toHaveBeenCalled();
    });

    it('should upload selected file', fakeAsync(() => {
      fixture.detectChanges();

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      component.selectedFile.set(file);

      component.uploadImage();
      tick();

      // With synchronous mocks, isSaving transitions from true to false immediately
      expect(component.isSaving()).toBe(false);
      expect(mockSettingsService.updateSettings).toHaveBeenCalled();
    }));

    it('should show success message after upload', fakeAsync(() => {
      fixture.detectChanges();

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      component.selectedFile.set(file);

      component.uploadImage();
      tick();

      expect(mockSnackBar.open).toHaveBeenCalled();
    }));

    it('should handle upload error', fakeAsync(() => {
      fixture.detectChanges();

      // Set the error mock AFTER fixture.detectChanges() to avoid affecting loadSettings
      (mockSettingsService.updateSettings as jest.Mock).mockReturnValue(
        throwError(() => new Error('Upload failed'))
      );

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      component.selectedFile.set(file);

      component.uploadImage();
      tick();

      expect(component.isSaving()).toBe(false);
      expect(mockSnackBar.open).toHaveBeenCalled();
    }));
  });

  // =============================================================================
  // cancelSelection TESTS
  // =============================================================================

  describe('cancelSelection', () => {
    it('should clear preview and selected file', () => {
      fixture.detectChanges();

      component.previewImage.set('data:image/jpeg;base64,test');
      component.selectedFile.set(new File(['test'], 'test.jpg'));

      component.cancelSelection();

      expect(component.previewImage()).toBeNull();
      expect(component.selectedFile()).toBeNull();
    });
  });

  // =============================================================================
  // resetToDefault TESTS
  // =============================================================================

  describe('resetToDefault', () => {
    it('should call resetHomepageImage', fakeAsync(() => {
      fixture.detectChanges();

      component.resetToDefault();
      tick();

      // With synchronous mocks, isSaving transitions from true to false immediately
      expect(component.isSaving()).toBe(false);
      expect(mockSettingsService.resetHomepageImage).toHaveBeenCalled();
    }));

    it('should show success message after reset', fakeAsync(() => {
      fixture.detectChanges();

      component.resetToDefault();
      tick();

      expect(mockSnackBar.open).toHaveBeenCalled();
    }));

    it('should handle reset error', fakeAsync(() => {
      fixture.detectChanges();

      // Set the error mock AFTER fixture.detectChanges() to avoid affecting loadSettings
      (mockSettingsService.resetHomepageImage as jest.Mock).mockReturnValue(
        throwError(() => new Error('Reset failed'))
      );

      component.resetToDefault();
      tick();

      expect(component.isSaving()).toBe(false);
      expect(mockSnackBar.open).toHaveBeenCalled();
    }));
  });

  // =============================================================================
  // formatDate TESTS
  // =============================================================================

  describe('formatDate', () => {
    it('should format date correctly', () => {
      fixture.detectChanges();
      const result = component.formatDate('2024-01-15T10:30:00Z');

      // Verify it returns a formatted string (format depends on locale)
      expect(result).toBeTruthy();
      expect(result.length).toBeGreaterThan(0);
    });

    it('should return empty string for undefined', () => {
      fixture.detectChanges();
      expect(component.formatDate(undefined)).toBe('');
    });

    it('should return empty string for empty string', () => {
      fixture.detectChanges();
      expect(component.formatDate('')).toBe('');
    });
  });
});
