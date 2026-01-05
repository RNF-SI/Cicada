import { Routes } from '@angular/router';
import { PlansListComponent } from './plans-list.component';
import { PlanDetailComponent } from './plan-detail.component';

export const PLANS_ROUTES: Routes = [
  {
    path: '',
    component: PlansListComponent
  },
  {
    path: ':id',
    component: PlanDetailComponent
  }
];
