import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { EnjeuFormComponent } from './enjeu-form.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Enjeu } from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        enjeuForm: {
          title: 'Nouvel enjeu',
          editTitle: 'Modifier l\'enjeu',
          ecologique: 'Écologique',
          socioEconomique: 'Socio-économique',
        },
        messages: {
          enjeuCreateSuccess: 'Enjeu créé avec succès',
          enjeuUpdateSuccess: 'Enjeu mis à jour',
          createError: 'Erreur lors de la création',
          updateError: 'Erreur lors de la mise à jour',
          loadError: 'Erreur lors du chargement',
        },
      },
      common: {
        actions: {
          save: 'Enregistrer',
          cancel: 'Annuler',
          close: 'Fermer',
        },
      },
    });
  }
}

const existingEnjeu: Enjeu = {
  id_enjeu: 5,
  id_pg: 10,
  id_categorie: 100,
  categorie_mnemonique: 'ENJEU',
  libelle: 'Enjeu existant',
  intitule_court: 'Court',
  rang: 2,
  categorie_ecologique: false,
  habitat: true,
  espece: false,
  processus: true,
  etat_enjeu: 'bon',
  description: 'Description existante',
  date_ajout: '2024-01-01T00:00:00Z',
  date_maj: '2024-01-15T00:00:00Z',
  slug: 'enjeu-existant',
};

function buildActivatedRoute(params: Record<string, string> = {}, parentParentParams: Record<string, string> = { slug: 'plan-test' }): any {
  return {
    snapshot: {
      paramMap: {
        get: (key: string) => params[key] || null,
      },
    },
    parent: {
      parent: {
        snapshot: {
          paramMap: {
            get: (key: string) => parentParentParams[key] || null,
          },
        },
      },
    },
  };
}

