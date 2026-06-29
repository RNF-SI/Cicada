import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import {
  DuplicatePlanDialogComponent,
  DuplicatePlanDialogData,
  DuplicatePlanDialogResult,
} from './duplicate-plan-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'plans.duplicate.dialog.title': 'Dupliquer le plan',
      'plans.duplicate.dialog.subtitle': 'Sélectionnez les éléments à copier',
      'plans.duplicate.dialog.planInfo': 'Plan source',
      'plans.duplicate.dialog.options.sites': 'Sites associés',
      'plans.duplicate.dialog.options.sitesDescription': 'Copier les sites',
      'plans.duplicate.dialog.options.referents': 'Référents',
      'plans.duplicate.dialog.options.referentsDescription': 'Copier les référents',
      'plans.duplicate.dialog.options.fichiers': 'Fichiers joints',
      'plans.duplicate.dialog.options.fichiersDescription': 'Copier les fichiers',
      'plans.duplicate.dialog.options.enjeux': 'Enjeux',
      'plans.duplicate.dialog.options.enjeuxDescription': 'Copier les enjeux',
      'plans.duplicate.dialog.options.subElements': 'Sous-éléments',
      'plans.duplicate.dialog.options.subElementsDescription': 'Copier les sous-éléments',
      'plans.duplicate.dialog.hints.subElementsDisabled': 'Activez les enjeux',
      'plans.duplicate.dialog.hints.excludedData': 'Les mesures ne sont pas copiées',
      'plans.duplicate.dialog.hints.newStatus': 'Le plan sera créé en brouillon',
      'plans.duplicate.dialog.cancel': 'Annuler',
      'plans.duplicate.dialog.confirm': 'Dupliquer',
    });
  }
}

describe('DuplicatePlanDialogComponent', () => {
  let component: DuplicatePlanDialogComponent;
  let fixture: ComponentFixture<DuplicatePlanDialogComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<DuplicatePlanDialogComponent>>;

  const mockData: DuplicatePlanDialogData = {
    planId: 42,
    planName: 'Plan de Gestion Camargue',
    planPeriod: '2024-2034',
    planStatus: 'valide',
    nbSites: 3,
    planRang: 2,
    planVersion: '1',
  };

  beforeEach(async () => {
    dialogRef = {
      close: jest.fn(),
    } as unknown as jest.Mocked<MatDialogRef<DuplicatePlanDialogComponent>>;

    await TestBed.configureTestingModule({
      imports: [
        DuplicatePlanDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr',
        }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    const translateService = TestBed.inject(TranslateService);
    translateService.use('fr');

    fixture = TestBed.createComponent(DuplicatePlanDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // ==================== initialization ====================

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should receive data from MAT_DIALOG_DATA', () => {
      expect(component.data.planId).toBe(42);
      expect(component.data.planName).toBe('Plan de Gestion Camargue');
    });

    it('should display plan name', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('Plan de Gestion Camargue');
    });

    it('should display plan period', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('2024-2034');
    });
  });

  // ==================== default options ====================

  describe('default options', () => {
    it('should have copySites true by default', () => {
      expect(component.copySites()).toBe(true);
    });

    it('should have copyReferents true by default', () => {
      expect(component.copyReferents()).toBe(true);
    });

    it('should have copyEnjeux true by default', () => {
      expect(component.copyEnjeux()).toBe(true);
    });

    it('should have copyFichiers false by default', () => {
      expect(component.copyFichiers()).toBe(false);
    });

    it('should have copySubElements true by default', () => {
      expect(component.copySubElements()).toBe(true);
    });
  });

  // ==================== enjeux/subElements interaction ====================

  describe('enjeux/subElements interaction', () => {
    it('should disable subElements when enjeux is unchecked', () => {
      component.onEnjeuxChange(false);
      expect(component.copySubElements()).toBe(false);
      expect(component.subElementsDisabled()).toBe(true);
    });

    it('should re-enable subElements toggle when enjeux is rechecked', () => {
      component.onEnjeuxChange(false);
      component.onEnjeuxChange(true);
      expect(component.subElementsDisabled()).toBe(false);
    });

    it('should keep subElements false after enjeux is rechecked (not auto-restore)', () => {
      component.onEnjeuxChange(false);
      component.onEnjeuxChange(true);
      // subElements was set to false when enjeux was unchecked, re-enabling enjeux
      // does not auto-restore subElements
      expect(component.copySubElements()).toBe(false);
    });
  });

  // ==================== onConfirm ====================

  describe('onConfirm', () => {
    it('should close dialog with confirmed true and options', () => {
      component.onConfirm();
      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: true,
        options: {
          copy_sites: true,
          copy_referents: true,
          copy_fichiers: false,
          copy_enjeux: true,
          copy_sub_elements: true,
        },
      } as DuplicatePlanDialogResult);
    });

    it('should include current checkbox values in options', () => {
      component.copySites.set(false);
      component.copyFichiers.set(true);
      component.onConfirm();
      const result = dialogRef.close.mock.calls[0][0] as DuplicatePlanDialogResult;
      expect(result.options!.copy_sites).toBe(false);
      expect(result.options!.copy_fichiers).toBe(true);
    });
  });

  // ==================== onCancel ====================

  describe('onCancel', () => {
    it('should close dialog with confirmed false', () => {
      component.onCancel();
      expect(dialogRef.close).toHaveBeenCalledWith({
        confirmed: false,
      } as DuplicatePlanDialogResult);
    });

    it('should not include options when cancelled', () => {
      component.onCancel();
      const result = dialogRef.close.mock.calls[0][0] as DuplicatePlanDialogResult;
      expect(result.confirmed).toBe(false);
      expect(result.options).toBeUndefined();
    });
  });

  // ==================== UI rendering ====================

  describe('UI rendering', () => {
    it('should render 5 checkboxes', () => {
      const checkboxes = fixture.nativeElement.querySelectorAll('app-checkbox');
      expect(checkboxes.length).toBe(5);
    });

    it('should have a cancel button', () => {
      const buttons = fixture.nativeElement.querySelectorAll('mat-dialog-actions button');
      const cancelBtn = Array.from(buttons).find((b: any) => b.textContent.includes('Annuler'));
      expect(cancelBtn).toBeTruthy();
    });

    it('should have a confirm button', () => {
      const buttons = fixture.nativeElement.querySelectorAll('mat-dialog-actions button');
      const confirmBtn = Array.from(buttons).find((b: any) => b.textContent.includes('Dupliquer'));
      expect(confirmBtn).toBeTruthy();
    });

    it('should disable buttons when loading', () => {
      component.loading.set(true);
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('mat-dialog-actions button');
      buttons.forEach((btn: HTMLButtonElement) => {
        expect(btn.disabled).toBe(true);
      });
    });

    it('should show spinner when loading', () => {
      component.loading.set(true);
      fixture.detectChanges();
      const spinner = fixture.nativeElement.querySelector('mat-spinner');
      expect(spinner).toBeTruthy();
    });
  });
});
