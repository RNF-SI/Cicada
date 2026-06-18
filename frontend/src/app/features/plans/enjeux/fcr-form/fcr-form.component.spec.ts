import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { FcrFormComponent } from './fcr-form.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Enjeu } from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        fcrForm: {
          title: 'Nouveau FCR',
          editTitle: 'Modifier le FCR',
          connaissance: 'Connaissance',
          ancrage: 'Ancrage territorial',
          fonctionnement: 'Fonctionnement de l\'aire protégée',
          autre: 'Autre',
          categorie: 'Catégorie FCR',
        },
        messages: {
          fcrCreateSuccess: 'FCR créé avec succès',
          fcrUpdateSuccess: 'FCR mis à jour',
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

const existingFcr: Enjeu = {
  id_enjeu: 7,
  id_pg: 10,
  id_categorie: 101,
  categorie_mnemonique: 'FCR',
  libelle: 'FCR existant',
  intitule_court: 'FCRE',
  id_categorie_fcr: 201,
  description: 'Description FCR',
  habitat: false,
  espece: false,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
  processus: false,
  valeur_paysagere: false,
  patrimoine_culturel: false,
  developpement_durable: false,
  usages: false,
  valeur_ajoutee: false,
  autre_socioeco: false,
  date_ajout: '2024-01-01T00:00:00Z',
  date_maj: '2024-01-15T00:00:00Z',
};

const mockNomenclatures = [
  { id_nomenclature: 201, mnemonique: 'CONNAISSANCE', label: 'Connaissance' },
  { id_nomenclature: 202, mnemonique: 'ANCRAGE', label: 'Ancrage territorial' },
  { id_nomenclature: 203, mnemonique: 'FONCTIONNEMENT', label: 'Fonctionnement' },
  { id_nomenclature: 204, mnemonique: 'AUTRE', label: 'Autre' },
];

function buildActivatedRoute(params: Record<string, string> = {}, parentParams: Record<string, string> = { slug: 'plan-test' }): any {
  const parentSnapshot = {
    paramMap: {
      get: (key: string) => parentParams[key] || null,
    },
  };
  const currentSnapshot = {
    paramMap: {
      get: (key: string) => params[key] || null,
    },
    pathFromRoot: [] as any[],
  };
  currentSnapshot.pathFromRoot = [parentSnapshot, currentSnapshot];
  return {
    snapshot: currentSnapshot,
    parent: {
      snapshot: parentSnapshot,
      parent: null,
    },
  };
}

describe('FcrFormComponent', () => {
  let component: FcrFormComponent;
  let fixture: ComponentFixture<FcrFormComponent>;
  let router: Router;
  let mockSnackBarOpen: jest.SpyInstance;
  let mockEnjeuService: {
    createFcr: jest.Mock;
    updateEnjeu: jest.Mock;
    getEnjeu: jest.Mock;
  };
  let mockAdminService: {
    getPlanBySlug: jest.Mock;
    getNomenclatureByMnemonique: jest.Mock;
    getNomenclaturesByType: jest.Mock;
  };

  function setup(routeParams: Record<string, string> = {}, parentParentParams: Record<string, string> = { slug: 'plan-test' }): void {
    mockEnjeuService = {
      createFcr: jest.fn().mockReturnValue(of(existingFcr)),
      updateEnjeu: jest.fn().mockReturnValue(of(existingFcr)),
      getEnjeu: jest.fn().mockReturnValue(of(existingFcr)),
    };
    mockAdminService = {
      getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test' })),
      getNomenclatureByMnemonique: jest.fn().mockReturnValue(of({ id_nomenclature: 101, mnemonique: 'FCR', label: 'FCR' })),
      getNomenclaturesByType: jest.fn().mockReturnValue(of(mockNomenclatures)),
    };
    TestBed.configureTestingModule({
      imports: [
        FcrFormComponent,
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
    // Spy on the MatSnackBar prototype to capture calls from any instance
    mockSnackBarOpen = jest.spyOn(MatSnackBar.prototype, 'open').mockImplementation();

    fixture = TestBed.createComponent(FcrFormComponent);
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
      expect(component.form.get('id_categorie_fcr')?.value).toBeNull();
      expect(component.form.get('description')?.value).toBe('');
    });

    it('should detect create mode when no fcrId param', () => {
      setup();
      expect(component.isEditMode()).toBe(false);
      expect(component.fcrId()).toBeNull();
    });

    it('should detect edit mode when fcrId param present', () => {
      setup({ fcrId: '7' });
      expect(component.isEditMode()).toBe(true);
      expect(component.fcrId()).toBe(7);
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

    it('should require id_categorie_fcr', () => {
      component.form.get('id_categorie_fcr')?.setValue(null);
      expect(component.form.get('id_categorie_fcr')?.hasError('required')).toBe(true);
    });

    it('should validate libelle maxLength(500)', () => {
      component.form.get('libelle')?.setValue('a'.repeat(501));
      expect(component.form.get('libelle')?.hasError('maxlength')).toBe(true);
    });

    it('should allow empty description', () => {
      component.form.get('description')?.setValue('');
      expect(component.form.get('description')?.valid).toBe(true);
    });
  });

  // =========================================================================
  // FCR categories
  // =========================================================================

  describe('FCR categories', () => {
    it('should load FCR categories from API', () => {
      setup();
      expect(mockAdminService.getNomenclaturesByType).toHaveBeenCalledWith('CATEGORIE_FCR');
      const options = component.fcrCategorieOptions();
      expect(options.length).toBe(4);
      expect(options[0].id).toBe(201);
      expect(options[0].mnemonique).toBe('CONNAISSANCE');
    });

    it('should use fallback categories on API error', () => {
      // Setup with error on getNomenclaturesByType
      const errorEnjeuService = {
        createFcr: jest.fn().mockReturnValue(of(existingFcr)),
        updateEnjeu: jest.fn().mockReturnValue(of(existingFcr)),
        getEnjeu: jest.fn().mockReturnValue(of(existingFcr)),
      };
      const errorAdminService = {
        getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test' })),
        getNomenclatureByMnemonique: jest.fn().mockReturnValue(of({ id_nomenclature: 101 })),
        getNomenclaturesByType: jest.fn().mockReturnValue(throwError(() => new Error('API error'))),
      };

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        imports: [
          FcrFormComponent,
          NoopAnimationsModule,
          HttpClientTestingModule,
          RouterTestingModule,
          TranslateModule.forRoot({
            loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          }),
        ],
        providers: [
          { provide: ActivatedRoute, useValue: buildActivatedRoute({}, { slug: 'plan-test' }) },
          { provide: EnjeuService, useValue: errorEnjeuService },
          { provide: AdminService, useValue: errorAdminService },
        ],
      }).compileComponents();

      const fix = TestBed.createComponent(FcrFormComponent);
      fix.detectChanges();

      const options = fix.componentInstance.fcrCategorieOptions();
      expect(options.length).toBe(5);
      expect(options[0].mnemonique).toBe('CONNAISSANCE');
      expect(options[0].id).toBe(0); // fallback uses id: 0
      expect(options.some(o => o.mnemonique === 'SURVEILLANCE')).toBe(true); // #370
    });

    it('should map mnemonique to translate key', () => {
      setup();
      const options = component.fcrCategorieOptions();
      expect(options[0].translateKey).toBe('enjeux.fcrForm.connaissance');
      expect(options[1].translateKey).toBe('enjeux.fcrForm.ancrage');
      expect(options[2].translateKey).toBe('enjeux.fcrForm.fonctionnement');
      expect(options[3].translateKey).toBe('enjeux.fcrForm.autre');
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
      expect(mockEnjeuService.createFcr).not.toHaveBeenCalled();
    });

    it('should call createFcr with correct payload', () => {
      component.form.patchValue({
        libelle: 'Mon FCR',
        intitule_court: 'MF',
        id_categorie_fcr: 201,
        description: 'Desc',
      });
      component.onSubmit();
      const payload = mockEnjeuService.createFcr.mock.calls[0][0];
      expect(payload.id_pg).toBe(10);
      expect(payload.libelle).toBe('Mon FCR');
      expect(payload.id_categorie_fcr).toBe(201);
    });

    it('should show snackbar and navigate on success', () => {
      component.form.patchValue({ libelle: 'FCR', id_categorie_fcr: 201 });
      component.onSubmit();
      expect(mockSnackBarOpen).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
    });

    it('should set errorMessage on error', () => {
      mockEnjeuService.createFcr.mockReturnValue(throwError(() => ({ message: 'Erreur serveur' })));
      component.form.patchValue({ libelle: 'FCR', id_categorie_fcr: 201 });
      component.onSubmit();
      expect(component.errorMessage()).toBe('Erreur serveur');
    });
  });

  // =========================================================================
  // Edition
  // =========================================================================

  describe('edition', () => {
    beforeEach(() => setup({ fcrId: '7' }));

    it('should load existing FCR and populate form', () => {
      expect(mockEnjeuService.getEnjeu).toHaveBeenCalledWith(7);
      expect(component.form.get('libelle')?.value).toBe('FCR existant');
      expect(component.form.get('id_categorie_fcr')?.value).toBe(201);
    });

    it('should call updateEnjeu on submit in edit mode', () => {
      component.form.patchValue({ libelle: 'Modifié' });
      component.onSubmit();
      expect(mockEnjeuService.updateEnjeu).toHaveBeenCalledWith(7, expect.objectContaining({ libelle: 'Modifié' }));
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
      mockEnjeuService.createFcr.mockReturnValue(throwError(() => ({ message: 'Erreur' })));

      const banner = document.createElement('div');
      banner.className = 'error-banner';
      fixture.nativeElement.appendChild(banner);

      component.form.patchValue({ libelle: 'Test FCR', id_categorie_fcr: 201 });
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
  // Navigation
  // =========================================================================

  describe('navigation', () => {
    it('should navigate back on cancel', () => {
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
      component.form.get('intitule_court')?.setValue('ABCD');
      expect(component.intituleCourtLength).toBe(4);
    });
  });
});
