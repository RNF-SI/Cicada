/**
 * Routes pour le module Enjeux et FCR.
 */
import { Routes } from '@angular/router';
import { authGuard } from '../../../core/guards/auth.guard';
import { planEditableGuard } from './guards/plan-editable.guard';

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
    canActivate: [authGuard, planEditableGuard],
    title: 'Nouvel enjeu'
  },
  {
    path: 'operations/nouveau',
    loadComponent: () => import('./operation-form/operation-form.component')
      .then(m => m.OperationFormComponent),
    canActivate: [authGuard, planEditableGuard],
    title: 'Nouvelle action'
  },
  {
    path: 'operations/:operationId/modifier',
    loadComponent: () => import('./operation-form/operation-form.component')
      .then(m => m.OperationFormComponent),
    canActivate: [authGuard, planEditableGuard],
    title: 'Modifier action'
  },
  {
    path: 'operations/:operationId',
    loadComponent: () => import('./operation-form/operation-form.component')
      .then(m => m.OperationFormComponent),
    canActivate: [authGuard],
    data: { readOnly: true },
    title: 'Détail action'
  },
  {
    path: 'fcr/nouveau',
    loadComponent: () => import('./fcr-form/fcr-form.component')
      .then(m => m.FcrFormComponent),
    canActivate: [authGuard, planEditableGuard],
    title: 'Nouveau FCR'
  },
  {
    path: 'fcr/:fcrId/modifier',
    loadComponent: () => import('./fcr-form/fcr-form.component')
      .then(m => m.FcrFormComponent),
    canActivate: [authGuard, planEditableGuard],
    title: 'Modifier FCR'
  },
  {
    path: ':enjeuSlug/modifier',
    loadComponent: () => import('./enjeu-form/enjeu-form.component')
      .then(m => m.EnjeuFormComponent),
    canActivate: [authGuard, planEditableGuard],
    title: 'Modifier enjeu'
  },
  {
    path: ':enjeuSlug',
    loadComponent: () => import('./enjeux-list/enjeux-list.component')
      .then(m => m.EnjeuxListComponent),
    canActivate: [authGuard],
    title: 'Détail enjeu'
  }
];
