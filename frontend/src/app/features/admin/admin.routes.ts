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

/**
 * Admin Routes Configuration
 *
 * Role-based access:
 * - super_admin: access to all pages (dashboard, utilisateurs, organismes, sites)
 * - admin_og: ONLY access to organismes (their own organisme)
 * - referent: NO access to admin
 * - utilisateur: NO access to admin
 */
export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminLayoutComponent,
    canActivate: [roleGuard],
    data: { requiredRole: 'admin_og' }, // Minimum role: admin_og (referent and utilisateur have NO access)
    children: [
      {
        // Dynamic redirect based on user role
        path: '',
        pathMatch: 'full',
        canActivate: [() => {
          const authService = inject(AuthService);
          const router = inject(Router);
          const user = authService.currentUser();

          // admin_og goes to organismes
          if (user?.niveau_role === 'admin_og') {
            router.navigate(['/administration/organismes']);
          } else {
            // referent and super_admin go to dashboard
            router.navigate(['/administration/dashboard']);
          }
          return false;
        }],
        component: AdminDashboardComponent // Required but never rendered
      },
      {
        path: 'dashboard',
        component: AdminDashboardComponent,
        canActivate: [notAdminOgOnlyGuard] // Block admin_og
      },
      {
        path: 'utilisateurs',
        component: AdminUsersComponent,
        canActivate: [notAdminOgOnlyGuard] // Block admin_og
      },
      {
        path: 'organismes',
        component: AdminOrganismesComponent,
        canActivate: [roleGuard],
        data: { requiredRole: 'admin_og' } // Only admin_og and super_admin
      },
      {
        path: 'sites',
        component: AdminSitesComponent,
        canActivate: [notAdminOgOnlyGuard] // Block admin_og
      }
    ]
  }
];
