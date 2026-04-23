import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, NavigationEnd, provideRouter, Routes } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import { Component, signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}
import { HeaderComponent } from './header.component';
import { AuthService } from '../../../core/services/auth.service';
import { ImpersonationGuardService } from '../../../core/services/impersonation-guard.service';
import { ModuleService } from '../../../core/services/module.service';
import { NotificationService } from '../../../core/services/notification.service';
import { User } from '../../../core/models/user.model';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;
  let router: Router;

  // Writable signals for mocking
  let isAuthenticatedSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<User | null>;
  let canAccessAdminSignal: WritableSignal<boolean>;
  let isImpersonatingSignal: WritableSignal<boolean>;
  let impersonationInfoSignal: WritableSignal<any>;
  let isReadOnlySignal: WritableSignal<boolean>;

  // Mock functions
  let logoutMock: jest.Mock;
  let stopImpersonationMock: jest.Mock;
  let getMyAccessibleModulesMock: jest.Mock;

  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    prenom_role: 'John',
    nom_role: 'Doe',
    niveau_role: 'super_admin',
    is_staff: true,
    is_active: true
  };

  const setupTestBed = async () => {
    // Create writable signals
    isAuthenticatedSignal = signal(true);
    currentUserSignal = signal<User | null>(mockUser);
    canAccessAdminSignal = signal(true);
    isImpersonatingSignal = signal(false);
    impersonationInfoSignal = signal(null);
    isReadOnlySignal = signal(false);

    // Create mock functions
    logoutMock = jest.fn().mockReturnValue(of(undefined));
    stopImpersonationMock = jest.fn().mockReturnValue(of(undefined));
    getMyAccessibleModulesMock = jest.fn().mockReturnValue(of([
      { id: 1, code: 'zonages', name: 'Zonages', active: true }
    ]));

    const authServiceMock = {
      isAuthenticated: isAuthenticatedSignal.asReadonly(),
      currentUser: currentUserSignal.asReadonly(),
      canAccessAdmin: canAccessAdminSignal.asReadonly(),
      isImpersonating: isImpersonatingSignal.asReadonly(),
      impersonationInfo: impersonationInfoSignal.asReadonly(),
      getUserDisplayName: jest.fn().mockReturnValue('John Doe'),
      getOriginalUserDisplayName: jest.fn().mockReturnValue('Admin User'),
      logout: logoutMock,
      stopImpersonation: stopImpersonationMock
    };

    const impersonationGuardMock = {
      isReadOnly: isReadOnlySignal.asReadonly()
    };

    const moduleServiceMock = {
      getMyAccessibleModules: getMyAccessibleModulesMock
    };

    // Mock NotificationService for NotificationBellComponent
    const notificationServiceMock = {
      notifications: signal([]),
      unreadCount: signal(0),
      pendingValidations: signal(0),
      hasUnread: signal(false),
      hasPendingValidations: signal(false),
      totalBadgeCount: signal(0),
      poll: jest.fn().mockReturnValue(of({ notifications: [], unread_count: 0, pending_validations: 0 })),
      startPolling: jest.fn(),
      stopPolling: jest.fn(),
      markAsRead: jest.fn().mockReturnValue(of({ status: 'ok' })),
      markAllAsRead: jest.fn().mockReturnValue(of({ status: 'ok' })),
      refresh: jest.fn().mockReturnValue(of({ notifications: [], unread_count: 0, pending_validations: 0 }))
    };

    await TestBed.configureTestingModule({
      imports: [
        HeaderComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot()
      ],
      providers: [
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'accueil', component: DummyComponent },
          { path: 'plans', component: DummyComponent },
          { path: 'administration', component: DummyComponent },
          { path: 'administration/utilisateurs', component: DummyComponent }
        ]),
        { provide: AuthService, useValue: authServiceMock },
        { provide: ImpersonationGuardService, useValue: impersonationGuardMock },
        { provide: ModuleService, useValue: moduleServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;
  };

  beforeEach(async () => {
    await setupTestBed();
  });

  afterEach(() => {
    // Clean up body overflow style
    document.body.style.overflow = '';
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should have menu closed initially', () => {
      fixture.detectChanges();
      expect(component.menuOpen).toBe(false);
    });

    it('should expose auth state to template', () => {
      fixture.detectChanges();
      expect(component.isAuthenticated()).toBe(true);
      expect(component.currentUser()).toEqual(mockUser);
      expect(component.canAccessAdmin()).toBe(true);
    });

    it('should have sidebar modules defined', () => {
      fixture.detectChanges();
      expect(component.sidebarModules.length).toBe(4);
      expect(component.sidebarModules[0].code).toBe('plans');
      expect(component.sidebarModules[1].code).toBe('sites');
      expect(component.sidebarModules.some(m => m.code === 'inventaires')).toBe(false);
    });
  });

  // ==================== USER DISPLAY ====================

  describe('User Display', () => {
    it('should get user display name from auth service', () => {
      fixture.detectChanges();
      expect(component.userDisplayName).toBe('John Doe');
    });

    it('should get original user display name when impersonating', () => {
      fixture.detectChanges();
      expect(component.originalUserDisplayName).toBe('Admin User');
    });

    it('should compute user initials from first and last name', () => {
      fixture.detectChanges();
      expect(component.userInitials).toBe('JD');
    });

    it('should compute user initials from email when no name', () => {
      currentUserSignal.set({
        ...mockUser,
        prenom_role: undefined,
        nom_role: undefined
      });
      fixture.detectChanges();

      expect(component.userInitials).toBe('T');
    });

    it('should return empty initials when no user', () => {
      currentUserSignal.set(null);
      fixture.detectChanges();

      expect(component.userInitials).toBe('');
    });
  });

  // ==================== MODULE ACCESS ====================

  describe('Module Access', () => {
    it('should have access to modules that do not require access', () => {
      fixture.detectChanges();
      const plansModule = component.sidebarModules.find(m => m.code === 'plans')!;
      expect(component.hasModuleAccess(plansModule)).toBe(true);
    });

    it('should check API for modules requiring access', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const zonagesModule = component.sidebarModules.find(m => m.code === 'zonages')!;
      expect(component.hasModuleAccess(zonagesModule)).toBe(true);
    }));

    it('should not have access when module requires access but not granted', fakeAsync(() => {
      getMyAccessibleModulesMock.mockReturnValue(of([]));
      fixture.detectChanges();
      tick();

      const zonagesModule = component.sidebarModules.find(m => m.code === 'zonages')!;
      expect(component.hasModuleAccess(zonagesModule)).toBe(false);
    }));

    it('should show module when user has access', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const plansModule = component.sidebarModules.find(m => m.code === 'plans')!;
      expect(component.shouldShowModule(plansModule)).toBe(true);
    }));

    it('should load modules when authenticated', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getMyAccessibleModulesMock).toHaveBeenCalled();
    }));

    it('should handle module loading error gracefully', fakeAsync(() => {
      getMyAccessibleModulesMock.mockReturnValue(throwError(() => new Error('API Error')));
      fixture.detectChanges();
      tick();

      // Should not throw, accessible modules should be empty
      const zonagesModule = component.sidebarModules.find(m => m.code === 'zonages')!;
      expect(component.hasModuleAccess(zonagesModule)).toBe(false);
    }));
  });

  // ==================== MENU OPERATIONS ====================

  describe('Menu Operations', () => {
    it('should toggle menu open', () => {
      fixture.detectChanges();
      expect(component.menuOpen).toBe(false);

      component.toggleMenu();

      expect(component.menuOpen).toBe(true);
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('should toggle menu closed', () => {
      fixture.detectChanges();
      component.menuOpen = true;
      document.body.style.overflow = 'hidden';

      component.toggleMenu();

      expect(component.menuOpen).toBe(false);
      expect(document.body.style.overflow).toBe('');
    });
  });

  // ==================== ROUTE DETECTION ====================

  describe('Route Detection', () => {
    it('should detect home page at root', fakeAsync(() => {
      router.navigate(['/']);
      tick();
      fixture.detectChanges();

      expect(component.isHomePage()).toBe(true);
    }));

    it('should detect home page at /accueil', fakeAsync(() => {
      router.navigate(['/accueil']);
      tick();
      fixture.detectChanges();

      expect(component.isHomePage()).toBe(true);
    }));

    it('should not detect other routes as home page', fakeAsync(() => {
      router.navigate(['/plans']);
      tick();
      fixture.detectChanges();

      expect(component.isHomePage()).toBe(false);
    }));

    it('should check if route is active for home', fakeAsync(() => {
      router.navigate(['/']);
      tick();
      fixture.detectChanges();

      expect(component.isActiveRoute('/accueil')).toBe(true);
    }));
  });

  // ==================== LOGOUT ====================

  describe('Logout', () => {
    it('should call auth service logout', () => {
      fixture.detectChanges();

      component.logout();

      expect(logoutMock).toHaveBeenCalled();
    });
  });

  // ==================== ADMIN ACCESS ====================

  describe('Admin Access', () => {
    it('should navigate to admin when impersonating', fakeAsync(() => {
      isImpersonatingSignal.set(true);
      fixture.detectChanges();
      const navigateSpy = jest.spyOn(router, 'navigate');

      component.openAdmin();
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/administration']);
    }));

    it('should open admin in new tab when not impersonating', () => {
      const originalOpen = window.open;
      window.open = jest.fn();

      fixture.detectChanges();

      component.openAdmin();

      expect(window.open).toHaveBeenCalledWith('/administration', '_blank');

      window.open = originalOpen;
    });
  });

  // ==================== IMPERSONATION ====================

  describe('Impersonation', () => {
    it('should expose impersonation state', () => {
      isImpersonatingSignal.set(true);
      impersonationInfoSignal.set({
        impersonatedUserId: 2,
        impersonatedUserEmail: 'impersonated@test.com',
        originalUserId: 1,
        originalUserEmail: 'admin@test.com'
      });
      fixture.detectChanges();

      expect(component.isImpersonating()).toBe(true);
      expect(component.impersonationInfo()).toBeTruthy();
    });

    it('should expose read-only state', () => {
      isReadOnlySignal.set(true);
      fixture.detectChanges();

      expect(component.isReadOnly()).toBe(true);
    });

    it('should stop impersonation and reload to admin page', fakeAsync(() => {
      fixture.detectChanges();
      // window.location.href triggers a full page reload — mock it to prevent jsdom error
      delete (window as any).location;
      (window as any).location = { href: '' };

      component.stopImpersonation();
      tick();

      expect(stopImpersonationMock).toHaveBeenCalled();
      expect((window as any).location.href).toBe('/administration/utilisateurs');
    }));

    it('should reload to home on stop impersonation error', fakeAsync(() => {
      stopImpersonationMock.mockReturnValue(throwError(() => new Error('Error')));
      fixture.detectChanges();
      delete (window as any).location;
      (window as any).location = { href: '' };

      component.stopImpersonation();
      tick();

      expect(stopImpersonationMock).toHaveBeenCalled();
      expect((window as any).location.href).toBe('/');
    }));
  });

  // ==================== NAVIGATION EVENTS ====================

  describe('Navigation Events', () => {
    it('should update home page detection on navigation', fakeAsync(() => {
      router.navigate(['/']);
      tick();
      fixture.detectChanges();

      expect(component.isHomePage()).toBe(true);

      // Simulate navigation to plans
      router.navigate(['/plans']);
      tick();
      fixture.detectChanges();

      expect(component.isHomePage()).toBe(false);
    }));
  });
});
