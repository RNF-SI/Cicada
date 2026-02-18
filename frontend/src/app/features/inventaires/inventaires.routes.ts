import { Routes } from '@angular/router';

export const INVENTAIRES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./inventaires-list/inventaires-list.component').then(m => m.InventairesListComponent)
  },
  {
    path: 'nouveau',
    loadComponent: () => import('./inventaire-form/inventaire-form.component').then(m => m.InventaireFormComponent)
  },
  {
    path: ':suiviId/modifier',
    loadComponent: () => import('./inventaire-form/inventaire-form.component').then(m => m.InventaireFormComponent)
  }
];
