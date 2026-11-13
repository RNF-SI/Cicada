import { Component, ViewChild } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { PlanExportKey } from '../plan-exports.catalog';
import { PlanGenerateMenuComponent } from './plan-generate-menu.component';

@Component({
  standalone: true,
  imports: [PlanGenerateMenuComponent, MatMenuModule],
  template: `
    <app-plan-generate-menu #gen [planId]="7" planSlug="mon-plan" [exports]="exports" [imprimer]="imprimer" />
    <button data-testid="trigger" [matMenuTriggerFor]="gen.menu">Générer</button>
  `,
})
class HoteComponent {
  @ViewChild(PlanGenerateMenuComponent) gen!: PlanGenerateMenuComponent;
  exports: PlanExportKey[] = ['budget-suivi', 'fiches-suivi'];
  imprimer = true;
}

/** #795 — menu « Générer » des pages du plan. */
describe('PlanGenerateMenuComponent', () => {
  const admin = {
    downloadBudgetSuivi: jest.fn(),
    downloadFichesSuivi: jest.fn(),
  };
  let snack: jest.SpyInstance;

  function ouvrir() {
    TestBed.configureTestingModule({
      imports: [HoteComponent, NoopAnimationsModule, RouterTestingModule, TranslateModule.forRoot()],
      providers: [{ provide: AdminService, useValue: admin }],
    });
    const fixture = TestBed.createComponent(HoteComponent);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-testid="trigger"]') as HTMLElement).click();
    fixture.detectChanges();
    return fixture;
  }

  const entrees = () =>
    Array.from(document.querySelectorAll('.cdk-overlay-container [mat-menu-item]')).map(e =>
      e.getAttribute('data-testid'),
    );

  beforeEach(() => {
    jest.clearAllMocks();
    (URL as any).createObjectURL = jest.fn().mockReturnValue('blob:x');
    (URL as any).revokeObjectURL = jest.fn();
    snack = jest.spyOn(MatSnackBar.prototype, 'open').mockImplementation();
  });
  afterEach(() => snack.mockRestore());

  it("propose l'impression, les exports sans choix d'année, puis la page Exports", () => {
    ouvrir();
    // L'export d'une année (fiches de suivi) reste sur la page Exports.
    expect(entrees()).toEqual(['generate-print', 'generate-budget-suivi-export', 'generate-all-exports']);
    const lien = document.querySelector('[data-testid="generate-all-exports"]') as HTMLAnchorElement;
    expect(lien.getAttribute('href')).toBe('/plans/mon-plan/exports');
  });

  it("imprime la page", () => {
    const print = jest.spyOn(window, 'print').mockImplementation(() => undefined);
    ouvrir();
    (document.querySelector('[data-testid="generate-print"]') as HTMLElement).click();
    expect(print).toHaveBeenCalled();
    print.mockRestore();
  });

  it("télécharge l'export choisi sous le nom du plan", () => {
    admin.downloadBudgetSuivi.mockReturnValue(of(new Blob(['x'])));
    const clic = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    ouvrir();
    (document.querySelector('[data-testid="generate-budget-suivi-export"]') as HTMLElement).click();
    expect(admin.downloadBudgetSuivi).toHaveBeenCalledWith(7);
    expect(clic).toHaveBeenCalled();
    clic.mockRestore();
  });

  it("signale un échec du téléchargement", () => {
    admin.downloadBudgetSuivi.mockReturnValue(throwError(() => new Error('Refusé')));
    ouvrir();
    (document.querySelector('[data-testid="generate-budget-suivi-export"]') as HTMLElement).click();
    expect(snack).toHaveBeenCalledWith('Refusé', expect.anything(), expect.anything());
  });
});
