import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, ActivatedRoute, provideRouter, convertToParamMap } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, signal, WritableSignal, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService, TranslateLoader } from '@ngx-translate/core';
import { BehaviorSubject, of, throwError } from 'rxjs';

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

import { SiteDetailComponent } from './site-detail.component';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { ImpersonationGuardService } from '../../core/services/impersonation-guard.service';
import { ModuleService } from '../../core/services/module.service';
import { LeafletMapComponent } from '../../shared/components/leaflet-map/leaflet-map.component';
import { AdminSite, GeoJSONFeature, AdminPlan } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

describe('SiteDetailComponent', () => {
  let component: SiteDetailComponent;
  let fixture: ComponentFixture<SiteDetailComponent>;
  let router: Router;

  // Route params mock
  let paramMapSubject: BehaviorSubject<any>;

  // Writable signals for mocking
  let isSuperAdminSignal: WritableSignal<boolean>;
  let isAuthenticatedSignal: WritableSignal<boolean>;
  let isImpersonatingSignal: WritableSignal<boolean>;
  let impersonationInfoSignal: WritableSignal<any>;
  let canAccessAdminSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<any>;
  let isReadOnlySignal: WritableSignal<boolean>;

  // Mock functions
  let getSiteMock: jest.Mock;
  let getSiteGeoJSONMock: jest.Mock;
  let getPlansMock: jest.Mock;
  let getMyRequestsMock: jest.Mock;
  let requestReferentMock: jest.Mock;
  let dialogOpenMock: jest.Mock;
  let snackBarOpenMock: jest.Mock;
  let logoutMock: jest.Mock;
  let stopImpersonationMock: jest.Mock;
  let getMyAccessibleModulesMock: jest.Mock;

  const mockOrganisme = {
    id_organisme: 1,
    nom_organisme: 'Test Organisme',
    ville_organisme: 'Paris',
    principal: true
  };

  const mockUser = {
    id: 1,
    email: 'test@test.fr',
    nom_complet: 'Test User'
  };

  const mockSite: AdminSite = {
    id_site: 1,
    slug: 'site-test',
    nom_site: 'Site Test',
    type_site_label: 'RNN',
    surf_off: 1500,
    id_local: 'LOC001',
    id_inpn: 'INPN001',
    marin: false,
    outre_mer: false,
    active: true,
    organismes: [mockOrganisme],
    current_user_is_referent: true,
    current_user_access: {
      has_access: true,
      is_referent: true,
      is_conservateur: false,
      role_label: 'Referent'
    }
  };

  const mockSiteWithUsers = {
    ...mockSite,
    users_assignes: [
      {
        user: {
          id_role: 1,
          nom_complet: 'Test User',
          email: 'test@test.fr',
          role_level: 'utilisateur',
          organisme: 'Test Organisme'
        },
        referent: true,
        referent_valid: true,
        conservateur: false
      },
      {
        user: {
          id_role: 2,
          nom_complet: 'Other User',
          email: 'other@test.fr',
          role_level: 'utilisateur',
          organisme: 'Test Organisme'
        },
        referent: false,
        referent_valid: false,
        conservateur: false
      }
    ]
  };

  const mockGeoJSON: GeoJSONFeature = {
    type: 'Feature',
    id: 1,
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]] },
    properties: {
      id_site: 1,
      slug: 'site-test',
      nom_site: 'Site Test'
    }
  };

  const mockPlan: AdminPlan = {
    id_pg: 1,
    nom: 'Plan Test',
    statut: 'valide',
    annee_debut: 2020,
    annee_fin: 2030,
    gestion_partagee: false,
    ct88: false,
    risque_incendie: false
  };

  const mockPlan2: AdminPlan = {
    id_pg: 2,
    nom: 'Plan Draft',
    statut: 'draft',
    annee_debut: 2024,
    gestion_partagee: false,
    ct88: false,
    risque_incendie: false
  };

  const mockValidationRequest: ValidationRequestListItem = {
    id: 1,
    request_type: 'referent_validation',
    status: 'pending',
    requester_id: 1,
    requester_name: 'Test User',
    target_site_id: 1,
    created_at: new Date().toISOString()
  };

  const setupTestBed = async () => {
    // Create route params subject
    paramMapSubject = new BehaviorSubject(convertToParamMap({ slug: 'site-test' }));

    // Create writable signals
    isSuperAdminSignal = signal(false);
    isAuthenticatedSignal = signal(true);
    isImpersonatingSignal = signal(false);
    impersonationInfoSignal = signal(null);
    canAccessAdminSignal = signal(false);
    currentUserSignal = signal(mockUser);
    isReadOnlySignal = signal(false);

    // Create mock functions
    getSiteMock = jest.fn().mockReturnValue(of(mockSiteWithUsers));
    getSiteGeoJSONMock = jest.fn().mockReturnValue(of(mockGeoJSON));
    getPlansMock = jest.fn().mockReturnValue(of({ results: [mockPlan, mockPlan2] }));
    getMyRequestsMock = jest.fn().mockReturnValue(of([]));
    requestReferentMock = jest.fn().mockReturnValue(of({ message: 'Success' }));
    dialogOpenMock = jest.fn().mockReturnValue({ afterClosed: () => of(null) });
    snackBarOpenMock = jest.fn();
    logoutMock = jest.fn().mockReturnValue(of(null));
    stopImpersonationMock = jest.fn().mockReturnValue(of(null));
    getMyAccessibleModulesMock = jest.fn().mockReturnValue(of([]));

    const adminServiceMock = {
      getSite: getSiteMock,
      getSiteGeoJSON: getSiteGeoJSONMock,
      getPlans: getPlansMock
    };

    const validationServiceMock = {
      getMyRequests: getMyRequestsMock,
      requestReferent: requestReferentMock,
      getValidationRequests: jest.fn().mockReturnValue(of({ count: 0, results: [] }))
    };

    const isAdminOrganismeSignal = signal(false);
    const hasGlobalAccessSignal = signal(false);

    const authServiceMock = {
      isSuperAdmin: isSuperAdminSignal.asReadonly(),
      isAdminOrganisme: isAdminOrganismeSignal.asReadonly(),
      hasGlobalAccess: hasGlobalAccessSignal.asReadonly(),
      isAuthenticated: isAuthenticatedSignal.asReadonly(),
      isImpersonating: isImpersonatingSignal.asReadonly(),
      impersonationInfo: impersonationInfoSignal.asReadonly(),
      canAccessAdmin: canAccessAdminSignal.asReadonly(),
      currentUser: currentUserSignal.asReadonly(),
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
        SiteDetailComponent,
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
          { path: 'plans/:id', component: DummyComponent },
          { path: 'accueil', component: DummyComponent }
        ]),
        { provide: AdminService, useValue: adminServiceMock },
        { provide: ValidationService, useValue: validationServiceMock },
        { provide: AuthService, useValue: authServiceMock },
        { provide: ImpersonationGuardService, useValue: impersonationGuardServiceMock },
        { provide: ModuleService, useValue: moduleServiceMock },
        { provide: MatDialog, useValue: dialogMock },
        { provide: MatSnackBar, useValue: snackBarMock },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: paramMapSubject.asObservable()
          }
        }
      ]
    })
    .overrideComponent(SiteDetailComponent, {
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
    fixture = TestBed.createComponent(SiteDetailComponent);
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

    it('should load site data on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getSiteMock).toHaveBeenCalledWith('site-test');
      expect(getSiteGeoJSONMock).toHaveBeenCalledWith('site-test');
      expect(component.site()).not.toBeNull();
    }));

    it('should set loading to false after data loads', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));
  });

  // ==================== ROUTE HANDLING ====================

  describe('Route Handling', () => {
    it('should load site from route slug parameter', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getSiteMock).toHaveBeenCalledWith('site-test');
    }));

    it('should redirect to sites list when no slug', fakeAsync(() => {
      const navigateSpy = jest.spyOn(router, 'navigate');
      paramMapSubject.next(convertToParamMap({}));

      fixture.detectChanges();
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/sites']);
    }));

    it('should reload when slug changes', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      getSiteMock.mockClear();
      paramMapSubject.next(convertToParamMap({ slug: 'autre-site' }));
      tick();

      expect(getSiteMock).toHaveBeenCalledWith('autre-site');
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

    it('should handle error and redirect to sites list', fakeAsync(() => {
      const navigateSpy = jest.spyOn(router, 'navigate');
      getSiteMock.mockReturnValue(throwError(() => new Error('Not found')));

      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
      expect(navigateSpy).toHaveBeenCalledWith(['/sites']);
    }));
  });

  // ==================== SITE DATA ====================

  describe('Site Data', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should store site data', () => {
      expect(component.site()?.nom_site).toBe('Site Test');
      expect(component.site()?.type_site_label).toBe('RNN');
    });

    it('should store site GeoJSON', () => {
      expect(component.siteGeoJSON()).toEqual(mockGeoJSON);
    });

    it('should compute map GeoJSON as FeatureCollection', () => {
      const mapGeoJSON = component.mapGeoJSON();
      expect(mapGeoJSON?.type).toBe('FeatureCollection');
      expect(mapGeoJSON?.features).toHaveLength(1);
    });

    it('should return null for map GeoJSON when no geometry', () => {
      component.siteGeoJSON.set(null);
      expect(component.mapGeoJSON()).toBeNull();
    });

    it('should compute site info array', () => {
      const info = component.siteInfo();
      expect(info.length).toBe(6);
      expect(info[0].label).toBe('sites.detail.fields.type');
      expect(info[0].value).toBe('RNN');
    });
  });

  // ==================== ASSOCIATED PLANS ====================

  describe('Associated Plans', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should load associated plans', () => {
      expect(getPlansMock).toHaveBeenCalledWith({ site: 1, page_size: 50 });
      expect(component.associatedPlans()).toHaveLength(2);
    });

    it('should handle plans load error gracefully', fakeAsync(() => {
      getPlansMock.mockReturnValue(throwError(() => new Error('Error')));
      component.loadSiteData('site-test');
      tick();

      expect(component.associatedPlans()).toHaveLength(0);
    }));
  });

  // ==================== USERS ====================

  describe('Users', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should extract users from site response', () => {
      expect(component.siteUsers()).toHaveLength(2);
    });

    it('should get user display name', () => {
      const user = component.siteUsers()[0].user;
      expect(component.getUserDisplayName(user)).toBe('Test User');
    });

    it('should fallback to email when nom_complet is empty', () => {
      const user = { ...component.siteUsers()[0].user, nom_complet: '' };
      expect(component.getUserDisplayName(user)).toBe('test@test.fr');
    });

    it('should get correct role label for referent', () => {
      const referentUser = component.siteUsers()[0];
      expect(component.getUserRoleLabel(referentUser)).toBe('sites.detail.roles.referent');
    });

    it('should get correct role label for regular user', () => {
      const regularUser = component.siteUsers()[1];
      expect(component.getUserRoleLabel(regularUser)).toBe('sites.detail.roles.user');
    });

    it('should get correct role label for conservateur', () => {
      const conservateur = {
        ...component.siteUsers()[0],
        conservateur: true
      };
      expect(component.getUserRoleLabel(conservateur)).toBe('sites.detail.roles.conservateur');
    });

    it('should get correct role variant (#296 <app-tag>)', () => {
      const referentUser = component.siteUsers()[0];
      const regularUser = component.siteUsers()[1];

      expect(component.getUserRoleVariant(referentUser)).toBe('warning');
      expect(component.getUserRoleVariant(regularUser)).toBe('muted');
    });
  });

  // ==================== SIDEBAR MENU ====================

  describe('Anchor Navigation (#304)', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should have anchor nav items defined', () => {
      expect(component.anchorNavItems).toHaveLength(4);
      expect(component.anchorNavItems.map(m => m.id)).toEqual([
        'site-info', 'site-organismes', 'site-users', 'site-plans'
      ]);
    });

    it('should set default active anchor to site-info', () => {
      expect(component.activeAnchorId()).toBe('site-info');
    });

    it('should change active anchor on click', () => {
      component.onAnchorClick({ id: 'site-users', label: 'users' });
      expect(component.activeAnchorId()).toBe('site-users');

      component.onAnchorClick({ id: 'site-plans', label: 'plans' });
      expect(component.activeAnchorId()).toBe('site-plans');
    });
  });

  // ==================== REFERENT STATUS ====================

  describe('Referent Status', () => {
    it('should identify referent from current_user_is_referent', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.isReferent()).toBe(true);
    }));

    it('should identify super admin as referent', fakeAsync(() => {
      const siteNonReferent = {
        ...mockSiteWithUsers,
        current_user_is_referent: false
      };
      getSiteMock.mockReturnValue(of(siteNonReferent));
      isSuperAdminSignal.set(true);

      fixture.detectChanges();
      tick();

      expect(component.isReferent()).toBe(true);
    }));

    it('should not be referent when not marked', fakeAsync(() => {
      const siteNonReferent = {
        ...mockSiteWithUsers,
        current_user_is_referent: false
      };
      getSiteMock.mockReturnValue(of(siteNonReferent));
      isSuperAdminSignal.set(false);

      fixture.detectChanges();
      tick();

      expect(component.isReferent()).toBe(false);
    }));
  });

  // ==================== REQUEST REFERENT ====================

  describe('Request Referent', () => {
    beforeEach(fakeAsync(() => {
      const siteWithAccess = {
        ...mockSiteWithUsers,
        current_user_is_referent: false,
        current_user_access: {
          has_access: true,
          is_referent: false,
          is_conservateur: false,
          role_label: 'Utilisateur'
        }
      };
      getSiteMock.mockReturnValue(of(siteWithAccess));

      fixture.detectChanges();
      tick();
    }));

    it('should be able to request referent when has access but not referent', () => {
      expect(component.canRequestReferent()).toBe(true);
    });

    it('should not be able to request referent when already referent', fakeAsync(() => {
      const siteAsReferent = {
        ...mockSiteWithUsers,
        current_user_access: {
          has_access: true,
          is_referent: true,
          is_conservateur: false,
          role_label: 'Referent'
        }
      };
      getSiteMock.mockReturnValue(of(siteAsReferent));

      component.loadSiteData('site-test');
      tick();

      expect(component.canRequestReferent()).toBe(false);
    }));

    it('should not be able to request referent without access', fakeAsync(() => {
      const siteNoAccess = {
        ...mockSiteWithUsers,
        current_user_access: null
      };
      getSiteMock.mockReturnValue(of(siteNoAccess));

      component.loadSiteData('site-test');
      tick();

      expect(component.canRequestReferent()).toBe(false);
    }));

    it('should request referent status', fakeAsync(() => {
      component.requestReferent();
      tick();

      expect(requestReferentMock).toHaveBeenCalledWith('site-test');
      expect(component.hasPendingReferentRequest()).toBe(true);
      expect(snackBarOpenMock).toHaveBeenCalled();
    }));

    it('should handle request referent error', fakeAsync(() => {
      requestReferentMock.mockReturnValue(throwError(() => ({
        error: { error: 'Request failed' }
      })));

      component.requestReferent();
      tick();

      expect(component.requestingReferent()).toBe(false);
      expect(snackBarOpenMock).toHaveBeenCalled();
    }));

    it('should detect pending referent request', fakeAsync(() => {
      getMyRequestsMock.mockReturnValue(of([mockValidationRequest]));

      component.loadSiteData('site-test');
      tick();

      expect(component.hasPendingReferentRequest()).toBe(true);
    }));
  });

  // ==================== NAVIGATION ====================

  describe('Navigation', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should navigate back to sites list', fakeAsync(() => {
      const navigateSpy = jest.spyOn(router, 'navigate');

      component.goBack();
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/sites']);
    }));

    it('should navigate to plan detail', fakeAsync(() => {
      const navigateSpy = jest.spyOn(router, 'navigate');

      component.viewPlan(mockPlan);
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/plans', 1]);
    }));
  });

  // ==================== DIALOGS ====================

  describe('Dialogs', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should open edit site dialog', () => {
      component.editSite();

      expect(dialogOpenMock).toHaveBeenCalled();
    });

    it('should reload data after successful site edit', fakeAsync(() => {
      dialogOpenMock.mockReturnValue({
        afterClosed: () => of({ site: mockSite })
      });

      const loadDataSpy = jest.spyOn(component, 'loadSiteData');

      component.editSite();
      tick();

      expect(loadDataSpy).toHaveBeenCalledWith('site-test');
    }));

    it('should open manage users dialog', () => {
      component.manageUsers();

      expect(dialogOpenMock).toHaveBeenCalled();
    });

    it('should reload data after users management', fakeAsync(() => {
      dialogOpenMock.mockReturnValue({
        afterClosed: () => of({ changed: true })
      });

      const loadDataSpy = jest.spyOn(component, 'loadSiteData');

      component.manageUsers();
      tick();

      expect(loadDataSpy).toHaveBeenCalledWith('site-test');
    }));

    it('should open invite organisme dialog', () => {
      component.inviteOrganisme();

      expect(dialogOpenMock).toHaveBeenCalled();
    });

    it('should show success message after invite', fakeAsync(() => {
      dialogOpenMock.mockReturnValue({
        afterClosed: () => of({ success: true, message: 'Invitation sent' })
      });

      component.inviteOrganisme();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalled();
    }));
  });

  // ==================== HELPER METHODS ====================

  describe('Helper Methods', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should format surface correctly', () => {
      expect(component.formatSurface(1500)).toMatch(/1[\s\u202f]500 ha/);
      expect(component.formatSurface(null)).toBe('-');
      expect(component.formatSurface(undefined)).toBe('-');
      expect(component.formatSurface(0)).toBe('-');
    });

    it('should format plan period with both years', () => {
      expect(component.formatPlanPeriod(mockPlan)).toBe('2020 - 2030');
    });

    it('should format plan period with only start year', () => {
      expect(component.formatPlanPeriod(mockPlan2)).toBe('Depuis 2024');
    });

    it('should format plan period with no years', () => {
      const planNoYears = { ...mockPlan, annee_debut: undefined, annee_fin: undefined };
      expect(component.formatPlanPeriod(planNoYears)).toBe('-');
    });

    it('should return correct plan status class', () => {
      expect(component.getPlanStatusClass('valide')).toBe('status-success');
      expect(component.getPlanStatusClass('draft')).toBe('status-warning');
      expect(component.getPlanStatusClass('archive')).toBe('status-neutre');
      // Util centralisé (plan-status.utils) : statut inconnu → pas de classe.
      expect(component.getPlanStatusClass('unknown')).toBe('');
    });

    it('should return correct plan status i18n key', () => {
      expect(component.getPlanStatusKey('valide')).toBe('plans.status.valide');
      expect(component.getPlanStatusKey('draft')).toBe('plans.status.draft');
      expect(component.getPlanStatusKey('archive')).toBe('plans.status.archive');
      expect(component.getPlanStatusKey('unknown')).toBe('plans.status.unknown');
    });
  });

  // ==================== EDGE CASES ====================

  describe('Edge Cases', () => {
    // These tests use component methods directly without triggering ngOnInit
    // which avoids issues with mock timing

    it('should not call editSite when site is null', () => {
      component.site.set(null);
      component.editSite();

      expect(dialogOpenMock).not.toHaveBeenCalled();
    });

    it('should not call manageUsers when site is null', () => {
      component.site.set(null);
      component.manageUsers();

      expect(dialogOpenMock).not.toHaveBeenCalled();
    });

    it('should not call inviteOrganisme when site is null', () => {
      component.site.set(null);
      component.inviteOrganisme();

      expect(dialogOpenMock).not.toHaveBeenCalled();
    });

    it('should not call requestReferent when site is null', () => {
      component.site.set(null);
      component.requestReferent();

      expect(requestReferentMock).not.toHaveBeenCalled();
    });

    it('should handle site with no organismes via loadSiteData', fakeAsync(() => {
      const siteNoOrgs = { ...mockSiteWithUsers, organismes: [] };
      getSiteMock.mockReturnValue(of(siteNoOrgs));
      getSiteGeoJSONMock.mockReturnValue(of(mockGeoJSON));
      getPlansMock.mockReturnValue(of({ results: [] }));
      getMyRequestsMock.mockReturnValue(of([]));

      component.loadSiteData('site-test');
      tick();

      expect(component.site()?.organismes).toHaveLength(0);
    }));

    it('should handle site with no users via loadSiteData', fakeAsync(() => {
      const siteNoUsers = { ...mockSiteWithUsers, users_assignes: [] };
      getSiteMock.mockReturnValue(of(siteNoUsers));
      getSiteGeoJSONMock.mockReturnValue(of(mockGeoJSON));
      getPlansMock.mockReturnValue(of({ results: [] }));
      getMyRequestsMock.mockReturnValue(of([]));

      component.loadSiteData('site-test');
      tick();

      expect(component.siteUsers()).toHaveLength(0);
    }));

    it('should handle missing GeoJSON via loadSiteData', fakeAsync(() => {
      getSiteMock.mockReturnValue(of(mockSiteWithUsers));
      getSiteGeoJSONMock.mockReturnValue(throwError(() => new Error('No geometry')));
      getPlansMock.mockReturnValue(of({ results: [] }));
      getMyRequestsMock.mockReturnValue(of([]));

      component.loadSiteData('site-test');
      tick();

      expect(component.siteGeoJSON()).toBeNull();
      expect(component.mapGeoJSON()).toBeNull();
    }));

    it('should handle site with null type_site_label', fakeAsync(() => {
      const siteNoType = { ...mockSiteWithUsers, type_site_label: null };
      getSiteMock.mockReturnValue(of(siteNoType));
      getSiteGeoJSONMock.mockReturnValue(of(mockGeoJSON));
      getPlansMock.mockReturnValue(of({ results: [] }));
      getMyRequestsMock.mockReturnValue(of([]));

      component.loadSiteData('site-test');
      tick();

      const info = component.siteInfo();
      const typeInfo = info.find(i => i.label === 'sites.detail.fields.type');
      expect(typeInfo?.value).toBe('-');
    }));
  });
});
