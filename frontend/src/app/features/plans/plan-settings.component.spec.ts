import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';

import { PlanSettingsComponent } from './plan-settings.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { ArborescenceImportReport } from '../../core/models/admin.model';

/** #770 — étape « Correspondance avec Gestref » de l'import des actions. */
describe('PlanSettingsComponent — correspondance avec Gestref (#770)', () => {
  let admin: {
    validateActionsImport: jest.Mock;
    importActions: jest.Mock;
    getNomenclaturesByType: jest.Mock;
  };

  const rapport = (appariements: any[], can_import = false): ArborescenceImportReport => ({
    can_import, n_errors: can_import ? 0 : 1, n_warnings: 0, issues: [], summary: { actions: 2 },
    appariements, organisme_appariement: { id: 3, nom: 'CEN Test' },
  });

  function creer(): PlanSettingsComponent {
    admin = {
      validateActionsImport: jest.fn(),
      importActions: jest.fn().mockReturnValue(of({ created: {}, total: 2 })),
      getNomenclaturesByType: jest.fn().mockReturnValue(of([
        { id_nomenclature: 10, mnemonique: 'IP.2', cd_nomenclature: 'IP.2', label: 'Entretien' },
        { id_nomenclature: 11, mnemonique: 'CS.8.3', cd_nomenclature: 'CS.8.3', label: 'Végétation' },
      ])),
    };
    TestBed.configureTestingModule({
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } },
        { provide: Router, useValue: { navigate: jest.fn() } },
        { provide: AuthService, useValue: {} },
        { provide: AdminService, useValue: admin },
        { provide: MatDialog, useValue: {} },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        { provide: TranslateService, useValue: { instant: (k: string) => k } },
      ],
    });
    const c = TestBed.runInInjectionContext(() => new PlanSettingsComponent());
    c.plan.set({ id_pg: 7, slug: 'plan' } as any);
    c.actionsFile.set(new File(['x'], 'actions.xlsx'));
    return c;
  }

  const valider = (c: PlanSettingsComponent) => (c as any).validateActionsImport(c.actionsFile());

  it('reprend les types déjà appariés pour l\'organisme et charge les types Gestref', () => {
    const c = creer();
    admin.validateActionsImport.mockReturnValue(of(rapport([
      { valeur: 'FAU-01', lignes: [2, 3], id_type_action: 10, type_action: 'IP.2 — Entretien', origine: 'enregistre' },
      { valeur: 'SUIVI VEG', lignes: [4], id_type_action: null, type_action: '', origine: '' },
    ])));
    valider(c);
    expect(c.appariementsChoisis()).toEqual({ 'FAU-01': 10, 'SUIVI VEG': null });
    expect(c.appariementsComplets()).toBe(false);
    expect(c.typesGestrefGroupes().flatMap(g => g.options).length).toBe(2);
  });

  it('revalide puis importe avec les correspondances choisies', () => {
    const c = creer();
    admin.validateActionsImport.mockReturnValueOnce(of(rapport([
      { valeur: 'SUIVI VEG', lignes: [4], id_type_action: null, type_action: '', origine: '' },
    ])));
    valider(c);
    c.choisirAppariement('SUIVI VEG', 11);
    expect(c.appariementsComplets()).toBe(true);
    expect(c.appariementsModifies()).toBe(true);

    admin.validateActionsImport.mockReturnValueOnce(of(rapport([
      { valeur: 'SUIVI VEG', lignes: [4], id_type_action: 11, type_action: 'CS.8.3 — Végétation', origine: 'saisi' },
    ], true)));
    c.appliquerAppariements();
    expect(admin.validateActionsImport).toHaveBeenLastCalledWith(7, expect.any(File), { 'SUIVI VEG': 11 });
    expect(c.appariementsModifies()).toBe(false);

    c.runActionsImport();
    expect(admin.importActions).toHaveBeenCalledWith(7, expect.any(File), { 'SUIVI VEG': 11 });
  });

  it('un nouveau fichier repart sans correspondance', () => {
    const c = creer();
    c.choisirAppariement('FAU-01', 10);
    c.clearActionsImport();
    expect(c.appariementsChoisis()).toEqual({});
  });
});
