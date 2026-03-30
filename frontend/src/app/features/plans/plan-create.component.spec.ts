import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';

import { PlanCreateComponent } from './plan-create.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { ImpersonationGuardService } from '../../core/services/impersonation-guard.service';
import { ModuleService } from '../../core/services/module.service';
import { NotificationService } from '../../core/services/notification.service';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      plans: { title: 'Plans de gestion', newPlan: 'Nouveau plan' },
      header: { title: 'CICADA' },
      modals: {
        planForm: {
          titleCreate: 'Créer un plan',
          requiredFieldsNote: '* Champs obligatoires',
          fields: {
            name: 'Nom du plan',
            sites: 'Sites',
            rang: 'Rang',
            surface: 'Surface',
            ct88: 'CT88',
            startYear: 'Année début',
            endYear: 'Année fin',
            cspnDate: 'Date CSPN',
            docGestion: 'Doc Gestion',
            editorType: 'Type rédacteur',
            editorName: 'Organisme rédacteur',
            redacteurs: 'Rédacteurs',
            relecteurs: 'Relecteurs',
          },
          placeholders: {
            name: 'Nom du plan',
            searchSite: 'Rechercher un site',
            editorName: 'Organisme',
            redacteurs: 'Rédacteurs',
            relecteurs: 'Relecteurs',
          },
          hints: {
            rang: 'Rang du plan',
            surface: 'Surface en hectares',
            editorName: 'Organisme rédacteur',
            redacteurs: 'Rédacteurs du plan',
            relecteurs: 'Relecteurs du plan',
          },
          validation: {
            nameRequired: 'Le nom est obligatoire',
            rangRequired: 'Le rang est obligatoire',
            rangMin: 'Rang minimum 1',
            sitesRequired: 'Sélectionnez au moins un site',
          },
          ct88Options: { yes: 'Oui', no: 'Non' },
          messages: {
            siteCreated: 'Site créé',
            sitePendingValidation: 'Site en attente',
          },
          sitesHint: 'Besoin d\'un nouveau site?',
          sitesHintLink: 'Créer un site',
          noSiteMatching: 'Aucun site trouvé',
          noSiteAvailable: 'Aucun site disponible',
          sitePending: 'En attente',
          addFreeText: 'Ajouter',
        },
      },
      common: {
        actions: {
          save: 'Enregistrer',
          cancel: 'Annuler',
          close: 'Fermer',
          validate: 'Valider',
          search: 'Rechercher',
        },
        validation: { required: 'Champ obligatoire' },
        loading: 'Chargement...',
        none: 'Aucun',
      },
    });
  }
}

