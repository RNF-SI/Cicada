import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import {
  AccessRequestDialogComponent,
  AccessRequestDialogData,
  SelectableSite
} from './access-request-dialog.component';
import { ValidationService } from '../../../core/services/validation.service';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'accessRequest.success': 'Demande envoyée',
      'accessRequest.error': 'Erreur lors de la demande',
      'accessRequest.alreadyPending': 'Une demande est déjà en cours',
      'common.actions.close': 'Fermer'
    });
  }
}

describe('AccessRequestDialogComponent', () => {
  let component: AccessRequestDialogComponent;
  let fixture: ComponentFixture<AccessRequestDialogComponent>;

  let dialogCloseMock: jest.Mock;
  let snackBarOpenMock: jest.Mock;
  let requestSiteAccessMock: jest.Mock;
  let requestPlanAccessMock: jest.Mock;

  const mockSelectableSites: SelectableSite[] = [
    { id_site: 1, slug: 'site-1', nom_site: 'Site Alpha' },
    { id_site: 2, slug: 'site-2', nom_site: 'Site Beta' },
    { id_site: 3, slug: 'site-3', nom_site: 'Site Gamma' }
  ];

  const setupTestBed = async (dialogData: AccessRequestDialogData) => {
    dialogCloseMock = jest.fn();
    snackBarOpenMock = jest.fn();
    requestSiteAccessMock = jest.fn().mockReturnValue(of({ success: true }));
    requestPlanAccessMock = jest.fn().mockReturnValue(of({ success: true }));

    const validationServiceMock = {
      requestSiteAccess: requestSiteAccessMock,
      requestPlanAccess: requestPlanAccessMock
    };

    const snackBarMock = {
      open: snackBarOpenMock
    };

    await TestBed.configureTestingModule({
      imports: [
        AccessRequestDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: { close: dialogCloseMock } },
        { provide: MAT_DIALOG_DATA, useValue: dialogData },
        { provide: ValidationService, useValue: validationServiceMock }
      ]
    })
    .overrideProvider(MatSnackBar, { useValue: snackBarMock })
    .compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(AccessRequestDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  // ==================== SITE SINGLE MODE ====================

  describe('Site Single Mode', () => {
    beforeEach(async () => {
      await setupTestBed({
        type: 'site',
        targetSlug: 'site-camargue',
        targetName: 'Réserve de Camargue'
      });
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should not be in selection mode', () => {
      expect(component.isSelectionMode).toBe(false);
    });

    it('should be able to submit with target slug', () => {
      expect(component.canSubmit).toBe(true);
    });

    it('should initialize with empty justification', () => {
      expect(component.justification).toBe('');
    });

    it('should call requestSiteAccess on submit', fakeAsync(() => {
      component.submit();
      tick();

      expect(requestSiteAccessMock).toHaveBeenCalledWith('site-camargue', undefined);
    }));

    it('should include justification when provided', fakeAsync(() => {
      component.justification = 'Je travaille sur ce site';

      component.submit();
      tick();

      expect(requestSiteAccessMock).toHaveBeenCalledWith(
        'site-camargue',
        { justification: 'Je travaille sur ce site' }
      );
    }));

    it('should close dialog with true on success', fakeAsync(() => {
      component.submit();
      tick();

      expect(dialogCloseMock).toHaveBeenCalledWith(true);
    }));

    it('should show success snackbar', fakeAsync(() => {
      component.submit();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalled();
    }));

    it('should set submitting state during request', fakeAsync(() => {
      expect(component.submitting).toBe(false);

      component.submit();
      expect(component.submitting).toBe(true);

      tick();
      // After success, dialog closes, but submitting might still be true since dialog is closed
    }));
  });

  // ==================== PLAN MODE ====================

  describe('Plan Mode', () => {
    beforeEach(async () => {
      await setupTestBed({
        type: 'plan',
        targetId: 42,
        targetName: 'Plan de Gestion 2024'
      });
    });

    it('should not be in selection mode', () => {
      expect(component.isSelectionMode).toBe(false);
    });

    it('should be able to submit with target id', () => {
      expect(component.canSubmit).toBe(true);
    });

    it('should call requestPlanAccess on submit with request_as_referent', fakeAsync(() => {
      component.submit();
      tick();

      expect(requestPlanAccessMock).toHaveBeenCalledWith(42, { request_as_referent: false });
    }));

    it('should not call requestSiteAccess', fakeAsync(() => {
      component.submit();
      tick();

      expect(requestSiteAccessMock).not.toHaveBeenCalled();
    }));
  });

  // ==================== SELECTION MODE ====================

  describe('Selection Mode', () => {
    beforeEach(async () => {
      await setupTestBed({
        type: 'site',
        selectableSites: mockSelectableSites
      });
    });

    it('should be in selection mode', () => {
      expect(component.isSelectionMode).toBe(true);
    });

    it('should not be able to submit without selection', () => {
      expect(component.selectedSiteSlug).toBeNull();
      expect(component.canSubmit).toBe(false);
    });

    it('should be able to submit after selection', () => {
      component.selectedSiteSlug = 'site-2';

      expect(component.canSubmit).toBe(true);
    });

    it('should use selected slug for request', fakeAsync(() => {
      component.selectedSiteSlug = 'site-2';

      component.submit();
      tick();

      expect(requestSiteAccessMock).toHaveBeenCalledWith('site-2', undefined);
    }));

    it('should not submit when no site selected', () => {
      component.selectedSiteSlug = null;

      component.submit();

      expect(requestSiteAccessMock).not.toHaveBeenCalled();
    });
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setupTestBed({
        type: 'site',
        targetSlug: 'site-test',
        targetName: 'Test Site'
      });
    });

    it('should handle generic error', fakeAsync(() => {
      requestSiteAccessMock.mockReturnValue(throwError(() => ({
        status: 500,
        error: { detail: 'Server error' }
      })));

      component.submit();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalled();
      expect(component.submitting).toBe(false);
      expect(dialogCloseMock).not.toHaveBeenCalled();
    }));

    it('should handle 409 conflict (already pending)', fakeAsync(() => {
      requestSiteAccessMock.mockReturnValue(throwError(() => ({
        status: 409,
        error: { detail: 'Request already pending' }
      })));

      component.submit();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalled();
      expect(component.submitting).toBe(false);
    }));

    it('should handle error with deja in message', fakeAsync(() => {
      requestSiteAccessMock.mockReturnValue(throwError(() => ({
        status: 400,
        error: { detail: 'Une demande existe deja' }
      })));

      component.submit();
      tick();

      expect(snackBarOpenMock).toHaveBeenCalled();
    }));

    it('should reset submitting on error', fakeAsync(() => {
      requestSiteAccessMock.mockReturnValue(throwError(() => new Error('Failed')));

      component.submit();
      tick();

      // After error, submitting should be reset to false
      expect(component.submitting).toBe(false);
    }));
  });

  // ==================== EDGE CASES ====================

  describe('Edge Cases', () => {
    it('should handle empty justification as undefined', async () => {
      await setupTestBed({
        type: 'site',
        targetSlug: 'site-test',
        targetName: 'Test'
      });

      component.justification = '';

      component.submit();

      expect(requestSiteAccessMock).toHaveBeenCalledWith('site-test', undefined);
    });

    it('should handle whitespace-only justification', async () => {
      await setupTestBed({
        type: 'site',
        targetSlug: 'site-test',
        targetName: 'Test'
      });

      component.justification = '   ';

      component.submit();

      // Whitespace-only is truthy, so it passes the check
      expect(requestSiteAccessMock).toHaveBeenCalledWith('site-test', { justification: '   ' });
    });

    it('should not submit when canSubmit is false', async () => {
      await setupTestBed({
        type: 'site'
        // No targetSlug, no selectableSites
      });

      expect(component.canSubmit).toBe(false);

      component.submit();

      expect(requestSiteAccessMock).not.toHaveBeenCalled();
    });

    it('should handle missing targetId for plan', async () => {
      await setupTestBed({
        type: 'plan',
        targetName: 'Some Plan'
        // No targetId
      });

      expect(component.canSubmit).toBe(false);
    });

    it('should handle empty selectableSites array', async () => {
      await setupTestBed({
        type: 'site',
        selectableSites: []
      });

      expect(component.isSelectionMode).toBe(false);
    });
  });

  // ==================== DISPLAY ====================

  describe('Display', () => {
    it('should expose data for template', async () => {
      await setupTestBed({
        type: 'site',
        targetSlug: 'test',
        targetName: 'Test Site Name'
      });

      expect(component.data.targetName).toBe('Test Site Name');
      expect(component.data.type).toBe('site');
    });

    it('should expose selectable sites for template', async () => {
      await setupTestBed({
        type: 'site',
        selectableSites: mockSelectableSites
      });

      expect(component.data.selectableSites).toEqual(mockSelectableSites);
      expect(component.data.selectableSites?.length).toBe(3);
    });
  });
});
