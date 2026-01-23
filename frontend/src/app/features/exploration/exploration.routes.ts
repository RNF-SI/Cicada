import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { ExplorationComponent } from './exploration.component';

export const EXPLORATION_ROUTES: Routes = [
  {
    path: '',
    component: ExplorationComponent,
    canActivate: [authGuard],
    title: 'Exploration des données'
  }
];
