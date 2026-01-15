import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const MY_REQUESTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./my-requests.component').then(m => m.MyRequestsComponent),
    canActivate: [authGuard]
  }
];
