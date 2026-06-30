import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { catchError, map, of } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';

// #248 — Bloque l'accès aux routes de création/édition d'enjeux, FCR et opérations
// quand le plan n'est pas en brouillon. Aligné sur EDITABLE_STATUSES côté backend
// (CanModifyOnlyDraftPlan). L'extension de durée (#250) est indépendante du statut.
const EDITABLE_STATUSES = new Set(['draft']);

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

  // #512 — Quand la route bloquée cible une action (« Modifier l'action » depuis
  // le suivi / tableau de bord d'un plan validé), rediriger directement vers la
  // fiche en lecture seule de cette action plutôt que vers la liste des enjeux.
  const operationId = route.paramMap.get('operationId');
  const lockedTarget = operationId
    ? router.createUrlTree(['/plans', slug, 'enjeux', 'operations', operationId])
    : router.createUrlTree(['/plans', slug, 'enjeux']);

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
      return lockedTarget;
    }),
    catchError(() => of(lockedTarget)),
  );
};
