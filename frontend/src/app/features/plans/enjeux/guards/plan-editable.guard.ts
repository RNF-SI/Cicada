import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { catchError, map, of } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';

// #248 — Bloque l'accès aux routes de création/édition d'enjeux, FCR et opérations
// quand le plan n'est pas en brouillon (ou en extension). Le statut éditable est aligné
// sur EDITABLE_STATUSES côté backend (CanModifyOnlyDraftPlan).
const EDITABLE_STATUSES = new Set(['draft', 'etendu']);

const findSlug = (route: ActivatedRouteSnapshot): string | null => {
  let current: ActivatedRouteSnapshot | null = route;
  while (current) {
    const slug = current.paramMap.get('slug');
    if (slug) return slug;
    current = current.parent;
  }
  return null;
};

export const planEditableGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  _state: RouterStateSnapshot,
) => {
  const adminService = inject(AdminService);
  const router = inject(Router);
  const snackBar = inject(MatSnackBar);
  const translate = inject(TranslateService);

  const slug = findSlug(route);
  if (!slug) {
    return router.createUrlTree(['/plans']);
  }

  return adminService.getPlanBySlug(slug).pipe(
    map((plan) => {
      if (EDITABLE_STATUSES.has(plan.statut)) {
        return true;
      }
      snackBar.open(
        translate.instant('plans.lifecycle.lockedBanner.title'),
        translate.instant('common.actions.close'),
        { duration: 4000 },
      );
      return router.createUrlTree(['/plans', slug, 'enjeux']);
    }),
    catchError(() => of(router.createUrlTree(['/plans', slug, 'enjeux']))),
  );
};
