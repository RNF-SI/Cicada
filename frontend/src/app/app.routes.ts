import { Routes } from '@angular/router';

// Titres de page dans l'onglet du navigateur (revue design — Amandine demandait que
// le titre se mette à jour selon la page, pas "mon profil" partout)
export const routes: Routes = [
  {
    path: '',
    redirectTo: '/accueil',
    pathMatch: 'full'
  },
  {
    path: 'accueil',
    title: 'Accueil · CICADA',
    loadChildren: () => import('./features/home/home.routes').then(m => m.HOME_ROUTES)
  },
  {
    path: 'auth',
    title: 'Connexion · CICADA',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
  },
  {
    path: 'plans',
    title: 'Plans de gestion · CICADA',
    loadChildren: () => import('./features/plans/plans.routes').then(m => m.PLANS_ROUTES)
  },
  {
    path: 'administration',
    title: 'Administration · CICADA',
    loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES)
  },
  {
    path: 'notifications',
    title: 'Notifications · CICADA',
    loadChildren: () => import('./features/notifications/notifications.routes').then(m => m.NOTIFICATIONS_ROUTES)
  },
  {
    path: 'profile',
    title: 'Mon profil · CICADA',
    loadChildren: () => import('./features/profile/profile.routes').then(m => m.PROFILE_ROUTES)
  },
  {
    path: 'mes-demandes',
    title: 'Mes demandes · CICADA',
    loadChildren: () => import('./features/my-requests/my-requests.routes').then(m => m.MY_REQUESTS_ROUTES)
  },
  {
    path: 'sites',
    title: 'Sites · CICADA',
    loadChildren: () => import('./features/sites/sites.routes').then(m => m.SITES_ROUTES)
  },
  {
    path: 'activite',
    title: 'Activité · CICADA',
    loadChildren: () => import('./features/activity/activity.routes').then(m => m.ACTIVITY_ROUTES)
  },
  {
    path: 'exploration',
    title: 'Exploration des données · CICADA',
    loadChildren: () => import('./features/exploration/exploration.routes').then(m => m.EXPLORATION_ROUTES)
  },
  {
    path: 'inventaires',
    title: 'Inventaires & suivis · CICADA',
    loadChildren: () => import('./features/inventaires/inventaires.routes').then(m => m.INVENTAIRES_ROUTES)
  }
];