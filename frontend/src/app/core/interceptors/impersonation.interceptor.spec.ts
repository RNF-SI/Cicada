import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpResponse, HttpErrorResponse, HttpHandlerFn } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';

import { impersonationInterceptor } from './impersonation.interceptor';
import { AuthService } from '../services/auth.service';
import * as environmentModule from '../../../environments/environment';

describe('ImpersonationInterceptor', () => {
  let snackBarOpenMock: jest.Mock;
  let isImpersonatingSignal: WritableSignal<boolean>;

  const mockNext: HttpHandlerFn = (req) => of(new HttpResponse({ status: 200 }));

  const setupTestBed = (allowModifications: boolean, impersonating: boolean) => {
    snackBarOpenMock = jest.fn();
    isImpersonatingSignal = signal(impersonating);

    // Mock environment
    (environmentModule as any).environment = {
      allowImpersonationModifications: allowModifications
    };

    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isImpersonating: isImpersonatingSignal.asReadonly()
          }
        },
        {
          provide: MatSnackBar,
          useValue: { open: snackBarOpenMock }
        }
      ]
    });
  };

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ==================== WHEN MODIFICATIONS ARE ALLOWED ====================

  describe('When allowImpersonationModifications = true', () => {
    beforeEach(() => {
      setupTestBed(true, true);
    });

    it('should allow GET requests', (done) => {
      const req = new HttpRequest('GET', '/api/users');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should allow POST requests when modifications are enabled', (done) => {
      const req = new HttpRequest('POST', '/api/users', { name: 'Test' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            expect(snackBarOpenMock).not.toHaveBeenCalled();
            done();
          }
        });
      });
    });

    it('should allow PUT requests when modifications are enabled', (done) => {
      const req = new HttpRequest('PUT', '/api/users/1', { name: 'Updated' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should allow DELETE requests when modifications are enabled', (done) => {
      const req = new HttpRequest('DELETE', '/api/users/1');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });
  });

  // ==================== WHEN NOT IMPERSONATING ====================

  describe('When not impersonating', () => {
    beforeEach(() => {
      setupTestBed(false, false); // modifications disabled, not impersonating
    });

    it('should allow POST requests when not impersonating', (done) => {
      const req = new HttpRequest('POST', '/api/users', { name: 'Test' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            expect(snackBarOpenMock).not.toHaveBeenCalled();
            done();
          }
        });
      });
    });

    it('should allow PUT requests when not impersonating', (done) => {
      const req = new HttpRequest('PUT', '/api/users/1', { name: 'Updated' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should allow DELETE requests when not impersonating', (done) => {
      const req = new HttpRequest('DELETE', '/api/users/1');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });
  });

  // ==================== WHEN IMPERSONATING (READ-ONLY MODE) ====================

  describe('When impersonating in read-only mode', () => {
    beforeEach(() => {
      setupTestBed(false, true); // modifications disabled, impersonating
    });

    it('should allow GET requests', (done) => {
      const req = new HttpRequest('GET', '/api/users');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            expect(snackBarOpenMock).not.toHaveBeenCalled();
            done();
          }
        });
      });
    });

    it('should allow HEAD requests', (done) => {
      const req = new HttpRequest('HEAD', '/api/users');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should allow OPTIONS requests', (done) => {
      const req = new HttpRequest('OPTIONS', '/api/users');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should block POST requests', (done) => {
      const req = new HttpRequest('POST', '/api/users', { name: 'Test' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: (error: HttpErrorResponse) => {
            expect(error.status).toBe(403);
            expect(error.error.code).toBe('IMPERSONATION_READ_ONLY');
            expect(snackBarOpenMock).toHaveBeenCalled();
            done();
          }
        });
      });
    });

    it('should block PUT requests', (done) => {
      const req = new HttpRequest('PUT', '/api/users/1', { name: 'Updated' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: (error: HttpErrorResponse) => {
            expect(error.status).toBe(403);
            expect(error.error.code).toBe('IMPERSONATION_READ_ONLY');
            done();
          }
        });
      });
    });

    it('should block PATCH requests', (done) => {
      const req = new HttpRequest('PATCH', '/api/users/1', { name: 'Patched' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: (error: HttpErrorResponse) => {
            expect(error.status).toBe(403);
            done();
          }
        });
      });
    });

    it('should block DELETE requests', (done) => {
      const req = new HttpRequest('DELETE', '/api/users/1');

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: (error: HttpErrorResponse) => {
            expect(error.status).toBe(403);
            done();
          }
        });
      });
    });

    it('should show snackbar message when blocking request', (done) => {
      const req = new HttpRequest('POST', '/api/users', { name: 'Test' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: () => {
            expect(snackBarOpenMock).toHaveBeenCalledWith(
              expect.stringContaining('Mode consultation'),
              'Fermer',
              expect.objectContaining({ duration: 5000 })
            );
            done();
          }
        });
      });
    });
  });

  // ==================== ALLOWED ENDPOINTS ====================

  describe('Allowed endpoints during impersonation', () => {
    beforeEach(() => {
      setupTestBed(false, true); // read-only mode
    });

    it('should allow POST to stop-impersonation endpoint', (done) => {
      const req = new HttpRequest('POST', '/api/auth/stop-impersonation/', {});

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            expect(snackBarOpenMock).not.toHaveBeenCalled();
            done();
          }
        });
      });
    });

    it('should allow POST to refresh endpoint', (done) => {
      const req = new HttpRequest('POST', '/api/auth/refresh/', { refresh: 'token' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });

    it('should allow POST to logout endpoint', (done) => {
      const req = new HttpRequest('POST', '/api/auth/logout/', {});

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          next: (response) => {
            expect(response).toBeTruthy();
            done();
          }
        });
      });
    });
  });

  // ==================== ERROR RESPONSE FORMAT ====================

  describe('Error response format', () => {
    beforeEach(() => {
      setupTestBed(false, true); // read-only mode
    });

    it('should return proper HttpErrorResponse', (done) => {
      const req = new HttpRequest('POST', '/api/users', { name: 'Test' });

      TestBed.runInInjectionContext(() => {
        impersonationInterceptor(req, mockNext).subscribe({
          error: (error: HttpErrorResponse) => {
            expect(error instanceof HttpErrorResponse).toBe(true);
            expect(error.status).toBe(403);
            expect(error.statusText).toBe('Forbidden');
            expect(error.url).toBe('/api/users');
            expect(error.error.detail).toContain('impersonnation');
            done();
          }
        });
      });
    });
  });
});
