import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { authGuard, roleGuard, adminGuard, guestGuard, notAdminOgOnlyGuard } from './auth.guard';
import { User } from '../models/user.model';

describe('Auth Guards', () => {
  let mockAuthService: {
    isAuthenticated: jest.Mock;
    hasRole: jest.Mock;
    canAccessAdmin: jest.Mock;
    currentUser: jest.Mock;
  };
  let router: { navigate: jest.Mock };
  let mockRoute: ActivatedRouteSnapshot;
  let mockState: RouterStateSnapshot;

  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    niveau_role: 'utilisateur',
    is_staff: false,
    is_active: true
  };

  const mockSuperAdmin: User = {
    id: 2,
    email: 'admin@example.com',
    niveau_role: 'super_admin',
    is_staff: true,
    is_active: true
  };

  const mockAdminOg: User = {
    id: 3,
    email: 'adminog@example.com',
    niveau_role: 'admin_og',
    is_staff: false,
    is_active: true
  };

  beforeEach(() => {
    mockAuthService = {
      isAuthenticated: jest.fn(),
      hasRole: jest.fn(),
      canAccessAdmin: jest.fn(),
      currentUser: jest.fn()
    };

    router = {
      navigate: jest.fn()
    };

    mockRoute = {
      data: {}
    } as ActivatedRouteSnapshot;

    mockState = {
      url: '/protected'
    } as RouterStateSnapshot;

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: router }
      ]
    });
  });

  describe('authGuard', () => {
    it('should allow access when user is authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);

      const result = TestBed.runInInjectionContext(() =>
        authGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('should redirect to login when user is not authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() =>
        authGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
        queryParams: { returnUrl: '/protected' }
      });
    });

    it('should include return URL in redirect', () => {
      mockAuthService.isAuthenticated.mockReturnValue(false);
      mockState.url = '/admin/users';

      TestBed.runInInjectionContext(() =>
        authGuard(mockRoute, mockState)
      );

      expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
        queryParams: { returnUrl: '/admin/users' }
      });
    });
  });

  describe('roleGuard', () => {
    it('should redirect to login if not authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() =>
        roleGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
        queryParams: { returnUrl: '/protected' }
      });
    });

    it('should allow access if authenticated and no role required', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);
      mockRoute.data = {};

      const result = TestBed.runInInjectionContext(() =>
        roleGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });

    it('should allow access if user has required role', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);
      mockAuthService.hasRole.mockReturnValue(true);
      mockRoute.data = { requiredRole: 'referent' };

      const result = TestBed.runInInjectionContext(() =>
        roleGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
      expect(mockAuthService.hasRole).toHaveBeenCalledWith('referent');
    });

    it('should redirect to accueil if user lacks required role', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);
      mockAuthService.hasRole.mockReturnValue(false);
      mockRoute.data = { requiredRole: 'admin_og' };

      const result = TestBed.runInInjectionContext(() =>
        roleGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/accueil']);
    });
  });

  describe('adminGuard', () => {
    it('should redirect to login if not authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() =>
        adminGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
        queryParams: { returnUrl: '/protected' }
      });
    });

    it('should allow access if user can access admin', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);
      mockAuthService.canAccessAdmin.mockReturnValue(true);

      const result = TestBed.runInInjectionContext(() =>
        adminGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });

    it('should redirect to accueil if user cannot access admin', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);
      mockAuthService.canAccessAdmin.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() =>
        adminGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/accueil']);
    });
  });

  describe('guestGuard', () => {
    it('should allow access if not authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() =>
        guestGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });

    it('should redirect to accueil if authenticated', () => {
      mockAuthService.isAuthenticated.mockReturnValue(true);

      const result = TestBed.runInInjectionContext(() =>
        guestGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/accueil']);
    });
  });

  describe('notAdminOgOnlyGuard', () => {
    it('should allow access for super_admin', () => {
      mockAuthService.currentUser.mockReturnValue(mockSuperAdmin);

      const result = TestBed.runInInjectionContext(() =>
        notAdminOgOnlyGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });

    it('should allow access for regular user', () => {
      mockAuthService.currentUser.mockReturnValue(mockUser);

      const result = TestBed.runInInjectionContext(() =>
        notAdminOgOnlyGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });

    it('should redirect admin_og to organismes page', () => {
      mockAuthService.currentUser.mockReturnValue(mockAdminOg);

      const result = TestBed.runInInjectionContext(() =>
        notAdminOgOnlyGuard(mockRoute, mockState)
      );

      expect(result).toBe(false);
      expect(router.navigate).toHaveBeenCalledWith(['/administration/organismes']);
    });

    it('should allow access if no user', () => {
      mockAuthService.currentUser.mockReturnValue(null);

      const result = TestBed.runInInjectionContext(() =>
        notAdminOgOnlyGuard(mockRoute, mockState)
      );

      expect(result).toBe(true);
    });
  });
});
