import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { PlansListComponent } from './plans-list.component';
import { PlanDetailComponent } from './plan-detail.component';

export const PLANS_ROUTES: Routes = [
  {
    path: '',
    component: PlansListComponent,
    canActivate: [authGuard]
  },
  {
    path: ':id',
    component: PlanDetailComponent,
    canActivate: [authGuard]
  }
];
