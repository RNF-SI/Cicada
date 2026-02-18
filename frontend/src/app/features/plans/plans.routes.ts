import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { PlansListComponent } from './plans-list.component';
import { PlanDetailComponent } from './plan-detail.component';
import { PlanCreateComponent } from './plan-create.component';

export const PLANS_ROUTES: Routes = [
  {
    path: '',
    component: PlansListComponent,
    canActivate: [authGuard]
  },
  {
    path: 'nouveau',
    component: PlanCreateComponent,
    canActivate: [authGuard]
  },
  {
    path: ':id',
    component: PlanDetailComponent,
    canActivate: [authGuard]
  },
  {
    path: ':id/enjeux',
    loadChildren: () => import('./enjeux/enjeux.routes').then(m => m.ENJEUX_ROUTES),
    canActivate: [authGuard]
  },
  {
    path: ':id/bilan',
    loadComponent: () => import('./suivis/plan-bilan.component').then(m => m.PlanBilanComponent),
    canActivate: [authGuard]
  },
  {
    path: ':id/suivi-actions',
    loadComponent: () => import('./suivis/plan-suivi-actions.component').then(m => m.PlanSuiviActionsComponent),
    canActivate: [authGuard]
  },
  {
    path: ':id/tableau-de-bord',
    loadComponent: () => import('./suivis/plan-tableau-de-bord.component').then(m => m.PlanTableauDeBordComponent),
    canActivate: [authGuard]
  }
];
