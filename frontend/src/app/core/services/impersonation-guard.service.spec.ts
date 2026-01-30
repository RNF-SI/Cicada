import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService, TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { of } from 'rxjs';

import { ImpersonationGuardService } from './impersonation-guard.service';
import { AuthService } from './auth.service';
import * as environmentModule from '../../../environments/environment';

// Fake translate loader
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'header.impersonation.readOnlyError': 'Modifications désactivées en mode impersonnation',
      'common.actions.close': 'Fermer'
    });
  }
}

describe('ImpersonationGuardService', () => {
  let service: ImpersonationGuardService;
  let snackBarOpenMock: jest.Mock;
  let isImpersonatingSignal: WritableSignal<boolean>;

  const setupTestBed = (allowModifications: boolean, impersonating: boolean) => {
    snackBarOpenMock = jest.fn();
    isImpersonatingSignal = signal(impersonating);

    // Mock environment
    (environmentModule as any).environment = {
      allowImpersonationModifications: allowModifications
    };

    TestBed.configureTestingModule({
      imports: [
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        ImpersonationGuardService,
        {
          provide: AuthService,
          useValue: {
            isImpersonating: isImpersonatingSignal.asReadonly()
          }
        },
        {
          provide: MatSnackBar,
          useValue: { open: snackBarOpenMock }
        }
      ]
    });

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    service = TestBed.inject(ImpersonationGuardService);
  };

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ==================== NOT IMPERSONATING ====================

  describe('When not impersonating', () => {
    beforeEach(() => {
      setupTestBed(false, false); // modifications disabled, not impersonating
    });

    it('should not be in read-only mode', () => {
      expect(service.isReadOnly()).toBe(false);
    });

    it('should allow modifications', () => {
      expect(service.canModify()).toBe(true);
    });

    it('should return true from checkCanModify', () => {
      const result = service.checkCanModify();
      expect(result).toBe(true);
      expect(snackBarOpenMock).not.toHaveBeenCalled();
    });
  });

  // ==================== IMPERSONATING WITH MODIFICATIONS ALLOWED ====================

  describe('When impersonating with modifications allowed (dev mode)', () => {
    beforeEach(() => {
      setupTestBed(true, true); // modifications allowed, impersonating
    });

    it('should not be in read-only mode', () => {
      expect(service.isReadOnly()).toBe(false);
    });

    it('should allow modifications', () => {
      expect(service.canModify()).toBe(true);
    });

    it('should return true from checkCanModify', () => {
      const result = service.checkCanModify();
      expect(result).toBe(true);
      expect(snackBarOpenMock).not.toHaveBeenCalled();
    });
  });

  // ==================== IMPERSONATING IN READ-ONLY MODE ====================

  describe('When impersonating in read-only mode (prod mode)', () => {
    beforeEach(() => {
      setupTestBed(false, true); // modifications disabled, impersonating
    });

    it('should be in read-only mode', () => {
      expect(service.isReadOnly()).toBe(true);
    });

    it('should not allow modifications', () => {
      expect(service.canModify()).toBe(false);
    });

    it('should return false from checkCanModify', () => {
      const result = service.checkCanModify();
      expect(result).toBe(false);
    });

    it('should show snackbar message when checkCanModify returns false', () => {
      service.checkCanModify();

      expect(snackBarOpenMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        expect.objectContaining({
          duration: 5000,
          panelClass: ['snackbar-warning']
        })
      );
    });

    it('should show message via showReadOnlyMessage', () => {
      service.showReadOnlyMessage();

      expect(snackBarOpenMock).toHaveBeenCalled();
    });
  });

  // ==================== REACTIVE BEHAVIOR ====================

  describe('Reactive behavior', () => {
    beforeEach(() => {
      setupTestBed(false, false); // start not impersonating
    });

    it('should update isReadOnly when impersonation state changes', () => {
      expect(service.isReadOnly()).toBe(false);
      expect(service.canModify()).toBe(true);

      // Start impersonating
      isImpersonatingSignal.set(true);

      expect(service.isReadOnly()).toBe(true);
      expect(service.canModify()).toBe(false);

      // Stop impersonating
      isImpersonatingSignal.set(false);

      expect(service.isReadOnly()).toBe(false);
      expect(service.canModify()).toBe(true);
    });
  });

  // ==================== COMPUTED PROPERTIES ====================

  describe('Computed properties', () => {
    it('should have isReadOnly and canModify as inverses', () => {
      // When not impersonating
      setupTestBed(false, false);
      expect(service.isReadOnly()).toBe(!service.canModify());

      TestBed.resetTestingModule();

      // When impersonating with modifications allowed
      setupTestBed(true, true);
      expect(service.isReadOnly()).toBe(!service.canModify());

      TestBed.resetTestingModule();

      // When impersonating in read-only mode
      setupTestBed(false, true);
      expect(service.isReadOnly()).toBe(!service.canModify());
    });
  });
});
