import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/accueil',
    pathMatch: 'full'
  },
  {
    path: 'accueil',
    loadChildren: () => import('./features/home/home.routes').then(m => m.HOME_ROUTES)
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
  },
  {
    path: 'plans',
    loadChildren: () => import('./features/plans/plans.routes').then(m => m.PLANS_ROUTES)
  },
  {
    path: 'administration',
    loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES)
  },
  {
    path: 'notifications',
    loadChildren: () => import('./features/notifications/notifications.routes').then(m => m.NOTIFICATIONS_ROUTES)
  },
  {
    path: 'profile',
    loadChildren: () => import('./features/profile/profile.routes').then(m => m.PROFILE_ROUTES)
  },
  {
    path: 'mes-demandes',
    loadChildren: () => import('./features/my-requests/my-requests.routes').then(m => m.MY_REQUESTS_ROUTES)
  },
  {
    path: 'sites',
    loadChildren: () => import('./features/sites/sites.routes').then(m => m.SITES_ROUTES)
  },
  {
    path: 'activite',
    loadChildren: () => import('./features/activity/activity.routes').then(m => m.ACTIVITY_ROUTES)
  }
];