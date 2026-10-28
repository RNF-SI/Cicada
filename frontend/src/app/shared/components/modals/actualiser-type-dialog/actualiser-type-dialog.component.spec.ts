import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { InventaireService } from '../../../../core/services/inventaire.service';
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
  { id_nomenclature: 20, mnemonique: 'GE.1', cd_nomenclature: 'GE.1', label: 'Infrastructures', group_label: 'GE — Équipements' },
  { id_nomenclature: 10, mnemonique: 'CS.1', cd_nomenclature: 'CS.1', label: 'Études des eaux', group_label: 'CS — Connaissance' },
  { id_nomenclature: 11, mnemonique: 'CS.1.1', cd_nomenclature: 'CS.1.1', label: 'Études hydrologiques', group_label: 'CS — Connaissance' },
];

const DATA: ActualiserTypeDialogData = {
  operationId: 42, libelle: 'Inventaire des chiroptères', codeAffichage: 'CS3',
  ancienCode: 'EI3', ancienLibelle: 'Étude des facteurs',
  options: [{ id: 10, code: 'CS.1', libelle: 'Études des eaux' },
            { id: 11, code: 'CS.1.1', libelle: 'Études hydrologiques' }],
  note: 'À préciser', typeActuelId: 5, typeActuelCode: 'EI3', aUnSuivi: false,
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
        { provide: InventaireService, useValue: { getInventaires: () => of({ results: [] }) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ActualiserTypeDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('les équivalents de la table se choisissent en un clic (#776)', () => {
    const boutons = fixture.nativeElement.querySelectorAll('[data-testid="actualiser-type-proposition"]');
    expect(boutons.length).toBe(2);
    component.choisirProposition(DATA.options[1]);
    expect(component.choisi()?.id_nomenclature).toBe(11);
  });

  it('enregistre avec le type affiché à l\'ouverture (ancien type conservé) et ferme', () => {
    service.actualiserType.mockReturnValue(of({ id_operation: 42 }));
    component.choisir(TYPES[0]);
    component.valider();
    expect(service.actualiserType).toHaveBeenCalledWith(42, 20, 5, undefined);
    expect(dialogRef.close).toHaveBeenCalledWith({ operation: { id_operation: 42 } });
  });

  it('une action qui devient CS sans suivi demande les questions du suivi (#776)', () => {
    component.choisirProposition(DATA.options[0]);
    fixture.detectChanges();
    expect(component.devientCs()).toBe(true);
    expect(fixture.nativeElement.querySelector('[data-testid="actualiser-type-suivi"]')).not.toBeNull();
    component.valider();
    expect(service.actualiserType).not.toHaveBeenCalled();
    expect(component.suiviIncomplet()).toBe(true);

    service.actualiserType.mockReturnValue(of({}));
    component.suiviForm.setValue({ intitule: 'Suivi', objectif_principal: 'OBJ', cibles_principales: 'ESPECES' });
    component.protocoleForm.patchValue({ protocole_dans_campanule: false, nom_protocole: 'Local' });
    component.valider();
    const suivi = service.actualiserType.mock.calls[0][3];
    expect(suivi).toEqual(expect.objectContaining({ intitule: 'Suivi', cibles_principales: 'ESPECES' }));
    expect(suivi.protocoles[0]).toEqual(expect.objectContaining({ protocole_dans_campanule: false, nom_protocole: 'Local' }));
  });

  it('409 : signale le choix d\'un autre référent sans fermer', () => {
    const conflit = { code: 'type_deja_modifie', detail: '', id_type_action: 10,
                      type_action_label: 'Études des eaux', actualise_par: 'Bob Martin' };
    service.actualiserType.mockReturnValue(throwError(() =>
      new HttpErrorResponse({ status: 409, error: conflit })));
    component.choisir(TYPES[0]);
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
