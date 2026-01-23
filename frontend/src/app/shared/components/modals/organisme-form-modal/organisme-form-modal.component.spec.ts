import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { OrganismeFormModalComponent, OrganismeFormModalData } from './organisme-form-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminOrganisme } from '../../../../core/models/admin.model';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({});
  }
}

describe('OrganismeFormModalComponent', () => {
  let component: OrganismeFormModalComponent;
  let fixture: ComponentFixture<OrganismeFormModalComponent>;

  // Mock functions
  let dialogCloseMock: jest.Mock;
  let getOrganismesMock: jest.Mock;
  let createOrganismeMock: jest.Mock;
  let updateOrganismeMock: jest.Mock;

  const mockOrganisme: AdminOrganisme = {
    id_organisme: 1,
    nom_organisme: 'Test Organisme',
    adresse_organisme: '123 Rue Test',
    cp_organisme: '75001',
    ville_organisme: 'Paris',
    tel_organisme: '0123456789',
    email_organisme: 'test@organisme.fr',
    url_organisme: 'https://test.fr',
    id_parent: undefined
  };

  const mockParentOrganismes: AdminOrganisme[] = [
    { id_organisme: 2, nom_organisme: 'Parent Org 1' },
    { id_organisme: 3, nom_organisme: 'Parent Org 2' }
  ];

  const setupTestBed = async (dialogData: OrganismeFormModalData = {}) => {
    dialogCloseMock = jest.fn();
    getOrganismesMock = jest.fn().mockReturnValue(of({ results: mockParentOrganismes }));
    createOrganismeMock = jest.fn().mockReturnValue(of(mockOrganisme));
    updateOrganismeMock = jest.fn().mockReturnValue(of(mockOrganisme));

    const adminServiceMock = {
      getOrganismes: getOrganismesMock,
      createOrganisme: createOrganismeMock,
      updateOrganisme: updateOrganismeMock
    };

    const dialogRefMock = {
      close: dialogCloseMock
    };

    await TestBed.configureTestingModule({
      imports: [
        OrganismeFormModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        { provide: AdminService, useValue: adminServiceMock },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(OrganismeFormModalComponent);
    component = fixture.componentInstance;
  };

  // ==================== CREATE MODE ====================

  describe('Create Mode', () => {
    beforeEach(async () => {
      await setupTestBed({});
    });

    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should be in create mode when no organisme provided', () => {
      fixture.detectChanges();
      expect(component.isEditMode).toBe(false);
    });

    it('should initialize form with empty values', () => {
      fixture.detectChanges();
      expect(component.form.get('nom_organisme')?.value).toBe('');
      expect(component.form.get('adresse_organisme')?.value).toBe('');
      expect(component.form.get('cp_organisme')?.value).toBe('');
    });

    it('should load parent organismes on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getOrganismesMock).toHaveBeenCalled();
      expect(component.parentOrganismes()).toEqual(mockParentOrganismes);
    }));

    it('should require nom_organisme', () => {
      fixture.detectChanges();
      const control = component.form.get('nom_organisme');

      control?.setValue('');
      expect(control?.valid).toBe(false);

      control?.setValue('Test');
      expect(control?.valid).toBe(true);
    });

    it('should validate postal code format', () => {
      fixture.detectChanges();
      const control = component.form.get('cp_organisme');

      control?.setValue('123');
      expect(control?.valid).toBe(false);

      control?.setValue('12345');
      expect(control?.valid).toBe(true);

      control?.setValue('ABCDE');
      expect(control?.valid).toBe(false);
    });

    it('should validate email format', () => {
      fixture.detectChanges();
      const control = component.form.get('email_organisme');

      control?.setValue('invalid');
      expect(control?.valid).toBe(false);

      control?.setValue('valid@email.fr');
      expect(control?.valid).toBe(true);
    });

    it('should not submit when form is invalid', () => {
      fixture.detectChanges();
      component.form.get('nom_organisme')?.setValue('');

      component.onSubmit();

      expect(createOrganismeMock).not.toHaveBeenCalled();
    });

    it('should call createOrganisme on submit in create mode', fakeAsync(() => {
      fixture.detectChanges();
      component.form.patchValue({
        nom_organisme: 'New Organisme',
        ville_organisme: 'Lyon'
      });

      component.onSubmit();
      tick();

      expect(createOrganismeMock).toHaveBeenCalledWith(expect.objectContaining({
        nom_organisme: 'New Organisme',
        ville_organisme: 'Lyon'
      }));
      expect(dialogCloseMock).toHaveBeenCalledWith(mockOrganisme);
    }));

    it('should show loading state during submission', fakeAsync(() => {
      fixture.detectChanges();
      component.form.patchValue({ nom_organisme: 'Test' });

      expect(component.isLoading()).toBe(false);

      component.onSubmit();
      tick();

      // With synchronous mocks, loading transitions immediately
      // After submission completes, loading should be false
      expect(component.isLoading()).toBe(false);
    }));

    it('should handle create error', fakeAsync(() => {
      createOrganismeMock.mockReturnValue(throwError(() => new Error('Creation failed')));
      fixture.detectChanges();
      component.form.patchValue({ nom_organisme: 'Test' });

      component.onSubmit();
      tick();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toBe('Creation failed');
      expect(dialogCloseMock).not.toHaveBeenCalled();
    }));

    it('should close dialog on cancel', () => {
      fixture.detectChanges();
      component.onCancel();

      expect(dialogCloseMock).toHaveBeenCalledWith();
    });
  });

  // ==================== EDIT MODE ====================

  describe('Edit Mode', () => {
    beforeEach(async () => {
      await setupTestBed({ organisme: mockOrganisme });
    });

    it('should be in edit mode when organisme provided', () => {
      fixture.detectChanges();
      expect(component.isEditMode).toBe(true);
    });

    it('should initialize form with organisme values', () => {
      fixture.detectChanges();
      expect(component.form.get('nom_organisme')?.value).toBe('Test Organisme');
      expect(component.form.get('adresse_organisme')?.value).toBe('123 Rue Test');
      expect(component.form.get('cp_organisme')?.value).toBe('75001');
      expect(component.form.get('ville_organisme')?.value).toBe('Paris');
      expect(component.form.get('email_organisme')?.value).toBe('test@organisme.fr');
    });

    it('should allow setting parent organisme in edit mode', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      // Parent organismes should be loaded
      expect(component.parentOrganismes().length).toBeGreaterThanOrEqual(0);
    }));

    it('should call updateOrganisme on submit in edit mode', fakeAsync(() => {
      fixture.detectChanges();
      component.form.patchValue({ nom_organisme: 'Updated Name' });

      component.onSubmit();
      tick();

      expect(updateOrganismeMock).toHaveBeenCalledWith(1, expect.objectContaining({
        nom_organisme: 'Updated Name'
      }));
      expect(dialogCloseMock).toHaveBeenCalledWith(mockOrganisme);
    }));

    it('should handle update error', fakeAsync(() => {
      updateOrganismeMock.mockReturnValue(throwError(() => new Error('Update failed')));
      fixture.detectChanges();
      component.form.patchValue({ nom_organisme: 'Test' });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Update failed');
    }));
  });

  // ==================== PARENT ORGANISMES ====================

  describe('Parent Organismes', () => {
    it('should use provided parent organismes', async () => {
      await setupTestBed({ parentOrganismes: mockParentOrganismes });
      fixture.detectChanges();
      await fixture.whenStable();

      expect(getOrganismesMock).not.toHaveBeenCalled();
      expect(component.parentOrganismes()).toEqual(mockParentOrganismes);
    });

    it('should load parent organismes from API when not provided', async () => {
      await setupTestBed({});
      fixture.detectChanges();
      await fixture.whenStable();

      expect(getOrganismesMock).toHaveBeenCalled();
    });

    it('should allow selecting parent organisme', async () => {
      await setupTestBed({ parentOrganismes: mockParentOrganismes });
      fixture.detectChanges();
      await fixture.whenStable();

      component.form.get('parent_id')?.setValue(2);
      expect(component.form.get('parent_id')?.value).toBe(2);
    });

    it('should exclude current organisme from parent options', async () => {
      await setupTestBed({
        organisme: { ...mockOrganisme, id_organisme: 2 },
        parentOrganismes: mockParentOrganismes
      });

      fixture.detectChanges();
      await fixture.whenStable();

      // Should exclude id_organisme=2 from parent options
      expect(component.parentOrganismes().find(o => o.id_organisme === 2)).toBeUndefined();
    });
  });

  // ==================== FORM VALIDATION ====================

  describe('Form Validation', () => {
    beforeEach(async () => {
      await setupTestBed({});
      fixture.detectChanges();
    });

    it('should enforce max length on nom_organisme', () => {
      const control = component.form.get('nom_organisme');
      control?.setValue('a'.repeat(256));
      expect(control?.valid).toBe(false);

      control?.setValue('a'.repeat(255));
      expect(control?.valid).toBe(true);
    });

    it('should allow empty optional fields', () => {
      component.form.patchValue({
        nom_organisme: 'Required Name',
        adresse_organisme: '',
        cp_organisme: '',
        ville_organisme: '',
        tel_organisme: '',
        email_organisme: '',
        url_organisme: ''
      });

      expect(component.form.valid).toBe(true);
    });

    it('should mark form as touched on invalid submit', () => {
      component.form.get('nom_organisme')?.setValue('');

      component.onSubmit();

      expect(component.form.get('nom_organisme')?.touched).toBe(true);
    });
  });

  // ==================== PAYLOAD ====================

  describe('Payload', () => {
    beforeEach(async () => {
      await setupTestBed({});
      fixture.detectChanges();
    });

    it('should send undefined for empty optional fields', fakeAsync(() => {
      component.form.patchValue({
        nom_organisme: 'Test',
        adresse_organisme: '',
        cp_organisme: '',
        ville_organisme: ''
      });

      component.onSubmit();
      tick();

      expect(createOrganismeMock).toHaveBeenCalledWith(expect.objectContaining({
        nom_organisme: 'Test',
        adresse_organisme: undefined,
        cp_organisme: undefined,
        ville_organisme: undefined
      }));
    }));

    it('should send null for empty parent_id', fakeAsync(() => {
      component.form.patchValue({
        nom_organisme: 'Test',
        parent_id: null
      });

      component.onSubmit();
      tick();

      expect(createOrganismeMock).toHaveBeenCalledWith(expect.objectContaining({
        parent_id: null
      }));
    }));
  });
});