describe('EnjeuFormComponent', () => {
  let component: EnjeuFormComponent;
  let fixture: ComponentFixture<EnjeuFormComponent>;
  let router: Router;
  let mockSnackBarOpen: jest.SpyInstance;
  let mockEnjeuService: {
    createEnjeu: jest.Mock;
    updateEnjeu: jest.Mock;
    getPlanEnjeux: jest.Mock;
  };
  let mockAdminService: {
    getPlanBySlug: jest.Mock;
    getNomenclatureByMnemonique: jest.Mock;
  };

  function setup(routeParams: Record<string, string> = {}, parentParentParams: Record<string, string> = { slug: 'plan-test' }): void {
    mockEnjeuService = {
      createEnjeu: jest.fn().mockReturnValue(of(existingEnjeu)),
      updateEnjeu: jest.fn().mockReturnValue(of(existingEnjeu)),
      getPlanEnjeux: jest.fn().mockReturnValue(of({
        plan_id: 10, plan_nom: 'Plan Test',
        enjeux: [existingEnjeu], fcr: [],
        total_enjeux: 1, total_fcr: 0,
        plan_slug: 'plan-test'
      })),
    };
    mockAdminService = {
      getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test' })),
      getNomenclatureByMnemonique: jest.fn().mockReturnValue(of({ id_nomenclature: 42, mnemonique: 'ENJEU', label: 'Enjeu' })),
    };
    TestBed.configureTestingModule({
      imports: [
        EnjeuFormComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        { provide: ActivatedRoute, useValue: buildActivatedRoute(routeParams, parentParentParams) },
        { provide: EnjeuService, useValue: mockEnjeuService },
        { provide: AdminService, useValue: mockAdminService },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    jest.spyOn(router, 'navigate').mockResolvedValue(true);
    mockSnackBarOpen = jest.spyOn(MatSnackBar.prototype, 'open').mockImplementation();

    fixture = TestBed.createComponent(EnjeuFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => {
    mockSnackBarOpen?.mockRestore();
  });

  // =========================================================================
  // Initialization
  // =========================================================================

  describe('initialization', () => {
    it('should create', () => {
      setup();
      expect(component).toBeTruthy();
    });

    it('should initialize form with default values', () => {
      setup();
      expect(component.form.get('libelle')?.value).toBe('');
      expect(component.form.get('intitule_court')?.value).toBe('');
      expect(component.form.get('rang')?.value).toBe(1);
      expect(component.form.get('categorie_ecologique')?.value).toBe(true);
      expect(component.form.get('habitat')?.value).toBe(false);
      expect(component.form.get('espece')?.value).toBe(false);
      expect(component.form.get('processus')?.value).toBe(false);
    });

    it('should detect create mode when no enjeuSlug param', () => {
      setup();
      expect(component.isEditMode()).toBe(false);
      expect(component.enjeuId()).toBeNull();
    });

    it('should detect edit mode when enjeuSlug param present', () => {
      setup({ enjeuSlug: 'enjeu-existant' });
      expect(component.isEditMode()).toBe(true);
      expect(component.enjeuSlug()).toBe('enjeu-existant');
    });

    it('should load planSlug from parent route', () => {
      setup();
      expect(component.planSlug()).toBe('plan-test');
    });

    it('should load plan name', () => {
      setup();
      expect(mockAdminService.getPlanBySlug).toHaveBeenCalledWith('plan-test');
      expect(component.planNom()).toBe('Plan Test');
    });

    it('should load nomenclature ENJEU category ID', () => {
      setup();
      expect(mockAdminService.getNomenclatureByMnemonique).toHaveBeenCalledWith('CATEGORIE_ENJEU', 'ENJEU');
      expect(component.enjeuCategorieId()).toBe(42);
    });
  });

  // =========================================================================
  // Form validation
  // =========================================================================

  describe('form validation', () => {
    beforeEach(() => setup());

    it('should require libelle', () => {
      component.form.get('libelle')?.setValue('');
      expect(component.form.get('libelle')?.hasError('required')).toBe(true);
    });

    it('should validate libelle maxLength(500)', () => {
      component.form.get('libelle')?.setValue('a'.repeat(501));
      expect(component.form.get('libelle')?.hasError('maxlength')).toBe(true);
    });

    it('should require rang', () => {
      component.form.get('rang')?.setValue(null);
      expect(component.form.get('rang')?.hasError('required')).toBe(true);
    });

    it('should validate rang min(1)', () => {
      component.form.get('rang')?.setValue(0);
      expect(component.form.get('rang')?.hasError('min')).toBe(true);
    });

    it('should validate rang max(3)', () => {
      component.form.get('rang')?.setValue(4);
      expect(component.form.get('rang')?.hasError('max')).toBe(true);
    });

    it('should require categorie_ecologique', () => {
      component.form.get('categorie_ecologique')?.setValue(null);
      expect(component.form.get('categorie_ecologique')?.hasError('required')).toBe(true);
    });

    it('should allow empty intitule_court', () => {
      component.form.get('intitule_court')?.setValue('');
      expect(component.form.get('intitule_court')?.valid).toBe(true);
    });
  });

  // =========================================================================
  // Creation
  // =========================================================================

  describe('creation', () => {
    beforeEach(() => setup());

    it('should not submit when form is invalid', () => {
      component.form.get('libelle')?.setValue('');
      component.onSubmit();
      expect(mockEnjeuService.createEnjeu).not.toHaveBeenCalled();
    });

    it('should call createEnjeu on submit in create mode', () => {
      component.form.patchValue({ libelle: 'Nouveau', rang: 1 });
      component.onSubmit();
      expect(mockEnjeuService.createEnjeu).toHaveBeenCalled();
    });

    it('should build correct payload with all form fields', () => {
      component.form.patchValue({
        libelle: 'Mon enjeu',
        intitule_court: 'ME',
        rang: 2,
        categorie_ecologique: true,
        habitat: true,
        espece: false,
        processus: true,
        etat_enjeu: 'bon',
        description: 'Description'
      });
      component.onSubmit();
      const payload = mockEnjeuService.createEnjeu.mock.calls[0][0];
      expect(payload.id_pg).toBe(10);
      expect(payload.id_categorie).toBe(42);
      expect(payload.libelle).toBe('Mon enjeu');
      expect(payload.rang).toBe(2);
      expect(payload.categorie_ecologique).toBe(true);
      expect(payload.habitat).toBe(true);
      expect(payload.processus).toBe(true);
    });

    it('should show snackbar on success', () => {
      component.form.patchValue({ libelle: 'Test', rang: 1 });
      component.onSubmit();
      expect(mockSnackBarOpen).toHaveBeenCalled();
    });

    it('should navigate back on success', () => {
      component.form.patchValue({ libelle: 'Test', rang: 1 });
      component.onSubmit();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
    });

    it('should set errorMessage on error', () => {
      mockEnjeuService.createEnjeu.mockReturnValue(throwError(() => ({ message: 'Erreur serveur' })));
      component.form.patchValue({ libelle: 'Test', rang: 1 });
      component.onSubmit();
      expect(component.errorMessage()).toBe('Erreur serveur');
    });
  });

  // =========================================================================
  // Edition
  // =========================================================================

  describe('edition', () => {
    beforeEach(() => setup({ enjeuSlug: 'enjeu-existant' }));

    it('should load existing enjeu and populate form', () => {
      expect(mockEnjeuService.getPlanEnjeux).toHaveBeenCalledWith(10);
      expect(component.form.get('libelle')?.value).toBe('Enjeu existant');
      expect(component.form.get('rang')?.value).toBe(2);
      expect(component.form.get('categorie_ecologique')?.value).toBe(false);
      expect(component.form.get('habitat')?.value).toBe(true);
    });

    it('should call updateEnjeu on submit in edit mode', () => {
      component.form.patchValue({ libelle: 'Modifié' });
      component.onSubmit();
      expect(mockEnjeuService.updateEnjeu).toHaveBeenCalledWith(5, expect.objectContaining({ libelle: 'Modifié' }));
    });

    it('should show snackbar on update success', () => {
      component.form.patchValue({ libelle: 'Modifié' });
      component.onSubmit();
      expect(mockSnackBarOpen).toHaveBeenCalled();
    });

    it('should set errorMessage on update error', () => {
      mockEnjeuService.updateEnjeu.mockReturnValue(throwError(() => ({ message: 'Update échoué' })));
      component.form.patchValue({ libelle: 'Modifié' });
      component.onSubmit();
      expect(component.errorMessage()).toBe('Update échoué');
    });
  });

  // =========================================================================
  // scrollToError
  // =========================================================================

  describe('scrollToError', () => {
    let scrollIntoViewMock: jest.Mock;

    beforeEach(() => {
      setup();
      scrollIntoViewMock = jest.fn();
      Element.prototype.scrollIntoView = scrollIntoViewMock;
    });

    afterEach(() => {
      // @ts-ignore
      delete Element.prototype.scrollIntoView;
    });

    it('should scroll to first invalid field when form is invalid', fakeAsync(() => {
      component.form.get('libelle')?.setValue('');
      component.onSubmit();
      tick();

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });
    }));

    it('should scroll to error-banner on API error', fakeAsync(() => {
      mockEnjeuService.createEnjeu.mockReturnValue(throwError(() => ({ message: 'Erreur' })));

      const banner = document.createElement('div');
      banner.className = 'error-banner';
      fixture.nativeElement.appendChild(banner);

      component.form.patchValue({ libelle: 'Test', rang: 1 });
      component.onSubmit();
      tick();

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });

      fixture.nativeElement.removeChild(banner);
    }));

    it('should not throw when no error elements exist', fakeAsync(() => {
      fixture.nativeElement.innerHTML = '';
      component.form.get('libelle')?.setValue('');
      expect(() => {
        component.onSubmit();
        tick();
      }).not.toThrow();
    }));
  });

  // =========================================================================
  // Navigation and helpers
  // =========================================================================

  describe('navigation and helpers', () => {
    it('should navigate back to enjeux list on cancel', () => {
      setup();
      component.onCancel();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
    });

    it('should navigate to /plans if no planId', () => {
      setup({}, {});
      component.onCancel();
      expect(router.navigate).toHaveBeenCalledWith(['/plans']);
    });

    it('should return intituleCourtLength', () => {
      setup();
      component.form.get('intitule_court')?.setValue('ABC');
      expect(component.intituleCourtLength).toBe(3);
    });

    it('should return 0 for empty intituleCourtLength', () => {
      setup();
      component.form.get('intitule_court')?.setValue('');
      expect(component.intituleCourtLength).toBe(0);
    });
  });
});
