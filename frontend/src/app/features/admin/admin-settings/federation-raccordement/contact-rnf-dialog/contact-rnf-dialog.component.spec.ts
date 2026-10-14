import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialogRef } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { ContactRnfDialogComponent } from './contact-rnf-dialog.component';
import { FederationRaccordementService } from '../../../../../core/services/federation-raccordement.service';

class FakeLoader implements TranslateLoader {
  getTranslation() {
    return of({
      admin: {
        settings: {
          federation: {
            etat: {
              erreurs: { jeton_suivi_absent: 'Pas de jeton de suivi' },
              formulaire: { requis: 'Obligatoire' },
            },
          },
        },
      },
    });
  }
}

describe('ContactRnfDialogComponent', () => {
  let fixture: ComponentFixture<ContactRnfDialogComponent>;
  let component: ContactRnfDialogComponent;
  let service: { contacterRnf: jest.Mock };
  let dialogRef: { close: jest.Mock };

  beforeEach(async () => {
    service = { contacterRnf: jest.fn() };
    dialogRef = { close: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        ContactRnfDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeLoader } }),
      ],
      providers: [
        { provide: FederationRaccordementService, useValue: service },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    TestBed.inject(TranslateService).use('fr');
    fixture = TestBed.createComponent(ContactRnfDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement;

  it('exige un sujet et un message', () => {
    component.envoyer();
    fixture.detectChanges();

    expect(service.contacterRnf).not.toHaveBeenCalled();
    expect(component.champInvalide('sujet')).toBe(true);
    expect(component.champInvalide('message')).toBe(true);
    expect(el().textContent).toContain('Obligatoire');
  });

  it('envoie le message et se ferme sur true', () => {
    service.contacterRnf.mockReturnValue(of(undefined));
    component.form.setValue({ sujet: ' Code non reçu ', message: ' Bonjour, ' });

    (el().querySelector('[data-testid="contact-envoyer"]') as HTMLButtonElement).click();

    expect(service.contacterRnf).toHaveBeenCalledWith({ sujet: 'Code non reçu', message: 'Bonjour,' });
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('reste ouvert et affiche l’erreur traduite si l’envoi échoue', () => {
    service.contacterRnf.mockReturnValue(throwError(() =>
      new HttpErrorResponse({ status: 400, error: { erreur: 'jeton_suivi_absent' } })));
    component.form.setValue({ sujet: 'Question', message: 'Bonjour' });

    component.envoyer();
    fixture.detectChanges();

    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(component.envoiEnCours()).toBe(false);
    expect(el().querySelector('[data-testid="contact-erreur"]')!.textContent).toContain('Pas de jeton de suivi');
  });

  it('se ferme sur false à l’annulation', () => {
    component.annuler();
    expect(dialogRef.close).toHaveBeenCalledWith(false);
  });
});
