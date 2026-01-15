import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import {
  DeactivateUserModalComponent,
  DeactivateUserModalData,
  DeactivateUserModalResult
} from './deactivate-user-modal.component';

// Fake translate loader that returns translations
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'modals.deactivateUser.title': 'Desactiver utilisateur',
      'modals.deactivateUser.warning.title': 'Attention',
      'modals.deactivateUser.warning.message': 'Cette action lui retirera l\'acces',
      'modals.deactivateUser.reason.label': 'Raison',
      'modals.deactivateUser.reason.placeholder': 'Placeholder',
      'modals.deactivateUser.reason.hint': 'Caracteres',
      'modals.deactivateUser.confirm': 'Confirmer',
      'modals.deactivateUser.validation.minLength': 'Veuillez fournir une raison d\'au moins 10 caracteres',
      'common.actions.cancel': 'Annuler'
    });
  }
}

describe('DeactivateUserModalComponent', () => {
  let component: DeactivateUserModalComponent;
  let fixture: ComponentFixture<DeactivateUserModalComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<DeactivateUserModalComponent>>;
  let translateService: TranslateService;

  const mockData: DeactivateUserModalData = {
    userName: 'Jean Dupont',
    userEmail: 'jean.dupont@test.fr'
  };

  beforeEach(async () => {
    dialogRef = {
      close: jest.fn()
    } as unknown as jest.Mocked<MatDialogRef<DeactivateUserModalComponent>>;

    await TestBed.configureTestingModule({
      imports: [
        DeactivateUserModalComponent,
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

    fixture = TestBed.createComponent(DeactivateUserModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have empty reason by default', () => {
      expect(component.reason).toBe('');
    });

    it('should have no error message by default', () => {
      expect(component.errorMessage()).toBeNull();
    });

    it('should receive user data from MAT_DIALOG_DATA', () => {
      expect(component.data.userName).toBe('Jean Dupont');
      expect(component.data.userEmail).toBe('jean.dupont@test.fr');
    });
  });

  describe('validation', () => {
    it('should be invalid when reason is empty', () => {
      component.reason = '';
      expect(component.isValid).toBe(false);
    });

    it('should be invalid when reason has less than 10 characters', () => {
      component.reason = 'Court';
      expect(component.isValid).toBe(false);
    });

    it('should be invalid when reason is only whitespace', () => {
      component.reason = '          ';
      expect(component.isValid).toBe(false);
    });

    it('should be valid when reason has exactly 10 characters', () => {
      component.reason = '1234567890';
      expect(component.isValid).toBe(true);
    });

    it('should be valid when reason has more than 10 characters', () => {
      component.reason = 'Utilisateur a quitte l\'organisme';
      expect(component.isValid).toBe(true);
    });

    it('should trim whitespace when validating', () => {
      component.reason = '   abc   ';
      expect(component.isValid).toBe(false); // 3 chars after trim
    });
  });

  describe('onConfirm', () => {
    it('should set error message when reason is invalid', () => {
      component.reason = 'Court';
      component.onConfirm();

      expect(component.errorMessage()).toBe('Veuillez fournir une raison d\'au moins 10 caracteres');
      expect(dialogRef.close).not.toHaveBeenCalled();
    });

    it('should close dialog with confirmed=true and trimmed reason when valid', () => {
      component.reason = '  Utilisateur parti de l\'organisme  ';
      component.onConfirm();

      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: true,
        reason: 'Utilisateur parti de l\'organisme'
      } as DeactivateUserModalResult);
    });

    it('should not set error message when reason is valid', () => {
      component.reason = 'Raison valide et suffisante';
      component.onConfirm();

      expect(component.errorMessage()).toBeNull();
    });
  });

  describe('onCancel', () => {
    it('should close dialog with confirmed=false', () => {
      component.onCancel();

      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: false
      } as DeactivateUserModalResult);
    });

    it('should not include reason when cancelled', () => {
      component.reason = 'Some reason';
      component.onCancel();

      const closeCall = dialogRef.close.mock.calls[0][0] as DeactivateUserModalResult;
      expect(closeCall.confirmed).toBe(false);
      expect(closeCall.reason).toBeUndefined();
    });
  });

  describe('UI rendering', () => {
    it('should display user name in the modal', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('Jean Dupont');
    });

    it('should display user email in the modal', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('jean.dupont@test.fr');
    });

    it('should display user initial in avatar', () => {
      const compiled = fixture.nativeElement;
      const avatar = compiled.querySelector('.user-avatar');
      expect(avatar.textContent.trim()).toBe('J');
    });

    it('should display warning message about deactivation consequences', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('retirera l\'acces');
    });

    it('should have disabled confirm button when reason is invalid', () => {
      component.reason = '';
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const confirmButton = compiled.querySelector('button[color="warn"]');
      expect(confirmButton.disabled).toBe(true);
    });

    it('should have enabled confirm button when reason is valid', () => {
      component.reason = 'Raison valide et suffisante';
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const confirmButton = compiled.querySelector('button[color="warn"]');
      expect(confirmButton.disabled).toBe(false);
    });
  });
});