describe('PlanCreateComponent', () => {
  let component: PlanCreateComponent;
  let fixture: ComponentFixture<PlanCreateComponent>;
  let router: Router;
  let mockSnackBarOpen: jest.SpyInstance;
  let mockAdminService: {
    getRedacteurTypes: jest.Mock;
    getUsers: jest.Mock;
    getOrganismes: jest.Mock;
    getSites: jest.Mock;
    getOrganismeSites: jest.Mock;
    createPlan: jest.Mock;
  };

  // Writable signals for AuthService mock
  let isSuperAdminSignal: WritableSignal<boolean>;
  let isAuthenticatedSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<any>;
  let canAccessAdminSignal: WritableSignal<boolean>;

  function setup(opts: { isSuperAdmin?: boolean } = {}): void {
    const isSuperAdmin = opts.isSuperAdmin ?? true;

    mockAdminService = {
      getRedacteurTypes: jest.fn().mockReturnValue(of([
        { id_nomenclature: 1, cd_nomenclature: 'TYPE1', label: 'Type 1' },
      ])),
      getUsers: jest.fn().mockReturnValue(of({
        results: [
          { id_role: 1, nom_role: 'Dupont', prenom_role: 'Jean', email: 'jean@test.fr' },
          { id_role: 2, nom_role: 'Martin', prenom_role: 'Marie', email: 'marie@test.fr' },
        ],
        count: 2,
      })),
      getOrganismes: jest.fn().mockReturnValue(of({
        results: [
          { id_organisme: 1, nom_organisme: 'RNF' },
          { id_organisme: 2, nom_organisme: 'CEN AURA' },
        ],
        count: 2,
      })),
      getSites: jest.fn().mockReturnValue(of({
        results: [
          { id_site: 10, nom_site: 'Camargue', type_site_label: 'RNN', current_user_access: { has_access: true, role_label: 'Référent', access_type: 'referent' } },
          { id_site: 20, nom_site: 'Vercors', type_site_label: 'PNR', current_user_access: { has_access: true, role_label: 'Membre', access_type: 'membre' } },
          { id_site: 30, nom_site: 'Scandola', type_site_label: 'RNN', current_user_access: { has_access: true, role_label: 'Membre', access_type: 'membre' } },
        ],
        count: 3,
      })),
      getOrganismeSites: jest.fn().mockReturnValue(of([])),
      createPlan: jest.fn().mockReturnValue(of({ id_pg: 99, slug: 'nouveau-plan', nom: 'Nouveau plan' })),
    };

    // Signal-based AuthService mock (required by HeaderComponent)
    isSuperAdminSignal = signal(isSuperAdmin);
    isAuthenticatedSignal = signal(true);
    currentUserSignal = signal({
      id_role: 1,
      email: 'admin@test.fr',
      prenom_role: 'Admin',
      nom_role: 'Test',
      niveau_role: isSuperAdmin ? 'super_admin' : 'admin_og',
      organisme: { id_organisme: 1, nom_organisme: 'RNF' },
    });
    canAccessAdminSignal = signal(true);

    const authServiceMock = {
      isAuthenticated: isAuthenticatedSignal.asReadonly(),
      currentUser: currentUserSignal.asReadonly(),
      isSuperAdmin: isSuperAdminSignal.asReadonly(),
      isAdminOrganisme: signal(false).asReadonly(),
      canAccessAdmin: canAccessAdminSignal.asReadonly(),
      isImpersonating: signal(false).asReadonly(),
      impersonationInfo: signal(null).asReadonly(),
      getUserDisplayName: jest.fn().mockReturnValue('Admin Test'),
      getOriginalUserDisplayName: jest.fn().mockReturnValue('Admin Test'),
      logout: jest.fn().mockReturnValue(of(undefined)),
      stopImpersonation: jest.fn().mockReturnValue(of(undefined)),
    };

    const impersonationGuardMock = {
      isReadOnly: signal(false).asReadonly(),
    };

    const moduleServiceMock = {
      getMyAccessibleModules: jest.fn().mockReturnValue(of([])),
    };

    const notificationServiceMock = {
      notifications: signal([]),
      unreadCount: signal(0),
      pendingValidations: signal(0),
      hasUnread: signal(false),
      hasPendingValidations: signal(false),
      totalBadgeCount: signal(0),
      poll: jest.fn().mockReturnValue(of({ notifications: [], unread_count: 0, pending_validations: 0 })),
      startPolling: jest.fn(),
      stopPolling: jest.fn(),
      markAsRead: jest.fn().mockReturnValue(of({ status: 'ok' })),
      markAllAsRead: jest.fn().mockReturnValue(of({ status: 'ok' })),
      refresh: jest.fn().mockReturnValue(of({ notifications: [], unread_count: 0, pending_validations: 0 })),
    };

    TestBed.configureTestingModule({
      imports: [
        PlanCreateComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        { provide: AdminService, useValue: mockAdminService },
        { provide: AuthService, useValue: authServiceMock },
        { provide: ImpersonationGuardService, useValue: impersonationGuardMock },
        { provide: ModuleService, useValue: moduleServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    jest.spyOn(router, 'navigate').mockResolvedValue(true);
    mockSnackBarOpen = jest.spyOn(MatSnackBar.prototype, 'open').mockImplementation();

    fixture = TestBed.createComponent(PlanCreateComponent);
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
      expect(component.form.get('nom')?.value).toBe('');
      expect(component.form.get('rang')?.value).toBe(1);
      expect(component.form.get('ct88')?.value).toBe(false);
      expect(component.form.get('annee_debut')?.value).toBe(new Date().getFullYear());
      expect(component.form.get('annee_fin')?.value).toBe(new Date().getFullYear() + 5);
      expect(component.form.get('statut')?.value).toBe('draft');
    });

    it('should load redacteur types', () => {
      setup();
      expect(mockAdminService.getRedacteurTypes).toHaveBeenCalled();
      expect(component.redacteurTypes().length).toBe(1);
    });

    it('should load available sites for super admin', () => {
      setup({ isSuperAdmin: true });
      expect(mockAdminService.getSites).toHaveBeenCalled();
      expect(component.availableSites().length).toBe(3);
    });

    it('should load organismes for rédacteurs autocomplete', () => {
      setup();
      expect(mockAdminService.getOrganismes).toHaveBeenCalled();
    });

    it('should load organismes for autocomplete', () => {
      setup();
      expect(mockAdminService.getOrganismes).toHaveBeenCalled();
      expect(component.availableOrganismes().length).toBe(2);
    });
  });

  // =========================================================================
  // Form validation
  // =========================================================================

  describe('form validation', () => {
    beforeEach(() => setup());

    it('should require nom', () => {
      component.form.get('nom')?.setValue('');
      expect(component.form.get('nom')?.hasError('required')).toBe(true);
    });

    it('should validate nom maxLength(255)', () => {
      component.form.get('nom')?.setValue('a'.repeat(256));
      expect(component.form.get('nom')?.hasError('maxlength')).toBe(true);
    });

    it('should require rang', () => {
      component.form.get('rang')?.setValue(null);
      expect(component.form.get('rang')?.hasError('required')).toBe(true);
    });

    it('should validate rang min(1)', () => {
      component.form.get('rang')?.setValue(0);
      expect(component.form.get('rang')?.hasError('min')).toBe(true);
    });

    it('should require annee_debut', () => {
      component.form.get('annee_debut')?.setValue(null);
      expect(component.form.get('annee_debut')?.hasError('required')).toBe(true);
    });

    it('should require annee_fin', () => {
      component.form.get('annee_fin')?.setValue(null);
      expect(component.form.get('annee_fin')?.hasError('required')).toBe(true);
    });

    it('should require ct88', () => {
      component.form.get('ct88')?.setValue(null);
      expect(component.form.get('ct88')?.hasError('required')).toBe(true);
    });
  });

  // =========================================================================
  // Site selection
  // =========================================================================

  describe('site selection', () => {
    beforeEach(() => setup());

    it('should toggle site selection', () => {
      component.toggleSite(10);
      expect(component.isSiteSelected(10)).toBe(true);
      component.toggleSite(10);
      expect(component.isSiteSelected(10)).toBe(false);
    });

    it('should select all sites', () => {
      component.selectAllSites();
      expect(component.getSelectedSitesCount()).toBe(3);
    });

    it('should deselect all sites', () => {
      component.selectAllSites();
      component.deselectAllSites();
      expect(component.getSelectedSitesCount()).toBe(0);
    });

    it('should filter sites by name', () => {
      component.siteSearchQuery = 'Cam';
      component.filterSites();
      expect(component.filteredSites().length).toBe(1);
      expect(component.filteredSites()[0].nom).toBe('Camargue');
    });

    it('should filter sites by type', () => {
      component.siteSearchQuery = 'RNN';
      component.filterSites();
      expect(component.filteredSites().length).toBe(2);
    });

    it('should show all sites with empty query', () => {
      component.siteSearchQuery = '';
      component.filterSites();
      expect(component.filteredSites().length).toBe(3);
    });
  });

  // =========================================================================
  // Submission
  // =========================================================================

  describe('submission', () => {
    beforeEach(() => setup());

    it('should not submit when form is invalid', () => {
      component.form.get('nom')?.setValue('');
      component.onSubmit();
      expect(mockAdminService.createPlan).not.toHaveBeenCalled();
    });

    it('should markAllAsTouched when form is invalid', () => {
      component.form.get('nom')?.setValue('');
      const spy = jest.spyOn(component.form, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
    });

    it('should not submit when no sites selected', () => {
      component.form.patchValue({ nom: 'Mon plan' });
      component.onSubmit();
      expect(mockAdminService.createPlan).not.toHaveBeenCalled();
      expect(component.errorMessage()).toContain('site');
    });

    it('should call createPlan with correct payload', () => {
      component.form.patchValue({
        nom: 'Mon plan',
        rang: 2,
        ct88: true,
        annee_debut: 2025,
        annee_fin: 2030,
      });
      component.selectedSiteIds.set([10, 20]);

      component.onSubmit();

      expect(mockAdminService.createPlan).toHaveBeenCalledWith(
        expect.objectContaining({
          nom: 'Mon plan',
          rang: 2,
          ct88: true,
          annee_debut: 2025,
          annee_fin: 2030,
          sites_ids: [10, 20],
          statut: 'draft',
        })
      );
    });

    it('should navigate to plan detail on success', () => {
      component.form.patchValue({ nom: 'Mon plan' });
      component.selectedSiteIds.set([10]);
      component.onSubmit();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'nouveau-plan']);
    });

    it('should set errorMessage on API error', () => {
      mockAdminService.createPlan.mockReturnValue(
        throwError(() => new Error('Erreur serveur'))
      );
      component.form.patchValue({ nom: 'Mon plan' });
      component.selectedSiteIds.set([10]);
      component.onSubmit();
      expect(component.errorMessage()).toBe('Erreur serveur');
    });

    it('should set isLoading during submission', () => {
      component.form.patchValue({ nom: 'Mon plan' });
      component.selectedSiteIds.set([10]);
      expect(component.isLoading()).toBe(false);
      component.onSubmit();
      // After synchronous success callback, isLoading is reset
      expect(component.isLoading()).toBe(false);
    });
  });

  // =========================================================================
  // scrollToError
  // =========================================================================

  describe('scrollToError', () => {
    let scrollIntoViewMock: jest.Mock;

    beforeEach(() => {
      setup();
      // Mock scrollIntoView on all elements (JSDOM doesn't implement it)
      scrollIntoViewMock = jest.fn();
      Element.prototype.scrollIntoView = scrollIntoViewMock;
    });

    afterEach(() => {
      // @ts-ignore - cleanup mock
      delete Element.prototype.scrollIntoView;
    });

    it('should scroll to error-banner when present', fakeAsync(() => {
      const banner = document.createElement('div');
      banner.className = 'error-banner';
      fixture.nativeElement.appendChild(banner);

      component.form.patchValue({ nom: 'Mon plan' });
      // No sites selected → triggers errorMessage + scrollToError
      component.onSubmit();
      tick();

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });

      fixture.nativeElement.removeChild(banner);
    }));

    it('should scroll to first invalid mat-form-field when no banner', fakeAsync(() => {
      component.form.get('nom')?.setValue('');
      component.onSubmit();
      tick();

      // Should scroll to the first invalid mat-form-field rendered by Angular
      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });
    }));

    it('should not throw when no error elements exist', fakeAsync(() => {
      // Remove all rendered content to ensure no mat-form-field.ng-invalid
      fixture.nativeElement.innerHTML = '';
      component.form.get('nom')?.setValue('');
      expect(() => {
        component.onSubmit();
        tick();
      }).not.toThrow();
    }));

    it('should scroll to banner on API error', fakeAsync(() => {
      mockAdminService.createPlan.mockReturnValue(
        throwError(() => new Error('Erreur API'))
      );

      const banner = document.createElement('div');
      banner.className = 'error-banner';
      fixture.nativeElement.appendChild(banner);

      component.form.patchValue({ nom: 'Mon plan' });
      component.selectedSiteIds.set([10]);
      component.onSubmit();
      tick();

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });

      fixture.nativeElement.removeChild(banner);
    }));
  });

  // =========================================================================
  // Navigation
  // =========================================================================

  describe('navigation', () => {
    it('should navigate to /plans on cancel', () => {
      setup();
      component.onCancel();
      expect(router.navigate).toHaveBeenCalledWith(['/plans']);
    });
  });

  // =========================================================================
  // Redacteurs / Relecteurs
  // =========================================================================

  describe('redacteurs/relecteurs fields', () => {
    beforeEach(() => setup());

    it('should have redacteurs form control', () => {
      expect(component.form.get('redacteurs')).toBeTruthy();
    });

    it('should accept redacteurs text', () => {
      component.form.get('redacteurs')?.setValue('Marie Dupont, Jean Martin');
      expect(component.form.get('redacteurs')?.value).toBe('Marie Dupont, Jean Martin');
    });

    it('should have relecteurs form control', () => {
      expect(component.form.get('relecteurs')).toBeTruthy();
    });

    it('should accept relecteurs text', () => {
      component.form.get('relecteurs')?.setValue('Dr. Bernard');
      expect(component.form.get('relecteurs')?.value).toBe('Dr. Bernard');
    });
  });

  // =========================================================================
  // Organisme rédacteur
  // =========================================================================

  describe('organisme rédacteur', () => {
    beforeEach(() => setup());

    it('should set organisme from text', () => {
      component.organismeCtrl.setValue('Mon organisme');
      component.setOrganismeFromText();
      expect(component.selectedOrganisme()?.type).toBe('text');
      expect(component.selectedOrganisme()?.displayName).toBe('Mon organisme');
    });

    it('should clear selected organisme', () => {
      component.organismeCtrl.setValue('Mon organisme');
      component.setOrganismeFromText();
      component.clearOrganisme();
      expect(component.selectedOrganisme()).toBeNull();
    });

    it('should not set organisme from empty text', () => {
      component.organismeCtrl.setValue('   ');
      component.setOrganismeFromText();
      expect(component.selectedOrganisme()).toBeNull();
    });
  });
});
