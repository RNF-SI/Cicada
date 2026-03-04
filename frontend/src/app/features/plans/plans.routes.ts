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
    path: 'dupliquer',
    loadComponent: () => import('./plan-duplicate.component').then(m => m.PlanDuplicateComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug',
    component: PlanDetailComponent,
    canActivate: [authGuard]
  },
  {
    path: ':slug/enjeux',
    loadChildren: () => import('./enjeux/enjeux.routes').then(m => m.ENJEUX_ROUTES),
    canActivate: [authGuard]
  },
  {
    path: ':slug/bilan',
    loadComponent: () => import('./suivis/plan-bilan.component').then(m => m.PlanBilanComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/suivi-actions',
    loadComponent: () => import('./suivis/plan-suivi-actions.component').then(m => m.PlanSuiviActionsComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/tableau-de-bord',
    loadComponent: () => import('./suivis/plan-tableau-de-bord.component').then(m => m.PlanTableauDeBordComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/mindmap',
    loadComponent: () => import('./mindmap/plan-mindmap.component').then(m => m.PlanMindmapComponent),
    canActivate: [authGuard]
  }
];
