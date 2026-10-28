import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { ReferentielActionsService } from '../../../../core/services/referentiel-actions.service';
import { ChoisirCodeDialogComponent, ChoisirCodeDialogData } from './choisir-code-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

const DATA: ChoisirCodeDialogData = {
  referentiel: 'TAXREF', referentielLibelle: 'Taxons (TaxRef)',
  element: {
    id: 7, cible: 'enjeu_taxon', cible_libelle: "Taxon d'un enjeu", contexte: 'Enjeu « Prairies »',
    statut: 'a_actualiser', confiance: 'a_arbitrer', ancien_code: '101', ancien_libelle: 'Taxon 101',
    code_actuel: '101', libelle_actuel: 'Taxon 101', note: 'Scission',
    options: [{ code: '201', libelle: 'Taxon A' }, { code: '202', libelle: 'Taxon B' }],
    actualise_par: null, actualise_le: null,
  },
};

describe('ChoisirCodeDialogComponent (#779)', () => {
  let component: ChoisirCodeDialogComponent;
  let fixture: ComponentFixture<ChoisirCodeDialogComponent>;
  let dialogRef: { close: jest.Mock };
  let service: { actualiserElement: jest.Mock };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    service = { actualiserElement: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [
        ChoisirCodeDialogComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } }),
      ],
      providers: [
        provideHttpClient(), provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: DATA },
        { provide: AdminService, useValue: { getNomenclaturesByType: () => of([]) } },
        { provide: ReferentielActionsService, useValue: service },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ChoisirCodeDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('propose les équivalents et enregistre avec le code affiché à l\'ouverture', () => {
    const boutons = fixture.nativeElement.querySelectorAll('[data-testid="choisir-code-proposition"]');
    expect(boutons.length).toBe(2);
    service.actualiserElement.mockReturnValue(of({ id: 7 }));
    component.choisirProposition('202');
    component.valider();
    expect(service.actualiserElement).toHaveBeenCalledWith(7, '202', '101');
    expect(dialogRef.close).toHaveBeenCalledWith({ element: { id: 7 } });
  });

  it('409 : signale le choix d\'un autre référent sans fermer', () => {
    service.actualiserElement.mockReturnValue(throwError(() => new HttpErrorResponse({
      status: 409, error: { code: 'code_deja_modifie', actualise_par: 'Bob', code_actuel: '201' } })));
    component.choisirProposition('202');
    component.valider();
    expect(component.conflit()?.actualise_par).toBe('Bob');
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
