import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from '../services/auth.service';
import { authInterceptor } from './auth.interceptor';
import { of, throwError } from 'rxjs';

describe('AuthInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let mockAuthService: {
    getAccessToken: jest.Mock;
    refreshToken: jest.Mock;
    logout: jest.Mock;
  };

  const mockAccessToken = 'test-access-token';
  const mockNewAccessToken = 'new-access-token';

  beforeEach(() => {
    mockAuthService = {
      getAccessToken: jest.fn(),
      refreshToken: jest.fn(),
      logout: jest.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService }
      ]
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('token injection', () => {
    it('should add Authorization header when token is available', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      httpClient.get('/api/users/').subscribe();

      const req = httpMock.expectOne('/api/users/');
      expect(req.request.headers.get('Authorization')).toBe(`Bearer ${mockAccessToken}`);
      req.flush({});
    });

    it('should not add Authorization header when no token', () => {
      mockAuthService.getAccessToken.mockReturnValue(null);

      httpClient.get('/api/users/').subscribe();

      const req = httpMock.expectOne('/api/users/');
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush({});
    });

    it('should skip auth for login endpoint', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      httpClient.post('/api/auth/login/', {}).subscribe();

      const req = httpMock.expectOne('/api/auth/login/');
      // Should not call getAccessToken for public URLs
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush({});
    });

    it('should skip auth for refresh endpoint', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      httpClient.post('/api/auth/refresh/', {}).subscribe();

      const req = httpMock.expectOne('/api/auth/refresh/');
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush({});
    });

    it('should skip auth for health endpoint', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      httpClient.get('/api/auth/health/').subscribe();

      const req = httpMock.expectOne('/api/auth/health/');
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush({});
    });
  });

  describe('401 handling', () => {
    it('should attempt token refresh on 401 error', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);
      mockAuthService.refreshToken.mockReturnValue(of(mockNewAccessToken));

      httpClient.get('/api/users/').subscribe();

      // First request fails with 401
      const req = httpMock.expectOne('/api/users/');
      req.flush({}, { status: 401, statusText: 'Unauthorized' });

      // After refresh, retry request should be made
      const retryReq = httpMock.expectOne('/api/users/');
      expect(retryReq.request.headers.get('Authorization')).toBe(`Bearer ${mockNewAccessToken}`);
      retryReq.flush({ data: 'success' });
    });

    it('should logout if refresh fails', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);
      mockAuthService.refreshToken.mockReturnValue(throwError(() => new Error('Refresh failed')));
      mockAuthService.logout.mockReturnValue(of(undefined));

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/users/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/users/');
      req.flush({}, { status: 401, statusText: 'Unauthorized' });

      expect(mockAuthService.logout).toHaveBeenCalled();
      expect(error).toBeDefined();
    });

    it('should not refresh for auth endpoints', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/auth/me/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/auth/me/');
      req.flush({}, { status: 401, statusText: 'Unauthorized' });

      // Should not attempt refresh for auth endpoints
      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(error).toBeDefined();
    });

    it('should not refresh if no token was used', () => {
      mockAuthService.getAccessToken.mockReturnValue(null);

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/users/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/users/');
      req.flush({}, { status: 401, statusText: 'Unauthorized' });

      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(error).toBeDefined();
    });
  });

  describe('other errors', () => {
    it('should pass through non-401 errors', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/users/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/users/');
      req.flush({ message: 'Not found' }, { status: 404, statusText: 'Not Found' });

      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(error?.status).toBe(404);
    });

    it('should pass through 403 errors without refresh', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/admin/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/admin/');
      req.flush({ message: 'Forbidden' }, { status: 403, statusText: 'Forbidden' });

      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(error?.status).toBe(403);
    });

    it('should pass through 500 errors', () => {
      mockAuthService.getAccessToken.mockReturnValue(mockAccessToken);

      let error: HttpErrorResponse | undefined;
      httpClient.get('/api/users/').subscribe({
        error: (e) => { error = e; }
      });

      const req = httpMock.expectOne('/api/users/');
      req.flush({ message: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });

      expect(mockAuthService.refreshToken).not.toHaveBeenCalled();
      expect(error?.status).toBe(500);
    });
  });
});
