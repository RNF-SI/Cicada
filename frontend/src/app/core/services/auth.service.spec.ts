import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { User, LoginResponse, RefreshResponse, ImpersonationResponse, StopImpersonationResponse } from '../models/user.model';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let router: Router;

  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    nom_role: 'Test',
    prenom_role: 'User',
    niveau_role: 'utilisateur',
    is_staff: false,
    is_active: true
  };

  const mockSuperAdmin: User = {
    id: 2,
    email: 'admin@example.com',
    nom_role: 'Admin',
    prenom_role: 'Super',
    niveau_role: 'super_admin',
    is_staff: true,
    is_active: true
  };

  const mockAdminOg: User = {
    ...mockUser,
    id: 3,
    email: 'adminog@example.com',
    niveau_role: 'admin_og'
  };

  const mockReferent: User = {
    ...mockUser,
    id: 4,
    email: 'referent@example.com',
    niveau_role: 'utilisateur',
    is_referent: true  // Site or plan referent
  };

  const mockTokens = {
    access: 'test-access-token',
    refresh: 'test-refresh-token'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        {
          provide: Router,
          useValue: {
            navigate: jest.fn()
          }
        }
      ]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  describe('initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should initialize as not authenticated', () => {
      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentUser()).toBeNull();
    });

    it('should be initialized after creation', () => {
      expect(service.isInitialized()).toBe(true);
    });
  });

  describe('login', () => {
    it('should login successfully and store tokens', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockUser
      };

      let result: User | undefined;
      service.login({ username: 'test@example.com', password: 'password' }).subscribe(user => {
        result = user;
      });

      const req = httpMock.expectOne('/api/auth/login/');
      expect(req.request.method).toBe('POST');
      req.flush(loginResponse);
      tick();

      expect(result).toEqual(mockUser);
      expect(service.isAuthenticated()).toBe(true);
      expect(service.currentUser()).toEqual(mockUser);
      expect(service.getAccessToken()).toBe(mockTokens.access);
    }));

    it('should handle login error', fakeAsync(() => {
      let error: Error | undefined;
      service.login({ username: 'test@example.com', password: 'wrong' }).subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/auth/login/');
      req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });
      tick();

      expect(error).toBeDefined();
      expect(service.isAuthenticated()).toBe(false);
    }));

    it('should set loading state during login', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockUser
      };

      service.login({ username: 'test@example.com', password: 'password' }).subscribe();

      expect(service.isLoading()).toBe(true);

      const req = httpMock.expectOne('/api/auth/login/');
      req.flush(loginResponse);
      tick();

      expect(service.isLoading()).toBe(false);
    }));
  });

  describe('logout', () => {
    beforeEach(() => {
      localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
      localStorage.setItem('current_user', JSON.stringify(mockUser));
    });

    it('should clear auth data on logout', fakeAsync(() => {
      service.logout().subscribe();

      const req = httpMock.expectOne('/api/auth/logout/');
      req.flush({});
      tick();

      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentUser()).toBeNull();
      expect(localStorage.getItem('auth_tokens')).toBeNull();
      expect(router.navigate).toHaveBeenCalledWith(['/accueil']);
    }));

    it('should clear auth data even if logout API fails', fakeAsync(() => {
      service.logout().subscribe();

      const req = httpMock.expectOne('/api/auth/logout/');
      req.error(new ProgressEvent('error'));
      tick();

      expect(service.isAuthenticated()).toBe(false);
      expect(localStorage.getItem('auth_tokens')).toBeNull();
    }));
  });

  describe('refreshToken', () => {
    beforeEach(() => {
      localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
    });

    it('should refresh token successfully', fakeAsync(() => {
      const newAccessToken = 'new-access-token';
      const refreshResponse: RefreshResponse = { access: newAccessToken };

      let result: string | undefined;
      service.refreshToken().subscribe(token => {
        result = token;
      });

      const req = httpMock.expectOne('/api/auth/refresh/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ refresh: mockTokens.refresh });
      req.flush(refreshResponse);
      tick();

      expect(result).toBe(newAccessToken);
      expect(service.getAccessToken()).toBe(newAccessToken);
    }));

    it('should clear auth data on refresh failure', fakeAsync(() => {
      let error: Error | undefined;
      service.refreshToken().subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/auth/refresh/');
      req.flush({}, { status: 401, statusText: 'Unauthorized' });
      tick();

      expect(error).toBeDefined();
      expect(service.isAuthenticated()).toBe(false);
    }));

    it('should throw error if no refresh token available', fakeAsync(() => {
      localStorage.clear();

      let error: Error | undefined;
      service.refreshToken().subscribe({
        error: (e) => { error = e; }
      });
      tick();

      expect(error).toBeDefined();
      expect(error?.message).toBe('No refresh token available');
    }));
  });

  describe('hasRole', () => {
    it('should return false if not authenticated', () => {
      expect(service.hasRole('utilisateur')).toBe(false);
    });

    it('should check role hierarchy correctly', fakeAsync(() => {
      // Login as super_admin
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockSuperAdmin
      };

      service.login({ username: 'admin@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      // Super admin has all roles
      expect(service.hasRole('utilisateur')).toBe(true);
      expect(service.hasRole('referent')).toBe(true);
      expect(service.hasRole('admin_og')).toBe(true);
      expect(service.hasRole('super_admin')).toBe(true);
    }));

    it('should deny higher roles for regular user', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockUser
      };

      service.login({ username: 'test@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.hasRole('utilisateur')).toBe(true);
      expect(service.hasRole('referent')).toBe(false);
      expect(service.hasRole('admin_og')).toBe(false);
      expect(service.hasRole('super_admin')).toBe(false);
    }));

    it('should handle referent role correctly', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockReferent
      };

      service.login({ username: 'referent@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.hasRole('utilisateur')).toBe(true);
      expect(service.hasRole('referent')).toBe(true);
      expect(service.hasRole('admin_og')).toBe(false);
      expect(service.hasRole('super_admin')).toBe(false);
    }));
  });

  describe('computed signals', () => {
    it('should compute isSuperAdmin correctly', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockSuperAdmin
      };

      service.login({ username: 'admin@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.isSuperAdmin()).toBe(true);
    }));

    it('should compute isAdminOrganisme correctly', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockAdminOg
      };

      service.login({ username: 'adminog@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.isAdminOrganisme()).toBe(true);
      expect(service.isSuperAdmin()).toBe(false);
    }));

    it('should compute isReferent correctly', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockReferent
      };

      service.login({ username: 'referent@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.isReferent()).toBe(true);
      expect(service.isAdminOrganisme()).toBe(false);
    }));

    it('should compute canAccessAdmin for admin roles', fakeAsync(() => {
      // Regular user cannot access admin
      let loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockUser
      };

      service.login({ username: 'test@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.canAccessAdmin()).toBe(false);
    }));
  });

  describe('getUserDisplayName', () => {
    it('should return empty string if not authenticated', () => {
      expect(service.getUserDisplayName()).toBe('');
    });

    it('should return full name if available', fakeAsync(() => {
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockUser
      };

      service.login({ username: 'test@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.getUserDisplayName()).toBe('User Test');
    }));

    it('should fallback to email if no name', fakeAsync(() => {
      const userWithoutName: User = {
        id: 1,
        email: 'noname@example.com',
        niveau_role: 'utilisateur',
        is_staff: false,
        is_active: true
      };

      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: userWithoutName
      };

      service.login({ username: 'noname@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();

      expect(service.getUserDisplayName()).toBe('noname@example.com');
    }));
  });

  describe('impersonation', () => {
    beforeEach(fakeAsync(() => {
      // Login as super admin first
      const loginResponse: LoginResponse = {
        access: mockTokens.access,
        refresh: mockTokens.refresh,
        user: mockSuperAdmin
      };

      service.login({ username: 'admin@example.com', password: 'password' }).subscribe();
      httpMock.expectOne('/api/auth/login/').flush(loginResponse);
      tick();
    }));

    it('should start impersonation successfully', fakeAsync(() => {
      const impersonationResponse: ImpersonationResponse = {
        access: 'impersonated-access-token',
        refresh: 'impersonated-refresh-token',
        user: mockUser,
        impersonation: {
          isImpersonating: true,
          impersonator: {
            id: mockSuperAdmin.id,
            email: mockSuperAdmin.email,
            nom_role: mockSuperAdmin.nom_role,
            prenom_role: mockSuperAdmin.prenom_role
          },
          logId: 1,
          startedAt: new Date().toISOString()
        }
      };

      service.startImpersonation(mockUser.id, 'Testing').subscribe();

      const req = httpMock.expectOne(`/api/auth/impersonate/${mockUser.id}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ reason: 'Testing' });
      req.flush(impersonationResponse);
      tick();

      expect(service.isImpersonating()).toBe(true);
      expect(service.currentUser()).toEqual(mockUser);
      expect(service.getAccessToken()).toBe('impersonated-access-token');
    }));

    it('should stop impersonation successfully', fakeAsync(() => {
      // First start impersonation
      const impersonationResponse: ImpersonationResponse = {
        access: 'impersonated-access-token',
        refresh: 'impersonated-refresh-token',
        user: mockUser,
        impersonation: {
          isImpersonating: true,
          impersonator: {
            id: mockSuperAdmin.id,
            email: mockSuperAdmin.email
          },
          logId: 1,
          startedAt: new Date().toISOString()
        }
      };

      service.startImpersonation(mockUser.id).subscribe();
      httpMock.expectOne(`/api/auth/impersonate/${mockUser.id}/`).flush(impersonationResponse);
      tick();

      // Now stop impersonation
      const stopResponse: StopImpersonationResponse = {
        access: 'admin-access-token',
        refresh: 'admin-refresh-token',
        user: mockSuperAdmin,
        message: 'Impersonation ended'
      };

      service.stopImpersonation().subscribe();
      const req = httpMock.expectOne('/api/auth/stop-impersonation/');
      expect(req.request.method).toBe('POST');
      req.flush(stopResponse);
      tick();

      expect(service.isImpersonating()).toBe(false);
      expect(service.currentUser()).toEqual(mockSuperAdmin);
    }));
  });

  describe('verifyToken', () => {
    beforeEach(() => {
      localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
    });

    it('should verify token and update user', fakeAsync(() => {
      service.verifyToken().subscribe();

      const req = httpMock.expectOne('/api/auth/me/');
      expect(req.request.method).toBe('GET');
      req.flush(mockUser);
      tick();

      expect(service.currentUser()).toEqual(mockUser);
    }));

    it('should return null if no tokens stored', fakeAsync(() => {
      localStorage.clear();

      let result: User | null | undefined;
      service.verifyToken().subscribe(user => {
        result = user;
      });
      tick();

      expect(result).toBeNull();
    }));

    it('should try refresh on verification failure', fakeAsync(() => {
      service.verifyToken().subscribe();

      // First /me call fails
      const meReq = httpMock.expectOne('/api/auth/me/');
      meReq.flush({}, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should try refresh
      const refreshReq = httpMock.expectOne('/api/auth/refresh/');
      refreshReq.flush({ access: 'new-token' });
      tick();

      // Should retry /me with new token
      const retryReq = httpMock.expectOne('/api/auth/me/');
      retryReq.flush(mockUser);
      tick();

      expect(service.currentUser()).toEqual(mockUser);
    }));
  });
});
