import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router, provideRouter } from '@angular/router';
import { Component, signal, WritableSignal } from '@angular/core';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { ProfileComponent } from './profile.component';
import { AuthService } from '../../core/services/auth.service';
import { User } from '../../core/models/user.model';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'profile.rgpd.messages.deletionRequested': 'Votre demande de suppression a été enregistrée',
      'profile.rgpd.messages.deletionCancelled': 'Votre demande de suppression a été annulée',
      'profile.rgpd.messages.error': 'Une erreur est survenue',
      'common.actions.close': 'Fermer'
    });
  }
}

describe('ProfileComponent', () => {
  let component: ProfileComponent;
  let fixture: ComponentFixture<ProfileComponent>;
  let router: Router;

  let currentUserSignal: WritableSignal<User | null>;
  let requestAccountDeletionMock: jest.Mock;
  let cancelAccountDeletionMock: jest.Mock;
  let logoutMock: jest.Mock;
  let dialogOpenMock: jest.Mock;
  let snackBarOpenMock: jest.Mock;

  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    prenom_role: 'Jean',
    nom_role: 'Dupont',
    niveau_role: 'utilisateur',
    is_staff: false,
    is_active: true,
    is_referent: false,
    organisme: { id_organisme: 1, nom_organisme: 'Test Org' },
    date_joined: '2024-01-15T10:00:00Z',
    last_login: '2024-06-20T14:30:00Z'
  };

  const mockSuperAdmin: User = {
    ...mockUser,
    id: 2,
    email: 'admin@example.com',
    niveau_role: 'super_admin',
    is_staff: true
  };

  const mockAdminOg: User = {
    ...mockUser,
    id: 3,
    email: 'adminog@example.com',
    niveau_role: 'admin_og'
  };

  const mockReferent: User = {
    ...mockUser,
    id: 4,
    email: 'referent@example.com',
    niveau_role: 'utilisateur',
    is_referent: true
  };

  const mockUserWithDeletion: User = {
    ...mockUser,
    deletion_requested_at: new Date().toISOString()
  };

  const setupTestBed = async (user: User | null = mockUser) => {
    currentUserSignal = signal<User | null>(user);
    requestAccountDeletionMock = jest.fn().mockReturnValue(of({ success: true }));
    cancelAccountDeletionMock = jest.fn().mockReturnValue(of({ success: true }));
    logoutMock = jest.fn().mockReturnValue(of(undefined));
    dialogOpenMock = jest.fn();
    snackBarOpenMock = jest.fn();

    const authServiceMock = {
      currentUser: currentUserSignal.asReadonly(),
      requestAccountDeletion: requestAccountDeletionMock,
      cancelAccountDeletion: cancelAccountDeletionMock,
      logout: logoutMock
    };

    await TestBed.configureTestingModule({
      imports: [
        ProfileComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'profile', component: DummyComponent },
          { path: 'activite', component: DummyComponent }
        ]),
        { provide: AuthService, useValue: authServiceMock },
        { provide: MatDialog, useValue: { open: dialogOpenMock } },
        { provide: MatSnackBar, useValue: { open: snackBarOpenMock } }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should expose currentUser from authService', () => {
      expect(component.currentUser()).toEqual(mockUser);
    });

    it('should start with isDeleting false', () => {
      expect(component.isDeleting()).toBe(false);
    });

    it('should start with isCancelling false', () => {
      expect(component.isCancelling()).toBe(false);
    });
  });

  // ==================== FULL NAME ====================

  describe('getFullName', () => {
    it('should return full name when prenom and nom are set', async () => {
      await setupTestBed();
      expect(component.getFullName()).toBe('Jean Dupont');
    });

    it('should return email when prenom is missing', async () => {
      const userWithoutPrenom: User = { ...mockUser, prenom_role: undefined };
      await setupTestBed(userWithoutPrenom);
      expect(component.getFullName()).toBe('test@example.com');
    });

    it('should return email when nom is missing', async () => {
      const userWithoutNom: User = { ...mockUser, nom_role: undefined };
      await setupTestBed(userWithoutNom);
      expect(component.getFullName()).toBe('test@example.com');
    });

    it('should return empty string when user is null', async () => {
      await setupTestBed(null);
      expect(component.getFullName()).toBe('');
    });
  });

  // ==================== ROLE LEVEL LABEL ====================

  describe('getRoleLevelLabel', () => {
    it('should return Super Administrateur for super_admin', async () => {
      await setupTestBed(mockSuperAdmin);
      expect(component.getRoleLevelLabel()).toBe('Super Administrateur');
    });

    it('should return Administrateur Organisme for admin_og', async () => {
      await setupTestBed(mockAdminOg);
      expect(component.getRoleLevelLabel()).toBe('Administrateur Organisme');
    });

    it('should return Utilisateur for utilisateur', async () => {
      await setupTestBed(mockUser);
      expect(component.getRoleLevelLabel()).toBe('Utilisateur');
    });

    it('should return Referent for utilisateur with is_referent', async () => {
      await setupTestBed(mockReferent);
      expect(component.getRoleLevelLabel()).toBe('Referent');
    });

    it('should return empty string when user is null', async () => {
      await setupTestBed(null);
      expect(component.getRoleLevelLabel()).toBe('');
    });

    it('should return raw niveau_role for unknown roles', async () => {
      const userWithUnknownRole: User = { ...mockUser, niveau_role: 'custom_role' as any };
      await setupTestBed(userWithUnknownRole);
      expect(component.getRoleLevelLabel()).toBe('custom_role');
    });
  });

  // ==================== DATE FORMATTING ====================

  describe('formatDate', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should format date correctly', () => {
      const result = component.formatDate('2024-01-15T10:00:00Z');
      // The exact format depends on locale, but should contain these parts
      expect(result).toContain('15');
      expect(result).toContain('2024');
    });

    it('should return dash for null date', () => {
      expect(component.formatDate(null)).toBe('-');
    });

    it('should return dash for undefined date', () => {
      expect(component.formatDate(undefined)).toBe('-');
    });
  });

  describe('formatDateTime', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should format date and time correctly', () => {
      const result = component.formatDateTime('2024-01-15T10:30:00Z');
      expect(result).toContain('15');
      expect(result).toContain('2024');
    });

    it('should return dash for null date', () => {
      expect(component.formatDateTime(null)).toBe('-');
    });

    it('should return dash for undefined date', () => {
      expect(component.formatDateTime(undefined)).toBe('-');
    });
  });

  // ==================== RGPD - PENDING DELETION ====================

  describe('hasPendingDeletion', () => {
    it('should return true when user has deletion_requested_at', async () => {
      await setupTestBed(mockUserWithDeletion);
      expect(component.hasPendingDeletion()).toBe(true);
    });

    it('should return false when user has no deletion_requested_at', async () => {
      await setupTestBed(mockUser);
      expect(component.hasPendingDeletion()).toBe(false);
    });

    it('should return false when user is null', async () => {
      await setupTestBed(null);
      expect(component.hasPendingDeletion()).toBe(false);
    });
  });

  describe('getDeletionRequestDate', () => {
    it('should return formatted date when deletion is requested', async () => {
      await setupTestBed(mockUserWithDeletion);
      const result = component.getDeletionRequestDate();
      expect(result).not.toBe('');
    });

    it('should return empty string when no deletion requested', async () => {
      await setupTestBed(mockUser);
      expect(component.getDeletionRequestDate()).toBe('');
    });
  });

  describe('getDaysUntilDeletion', () => {
    it('should return number of days until deletion', async () => {
      await setupTestBed(mockUserWithDeletion);
      const days = component.getDaysUntilDeletion();
      // Should be around 30 days since deletion_requested_at is today
      expect(days).toBeGreaterThan(0);
      expect(days).toBeLessThanOrEqual(30);
    });

    it('should return 0 when no deletion requested', async () => {
      await setupTestBed(mockUser);
      expect(component.getDaysUntilDeletion()).toBe(0);
    });

    it('should never return negative days', async () => {
      // Create a user with deletion requested 31 days ago
      const oldDeletionUser: User = {
        ...mockUser,
        deletion_requested_at: new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString()
      };
      await setupTestBed(oldDeletionUser);
      expect(component.getDaysUntilDeletion()).toBe(0);
    });
  });

  // ==================== DELETE ACCOUNT DIALOG ====================

  describe('openDeleteAccountDialog', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should open dialog with user email', () => {
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of(undefined))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();

      expect(dialogOpenMock).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          width: '550px',
          data: { userEmail: 'test@example.com' }
        })
      );
    });

    it('should request deletion when dialog is confirmed', fakeAsync(() => {
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(requestAccountDeletionMock).toHaveBeenCalled();
    }));

    it('should not request deletion when dialog is cancelled', fakeAsync(() => {
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of(undefined))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(requestAccountDeletionMock).not.toHaveBeenCalled();
    }));
  });

  describe('openDeleteAccountDialog when user is null', () => {
    it('should not open dialog when user is null', async () => {
      await setupTestBed(null);

      component.openDeleteAccountDialog();

      expect(dialogOpenMock).not.toHaveBeenCalled();
    });
  });

  // ==================== REQUEST ACCOUNT DELETION ====================

  describe('requestAccountDeletion (via dialog)', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should show success snackbar on successful deletion request', fakeAsync(() => {
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Votre demande de suppression a été enregistrée',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should logout user after successful deletion request', fakeAsync(() => {
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(logoutMock).toHaveBeenCalled();
    }));

    it('should show error snackbar on deletion failure', fakeAsync(() => {
      requestAccountDeletionMock.mockReturnValue(throwError(() => ({ message: 'Custom error' })));
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Custom error',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should show generic error on unknown error', fakeAsync(() => {
      requestAccountDeletionMock.mockReturnValue(throwError(() => ({})));
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Une erreur est survenue',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should set isDeleting to false after error', fakeAsync(() => {
      requestAccountDeletionMock.mockReturnValue(throwError(() => new Error('Error')));
      const mockDialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ confirmed: true }))
      };
      dialogOpenMock.mockReturnValue(mockDialogRef);

      component.openDeleteAccountDialog();
      tick();

      expect(component.isDeleting()).toBe(false);
    }));
  });

  // ==================== CANCEL ACCOUNT DELETION ====================

  describe('cancelAccountDeletion', () => {
    beforeEach(async () => {
      await setupTestBed(mockUserWithDeletion);
    });

    it('should call cancelAccountDeletion on authService', fakeAsync(() => {
      component.cancelAccountDeletion();
      tick();

      expect(cancelAccountDeletionMock).toHaveBeenCalled();
    }));

    it('should show success snackbar on successful cancellation', fakeAsync(() => {
      component.cancelAccountDeletion();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Votre demande de suppression a été annulée',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should set isCancelling to false after success', fakeAsync(() => {
      component.cancelAccountDeletion();
      tick();

      expect(component.isCancelling()).toBe(false);
    }));

    it('should show error snackbar on cancellation failure', fakeAsync(() => {
      cancelAccountDeletionMock.mockReturnValue(throwError(() => ({ message: 'Cancel error' })));

      component.cancelAccountDeletion();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Cancel error',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should show generic error on unknown error', fakeAsync(() => {
      cancelAccountDeletionMock.mockReturnValue(throwError(() => ({})));

      component.cancelAccountDeletion();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        'Une erreur est survenue',
        'Fermer',
        expect.objectContaining({ duration: 5000 })
      );
    }));

    it('should set isCancelling to false after error', fakeAsync(() => {
      cancelAccountDeletionMock.mockReturnValue(throwError(() => new Error('Error')));

      component.cancelAccountDeletion();
      tick();

      expect(component.isCancelling()).toBe(false);
    }));
  });

  // ==================== REACTIVE BEHAVIOR ====================

  describe('Reactive behavior', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should update when user changes', () => {
      expect(component.getFullName()).toBe('Jean Dupont');

      currentUserSignal.set({
        ...mockUser,
        prenom_role: 'Marie',
        nom_role: 'Martin'
      });

      expect(component.getFullName()).toBe('Marie Martin');
    });

    it('should update role label when user changes', () => {
      expect(component.getRoleLevelLabel()).toBe('Utilisateur');

      currentUserSignal.set(mockSuperAdmin);

      expect(component.getRoleLevelLabel()).toBe('Super Administrateur');
    });
  });
});
