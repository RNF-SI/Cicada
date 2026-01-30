import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../services/auth.service';
import { environment } from '../../../environments/environment';

/**
 * HTTP Interceptor qui bloque les modifications (POST/PUT/PATCH/DELETE)
 * pendant une session d'impersonnation en mode production.
 *
 * En mode développement (environment.allowImpersonationModifications = true),
 * les modifications sont autorisées pour faciliter les tests.
 *
 * En mode production (environment.allowImpersonationModifications = false),
 * seule la consultation (GET) est autorisée pendant l'impersonnation.
 */
export const impersonationInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);
  const snackBar = inject(MatSnackBar);

  // Si les modifications sont autorisées en impersonnation, laisser passer
  if (environment.allowImpersonationModifications) {
    return next(req);
  }

  // Vérifier si l'utilisateur est en mode impersonnation
  if (!authService.isImpersonating()) {
    return next(req);
  }

  // Les méthodes de lecture sont toujours autorisées
  const readOnlyMethods = ['GET', 'HEAD', 'OPTIONS'];
  if (readOnlyMethods.includes(req.method.toUpperCase())) {
    return next(req);
  }

  // Autoriser les endpoints spécifiques même en impersonnation
  // (ex: arrêter l'impersonnation, rafraîchir le token)
  const allowedEndpoints = [
    '/api/auth/stop-impersonation/',
    '/api/auth/refresh/',
    '/api/auth/logout/'
  ];
  const isAllowedEndpoint = allowedEndpoints.some(endpoint => req.url.includes(endpoint));
  if (isAllowedEndpoint) {
    return next(req);
  }

  // Bloquer les modifications (POST, PUT, PATCH, DELETE)
  console.warn(
    `[Impersonnation] Modification bloquée: ${req.method} ${req.url}`
  );

  // Afficher un message à l'utilisateur
  snackBar.open(
    'Mode consultation : les modifications sont désactivées pendant l\'impersonnation.',
    'Fermer',
    {
      duration: 5000,
      panelClass: ['snackbar-warning']
    }
  );

  // Retourner une erreur 403 Forbidden
  const error = new HttpErrorResponse({
    status: 403,
    statusText: 'Forbidden',
    url: req.url,
    error: {
      detail: 'Les modifications sont désactivées pendant l\'impersonnation. Mode consultation uniquement.',
      code: 'IMPERSONATION_READ_ONLY'
    }
  });

  return throwError(() => error);
};
