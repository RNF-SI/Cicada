import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { ExplorationComponent } from './exploration.component';

export const EXPLORATION_ROUTES: Routes = [
  {
    path: '',
    component: ExplorationComponent,
    canActivate: [authGuard],
    title: 'Exploration des données',
  },
  {
    path: 'contenus',
    loadComponent: () =>
      import('./contenus/exploration-contenus.component').then(
        (m) => m.ExplorationContenusComponent,
      ),
    canActivate: [authGuard],
    title: "Rechercher un contenu d'un plan de gestion",
  },
  {
    path: 'plans',
    loadComponent: () =>
      import('./plans/exploration-plans.component').then(
        (m) => m.ExplorationPlansComponent,
      ),
    canActivate: [authGuard],
    title: 'Rechercher un plan de gestion',
  },
];
