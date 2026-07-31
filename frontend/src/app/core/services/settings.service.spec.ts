import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { SettingsService, SiteConfiguration } from './settings.service';

describe('SettingsService', () => {
  let service: SettingsService;
  let httpMock: HttpTestingController;

  const mockConfig: SiteConfiguration = {
    homepage_image: 'settings/homepage/image.jpg',
    homepage_image_url: 'http://localhost:8000/media/settings/homepage/image.jpg',
    homepage_image_position: 'center',
    header_color: '#025359',
    export_color: '#025359',
    structure_logo: null,
    structure_logo_url: null,
    enable_docgestion_fcen: false,
    updated_at: '2024-01-15T10:30:00Z',
    updated_by: 1,
    updated_by_name: 'Admin User'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [SettingsService]
    });

    service = TestBed.inject(SettingsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // =============================================================================
  // INITIAL STATE TESTS
  // =============================================================================

  describe('Initial State', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have null config initially', () => {
      expect(service.config()).toBeNull();
    });

    it('should not be loading initially', () => {
      expect(service.isLoading()).toBe(false);
    });

    it('should have no error initially', () => {
      expect(service.error()).toBeNull();
    });

    it('should have a default homepage image path', () => {
      expect(service.defaultHomepageImage).toBe('assets/images/homepage-default.jpg');
    });
  });

  // =============================================================================
  // getHomepageImageUrl TESTS
  // =============================================================================

  describe('getHomepageImageUrl', () => {
    it('should return default image when config is null', () => {
      expect(service.getHomepageImageUrl()).toBe('assets/images/homepage-default.jpg');
    });

    it('should return custom URL when config has homepage_image_url', fakeAsync(() => {
      service.loadSettings().subscribe();

      const req = httpMock.expectOne('/api/settings/');
      req.flush(mockConfig);
      tick();

      expect(service.getHomepageImageUrl()).toBe(mockConfig.homepage_image_url);
    }));

    it('should return default when config has no image', fakeAsync(() => {
      const configNoImage: SiteConfiguration = {
        ...mockConfig,
        homepage_image: null,
        homepage_image_url: null
      };

      service.loadSettings().subscribe();

      const req = httpMock.expectOne('/api/settings/');
      req.flush(configNoImage);
      tick();

      expect(service.getHomepageImageUrl()).toBe('assets/images/homepage-default.jpg');
    }));
  });

  // =============================================================================
  // #458 — ID Doc'Gestion FCEN : paramètre d'instance
  // =============================================================================

  describe('isDocGestionFcenEnabled (#458)', () => {
    it('should be false before the configuration is loaded', () => {
      expect(service.isDocGestionFcenEnabled()).toBe(false);
    });

    it('should be false when the instance has not enabled it', fakeAsync(() => {
      service.loadSettings().subscribe();

      httpMock.expectOne('/api/settings/').flush(mockConfig);
      tick();

      expect(service.isDocGestionFcenEnabled()).toBe(false);
    }));

    it('should be true when the instance has enabled it', fakeAsync(() => {
      service.loadSettings().subscribe();

      httpMock.expectOne('/api/settings/').flush({
        ...mockConfig,
        enable_docgestion_fcen: true
      });
      tick();

      expect(service.isDocGestionFcenEnabled()).toBe(true);
    }));

    it('should stay false when the configuration fails to load', fakeAsync(() => {
      service.loadSettings().subscribe();

      httpMock
        .expectOne('/api/settings/')
        .flush('error', { status: 500, statusText: 'Server Error' });
      tick();

      expect(service.isDocGestionFcenEnabled()).toBe(false);
    }));
  });

  // =============================================================================
  // loadSettings TESTS
  // =============================================================================

  describe('loadSettings', () => {
    it('should load settings successfully', fakeAsync(() => {
      let result: SiteConfiguration | undefined;

      service.loadSettings().subscribe(config => {
        result = config;
      });

      expect(service.isLoading()).toBe(true);

      const req = httpMock.expectOne('/api/settings/');
      expect(req.request.method).toBe('GET');
      req.flush(mockConfig);
      tick();

      expect(result).toEqual(mockConfig);
      expect(service.config()).toEqual(mockConfig);
      expect(service.isLoading()).toBe(false);
      expect(service.error()).toBeNull();
    }));

    it('should handle error gracefully', fakeAsync(() => {
      let result: SiteConfiguration | undefined;

      service.loadSettings().subscribe(config => {
        result = config;
      });

      const req = httpMock.expectOne('/api/settings/');
      req.error(new ProgressEvent('error'), { status: 500 });
      tick();

      // Should return empty config
      expect(result).toEqual({
        homepage_image: null,
        homepage_image_url: null,
        homepage_image_position: 'top',
        header_color: '#FFFFFF',
        export_color: '#025359',
        structure_logo: null,
        structure_logo_url: null,
        enable_docgestion_fcen: false,
        updated_at: '',
        updated_by: null,
        updated_by_name: null
      });
      expect(service.isLoading()).toBe(false);
      expect(service.error()).toBe('Unable to load site configuration');
    }));

    it('should clear previous error on new load', fakeAsync(() => {
      // First load with error
      service.loadSettings().subscribe();
      const req1 = httpMock.expectOne('/api/settings/');
      req1.error(new ProgressEvent('error'), { status: 500 });
      tick();

      expect(service.error()).toBe('Unable to load site configuration');

      // Second load should clear error
      service.loadSettings().subscribe();
      expect(service.error()).toBeNull();

      const req2 = httpMock.expectOne('/api/settings/');
      req2.flush(mockConfig);
      tick();
    }));
  });

  // =============================================================================
  // updateSettings TESTS
  // =============================================================================

  describe('updateSettings', () => {
    it('should update settings successfully', fakeAsync(() => {
      const formData = new FormData();
      formData.append('homepage_image', new Blob(['test']), 'test.jpg');

      let result: SiteConfiguration | undefined;

      service.updateSettings(formData).subscribe(config => {
        result = config;
      });

      expect(service.isLoading()).toBe(true);

      const req = httpMock.expectOne('/api/settings/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockConfig);
      tick();

      expect(result).toEqual(mockConfig);
      expect(service.config()).toEqual(mockConfig);
      expect(service.isLoading()).toBe(false);
    }));

    it('should handle update error', fakeAsync(() => {
      const formData = new FormData();
      let errorCaught = false;

      service.updateSettings(formData).subscribe({
        error: () => {
          errorCaught = true;
        }
      });

      const req = httpMock.expectOne('/api/settings/');
      req.error(new ProgressEvent('error'), { status: 403 });
      tick();

      expect(errorCaught).toBe(true);
      expect(service.isLoading()).toBe(false);
      expect(service.error()).toBe('Unable to update site configuration');
    }));
  });

  // =============================================================================
  // resetHomepageImage TESTS
  // =============================================================================

  describe('resetHomepageImage', () => {
    it('should send reset_image flag', fakeAsync(() => {
      const resetConfig: SiteConfiguration = {
        ...mockConfig,
        homepage_image: null,
        homepage_image_url: null
      };

      let result: SiteConfiguration | undefined;

      service.resetHomepageImage().subscribe(config => {
        result = config;
      });

      const req = httpMock.expectOne('/api/settings/');
      expect(req.request.method).toBe('PATCH');

      // Check that FormData contains reset_image
      const body = req.request.body as FormData;
      expect(body.get('reset_image')).toBe('true');

      req.flush(resetConfig);
      tick();

      expect(result?.homepage_image).toBeNull();
      expect(result?.homepage_image_url).toBeNull();
    }));

    it('should update config signal after reset', fakeAsync(() => {
      // First set a config with image
      service.loadSettings().subscribe();
      const loadReq = httpMock.expectOne('/api/settings/');
      loadReq.flush(mockConfig);
      tick();

      expect(service.config()?.homepage_image).not.toBeNull();

      // Then reset
      const resetConfig: SiteConfiguration = {
        ...mockConfig,
        homepage_image: null,
        homepage_image_url: null
      };

      service.resetHomepageImage().subscribe();

      const resetReq = httpMock.expectOne('/api/settings/');
      resetReq.flush(resetConfig);
      tick();

      expect(service.config()?.homepage_image).toBeNull();
    }));
  });

  // =============================================================================
  // SIGNAL UPDATES TESTS
  // =============================================================================

  describe('Signal Updates', () => {
    it('should update config signal on successful load', fakeAsync(() => {
      expect(service.config()).toBeNull();

      service.loadSettings().subscribe();
      const req = httpMock.expectOne('/api/settings/');
      req.flush(mockConfig);
      tick();

      expect(service.config()).toEqual(mockConfig);
    }));

    it('should maintain isLoading state correctly', fakeAsync(() => {
      expect(service.isLoading()).toBe(false);

      service.loadSettings().subscribe();
      expect(service.isLoading()).toBe(true);

      const req = httpMock.expectOne('/api/settings/');
      req.flush(mockConfig);
      tick();

      expect(service.isLoading()).toBe(false);
    }));

    it('should update error signal on failure', fakeAsync(() => {
      expect(service.error()).toBeNull();

      service.loadSettings().subscribe();
      const req = httpMock.expectOne('/api/settings/');
      req.error(new ProgressEvent('error'), { status: 500 });
      tick();

      expect(service.error()).toBe('Unable to load site configuration');
    }));
  });
});
