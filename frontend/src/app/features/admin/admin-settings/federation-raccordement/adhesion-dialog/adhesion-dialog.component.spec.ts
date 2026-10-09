import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpErrorResponse } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { AdhesionDialogComponent, AdhesionDialogData } from './adhesion-dialog.component';
import { FederationRaccordementService } from '../../../../../core/services/federation-raccordement.service';

class FakeLoader implements TranslateLoader {
  getTranslation() {
    return of({
      admin: {
        settings: {
          federation: {
            partageTitre: 'Ce qui est partagé',
            exclusTitre: 'Ce qui n’est jamais partagé',
            etat: {
              erreurs: { contact_invalide: 'Contact invalide' },
              formulaire: { requis: 'Obligatoire', emailInvalide: 'E-mail invalide' },
              adhesion: { formulaire: { consentement: 'Envoyer cette demande active le partage' } },
            },
          },
        },
      },
    });
  }
}

const DATA: AdhesionDialogData = {
  instance_id: 'cen-aura',
  libelle: 'CEN Auvergne-Rhône-Alpes',
  contact_nom: 'Marie Dupont',
  contact_email: 'marie@cen-aura.org',
};

describe('AdhesionDialogComponent', () => {
  let fixture: ComponentFixture<AdhesionDialogComponent>;
  let component: AdhesionDialogComponent;
  let service: { demanderAdhesion: jest.Mock };
  let dialogRef: { close: jest.Mock };

  beforeEach(async () => {
    service = { demanderAdhesion: jest.fn() };
    dialogRef = { close: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        AdhesionDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeLoader } }),
      ],
      providers: [
        { provide: FederationRaccordementService, useValue: service },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: DATA },
      ],
    }).compileComponents();

    TestBed.inject(TranslateService).use('fr');
    fixture = TestBed.createComponent(AdhesionDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement;

  it('dit que la demande vaut consentement au partage, et ce qui est partagé ou non', () => {
    const bloc = el().querySelector('[data-testid="adhesion-consentement"]')!;
    expect(bloc.textContent).toContain('Envoyer cette demande active le partage');
    expect(bloc.textContent).toContain('Ce qui est partagé');
    expect(bloc.textContent).toContain('Ce qui n’est jamais partagé');
  });

  it('pré-remplit le nom et l’e-mail avec l’utilisateur connecté', () => {
    expect((el().querySelector('[data-testid="adhesion-nom"]') as HTMLInputElement).value).toBe('Marie Dupont');
    expect((el().querySelector('[data-testid="adhesion-email"]') as HTMLInputElement).value).toBe('marie@cen-aura.org');
  });

  it('refuse d’envoyer sans nom ni e-mail valide', () => {
    component.form.patchValue({ contact_nom: '', contact_email: 'pas-une-adresse' });
    component.envoyer();
    fixture.detectChanges();

    expect(service.demanderAdhesion).not.toHaveBeenCalled();
    expect(component.erreurChamp('contact_nom')).toBe('admin.settings.federation.etat.formulaire.requis');
    expect(component.erreurChamp('contact_email')).toBe('admin.settings.federation.etat.formulaire.emailInvalide');
    expect(el().textContent).toContain('Obligatoire');
    expect(el().textContent).toContain('E-mail invalide');
  });

  it('envoie la demande et se ferme sur l’état renvoyé', () => {
    const etat = { adhesion: { statut: 'en_attente' } };
    service.demanderAdhesion.mockReturnValue(of(etat));
    component.form.patchValue({ contact_telephone: ' 04 00 00 00 00 ', message: ' Bonjour ' });

    (el().querySelector('[data-testid="adhesion-envoyer"]') as HTMLButtonElement).click();

    expect(service.demanderAdhesion).toHaveBeenCalledWith({
      contact_nom: 'Marie Dupont',
      contact_email: 'marie@cen-aura.org',
      contact_telephone: '04 00 00 00 00',
      message: 'Bonjour',
    });
    expect(dialogRef.close).toHaveBeenCalledWith(etat);
  });

  it('reste ouvert et affiche l’erreur traduite si la demande échoue', () => {
    service.demanderAdhesion.mockReturnValue(throwError(() =>
      new HttpErrorResponse({ status: 400, error: { erreur: 'contact_invalide' } })));

    component.envoyer();
    fixture.detectChanges();

    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(component.envoiEnCours()).toBe(false);
    expect(el().querySelector('[data-testid="adhesion-erreur"]')!.textContent).toContain('Contact invalide');
  });

  it('se ferme sans résultat à l’annulation', () => {
    component.annuler();
    expect(dialogRef.close).toHaveBeenCalledWith();
  });
});
