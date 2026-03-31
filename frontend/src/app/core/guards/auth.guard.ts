import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';

/**
 * Guard to check if user is authenticated
 * Redirects to login page if not authenticated
 */
export const authGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  // Store the attempted URL for redirecting after login
  router.navigate(['/auth/login'], {
    queryParams: { returnUrl: state.url }
  });

  return false;
};

/**
 * Guard to check if user has required role
 * Usage: canActivate: [roleGuard], data: { requiredRole: 'admin_og' }
 */
export const roleGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // First check authentication
  if (!authService.isAuthenticated()) {
    router.navigate(['/auth/login'], {
      queryParams: { returnUrl: state.url }
    });
    return false;
  }

  // Check role if specified
  const requiredRole = route.data['requiredRole'] as UserRole | undefined;
  if (requiredRole && !authService.hasRole(requiredRole)) {
    router.navigate(['/accueil']);
    return false;
  }

  return true;
};

/**
 * Guard to check if user can access admin pages
 */
export const adminGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/auth/login'], {
      queryParams: { returnUrl: state.url }
    });
    return false;
  }

  if (!authService.canAccessAdmin()) {
    router.navigate(['/accueil']);
    return false;
  }

  return true;
};

/**
 * Guard to prevent authenticated users from accessing login/register pages
 */
export const guestGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    router.navigate(['/accueil']);
    return false;
  }

  return true;
};

/**
 * Guard to block admin_og from accessing certain pages
 * admin_og can ONLY access /administration/organismes
 * Redirects to /administration/organismes if trying to access other admin pages
 */
export const notAdminOgOnlyGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const user = authService.currentUser();

  // If user is admin_og or redacteur_principal (but not super_admin), redirect to organismes
  if (user && (user.niveau_role === 'admin_og' || user.niveau_role === 'redacteur_principal')) {
    router.navigate(['/administration/organismes']);
    return false;
  }

  return true;
};
