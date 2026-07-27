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

// ===========================================================================
// #616 — la fiche globale ignorait les jours saisis et le budget réalisé.
// ===========================================================================
describe('ActionGlobalComponent — budget et temps de travail (#616)', () => {
  /** Action en ventilation maximale : coûts par organisme + lignes RH. */
  function actionOrgPoste(): Operation {
    return {
      id_operation: 42, libelle: 'Action test',
      ventilation_mode: 'by_org_type_poste',
      operation_annees: [{
        annee: 2027, periodicite: true, budget: null, etp: null,
        budget_fonctionnement: null, budget_investissement: null,
        periodicite_mensuelle: {},
        organismes: [{
          id_organisme: 100, budget_fonctionnement: null, budget_investissement: null,
          cout_stage: '200.00', cout_prestataire: '1000.00', autre_cout: '500.00',
          etp: null,
          realisation: { cout_prestataire_realise: '800.00' },
        }],
        rh_lignes: [
          { id_poste: 1, jours: '10.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
          { id_poste: 2, jours: '5.00', finance: false, categorie_depense: 'benevolat_partenariat', poste_cout_jour: '0.00' },
        ],
        realisation: {
          rh_lignes: [
            { id_poste: 1, jours: '8.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
          ],
        },
      }],
    } as unknown as Operation;
  }

  it('totalise le temps de travail depuis les lignes RH, prévu et réalisé', () => {
    const c = setup({ navigate: jest.fn() });
    c.operation.set(actionOrgPoste());

    const row = c.yearRows()[0];
    expect(row.etpPrev).toBe(15);   // 10 j + 5 j de bénévolat, et non 0 j
    expect(row.etpReal).toBe(8);
    expect(c.etpTotal()).toEqual({ prev: 15, real: 8 });
  });

  it('dérive le budget prévu ET réalisé des coûts saisis', () => {
    const c = setup({ navigate: jest.fn() });
    c.operation.set(actionOrgPoste());

    const row = c.yearRows()[0];
    // 3000 (salarial) + 200 + 1000 + 500 ; le bénévolat ne pèse aucun euro.
    expect(row.budgetPrev).toBe(4700);
    // 2400 (salarial réalisé) + 800 (prestataire réalisé), et non 0 €.
    expect(row.budgetReal).toBe(3200);
    expect(c.budgetTotal()).toEqual({ prev: 4700, real: 3200 });
  });

  it('conserve le mode « totaux directs » (budget saisi tel quel)', () => {
    const c = setup({ navigate: jest.fn() });
    c.operation.set({
      id_operation: 43, libelle: 'Action directe', ventilation_mode: 'none',
      operation_annees: [{
        annee: 2027, periodicite: true, budget: '1500.00', etp: null,
        periodicite_mensuelle: {},
        rh_lignes: [{ id_poste: 1, jours: '4.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' }],
        realisation: { budget_realise: '1200.00', rh_lignes: [] },
      }],
    } as unknown as Operation);

    const row = c.yearRows()[0];
    // Le coût salarial ne s'ajoute PAS au total saisi à la main.
    expect(row.budgetPrev).toBe(1500);
    expect(row.budgetReal).toBe(1200);
    expect(row.etpPrev).toBe(4);
  });
});
