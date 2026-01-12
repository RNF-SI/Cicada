import { Routes } from '@angular/router';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { roleGuard, notAdminOgOnlyGuard } from '../../core/guards/auth.guard';
import { AuthService } from '../../core/services/auth.service';
import { AdminLayoutComponent } from './admin-layout.component';
import { AdminDashboardComponent } from './admin-dashboard.component';
import { AdminUsersComponent } from './admin-users.component';
import { AdminOrganismesComponent } from './admin-organismes.component';
import { AdminSitesComponent } from './admin-sites.component';
import { AdminPlansComponent } from './admin-plans.component';
import { AdminValidationsComponent } from './admin-validations/admin-validations.component';
import { AdminModulesComponent } from './admin-modules/admin-modules.component';

/**
 * Admin Routes Configuration
 *
 * Role-based access:
 * - super_admin: access to all pages (dashboard, utilisateurs, organismes, sites, plans)
 * - admin_og: access to utilisateurs, organismes, sites, plans (filtered by their organisme)
 * - referent: access to validations, sites, plans (filtered to their assigned sites/plans)
 * - utilisateur: NO access to admin
 */
export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminLayoutComponent,
    canActivate: [roleGuard],
    data: { requiredRole: 'referent' }, // Minimum role: referent (can access plans for validations)
    children: [
      {
        // Dynamic redirect based on user role
        path: '',
        pathMatch: 'full',
        canActivate: [() => {
          const authService = inject(AuthService);
          const router = inject(Router);
          const user = authService.currentUser();

          // Referent (via is_referent, not admin) goes to validations
          if (user?.is_referent && user?.niveau_role === 'utilisateur') {
            router.navigate(['/administration/validations']);
          }
          // admin_og goes to utilisateurs (their main view)
          else if (user?.niveau_role === 'admin_og') {
            router.navigate(['/administration/utilisateurs']);
          } else {
            // super_admin goes to dashboard
            router.navigate(['/administration/dashboard']);
          }
          return false;
        }],
        component: AdminDashboardComponent // Required but never rendered
      },
      {
        path: 'dashboard',
        component: AdminDashboardComponent,
        canActivate: [notAdminOgOnlyGuard] // Only super_admin (dashboard has global stats)
      },
      {
        path: 'validations',
        component: AdminValidationsComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'referent' } // All admin roles can access validations
      },
      {
        path: 'utilisateurs',
        component: AdminUsersComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'admin_og' } // admin_og sees users from their organisme only
      },
      {
        path: 'organismes',
        component: AdminOrganismesComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'admin_og' } // admin_og sees their organisme only
      },
      {
        path: 'sites',
        component: AdminSitesComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'referent' } // referent sees their assigned sites only
      },
      {
        path: 'plans',
        component: AdminPlansComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'referent' } // referent can access for validations
      },
      {
        path: 'modules',
        component: AdminModulesComponent,
        canActivate: [notAdminOgOnlyGuard] // Only super_admin can manage module access
      }
    ]
  }
];
