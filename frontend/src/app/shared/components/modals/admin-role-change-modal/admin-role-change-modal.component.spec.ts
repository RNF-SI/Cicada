import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';

import {
  AdminRoleChangeModalComponent,
  AdminRoleChangeModalData,
  AdminRoleChangeModalResult
} from './admin-role-change-modal.component';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'modals.adminRoleChange.validation.minLength': 'Minimum 10 caractères requis'
    });
  }
}

describe('AdminRoleChangeModalComponent', () => {
  let component: AdminRoleChangeModalComponent;
  let fixture: ComponentFixture<AdminRoleChangeModalComponent>;
  let dialogCloseMock: jest.Mock;

  const mockPromotionData: AdminRoleChangeModalData = {
    type: 'promotion',
    userName: 'Jean Dupont',
    userEmail: 'jean.dupont@test.fr'
  };

  const mockDemotionData: AdminRoleChangeModalData = {
    type: 'demotion',
    userName: 'Marie Martin',
    userEmail: 'marie.martin@test.fr'
  };

  const setupTestBed = async (dialogData: AdminRoleChangeModalData) => {
    dialogCloseMock = jest.fn();

    await TestBed.configureTestingModule({
      imports: [
        AdminRoleChangeModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: { close: dialogCloseMock } },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ]
    }).compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(AdminRoleChangeModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should expose dialog data', () => {
      expect(component.data.userName).toBe('Jean Dupont');
      expect(component.data.userEmail).toBe('jean.dupont@test.fr');
    });

    it('should initialize with empty justification', () => {
      expect(component.justification).toBe('');
    });

    it('should initialize with no error message', () => {
      expect(component.errorMessage()).toBeNull();
    });
  });

  // ==================== PROMOTION MODE ====================

  describe('Promotion Mode', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should identify promotion mode', () => {
      expect(component.isPromotion).toBe(true);
    });

    it('should return promotion title key', () => {
      expect(component.titleKey).toBe('modals.adminRoleChange.promotion.title');
    });

    it('should return promotion warning key', () => {
      expect(component.warningMessageKey).toBe('modals.adminRoleChange.promotion.warning');
    });

    it('should return promotion confirm button key', () => {
      expect(component.confirmButtonKey).toBe('modals.adminRoleChange.promotion.confirm');
    });
  });

  // ==================== DEMOTION MODE ====================

  describe('Demotion Mode', () => {
    beforeEach(async () => {
      await setupTestBed(mockDemotionData);
    });

    it('should identify demotion mode', () => {
      expect(component.isPromotion).toBe(false);
    });

    it('should return demotion title key', () => {
      expect(component.titleKey).toBe('modals.adminRoleChange.demotion.title');
    });

    it('should return demotion warning key', () => {
      expect(component.warningMessageKey).toBe('modals.adminRoleChange.demotion.warning');
    });

    it('should return demotion confirm button key', () => {
      expect(component.confirmButtonKey).toBe('modals.adminRoleChange.demotion.confirm');
    });
  });

  // ==================== VALIDATION ====================

  describe('Validation', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should be invalid with empty justification', () => {
      component.justification = '';
      expect(component.isValid).toBe(false);
    });

    it('should be invalid with justification less than 10 characters', () => {
      component.justification = 'short';
      expect(component.isValid).toBe(false);
    });

    it('should be invalid with exactly 9 characters', () => {
      component.justification = '123456789';
      expect(component.isValid).toBe(false);
    });

    it('should be valid with exactly 10 characters', () => {
      component.justification = '1234567890';
      expect(component.isValid).toBe(true);
    });

    it('should be valid with more than 10 characters', () => {
      component.justification = 'This is a valid justification for the role change';
      expect(component.isValid).toBe(true);
    });

    it('should count only non-whitespace content', () => {
      component.justification = '     ';
      expect(component.isValid).toBe(false);
    });

    it('should trim justification when checking validity', () => {
      component.justification = '   short   ';
      expect(component.isValid).toBe(false);
    });
  });

  // ==================== CONFIRM ACTION ====================

  describe('Confirm Action', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should not close dialog when justification is invalid', () => {
      component.justification = 'short';

      component.onConfirm();

      expect(dialogCloseMock).not.toHaveBeenCalled();
    });

    it('should set error message when justification is invalid', () => {
      component.justification = 'short';

      component.onConfirm();

      expect(component.errorMessage()).not.toBeNull();
    });

    it('should close dialog with confirmed result when valid', () => {
      component.justification = 'This is a valid justification';

      component.onConfirm();

      expect(dialogCloseMock).toHaveBeenCalledWith({
        confirmed: true,
        justification: 'This is a valid justification'
      } as AdminRoleChangeModalResult);
    });

    it('should trim justification in result', () => {
      component.justification = '  Valid justification text  ';

      component.onConfirm();

      expect(dialogCloseMock).toHaveBeenCalledWith({
        confirmed: true,
        justification: 'Valid justification text'
      });
    });
  });

  // ==================== CANCEL ACTION ====================

  describe('Cancel Action', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should close dialog with confirmed false on cancel', () => {
      component.onCancel();

      expect(dialogCloseMock).toHaveBeenCalledWith({
        confirmed: false
      } as AdminRoleChangeModalResult);
    });

    it('should not include justification on cancel', () => {
      component.justification = 'Some text';

      component.onCancel();

      const result = dialogCloseMock.mock.calls[0][0] as AdminRoleChangeModalResult;
      expect(result.justification).toBeUndefined();
    });
  });

  // ==================== DIRECT MODE (#655) ====================

  describe('Direct mode (#655)', () => {
    it('should not require a justification when the change is applied directly', async () => {
      await setupTestBed({ ...mockPromotionData, direct: true });

      expect(component.isDirect).toBe(true);
      expect(component.isValid).toBe(true);

      component.onConfirm();

      expect(dialogCloseMock).toHaveBeenCalled();
      const result = dialogCloseMock.mock.calls[0][0] as AdminRoleChangeModalResult;
      expect(result.confirmed).toBe(true);
      expect(result.justification).toBe('');
    });

    it('should use the direct wording for title and confirm button', async () => {
      await setupTestBed({ ...mockPromotionData, direct: true });

      expect(component.titleKey).toBe('modals.adminRoleChange.promotion.titleDirect');
      expect(component.confirmButtonKey).toBe('modals.adminRoleChange.promotion.confirmDirect');
      expect(component.noticeKey).toBe('modals.adminRoleChange.directNotice');
    });

    it('should keep the request wording and the mandatory justification otherwise', async () => {
      await setupTestBed(mockDemotionData);

      expect(component.isDirect).toBe(false);
      expect(component.isValid).toBe(false);
      expect(component.titleKey).toBe('modals.adminRoleChange.demotion.title');
      expect(component.confirmButtonKey).toBe('modals.adminRoleChange.demotion.confirm');
      expect(component.noticeKey).toBe('modals.adminRoleChange.superAdminNotice');
    });
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setupTestBed(mockPromotionData);
    });

    it('should clear error message when user types valid content', () => {
      component.justification = 'short';
      component.onConfirm();

      expect(component.errorMessage()).not.toBeNull();

      component.justification = 'This is now a valid justification';
      // Error would be cleared on next submit or by component logic

      component.onConfirm();
      // If valid, no new error set and dialog closes
      expect(dialogCloseMock).toHaveBeenCalled();
    });
  });
});
