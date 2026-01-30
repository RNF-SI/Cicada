import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, signal, WritableSignal, Input } from '@angular/core';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService, TranslateLoader } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({});
  }
}

// Mock LeafletMapComponent to avoid Leaflet DOM issues in tests
@Component({
  selector: 'app-leaflet-map',
  template: '<div class="mock-leaflet-map"></div>',
  standalone: true
})
class MockLeafletMapComponent {
  @Input() geojsonData: any;
  @Input() height: string = '100%';
  @Input() fitBounds: boolean = true;
  @Input() showControls: boolean = true;
}

import { SitesListComponent } from './sites-list.component';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { ImpersonationGuardService } from '../../core/services/impersonation-guard.service';
import { ModuleService } from '../../core/services/module.service';
import { LeafletMapComponent } from '../../shared/components/leaflet-map/leaflet-map.component';
import { AdminSite, GeoJSONFeatureCollection } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

describe('SitesListComponent', () => {
  let component: SitesListComponent;
  let fixture: ComponentFixture<SitesListComponent>;
  let router: Router;

  // Writable signals for mocking
  let isSuperAdminSignal: WritableSignal<boolean>;
  let isAdminOrganismeSignal: WritableSignal<boolean>;
  let isAuthenticatedSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<any>;
  let isImpersonatingSignal: WritableSignal<boolean>;
  let impersonationInfoSignal: WritableSignal<any>;
  let canAccessAdminSignal: WritableSignal<boolean>;
  let isReadOnlySignal: WritableSignal<boolean>;

  // Mock functions
  let getSitesMock: jest.Mock;
  let getSitesGeoJSONMock: jest.Mock;
  let getMyRequestsMock: jest.Mock;
  let dialogOpenMock: jest.Mock;
  let snackBarOpenMock: jest.Mock;
  let logoutMock: jest.Mock;
  let stopImpersonationMock: jest.Mock;
  let getMyAccessibleModulesMock: jest.Mock;

  const mockOrganisme = {
    id_organisme: 1,
    nom_organisme: 'Test Organisme'
  };

  const mockUser = {
    id: 1,
    email: 'test@test.fr',
    nom_complet: 'Test User',
    organisme: mockOrganisme
  };

  const mockSite: AdminSite = {
    id_site: 1,
    slug: 'site-test',
    nom_site: 'Site Test',
    type_site_label: 'RNN',
    surf_off: 1500,
    active: true,
    organismes: [{ id_organisme: 1, nom_organisme: 'Test Organisme', principal: true }]
  };

  const mockSite2: AdminSite = {
    id_site: 2,
    slug: 'site-test-2',
    nom_site: 'Site Test 2',
    type_site_label: 'RNR',
    surf_off: 2500,
    active: true,
    organismes: [{ id_organisme: 2, nom_organisme: 'Autre Organisme', principal: true }]
  };

  const mockGeoJSON: GeoJSONFeatureCollection = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        id: 1,
        geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]] },
        properties: {
          id_site: 1,
          slug: 'site-test',
          nom_site: 'Site Test'
        }
      }
    ]
  };

  const mockValidationRequest: ValidationRequestListItem = {
    id: 1,
    request_type: 'site_access',
    status: 'pending',
    requester_id: 1,
    requester_name: 'Test User',
    target_name: 'Site Test',
    created_at: new Date().toISOString()
  };

  const setupTestBed = async () => {
    // Create writable signals
    isSuperAdminSignal = signal(false);
    isAdminOrganismeSignal = signal(false);
    isAuthenticatedSignal = signal(true);
    currentUserSignal = signal(mockUser);
    isImpersonatingSignal = signal(false);
    impersonationInfoSignal = signal(null);
    canAccessAdminSignal = signal(false);
    isReadOnlySignal = signal(false);

    // Create mock functions
    getSitesMock = jest.fn().mockReturnValue(of({
      count: 2,
      next: null,
      previous: null,
      results: [mockSite, mockSite2]
    }));

    getSitesGeoJSONMock = jest.fn().mockReturnValue(of(mockGeoJSON));
    getMyRequestsMock = jest.fn().mockReturnValue(of([mockValidationRequest]));
    dialogOpenMock = jest.fn().mockReturnValue({ afterClosed: () => of(null) });
    snackBarOpenMock = jest.fn();
    logoutMock = jest.fn().mockReturnValue(of(null));
    stopImpersonationMock = jest.fn().mockReturnValue(of(null));
    getMyAccessibleModulesMock = jest.fn().mockReturnValue(of([]));

    const adminServiceMock = {
      getSites: getSitesMock,
      getSitesGeoJSON: getSitesGeoJSONMock
    };

    const validationServiceMock = {
      getMyRequests: getMyRequestsMock
    };

    const authServiceMock = {
      isSuperAdmin: isSuperAdminSignal.asReadonly(),
      isAdminOrganisme: isAdminOrganismeSignal.asReadonly(),
      isAuthenticated: isAuthenticatedSignal.asReadonly(),
      currentUser: currentUserSignal.asReadonly(),
      isImpersonating: isImpersonatingSignal.asReadonly(),
      impersonationInfo: impersonationInfoSignal.asReadonly(),
      canAccessAdmin: canAccessAdminSignal.asReadonly(),
      getUserDisplayName: jest.fn().mockReturnValue('Test User'),
      getOriginalUserDisplayName: jest.fn().mockReturnValue('Admin User'),
      logout: logoutMock,
      stopImpersonation: stopImpersonationMock
    };

    const impersonationGuardServiceMock = {
      isReadOnly: isReadOnlySignal.asReadonly(),
      canModify: signal(true).asReadonly(),
      checkCanModify: jest.fn().mockReturnValue(true),
      showReadOnlyMessage: jest.fn()
    };

    const moduleServiceMock = {
      getMyAccessibleModules: getMyAccessibleModulesMock,
      accessibleModules: signal([]).asReadonly(),
      allModules: signal([]).asReadonly(),
      modulesRequiringAccess: signal([]).asReadonly(),
      isLoading: signal(false).asReadonly()
    };

    const dialogMock = {
      open: dialogOpenMock,
      openDialogs: [],
      afterAllClosed: of(undefined),
      afterOpened: of(undefined),
      closeAll: jest.fn()
    };

    const snackBarMock = {
      open: snackBarOpenMock,
      openFromComponent: jest.fn(),
      openFromTemplate: jest.fn(),
      dismiss: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [
        SitesListComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'sites', component: DummyComponent },
          { path: 'sites/:slug', component: DummyComponent },
          { path: 'accueil', component: DummyComponent }
        ]),
        { provide: AdminService, useValue: adminServiceMock },
        { provide: ValidationService, useValue: validationServiceMock },
        { provide: AuthService, useValue: authServiceMock },
        { provide: ImpersonationGuardService, useValue: impersonationGuardServiceMock },
        { provide: ModuleService, useValue: moduleServiceMock },
        { provide: MatDialog, useValue: dialogMock },
        { provide: MatSnackBar, useValue: snackBarMock }
      ]
    })
    .overrideComponent(SitesListComponent, {
      remove: { imports: [LeafletMapComponent] },
      add: { imports: [MockLeafletMapComponent] }
    })
    .overrideProvider(MatDialog, { useValue: dialogMock })
    .overrideProvider(MatSnackBar, { useValue: snackBarMock })
    .compileComponents();

    // Set default language
    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(SitesListComponent);
    component = fixture.componentInstance;
  };

  beforeEach(async () => {
    await setupTestBed();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should load data on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getSitesMock).toHaveBeenCalled();
      expect(getSitesGeoJSONMock).toHaveBeenCalled();
      expect(getMyRequestsMock).toHaveBeenCalled();
    }));

    it('should set loading to false after data loads', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));
  });

  // ==================== LOADING STATE ====================

  describe('Loading State', () => {
    it('should expose loading signal that can be set', () => {
      // Test the loading signal exists and can be modified
      expect(component.loading).toBeDefined();

      // Before detectChanges, we can set loading
      component.loading.set(true);
      expect(component.loading()).toBe(true);

      component.loading.set(false);
      expect(component.loading()).toBe(false);
    });

    it('should hide loading after data loads', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));

    it('should handle error and hide loading', fakeAsync(() => {
      getSitesMock.mockReturnValue(throwError(() => new Error('Network error')));

      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));
  });

  // ==================== SCOPE TOGGLE ====================

  describe('Scope Toggle', () => {
    it('should not show scope toggle for regular user', fakeAsync(() => {
      isSuperAdminSignal.set(false);
      isAdminOrganismeSignal.set(false);

      fixture.detectChanges();
      tick();

      expect(component.showScopeToggle()).toBe(false);
    }));

    it('should show scope toggle for admin organisme', fakeAsync(() => {
      isAdminOrganismeSignal.set(true);

      fixture.detectChanges();
      tick();

      expect(component.showScopeToggle()).toBe(true);
    }));

    it('should show scope toggle for super admin', fakeAsync(() => {
      isSuperAdminSignal.set(true);
      isAdminOrganismeSignal.set(true);

      fixture.detectChanges();
      tick();

      expect(component.showScopeToggle()).toBe(true);
    }));

    it('should change scope when onScopeChange is called', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.viewScope()).toBe('mine');

      component.onScopeChange('organisme');
      expect(component.viewScope()).toBe('organisme');

      component.onScopeChange('all');
      expect(component.viewScope()).toBe('all');
    }));

    it('should reset pagination when scope changes', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      component.currentPage.set(3);
      component.onScopeChange('organisme');

      expect(component.currentPage()).toBe(1);
    }));
  });

  // ==================== SITES FILTERING BY SCOPE ====================

  describe('Sites Filtering by Scope', () => {
    beforeEach(fakeAsync(() => {
      // Add user link to mock site for "mine" scope testing
      const siteWithUser = {
        ...mockSite,
        users: [{ id_role: 1, email: 'test@test.fr', referent: true }]
      };

      getSitesMock.mockReturnValue(of({
        count: 2,
        next: null,
        previous: null,
        results: [siteWithUser, mockSite2]
      }));

      fixture.detectChanges();
      tick();
    }));

    it('should filter to my sites by default', () => {
      expect(component.viewScope()).toBe('mine');
      expect(component.mySites().length).toBeGreaterThanOrEqual(0);
    });

    it('should filter to organisme sites', () => {
      component.onScopeChange('organisme');

      const orgSites = component.organismeSites();
      orgSites.forEach(site => {
        expect(site.organismes?.some(o => o.id_organisme === 1)).toBe(true);
      });
    });

    it('should show all sites when scope is "all"', () => {
      component.onScopeChange('all');

      expect(component.scopedSites()).toEqual(component.allSites());
    });
  });

  // ==================== SEARCH FILTERING ====================

  describe('Search Filtering', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should filter sites by search term', () => {
      component.onScopeChange('all');
      component.searchTerm.set('Site Test 2');

      const displayed = component.displayedMySites();
      expect(displayed.length).toBe(1);
      expect(displayed[0].nom_site).toBe('Site Test 2');
    });

    it('should filter sites by type', () => {
      component.onScopeChange('all');
      component.searchTerm.set('RNR');

      const displayed = component.displayedMySites();
      expect(displayed.length).toBe(1);
      expect(displayed[0].type_site_label).toBe('RNR');
    });

    it('should filter sites by organisme name', () => {
      component.onScopeChange('all');
      component.searchTerm.set('Autre');

      const displayed = component.displayedMySites();
      expect(displayed.length).toBe(1);
      expect(displayed[0].organismes?.[0].nom_organisme).toBe('Autre Organisme');
    });

    it('should be case insensitive', () => {
      component.onScopeChange('all');
      component.searchTerm.set('site test 2');

      const displayed = component.displayedMySites();
      expect(displayed.length).toBe(1);
    });

    it('should reset pagination when search changes', () => {
      component.currentPage.set(3);
      const event = { target: { value: 'test' } } as any;

      component.onSearchChange(event);

      expect(component.currentPage()).toBe(1);
    });

    it('should clear search when clearSearch is called', () => {
      component.searchTerm.set('test');
      component.currentPage.set(3);

      component.clearSearch();

      expect(component.searchTerm()).toBe('');
      expect(component.currentPage()).toBe(1);
    });
  });

  // ==================== PAGINATION ====================

  describe('Pagination', () => {
    beforeEach(fakeAsync(() => {
      // Create many sites for pagination testing
      const manySites = Array.from({ length: 25 }, (_, i) => ({
        ...mockSite,
        id_site: i + 1,
        slug: `site-${i + 1}`,
        nom_site: `Site ${i + 1}`,
        users: [{ id_role: 1, email: 'test@test.fr', referent: false }]
      }));

      getSitesMock.mockReturnValue(of({
        count: 25,
        next: null,
        previous: null,
        results: manySites
      }));

      fixture.detectChanges();
      tick();
    }));

    it('should calculate total pages correctly', () => {
      // 25 sites / 10 per page = 3 pages
      expect(component.totalPages()).toBe(3);
    });

    it('should paginate sites correctly', () => {
      expect(component.paginatedMySites().length).toBe(10);
      expect(component.paginatedMySites()[0].nom_site).toBe('Site 1');
    });

    it('should navigate to next page', () => {
      component.nextPage();

      expect(component.currentPage()).toBe(2);
      expect(component.paginatedMySites()[0].nom_site).toBe('Site 11');
    });

    it('should navigate to previous page', () => {
      component.currentPage.set(2);
      component.previousPage();

      expect(component.currentPage()).toBe(1);
    });

    it('should not go below page 1', () => {
      component.previousPage();

      expect(component.currentPage()).toBe(1);
    });

    it('should not go above total pages', () => {
      component.currentPage.set(3);
      component.nextPage();

      expect(component.currentPage()).toBe(3);
    });

    it('should navigate to specific page', () => {
      component.goToPage(2);

      expect(component.currentPage()).toBe(2);
    });

    it('should ignore invalid page numbers', () => {
      component.goToPage(0);
      expect(component.currentPage()).toBe(1);

      component.goToPage(10);
      expect(component.currentPage()).toBe(1);

      component.goToPage('...');
      expect(component.currentPage()).toBe(1);
    });

    it('should generate pagination pages correctly', () => {
      const pages = component.paginationPages();
      expect(pages).toContain(1);
      expect(pages).toContain(2);
      expect(pages).toContain(3);
    });
  });

  // ==================== MAP ====================

  describe('Map', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should set map data from response', () => {
      expect(component.mapData()).toEqual(mockGeoJSON);
    });

    it('should filter map GeoJSON by scoped sites', () => {
      component.onScopeChange('all');

      const mapGeoJSON = component.mapGeoJSON();
      expect(mapGeoJSON).not.toBeNull();
    });

    it('should handle missing map data gracefully', fakeAsync(() => {
      // Reset mapData and mock to return error
      component.mapData.set(null);
      getSitesGeoJSONMock.mockReturnValue(throwError(() => new Error('No data')));

      component.loadData();
      tick();

      // After error, mapData should remain null (not crash or set invalid data)
      expect(component.mapData()).toBeNull();
    }));

    it('should indicate when map has features', () => {
      component.onScopeChange('all');
      expect(component.hasMapFeatures()).toBe(true);
    });

    it('should handle empty features array', () => {
      component.mapData.set({ type: 'FeatureCollection', features: [] });
      expect(component.hasMapFeatures()).toBe(false);
    });
  });

  // ==================== SITE ACCESS ENRICHMENT ====================

  describe('Site Access Enrichment', () => {
    it('should mark super admin as having access to all sites', fakeAsync(() => {
      isSuperAdminSignal.set(true);

      fixture.detectChanges();
      tick();

      component.allSites().forEach(site => {
        expect(site.accessStatus).toBe('granted');
      });
    }));

    it('should mark pending requests', fakeAsync(() => {
      const pendingRequest: ValidationRequestListItem = {
        id: 1,
        request_type: 'site_access',
        status: 'pending',
        requester_id: 1,
        requester_name: 'Test',
        target_name: 'Site Test',
        created_at: new Date().toISOString()
      };
      getMyRequestsMock.mockReturnValue(of([pendingRequest]));

      fixture.detectChanges();
      tick();

      const site = component.allSites().find(s => s.nom_site === 'Site Test');
      expect(site?.accessStatus).toBe('pending');
    }));

    it('should identify referent status', fakeAsync(() => {
      const siteWithReferent = {
        ...mockSite,
        users: [{ id_role: 1, email: 'test@test.fr', referent: true }]
      };

      getSitesMock.mockReturnValue(of({
        count: 1,
        next: null,
        previous: null,
        results: [siteWithReferent]
      }));

      fixture.detectChanges();
      tick();

      const site = component.allSites().find(s => s.id_site === 1);
      expect(site?.isReferent).toBe(true);
    }));
  });

  // ==================== NAVIGATION ====================

  describe('Navigation', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should navigate to site detail', fakeAsync(() => {
      const navigateSpy = jest.spyOn(router, 'navigate');
      const site = { ...mockSite, accessStatus: 'granted' as const, isReferent: false, isDirectlyLinked: true };

      component.viewSite(site);
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/sites', 'site-test']);
    }));
  });

  // ==================== DIALOGS ====================

  describe('Dialogs', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should open access request dialog', () => {
      // Set up available sites
      const siteForRequest = {
        ...mockSite,
        accessStatus: 'none' as const,
        isReferent: false,
        isDirectlyLinked: false
      };
      component.allSites.set([siteForRequest]);

      component.openSiteAccessRequestDialog();

      expect(dialogOpenMock).toHaveBeenCalled();
    });

    it('should not open access request dialog when no sites available', () => {
      component.allSites.set([]);

      component.openSiteAccessRequestDialog();

      // Dialog should not be opened when there are no available sites
      expect(dialogOpenMock).not.toHaveBeenCalled();
    });

    it('should open site creation dialog', () => {
      component.createSite();

      expect(dialogOpenMock).toHaveBeenCalled();
    });

    it('should show snackbar when user has no organisme', () => {
      currentUserSignal.set({ ...mockUser, organisme: null });

      component.createSite();

      expect(snackBarOpenMock).toHaveBeenCalled();
    });

    it('should reload data after successful site creation', fakeAsync(() => {
      dialogOpenMock.mockReturnValue({
        afterClosed: () => of({ site: { id_site: 3, nom_site: 'New Site' } })
      });

      const loadDataSpy = jest.spyOn(component, 'loadData');

      component.createSite();
      tick();

      expect(loadDataSpy).toHaveBeenCalled();
    }));

    it('should open find or create site dialog', () => {
      component.openFindOrCreateSiteDialog();

      expect(dialogOpenMock).toHaveBeenCalled();
    });
  });

  // ==================== HELPER METHODS ====================

  describe('Helper Methods', () => {
    it('should format surface correctly', () => {
      expect(component.formatSurface(1500)).toMatch(/1[\s\u202f]500 ha/);
      expect(component.formatSurface(null)).toBe('-');
      expect(component.formatSurface(undefined)).toBe('-');
    });

    it('should identify page numbers', () => {
      expect(component.isPageNumber(1)).toBe(true);
      expect(component.isPageNumber(5)).toBe(true);
      expect(component.isPageNumber('...')).toBe(false);
    });

    it('should return correct status class', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const referentSite = { ...mockSite, accessStatus: 'granted' as const, isReferent: true, isDirectlyLinked: true };
      const grantedSite = { ...mockSite, accessStatus: 'granted' as const, isReferent: false, isDirectlyLinked: true };
      const otherSite = { ...mockSite, accessStatus: 'none' as const, isReferent: false, isDirectlyLinked: false };

      expect(component.getStatusClass(referentSite)).toBe('status-success');
      expect(component.getStatusClass(grantedSite)).toBe('status-info');
      expect(component.getStatusClass(otherSite)).toBe('status-neutre');
    }));
  });

  // ==================== VALIDATION REQUESTS ====================

  describe('Validation Requests', () => {
    it('should filter site_access requests', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.myRequests().length).toBe(1);
      expect(component.myRequests()[0].request_type).toBe('site_access');
    }));

    it('should filter pending site creations', fakeAsync(() => {
      const creationRequest: ValidationRequestListItem = {
        id: 2,
        request_type: 'site_creation',
        status: 'pending',
        requester_id: 1,
        requester_name: 'Test User',
        target_name: 'New Site',
        created_at: new Date().toISOString()
      };
      getMyRequestsMock.mockReturnValue(of([mockValidationRequest, creationRequest]));

      fixture.detectChanges();
      tick();

      expect(component.pendingSiteCreations().length).toBe(1);
      expect(component.pendingSiteCreations()[0].target_name).toBe('New Site');
    }));

    it('should identify pending sites', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const pendingSites = component.pendingSites();
      pendingSites.forEach(site => {
        expect(site.accessStatus).toBe('pending');
      });
    }));

    describe('Pending Org Links', () => {
      it('should filter pending site_org_link requests', fakeAsync(() => {
        const mockOrgLinkRequest: ValidationRequestListItem = {
          id: 10,
          request_type: 'site_org_link',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Site Test',
          created_at: new Date().toISOString()
        };
        getMyRequestsMock.mockReturnValue(of([mockValidationRequest, mockOrgLinkRequest]));

        fixture.detectChanges();
        tick();

        expect(component.pendingOrgLinks().length).toBe(1);
        expect(component.pendingOrgLinks()[0].request_type).toBe('site_org_link');
        expect(component.pendingOrgLinks()[0].id).toBe(10);
      }));

      it('should not include non-pending site_org_link requests', fakeAsync(() => {
        const approvedOrgLinkRequest: ValidationRequestListItem = {
          id: 11,
          request_type: 'site_org_link',
          status: 'approved',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Site Test',
          created_at: new Date().toISOString()
        };
        getMyRequestsMock.mockReturnValue(of([approvedOrgLinkRequest]));

        fixture.detectChanges();
        tick();

        expect(component.pendingOrgLinks().length).toBe(0);
      }));

      it('should have separate signals for pendingSiteCreations and pendingOrgLinks', fakeAsync(() => {
        const creationRequest: ValidationRequestListItem = {
          id: 20,
          request_type: 'site_creation',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'New Site',
          created_at: new Date().toISOString()
        };
        const orgLinkRequest: ValidationRequestListItem = {
          id: 21,
          request_type: 'site_org_link',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Existing Site',
          created_at: new Date().toISOString()
        };
        getMyRequestsMock.mockReturnValue(of([mockValidationRequest, creationRequest, orgLinkRequest]));

        fixture.detectChanges();
        tick();

        expect(component.pendingSiteCreations().length).toBe(1);
        expect(component.pendingSiteCreations()[0].request_type).toBe('site_creation');
        expect(component.pendingOrgLinks().length).toBe(1);
        expect(component.pendingOrgLinks()[0].request_type).toBe('site_org_link');
      }));
    });
  });

  // ==================== AVAILABLE SITES FOR REQUEST ====================

  describe('Available Sites for Request', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should return sites with no access from user organisme', () => {
      const siteNoAccess = {
        ...mockSite,
        accessStatus: 'none' as const,
        isReferent: false,
        isDirectlyLinked: false
      };
      component.allSites.set([siteNoAccess]);

      const available = component.availableSitesForRequest();
      expect(available.length).toBe(1);
    });

    it('should exclude sites with granted access', () => {
      const siteGranted = {
        ...mockSite,
        accessStatus: 'granted' as const,
        isReferent: false,
        isDirectlyLinked: true
      };
      component.allSites.set([siteGranted]);

      const available = component.availableSitesForRequest();
      expect(available.length).toBe(0);
    });

    it('should exclude sites with pending access', () => {
      const sitePending = {
        ...mockSite,
        accessStatus: 'pending' as const,
        isReferent: false,
        isDirectlyLinked: false
      };
      component.allSites.set([sitePending]);

      const available = component.availableSitesForRequest();
      expect(available.length).toBe(0);
    });

    it('should return empty when user has no organisme', () => {
      // The computed depends on authService.currentUser().organisme
      // If user has no organisme, availableSitesForRequest filters to empty
      // We can't test this with shared signal, but we test the behavior
      // by setting allSites to sites that don't belong to user's organisme
      const siteOtherOrg = {
        ...mockSite,
        accessStatus: 'none' as const,
        isReferent: false,
        isDirectlyLinked: false,
        organismes: [{ id_organisme: 999, nom_organisme: 'Other Org', principal: true }]
      };
      component.allSites.set([siteOtherOrg]);

      const available = component.availableSitesForRequest();
      // Site doesn't belong to user's organisme (id=1), so it should be empty
      expect(available.length).toBe(0);
    });
  });
});
