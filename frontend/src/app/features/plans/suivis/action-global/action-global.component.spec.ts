/**
 * Tests unitaires — ActionGlobalComponent (#531).
 *
 * Vérifie le lien « Voir la fiche de l'action » depuis la page globale de suivi :
 * la navigation cible la route fiche de l'action, avec `from=suivi` pour que le
 * bouton « Retour » de la fiche revienne au suivi des actions.
 */
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { ActionGlobalComponent } from './action-global.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { Operation } from '../../../../core/models/enjeu.model';

function setup(router: { navigate: jest.Mock }): ActionGlobalComponent {
  const route = {
    snapshot: { paramMap: new Map<string, string>() },
  };
  TestBed.configureTestingModule({
    providers: [
      ActionGlobalComponent,
      { provide: ActivatedRoute, useValue: route },
      { provide: Router, useValue: router },
      { provide: AdminService, useValue: { getPlanBySlug: jest.fn().mockReturnValue(of({})), getNomenclaturesByType: jest.fn().mockReturnValue(of([])) } },
      { provide: AuthService, useValue: { hasGlobalAccess: () => false, isAdminOrganisme: () => false, currentUser: () => null } },
      { provide: EnjeuService, useValue: { getOperation: jest.fn().mockReturnValue(of({})), getMesuresByMetrique: jest.fn().mockReturnValue(of([])) } },
      { provide: MatSnackBar, useValue: { open: jest.fn() } },
      { provide: TranslateService, useValue: { instant: (k: string) => k } },
    ],
  });
  return TestBed.inject(ActionGlobalComponent);
}

describe('ActionGlobalComponent — lien vers la fiche action (#531)', () => {
  it('navigue vers la fiche de l\'action avec from=suivi', () => {
    const router = { navigate: jest.fn() };
    const c = setup(router);
    c.planSlug.set('plan-x');
    c.operation.set({ id_operation: 42, libelle: 'Action test' } as unknown as Operation);

    c.goToFiche();

    expect(router.navigate).toHaveBeenCalledWith(
      ['/plans', 'plan-x', 'enjeux', 'operations', 42, 'fiche'],
      { queryParams: { from: 'suivi' } },
    );
  });

  it('ne navigue pas si l\'action n\'est pas chargée', () => {
    const router = { navigate: jest.fn() };
    const c = setup(router);
    c.planSlug.set('plan-x');
    c.operation.set(null);

    c.goToFiche();

    expect(router.navigate).not.toHaveBeenCalled();
  });
});
