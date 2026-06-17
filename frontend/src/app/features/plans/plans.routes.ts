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
    path: ':slug/suivi-actions/saisie/:operation_id/:annee',
    loadComponent: () => import('./suivis/suivi-saisie/suivi-saisie.component').then(m => m.SuiviSaisieComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/tableau-de-bord',
    loadComponent: () => import('./suivis/plan-tableau-de-bord.component').then(m => m.PlanTableauDeBordComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/tableau-de-bord/saisie/:indicateur_id/:annee',
    loadComponent: () => import('./suivis/indicateur-saisie/indicateur-saisie.component').then(m => m.IndicateurSaisieComponent),
    canActivate: [authGuard]
  },
  {
    // #355 — Page globale d'un indicateur (état courant + moyenne + tendance)
    path: ':slug/tableau-de-bord/indicateur/:indicateur_id',
    loadComponent: () => import('./suivis/indicateur-global/indicateur-global.component').then(m => m.IndicateurGlobalComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/tableau-d-arborescence',
    loadComponent: () => import('./mindmap/plan-mindmap.component').then(m => m.PlanMindmapComponent),
    canActivate: [authGuard]
  },
  {
    // Ancien chemin conservé pour compatibilité ; les navigations internes
    // utilisent désormais /tableau-d-arborescence.
    path: ':slug/mindmap',
    loadComponent: () => import('./mindmap/plan-mindmap.component').then(m => m.PlanMindmapComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug/parametres',
    loadComponent: () => import('./plan-settings.component').then(m => m.PlanSettingsComponent),
    canActivate: [authGuard]
  },
  {
    path: ':slug',
    component: PlanDetailComponent,
    canActivate: [authGuard]
  }
];
