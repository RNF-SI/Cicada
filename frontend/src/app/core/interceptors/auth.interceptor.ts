import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * HTTP Interceptor to add JWT token to outgoing requests
 * and handle token refresh on 401 errors
 */
export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);

  // Skip authentication for public endpoints
  const publicUrls = ['/api/auth/login/', '/api/auth/refresh/', '/api/auth/health/'];
  const isPublicUrl = publicUrls.some(url => req.url.includes(url));

  // Le jeton ne part que vers l'API de cette instance (URL relative ou même
  // origine) : un appel futur vers un service tiers (tuiles, Matomo, hub…) ne
  // doit jamais l'emporter.
  if (isPublicUrl || !versCetteInstance(req.url)) {
    return next(req);
  }

  // Add token to request if available
  const token = authService.getAccessToken();
  if (token) {
    req = addTokenToRequest(req, token);
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 Unauthorized - try to refresh token
      if (error.status === 401 && token && !req.url.includes('/api/auth/')) {
        return authService.refreshToken().pipe(
          switchMap(newToken => {
            // Retry the original request with new token
            return next(addTokenToRequest(req, newToken));
          }),
          catchError(refreshError => {
            // Refresh failed, logout user
            authService.logout().subscribe();
            return throwError(() => refreshError);
          })
        );
      }

      return throwError(() => error);
    })
  );
};

/**
 * Clone request and add Authorization header
 */
function addTokenToRequest(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });
}

/** Vrai pour une URL relative ou de la même origine que l'application. */
export function versCetteInstance(url: string): boolean {
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(url) && !url.startsWith('//')) {
    return true;
  }
  try {
    return new URL(url, window.location.href).origin === window.location.origin;
  } catch {
    return false;
  }
}
