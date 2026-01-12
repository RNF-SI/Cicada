import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const SITES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./sites-list.component').then(m => m.SitesListComponent),
    canActivate: [authGuard]
  }
];
