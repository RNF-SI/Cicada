import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const ACTIVITY_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./activity.component').then(m => m.ActivityComponent),
    canActivate: [authGuard],
    title: 'Activite'
  }
];
