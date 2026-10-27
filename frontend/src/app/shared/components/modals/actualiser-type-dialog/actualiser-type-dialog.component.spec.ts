import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { ReferentielActionsService } from '../../../../core/services/referentiel-actions.service';
import {
  ActualiserTypeDialogComponent, ActualiserTypeDialogData,
} from './actualiser-type-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

const TYPES = [
  { id_nomenclature: 10, mnemonique: 'CS.1', cd_nomenclature: 'CS.1', label: 'Études des eaux', group_label: 'CS — Connaissance' },
  { id_nomenclature: 11, mnemonique: 'CS.1.1', cd_nomenclature: 'CS.1.1', label: 'Études hydrologiques', group_label: 'CS — Connaissance' },
];

const DATA: ActualiserTypeDialogData = {
  operationId: 42, libelle: 'Inventaire des chiroptères', codeAffichage: 'CS3',
  ancienCode: 'CS8', ancienLibelle: 'Inventaire de la faune',
  suggestionId: 10, suggestionCode: 'CS.1', suggestionLibelle: 'Études des eaux',
  note: 'À préciser', typeActuelId: null,
};

describe('ActualiserTypeDialogComponent (#751)', () => {
  let component: ActualiserTypeDialogComponent;
  let fixture: ComponentFixture<ActualiserTypeDialogComponent>;
  let dialogRef: { close: jest.Mock };
  let service: { actualiserType: jest.Mock };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    service = { actualiserType: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [
        ActualiserTypeDialogComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: DATA },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of(TYPES) } },
        { provide: ReferentielActionsService, useValue: service },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ActualiserTypeDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('la proposition de la table se choisit en un clic', () => {
    component.utiliserSuggestion();
    expect(component.choisi()?.id_nomenclature).toBe(10);
  });

  it('enregistre avec le type affiché à l\'ouverture et ferme', () => {
    service.actualiserType.mockReturnValue(of({ id_operation: 42 }));
    component.choisir(TYPES[1]);
    component.valider();
    expect(service.actualiserType).toHaveBeenCalledWith(42, 11, null);
    expect(dialogRef.close).toHaveBeenCalledWith({ operation: { id_operation: 42 } });
  });

  it('409 : signale le choix d\'un autre référent sans fermer', () => {
    const conflit = { code: 'type_deja_modifie', detail: '', id_type_action: 10,
                      type_action_label: 'Études des eaux', actualise_par: 'Bob Martin' };
    service.actualiserType.mockReturnValue(throwError(() =>
      new HttpErrorResponse({ status: 409, error: conflit })));
    component.choisir(TYPES[1]);
    component.valider();
    expect(component.conflit()?.actualise_par).toBe('Bob Martin');
    expect(dialogRef.close).not.toHaveBeenCalled();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="actualiser-type-conflit"]')).not.toBeNull();
  });

  it('sans type choisi, rien n\'est envoyé', () => {
    component.valider();
    expect(service.actualiserType).not.toHaveBeenCalled();
  });
});
