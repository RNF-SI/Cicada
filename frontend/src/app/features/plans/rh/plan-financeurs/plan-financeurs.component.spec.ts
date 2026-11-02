import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { RhService } from '../../../../core/services/rh.service';
import { AUTRE_CATEGORIE, PlanFinanceursComponent } from './plan-financeurs.component';

describe('PlanFinanceursComponent (#790)', () => {
  let fixture: ComponentFixture<PlanFinanceursComponent>;
  let component: PlanFinanceursComponent;
  let rh: { getFinanceursByPlan: jest.Mock; createFinanceur: jest.Mock; updateFinanceur: jest.Mock; deleteFinanceur: jest.Mock };

  beforeEach(async () => {
    rh = {
      getFinanceursByPlan: jest.fn().mockReturnValue(of([
        { id_financeur: 1, id_pg: 7, nom: 'Agence RMC', id_categorie: 3, categorie_libre: '',
          categorie_affichage: "Agence de l'eau", nb_actions: 2 },
      ])),
      createFinanceur: jest.fn().mockReturnValue(of({})),
      updateFinanceur: jest.fn().mockReturnValue(of({})),
      deleteFinanceur: jest.fn().mockReturnValue(of(undefined)),
    };
    await TestBed.configureTestingModule({
      imports: [PlanFinanceursComponent, NoopAnimationsModule, TranslateModule.forRoot()],
      providers: [
        { provide: RhService, useValue: rh },
        { provide: AdminService, useValue: {
          getNomenclaturesByType: jest.fn().mockReturnValue(of([{ id_nomenclature: 3, label: "Agence de l'eau" }])),
        } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PlanFinanceursComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('planId', 7);
    fixture.componentRef.setInput('canManage', true);
    component.ngOnChanges();
    fixture.detectChanges();
  });

  it('liste les financeurs du plan avec leur catégorie', () => {
    expect(rh.getFinanceursByPlan).toHaveBeenCalledWith(7);
    expect(fixture.nativeElement.textContent).toContain('Agence RMC');
    expect(fixture.nativeElement.textContent).toContain("Agence de l'eau");
  });

  it('une catégorie hors liste reste propre au plan (catégorie libre)', () => {
    component.nom = 'Commune';
    component.categorie = AUTRE_CATEGORIE;
    expect(component.peutEnregistrer()).toBe(false); // libellé de la catégorie requis
    component.categorieLibre = 'Mécénat local';
    component.enregistrer();
    expect(rh.createFinanceur).toHaveBeenCalledWith({
      id_pg: 7, nom: 'Commune', id_categorie: null, categorie_libre: 'Mécénat local',
    });
  });

  it('modifie un financeur existant', () => {
    component.modifier(component.financeurs()[0]);
    component.nom = 'Agence RMC (contrat)';
    component.enregistrer();
    expect(rh.updateFinanceur).toHaveBeenCalledWith(1, expect.objectContaining({
      nom: 'Agence RMC (contrat)', id_categorie: 3, categorie_libre: '',
    }));
  });
});
