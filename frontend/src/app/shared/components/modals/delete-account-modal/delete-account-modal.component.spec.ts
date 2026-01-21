import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import {
  DeleteAccountModalComponent,
  DeleteAccountModalData,
  DeleteAccountModalResult
} from './delete-account-modal.component';

// Fake translate loader that returns translations
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'profile.rgpd.dialog.title': 'Supprimer mon compte',
      'profile.rgpd.dialog.warning': 'Cette action est irreversible',
      'profile.rgpd.dialog.consequences.title': 'Consequences',
      'profile.rgpd.dialog.consequences.item1': 'Votre compte sera desactive immediatement',
      'profile.rgpd.dialog.consequences.item2': 'Vous ne pourrez plus vous connecter',
      'profile.rgpd.dialog.consequences.item3': 'Vos associations seront supprimees',
      'profile.rgpd.dialog.consequences.item4': 'Vos donnees seront anonymisees apres 30 jours',
      'profile.rgpd.dialog.gracePeriod': 'Vous disposez de 30 jours pour annuler cette demande',
      'profile.rgpd.dialog.confirmLabel': 'Confirmez votre email',
      'profile.rgpd.dialog.confirmPlaceholder': 'Saisissez votre email',
      'profile.rgpd.dialog.cancelButton': 'Annuler',
      'profile.rgpd.dialog.confirmButton': 'Supprimer definitivement'
    });
  }
}

describe('DeleteAccountModalComponent', () => {
  let component: DeleteAccountModalComponent;
  let fixture: ComponentFixture<DeleteAccountModalComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<DeleteAccountModalComponent>>;
  let translateService: TranslateService;

  const mockData: DeleteAccountModalData = {
    userEmail: 'jean.dupont@test.fr'
  };

  beforeEach(async () => {
    dialogRef = {
      close: jest.fn()
    } as unknown as jest.Mocked<MatDialogRef<DeleteAccountModalComponent>>;

    await TestBed.configureTestingModule({
      imports: [
        DeleteAccountModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr'
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockData }
      ]
    }).compileComponents();

    translateService = TestBed.inject(TranslateService);
    translateService.use('fr');

    fixture = TestBed.createComponent(DeleteAccountModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have empty confirmEmail by default', () => {
      expect(component.confirmEmail).toBe('');
    });

    it('should have isLoading as false by default', () => {
      expect(component.isLoading()).toBe(false);
    });

    it('should receive user email from MAT_DIALOG_DATA', () => {
      expect(component.data.userEmail).toBe('jean.dupont@test.fr');
    });
  });

  describe('validation', () => {
    it('should be invalid when confirmEmail is empty', () => {
      component.confirmEmail = '';
      expect(component.isValid).toBe(false);
    });

    it('should be invalid when confirmEmail does not match user email', () => {
      component.confirmEmail = 'wrong@email.fr';
      expect(component.isValid).toBe(false);
    });

    it('should be valid when confirmEmail matches user email exactly', () => {
      component.confirmEmail = 'jean.dupont@test.fr';
      expect(component.isValid).toBe(true);
    });

    it('should be valid when confirmEmail matches case-insensitively', () => {
      component.confirmEmail = 'JEAN.DUPONT@TEST.FR';
      expect(component.isValid).toBe(true);
    });

    it('should be valid when confirmEmail has leading/trailing whitespace', () => {
      component.confirmEmail = '  jean.dupont@test.fr  ';
      expect(component.isValid).toBe(true);
    });

    it('should be invalid when partial email is entered', () => {
      component.confirmEmail = 'jean.dupont';
      expect(component.isValid).toBe(false);
    });
  });

  describe('onConfirm', () => {
    it('should not close dialog when email is invalid', () => {
      component.confirmEmail = 'wrong@email.fr';
      component.onConfirm();

      expect(dialogRef.close).not.toHaveBeenCalled();
    });

    it('should close dialog with confirmed=true when email is valid', () => {
      component.confirmEmail = 'jean.dupont@test.fr';
      component.onConfirm();

      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: true
      } as DeleteAccountModalResult);
    });

    it('should close dialog when email matches case-insensitively', () => {
      component.confirmEmail = 'Jean.Dupont@Test.FR';
      component.onConfirm();

      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: true
      } as DeleteAccountModalResult);
    });
  });

  describe('onCancel', () => {
    it('should close dialog with confirmed=false', () => {
      component.onCancel();

      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: false
      } as DeleteAccountModalResult);
    });

    it('should close dialog even when email was entered', () => {
      component.confirmEmail = 'jean.dupont@test.fr';
      component.onCancel();

      const closeCall = dialogRef.close.mock.calls[0][0] as DeleteAccountModalResult;
      expect(closeCall.confirmed).toBe(false);
    });
  });

  describe('UI rendering', () => {
    it('should display the dialog title element', () => {
      const compiled = fixture.nativeElement;
      const title = compiled.querySelector('h2[mat-dialog-title]');
      expect(title).toBeTruthy();
    });

    it('should display warning box', () => {
      const compiled = fixture.nativeElement;
      const warningBox = compiled.querySelector('.warning-box');
      expect(warningBox).toBeTruthy();
    });

    it('should display consequences list', () => {
      const compiled = fixture.nativeElement;
      const consequencesList = compiled.querySelector('.consequences ul');
      expect(consequencesList).toBeTruthy();
    });

    it('should display user email as hint', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('jean.dupont@test.fr');
    });

    it('should have disabled confirm button when email is invalid', () => {
      component.confirmEmail = '';
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const confirmButton = compiled.querySelector('button[color="warn"]');
      expect(confirmButton.disabled).toBe(true);
    });

    it('should have enabled confirm button when email is valid', () => {
      component.confirmEmail = 'jean.dupont@test.fr';
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const confirmButton = compiled.querySelector('button[color="warn"]');
      expect(confirmButton.disabled).toBe(false);
    });

    it('should have a cancel button', () => {
      const compiled = fixture.nativeElement;
      const cancelButton = compiled.querySelector('button[mat-stroked-button]');
      expect(cancelButton).toBeTruthy();
    });
  });

  describe('isLoading state', () => {
    it('should disable confirm button when loading', () => {
      component.confirmEmail = 'jean.dupont@test.fr';
      component.isLoading.set(true);
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const confirmButton = compiled.querySelector('button[color="warn"]');
      expect(confirmButton.disabled).toBe(true);
    });
  });
});
