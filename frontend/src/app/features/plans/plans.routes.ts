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
  }
];
