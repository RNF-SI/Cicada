import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { BehaviorSubject, NEVER, Subject, of, throwError } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';
import { ActivatedRoute, convertToParamMap, ParamMap, Router } from '@angular/router';

import { AdminSettingsComponent } from './admin-settings.component';
import { SettingsService, SiteConfiguration } from '../../../core/services/settings.service';
import { FederationRaccordementService } from '../../../core/services/federation-raccordement.service';
import { AuthService } from '../../../core/services/auth.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

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
  let mockDialog: { open: jest.Mock };
  let translateService: TranslateService;
  let queryParamMap$: BehaviorSubject<ParamMap>;
  let mockRouter: { navigate: jest.Mock };
  let mockActivatedRoute: { queryParamMap: BehaviorSubject<ParamMap> };
  let mockFederationService: { etat: jest.Mock; verifier: jest.Mock; demanderAdhesion: jest.Mock };

  // Writable signals for mocking
  let configSignal: WritableSignal<SiteConfiguration | null>;
  let isLoadingSignal: WritableSignal<boolean>;

  const mockConfig: SiteConfiguration = {
    homepage_image: 'settings/homepage/image.jpg',
    homepage_image_url: 'http://localhost:8000/media/settings/homepage/image.jpg',
    homepage_image_position: 'center',
    header_color: '#025359',
    export_color: '#025359',
    structure_logo: null,
    structure_logo_url: null,
    accueil_titre: '',
    accueil_sous_titre: '',
    enable_docgestion_fcen: false,
    federation_partage: false,
    api_publique_plans: false,
    matomo_enabled: false,
    matomo_url: '',
    matomo_site_id: '',
    inscription_url_externe: '',
    taille_max_document_mo: 20,
    cgu_texte: '# CGU',
    cgu_version: '2026-10-21T10:00:00Z',
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
      })),
      resetStructureLogo: jest.fn().mockReturnValue(of({
        ...mockConfig,
        structure_logo: null,
        structure_logo_url: null
      }))
    };

    mockSnackBar = {
      open: jest.fn()
    };
    mockDialog = { open: jest.fn() };

    queryParamMap$ = new BehaviorSubject<ParamMap>(convertToParamMap({}));
    mockActivatedRoute = { queryParamMap: queryParamMap$ };
    mockRouter = { navigate: jest.fn().mockResolvedValue(true) };
    mockFederationService = {
      etat: jest.fn().mockReturnValue(NEVER),
      verifier: jest.fn(),
      demanderAdhesion: jest.fn(),
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
        { provide: MatSnackBar, useValue: mockSnackBar },
        { provide: MatDialog, useValue: mockDialog },
        // #696 — le bloc de raccordement a sa propre spec : ici il reste muet.
        { provide: FederationRaccordementService, useValue: mockFederationService },
        // Le bloc du raccordement pré-remplit la demande d'adhésion avec l'utilisateur connecté.
        { provide: AuthService, useValue: { currentUser: () => null, getUserDisplayName: () => '' } },
        { provide: ActivatedRoute, useValue: mockActivatedRoute },
        { provide: Router, useValue: mockRouter },
      ]
    });

    // Override provider for standalone component (must be before compileComponents)
    TestBed.overrideProvider(MatSnackBar, { useValue: mockSnackBar });
    TestBed.overrideProvider(MatDialog, { useValue: mockDialog });

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
    // #725 — Rétablir l'image par défaut SUPPRIME le fichier déposé : un clic
    // de trop effaçait l'image d'accueil sans retour possible. Une
    // confirmation est désormais demandée.
    const confirmer = (reponse: boolean) =>
      mockDialog.open.mockReturnValue({ afterClosed: () => of(reponse) });

    it('demande confirmation avant de supprimer l\'image (#725)', () => {
      fixture.detectChanges();
      confirmer(false);
      component.resetToDefault();
      expect(mockDialog.open).toHaveBeenCalledWith(ConfirmDialogComponent, expect.objectContaining({
        data: expect.objectContaining({ destructive: true }),
      }));
    });

    it('ne supprime rien si la confirmation est annulée (#725)', () => {
      fixture.detectChanges();
      confirmer(false);
      component.resetToDefault();
      expect(mockSettingsService.resetHomepageImage).not.toHaveBeenCalled();
    });

    it('should call resetHomepageImage once confirmed', fakeAsync(() => {
      fixture.detectChanges();
      confirmer(true);

      component.resetToDefault();
      tick();

      // With synchronous mocks, isSaving transitions from true to false immediately
      expect(component.isSaving()).toBe(false);
      expect(mockSettingsService.resetHomepageImage).toHaveBeenCalled();
    }));

    it('should show success message after reset', fakeAsync(() => {
      fixture.detectChanges();
      confirmer(true);

      component.resetToDefault();
      tick();

      expect(mockSnackBar.open).toHaveBeenCalled();
    }));

    it('should handle reset error', fakeAsync(() => {
      fixture.detectChanges();
      confirmer(true);

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

  describe('resetLogo (#725)', () => {
    const confirmer = (reponse: boolean) =>
      mockDialog.open.mockReturnValue({ afterClosed: () => of(reponse) });

    it('demande confirmation et ne supprime rien si on annule', () => {
      fixture.detectChanges();
      confirmer(false);
      component.resetLogo();
      expect(mockDialog.open).toHaveBeenCalledWith(ConfirmDialogComponent, expect.anything());
      expect(mockSettingsService.resetStructureLogo).not.toHaveBeenCalled();
    });

    it('supprime le logo une fois confirmé', () => {
      fixture.detectChanges();
      confirmer(true);
      component.resetLogo();
      expect(mockSettingsService.resetStructureLogo).toHaveBeenCalled();
    });
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

  // =============================================================================
  // #670 — MESURE D'AUDIENCE MATOMO
  // =============================================================================

  describe('Partage avec l\'exploration nationale (#636)', () => {
    const updateSettings = () => mockSettingsService.updateSettings as jest.Mock;
    const lastFormData = (): FormData => updateSettings().mock.calls.at(-1)[0];

    beforeEach(() => {
      configSignal.set({ ...mockConfig, federation_partage: true });
      fixture.detectChanges();
    });

    it('cocher enregistre directement, sans confirmation', () => {
      configSignal.set({ ...mockConfig, federation_partage: false });
      fixture.detectChanges();

      component.onFederationPartageToggle(true);

      expect(mockDialog.open).not.toHaveBeenCalled();
      expect(lastFormData().get('federation_partage')).toBe('true');
    });

    it('décocher ouvre une confirmation destructive', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => NEVER });

      component.onFederationPartageToggle(false);

      expect(mockDialog.open).toHaveBeenCalledWith(ConfirmDialogComponent, expect.objectContaining({
        data: expect.objectContaining({
          destructive: true,
          message: 'admin.settings.federation.retrait.message',
        }),
      }));
      expect(updateSettings()).not.toHaveBeenCalled();
    });

    it('annuler garde la case cochée et n\'envoie rien', () => {
      const fermeture = new Subject<boolean | undefined>();
      mockDialog.open.mockReturnValue({ afterClosed: () => fermeture });

      component.onFederationPartageToggle(false);
      fermeture.next(false);
      fixture.detectChanges();

      expect(updateSettings()).not.toHaveBeenCalled();
      expect(component.federationPartage()).toBe(true);
    });

    it('fermer la fenêtre sans choisir vaut annulation', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(undefined) });

      component.onFederationPartageToggle(false);

      expect(updateSettings()).not.toHaveBeenCalled();
      expect(component.federationPartage()).toBe(true);
    });

    it('confirmer enregistre le retrait du partage', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      component.onFederationPartageToggle(false);

      expect(updateSettings()).toHaveBeenCalledTimes(1);
      expect(lastFormData().get('federation_partage')).toBe('false');
      expect(component.federationPartage()).toBe(false);
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'admin.settings.federation.messages.desactive', expect.anything(), expect.anything(),
      );
    });

    it('un échec d\'enregistrement recoche la case', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
      updateSettings().mockReturnValue(throwError(() => new Error('500')));

      component.onFederationPartageToggle(false);

      expect(component.federationPartage()).toBe(true);
    });
  });

  describe('Matomo (#670)', () => {
    const lastFormData = (): FormData =>
      (mockSettingsService.updateSettings as jest.Mock).mock.calls.at(-1)[0];

    it('reprend les réglages de l\'instance', () => {
      configSignal.set({
        ...mockConfig,
        matomo_enabled: true,
        matomo_url: 'https://matomo.example.org',
        matomo_site_id: '12',
      });
      fixture.detectChanges();

      expect(component.matomoEnabled()).toBe(true);
      expect(component.matomoUrl()).toBe('https://matomo.example.org');
      expect(component.matomoSiteId()).toBe('12');
    });

    it('enregistre l\'activation, l\'URL et l\'identifiant en un clic', fakeAsync(() => {
      fixture.detectChanges();
      component.matomoEnabled.set(true);
      component.matomoUrl.set(' https://matomo.example.org ');
      component.matomoSiteId.set('12');

      component.saveMatomo();
      tick();

      const data = lastFormData();
      expect(data.get('matomo_enabled')).toBe('true');
      expect(data.get('matomo_url')).toBe('https://matomo.example.org');
      expect(data.get('matomo_site_id')).toBe('12');
      expect(mockSnackBar.open).toHaveBeenCalled();
    }));

    it('refuse d\'activer sans URL ni identifiant, sans appeler l\'API', () => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockClear();
      component.matomoEnabled.set(true);

      component.saveMatomo();

      expect(mockSettingsService.updateSettings).not.toHaveBeenCalled();
      expect(component.matomoError()).toBeTruthy();
    });

    it('affiche l\'erreur renvoyée par le serveur', fakeAsync(() => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockReturnValueOnce(
        throwError(() => ({ error: { matomo_url: ['Saisissez une URL valide.'] } })),
      );
      component.matomoUrl.set('pas une url');
      component.matomoSiteId.set('12');

      component.saveMatomo();
      tick();

      expect(component.matomoError()).toBe('Saisissez une URL valide.');
    }));
  });

  describe('Inscription externe (#724)', () => {
    const lastFormData = (): FormData =>
      (mockSettingsService.updateSettings as jest.Mock).mock.calls.at(-1)[0];

    it('reprend l\'URL de l\'instance', () => {
      configSignal.set({ ...mockConfig, inscription_url_externe: 'https://inscription.example.org' });
      fixture.detectChanges();
      expect(component.inscriptionUrl()).toBe('https://inscription.example.org');
    });

    it('enregistre l\'URL (espaces retirés)', fakeAsync(() => {
      fixture.detectChanges();
      component.inscriptionUrl.set(' https://inscription.example.org ');
      component.saveInscription();
      tick();
      expect(lastFormData().get('inscription_url_externe')).toBe('https://inscription.example.org');
      expect(mockSnackBar.open).toHaveBeenCalled();
    }));

    it('un champ vidé rétablit l\'inscription dans CICADA', fakeAsync(() => {
      fixture.detectChanges();
      component.inscriptionUrl.set('');
      component.saveInscription();
      tick();
      expect(lastFormData().get('inscription_url_externe')).toBe('');
    }));

    it('affiche l\'erreur renvoyée par le serveur', fakeAsync(() => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockReturnValueOnce(
        throwError(() => ({ error: { inscription_url_externe: ['Saisissez une URL valide.'] } })),
      );
      component.inscriptionUrl.set('pas une url');
      component.saveInscription();
      tick();
      expect(component.inscriptionError()).toBe('Saisissez une URL valide.');
    }));
  });

  describe('CGU (#746)', () => {
    const lastFormData = (): FormData =>
      (mockSettingsService.updateSettings as jest.Mock).mock.calls.at(-1)[0];

    it('reprend le texte de l\'instance', () => {
      configSignal.set({ ...mockConfig, cgu_texte: '# Mes CGU' });
      fixture.detectChanges();
      expect(component.cguTexte()).toBe('# Mes CGU');
    });

    it('publie une nouvelle version après confirmation', fakeAsync(() => {
      fixture.detectChanges();
      jest.spyOn(component['dialog'], 'open').mockReturnValue({ afterClosed: () => of(true) } as never);
      component.cguTexte.set('# V2');
      component.saveCgu();
      tick();
      expect(lastFormData().get('cgu_texte')).toBe('# V2');
    }));

    it('n\'envoie rien si la confirmation est annulée', fakeAsync(() => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockClear();
      jest.spyOn(component['dialog'], 'open').mockReturnValue({ afterClosed: () => of(false) } as never);
      component.cguTexte.set('# V2');
      component.saveCgu();
      tick();
      expect(mockSettingsService.updateSettings).not.toHaveBeenCalled();
    }));

    it('refuse un texte vide sans appeler le serveur', () => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockClear();
      component.cguTexte.set('   ');
      component.saveCgu();
      expect(mockSettingsService.updateSettings).not.toHaveBeenCalled();
      expect(component.cguError()).toBeTruthy();
    });
  });

  describe('Taille maximale d\'un document (#745)', () => {
    const lastFormData = (): FormData =>
      (mockSettingsService.updateSettings as jest.Mock).mock.calls.at(-1)[0];

    it('reprend la limite de l\'instance', () => {
      configSignal.set({ ...mockConfig, taille_max_document_mo: 50 });
      fixture.detectChanges();
      expect(component.tailleMaxDocument()).toBe(50);
    });

    it('enregistre la limite', fakeAsync(() => {
      fixture.detectChanges();
      component.tailleMaxDocument.set(100);
      component.saveTailleMaxDocument();
      tick();
      expect(lastFormData().get('taille_max_document_mo')).toBe('100');
    }));

    it.each([0, 1025, 2.5, null])('refuse %p sans appeler le serveur', (valeur) => {
      fixture.detectChanges();
      (mockSettingsService.updateSettings as jest.Mock).mockClear();
      component.tailleMaxDocument.set(valeur);
      component.saveTailleMaxDocument();
      expect(mockSettingsService.updateSettings).not.toHaveBeenCalled();
      expect(component.tailleMaxError()).toBeTruthy();
    });
  });

  // =============================================================================
  // ONGLETS THÉMATIQUES (?onglet=)
  // =============================================================================

  describe('Onglets', () => {
    const libellesOnglets = (): HTMLElement[] =>
      Array.from(fixture.nativeElement.querySelectorAll('.mat-mdc-tab')) as HTMLElement[];
    const raccordement = (): Element | null =>
      fixture.nativeElement.querySelector('app-federation-raccordement');

    it('affiche cinq onglets (dont « Connexion », #769) et ouvre « Apparence » par défaut', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      expect(libellesOnglets().length).toBe(5);
      expect(component.ongletIndex()).toBe(0);
      expect(fixture.nativeElement.textContent).toContain('Image de la page d\'accueil');
    });

    it('n\'instancie pas le raccordement au hub hors de son onglet', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      expect(raccordement()).toBeNull();
      expect(mockFederationService.etat).not.toHaveBeenCalled();
    });

    it('ouvre l\'onglet demandé par ?onglet= (et seulement alors le raccordement)', async () => {
      queryParamMap$.next(convertToParamMap({ onglet: 'exploration' }));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(component.ongletIndex()).toBe(3);
      expect(raccordement()).not.toBeNull();
      expect(mockFederationService.etat).toHaveBeenCalled();
    });

    it.each([
      ['apparence', 0],
      ['exports', 1],
      ['fonctionnalites', 2],
      ['exploration', 3],
      ['inconnu', 0],
    ])('?onglet=%s → onglet %i', (onglet, index) => {
      queryParamMap$.next(convertToParamMap({ onglet }));
      fixture.detectChanges();
      expect(component.ongletIndex()).toBe(index);
    });

    it('reporte l\'onglet choisi dans l\'URL sans empiler d\'historique', () => {
      fixture.detectChanges();

      component.onOngletChange(1);

      expect(mockRouter.navigate).toHaveBeenCalledWith([], {
        relativeTo: mockActivatedRoute,
        queryParams: { onglet: 'exports' },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    });

    it('met l\'URL à jour au clic sur un onglet', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      libellesOnglets()[2].click();
      fixture.detectChanges();
      await fixture.whenStable();

      expect(mockRouter.navigate).toHaveBeenCalledWith(
        [],
        expect.objectContaining({ queryParams: { onglet: 'fonctionnalites' } }),
      );
    });
  });
  describe('Textes de la page d\'accueil (#710)', () => {
    it('reprend les textes enregistrés', () => {
      configSignal.set({ ...mockConfig, accueil_titre: 'Portail CEN', accueil_sous_titre: 'Bienvenue' });
      fixture.detectChanges();

      expect(component.accueilTitre()).toBe('Portail CEN');
      expect(component.accueilSousTitre()).toBe('Bienvenue');
    });

    it('enregistre les textes, rognés (vide = texte par défaut)', () => {
      fixture.detectChanges();
      component.accueilTitre.set('  Portail CEN  ');
      component.accueilSousTitre.set('   ');

      component.saveTextesAccueil();

      const formData = (mockSettingsService.updateSettings as jest.Mock).mock.calls[0][0] as FormData;
      expect(formData.get('accueil_titre')).toBe('Portail CEN');
      expect(formData.get('accueil_sous_titre')).toBe('');
      expect(mockSnackBar.open).toHaveBeenCalled();
    });
  });
});
