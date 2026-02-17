/**
 * Routes pour le module Enjeux et FCR.
 */
import { Routes } from '@angular/router';
import { authGuard } from '../../../core/guards/auth.guard';

export const ENJEUX_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./enjeux-list/enjeux-list.component')
      .then(m => m.EnjeuxListComponent),
    canActivate: [authGuard],
    title: 'Enjeux et FCR'
  },
  {
    path: 'nouveau',
    loadComponent: () => import('./enjeu-form/enjeu-form.component')
      .then(m => m.EnjeuFormComponent),
    canActivate: [authGuard],
    title: 'Nouvel enjeu'
  },
  {
    path: 'operations/nouveau',
    loadComponent: () => import('./operation-form/operation-form.component')
      .then(m => m.OperationFormComponent),
    canActivate: [authGuard],
    title: 'Nouvelle action'
  },
  {
    path: 'operations/:operationId/modifier',
    loadComponent: () => import('./operation-form/operation-form.component')
      .then(m => m.OperationFormComponent),
    canActivate: [authGuard],
    title: 'Modifier action'
  },
  {
    path: 'fcr/nouveau',
    loadComponent: () => import('./fcr-form/fcr-form.component')
      .then(m => m.FcrFormComponent),
    canActivate: [authGuard],
    title: 'Nouveau FCR'
  },
  {
    path: 'fcr/:fcrId/modifier',
    loadComponent: () => import('./fcr-form/fcr-form.component')
      .then(m => m.FcrFormComponent),
    canActivate: [authGuard],
    title: 'Modifier FCR'
  },
  {
    path: ':enjeuId/modifier',
    loadComponent: () => import('./enjeu-form/enjeu-form.component')
      .then(m => m.EnjeuFormComponent),
    canActivate: [authGuard],
    title: 'Modifier enjeu'
  },
  {
    path: ':enjeuId',
    loadComponent: () => import('./enjeux-list/enjeux-list.component')
      .then(m => m.EnjeuxListComponent),
    canActivate: [authGuard],
    title: 'Détail enjeu'
  }
];
