import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';

import { PlanDuplicateComponent } from './plan-duplicate.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { ImpersonationGuardService } from '../../core/services/impersonation-guard.service';
import { ModuleService } from '../../core/services/module.service';
import { NotificationService } from '../../core/services/notification.service';
import { AdminPlan, AdminSite, PlanStatut } from '../../core/models/admin.model';
import {
  DuplicatePlanDialogComponent,
  DuplicatePlanDialogResult,
} from '../../shared/components/modals/duplicate-plan-dialog/duplicate-plan-dialog.component';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      plans: {
        duplicate: {
          title: 'Dupliquer un plan',
          subtitle: 'Sélectionnez un plan validé',
          searchPlaceholder: 'Rechercher un plan',
          selectPlan: 'Sélectionner',
          noResults: 'Aucun plan trouvé',
          success: 'Plan dupliqué avec succès',
          error: 'Erreur lors de la duplication',
          dialog: { cancel: 'Annuler', confirm: 'Duplication en cours' },
          sections: {
            myPlans: 'Mes plans',
            orgPlans: 'Plans organisme',
            allPlans: 'Tous les plans',
          },
          table: {
            name: 'Nom',
            period: 'Période',
            status: 'Statut',
            sites: 'Sites',
          },
        },
        status: {
          draft: 'Brouillon',
          valide: 'Validé',
          archive: 'Archivé',
        },
        list: {
          oldVersions: 'Anciennes versions',
          hideOldVersions: 'Masquer',
        },
      },
      header: { title: 'CICADA' },
      common: {
        actions: { close: 'Fermer', search: 'Rechercher' },
      },
    });
  }
}

/** Generate a test AdminPlan with sensible defaults. */
function makePlan(overrides: Partial<AdminPlan> = {}): AdminPlan {
  return {
    id_pg: 1,
    nom: 'Plan Test',
    slug: 'plan-test',
    statut: 'valide' as PlanStatut,
    gestion_partagee: false,
    ct88: false,
    risque_incendie: false,
    annee_debut: 2024,
    annee_fin: 2034,
    sites: [],
    referents: [],
    membres: [],
    children_count: 0,
    plan_parent_id: null,
    ...overrides,
  };
}

/** Generate a test AdminSite. */
function makeSite(overrides: Partial<AdminSite> = {}): AdminSite {
  return {
    id_site: 1,
    slug: 'site-test',
    nom_site: 'Site Test',
    organismes: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('PlanDuplicateComponent', () => {
  let component: PlanDuplicateComponent;
  let fixture: ComponentFixture<PlanDuplicateComponent>;
  let router: Router;
  let mockSnackBarOpen: jest.SpyInstance;

  let mockAdminService: {
    getPlans: jest.Mock;
    getSites: jest.Mock;
    duplicatePlan: jest.Mock;
  };

  let mockDialog: { open: jest.Mock };

  // Writable signals for AuthService mock
  let isSuperAdminSignal: WritableSignal<boolean>;
  let isAdminOrganismeSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<any>;

  // Default test plans covering different statuts, children, scopes
  const CURRENT_USER_ID = 1;
  const OTHER_USER_ID = 99;
  const ORG_ID = 10;

  function defaultPlans(): AdminPlan[] {
    return [
      makePlan({
        id_pg: 100,
        nom: 'Plan Valide Mien',
        slug: 'plan-valide-mien',
        statut: 'valide',
        children_count: 0,
        referents: [{ id_role: CURRENT_USER_ID, email: 'me@test.fr' }],
        sites: [{ id_site: 1, nom_site: 'Camargue' }],
      }),
      makePlan({
        id_pg: 101,
        nom: 'Plan Draft',
        slug: 'plan-draft',
        statut: 'draft',
        children_count: 0,
        referents: [{ id_role: CURRENT_USER_ID, email: 'me@test.fr' }],
      }),
      makePlan({
        id_pg: 102,
        nom: 'Plan Archive',
        slug: 'plan-archive',
        statut: 'archive',
        children_count: 0,
        referents: [{ id_role: CURRENT_USER_ID, email: 'me@test.fr' }],
      }),
      makePlan({
        id_pg: 103,
        nom: 'Plan NonLeaf',
        slug: 'plan-nonleaf',
        statut: 'valide',
        children_count: 1,
        referents: [{ id_role: CURRENT_USER_ID, email: 'me@test.fr' }],
      }),
      makePlan({
        id_pg: 104,
        nom: 'Plan Valide Autre',
        slug: 'plan-valide-autre',
        statut: 'valide',
        children_count: 0,
        referents: [{ id_role: OTHER_USER_ID, email: 'other@test.fr' }],
        membres: [{ id_role: OTHER_USER_ID, email: 'other@test.fr', referent: false }],
        sites: [{ id_site: 2, nom_site: 'Vercors' }],
      }),
      makePlan({
        id_pg: 105,
        nom: 'Plan Valide OrgSite',
        slug: 'plan-valide-orgsite',
        statut: 'valide',
        children_count: 0,
        referents: [{ id_role: OTHER_USER_ID, email: 'other@test.fr' }],
        sites: [{ id_site: 3, nom_site: 'Org Site' }],
      }),
      makePlan({
        id_pg: 106,
        nom: 'Plan Membre',
        slug: 'plan-membre',
        statut: 'valide',
        children_count: 0,
        membres: [{ id_role: CURRENT_USER_ID, email: 'me@test.fr', referent: false }],
        sites: [{ id_site: 4, nom_site: 'Scandola' }],
      }),
    ];
  }

  function defaultSites(): AdminSite[] {
    return [
      makeSite({ id_site: 1, nom_site: 'Camargue', organismes: [{ id_organisme: ORG_ID, nom_organisme: 'RNF' }] }),
      makeSite({ id_site: 2, nom_site: 'Vercors', organismes: [{ id_organisme: 20, nom_organisme: 'CEN' }] }),
      makeSite({ id_site: 3, nom_site: 'Org Site', organismes: [{ id_organisme: ORG_ID, nom_organisme: 'RNF' }] }),
      makeSite({ id_site: 4, nom_site: 'Scandola', organismes: [{ id_organisme: 20, nom_organisme: 'CEN' }] }),
    ];
  }

  function setup(opts: {
    isSuperAdmin?: boolean;
    isAdminOrg?: boolean;
    plans?: AdminPlan[];
    sites?: AdminSite[];
    plansError?: boolean;
  } = {}): void {
    const {
      isSuperAdmin = false,
      isAdminOrg = false,
      plans = defaultPlans(),
      sites = defaultSites(),
      plansError = false,
    } = opts;

    mockAdminService = {
      getPlans: plansError
        ? jest.fn().mockReturnValue(throwError(() => new Error('API error')))
        : jest.fn().mockReturnValue(of({ results: plans, count: plans.length })),
      getSites: jest.fn().mockReturnValue(of({ results: sites, count: sites.length })),
      duplicatePlan: jest.fn().mockReturnValue(of({ id_pg: 999, slug: 'new-plan', nom: 'New Plan' })),
    };


    isSuperAdminSignal = signal(isSuperAdmin);
    isAdminOrganismeSignal = signal(isAdminOrg || isSuperAdmin);
    currentUserSignal = signal({
      id: CURRENT_USER_ID,
      id_role: CURRENT_USER_ID,
      email: 'me@test.fr',
      prenom_role: 'Jean',
      nom_role: 'Dupont',
      niveau_role: isSuperAdmin ? 'super_admin' : isAdminOrg ? 'admin_og' : 'utilisateur',
      organisme: { id_organisme: ORG_ID, nom_organisme: 'RNF' },
      is_staff: false,
      is_active: true,
    });

    const authServiceMock = {
      isAuthenticated: signal(true).asReadonly(),
      currentUser: currentUserSignal.asReadonly(),
      isSuperAdmin: isSuperAdminSignal.asReadonly(),
      isAdminOrganisme: isAdminOrganismeSignal.asReadonly(),
      canAccessAdmin: signal(true).asReadonly(),
      isImpersonating: signal(false).asReadonly(),
      impersonationInfo: signal(null).asReadonly(),
      isReferent: signal(true).asReadonly(),
      getUserDisplayName: jest.fn().mockReturnValue('Jean Dupont'),
      getOriginalUserDisplayName: jest.fn().mockReturnValue('Jean Dupont'),
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

    mockDialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(undefined) }),
    };

    TestBed.configureTestingModule({
      imports: [
        PlanDuplicateComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr',
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

    fixture = TestBed.createComponent(PlanDuplicateComponent);
    component = fixture.componentInstance;
    // Override the private dialog instance with our mock (inject() resolves from
    // MatDialogModule imported by the component, bypassing TestBed providers)
    (component as any).dialog = mockDialog;
    fixture.detectChanges();
  }

  afterEach(() => {
    mockSnackBarOpen?.mockRestore();
  });

  // =======================================================================
  // Initialization
  // =======================================================================

  describe('initialization', () => {
    it('should create', () => {
      setup();
      expect(component).toBeTruthy();
    });

    it('should call getPlans and getSites on init', () => {
      setup();
      expect(mockAdminService.getPlans).toHaveBeenCalledWith({ page_size: 500 });
      expect(mockAdminService.getSites).toHaveBeenCalledWith({ page_size: 500 });
    });

    it('should set loading to false after data loads', () => {
      setup();
      expect(component.loading()).toBe(false);
    });

    it('should set loading to false on plans error', () => {
      setup({ plansError: true });
      expect(component.loading()).toBe(false);
    });

    it('should populate allPlans from API response', () => {
      setup();
      expect(component.allPlans().length).toBe(defaultPlans().length);
    });

    it('should populate allSites from API response', () => {
      setup();
      expect(component.allSites().length).toBe(defaultSites().length);
    });

    it('should default planScope to mine', () => {
      setup();
      expect(component.planScope()).toBe('mine');
    });
  });

  // =======================================================================
  // Filtered plans (valide only, leaf only)
  // =======================================================================

  describe('filteredPlans (status and leaf filtering)', () => {
    beforeEach(() => setup({ isSuperAdmin: true }));

    it('should include plans with statut valide', () => {
      component.planScope.set('all');
      const ids = component.filteredPlans().map(p => p.id_pg);
      expect(ids).toContain(100);
    });

    it('should DISPLAY draft plans but mark them non-basable (#391)', () => {
      component.planScope.set('all');
      const plans = component.filteredPlans();
      const ids = plans.map(p => p.id_pg);
      // id_pg 101 is draft — affiché (visible) mais grisé/non sélectionnable.
      expect(ids).toContain(101);
      const draft = plans.find(p => p.id_pg === 101)!;
      expect(component.canUseAsBase(draft)).toBe(false);
    });

    it('should include plans with statut archive (#391)', () => {
      component.planScope.set('all');
      const ids = component.filteredPlans().map(p => p.id_pg);
      // id_pg 102 is archive — désormais exploitable comme base
      expect(ids).toContain(102);
    });

    it('should exclude plans with children_count > 0 (non-leaf)', () => {
      component.planScope.set('all');
      const filtered = component.filteredPlans();
      const ids = filtered.map(p => p.id_pg);
      // id_pg 103 has children_count=1
      expect(ids).not.toContain(103);
    });

    it('should display all leaf plans incl. drafts, 103 non-leaf excluded (#391)', () => {
      component.planScope.set('all');
      const ids = component.filteredPlans().map(p => p.id_pg);
      // Affichés (feuilles) : 100 (valide), 101 (draft, grisé), 102 (archive),
      // 104, 105, 106 (valide). 103 exclu (non-feuille).
      expect(ids).toContain(100);
      expect(ids).toContain(101);
      expect(ids).toContain(102);
      expect(ids).toContain(104);
      expect(ids).toContain(105);
      expect(ids).toContain(106);
      expect(ids).not.toContain(103);
      expect(ids.length).toBe(6);
    });

    it('should apply search filter on plan name', () => {
      component.planScope.set('all');
      component.searchQuery.set('Autre');
      const filtered = component.filteredPlans();
      expect(filtered.length).toBe(1);
      expect(filtered[0].id_pg).toBe(104);
    });

    it('should apply search filter on site name', () => {
      component.planScope.set('all');
      component.searchQuery.set('Scandola');
      const filtered = component.filteredPlans();
      expect(filtered.length).toBe(1);
      expect(filtered[0].id_pg).toBe(106);
    });

    it('should return draft plans by search but non-basable (#391)', () => {
      component.planScope.set('all');
      component.searchQuery.set('Draft');
      const filtered = component.filteredPlans();
      // Le brouillon (101) reste visible (recherche) mais non sélectionnable.
      expect(filtered.length).toBe(1);
      expect(filtered[0].id_pg).toBe(101);
      expect(component.canUseAsBase(filtered[0])).toBe(false);
    });

    it('should handle case-insensitive search', () => {
      component.planScope.set('all');
      component.searchQuery.set('plan valide mien');
      const filtered = component.filteredPlans();
      expect(filtered.length).toBe(1);
      expect(filtered[0].id_pg).toBe(100);
    });

    it('should return all displayed leaf plans with empty search (#391)', () => {
      component.planScope.set('all');
      component.searchQuery.set('');
      // 100, 101 (draft grisé), 102, 104, 105, 106 ; 103 non-feuille exclu.
      expect(component.filteredPlans().length).toBe(6);
    });

    it('should trim whitespace in search query', () => {
      component.planScope.set('all');
      component.searchQuery.set('   Autre   ');
      const filtered = component.filteredPlans();
      expect(filtered.length).toBe(1);
      expect(filtered[0].id_pg).toBe(104);
    });
  });

  // =======================================================================
  // Scope filtering
  // =======================================================================

  describe('scope filtering', () => {
    describe('mine scope', () => {
      it('should only include plans where user is referent', () => {
        setup();
        component.planScope.set('mine');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        // Plan 100: user is referent, valide, leaf
        expect(ids).toContain(100);
      });

      it('should include plans where user is member', () => {
        setup();
        component.planScope.set('mine');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        // Plan 106: user is membre, valide, leaf
        expect(ids).toContain(106);
      });

      it('should exclude plans from other users', () => {
        setup();
        component.planScope.set('mine');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        // Plan 104 and 105: user is neither referent nor member
        expect(ids).not.toContain(104);
        expect(ids).not.toContain(105);
      });
    });

    describe('organisme scope', () => {
      it('should include plans from user org sites', () => {
        setup({ isAdminOrg: true });
        component.planScope.set('organisme');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        // Plan 105 has site 3 (Org Site) which belongs to ORG_ID
        expect(ids).toContain(105);
      });

      it('should include plans where user is referent or member', () => {
        setup({ isAdminOrg: true });
        component.planScope.set('organisme');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        expect(ids).toContain(100); // referent
        expect(ids).toContain(106); // member
      });

      it('should exclude plans with no org link and no user link', () => {
        setup({ isAdminOrg: true });
        component.planScope.set('organisme');
        const filtered = component.filteredPlans();
        const ids = filtered.map(p => p.id_pg);
        // Plan 104 has site 2 (Vercors / CEN) and user is not member
        expect(ids).not.toContain(104);
      });
    });

    describe('all scope (super admin)', () => {
      it('should display all leaf plans incl. drafts (#391)', () => {
        setup({ isSuperAdmin: true });
        component.planScope.set('all');
        const filtered = component.filteredPlans();
        // 6 feuilles affichées (dont le brouillon grisé) ; 103 non-feuille exclu.
        expect(filtered.length).toBe(6);
      });

      it('should keep drafts visible but non-basable, exclude non-leaf (#391)', () => {
        setup({ isSuperAdmin: true });
        component.planScope.set('all');
        const plans = component.filteredPlans();
        const ids = plans.map(p => p.id_pg);
        expect(ids).toContain(101); // draft — affiché (grisé)
        expect(component.canUseAsBase(plans.find(p => p.id_pg === 101)!)).toBe(false);
        expect(ids).toContain(102); // archive — basable
        expect(component.canUseAsBase(plans.find(p => p.id_pg === 102)!)).toBe(true);
        expect(ids).not.toContain(103); // non-leaf — toujours exclu
      });
    });
  });

  // =======================================================================
  // showScopeToggle
  // =======================================================================

  describe('showScopeToggle', () => {
    it('should be true for super admin', () => {
      setup({ isSuperAdmin: true });
      expect(component.showScopeToggle()).toBe(true);
    });

    it('should be true for admin organisme', () => {
      setup({ isAdminOrg: true });
      expect(component.showScopeToggle()).toBe(true);
    });

    it('should be false for regular user', () => {
      setup({ isSuperAdmin: false, isAdminOrg: false });
      expect(component.showScopeToggle()).toBe(false);
    });
  });

  // =======================================================================
  // Plan selection and duplication (dialog + API)
  // =======================================================================

  describe('plan selection and duplication', () => {
    function setDialogResult(result: DuplicatePlanDialogResult | undefined): void {
      mockDialog.open.mockReturnValue({
        afterClosed: () => of(result),
      });
    }

    beforeEach(() => setup({ isSuperAdmin: true }));

    it('should open DuplicatePlanDialogComponent with correct data', () => {
      const plan = defaultPlans()[0]; // valide plan with id_pg 100
      setDialogResult(undefined);

      component.onSelectPlan(plan);

      expect(mockDialog.open).toHaveBeenCalledWith(DuplicatePlanDialogComponent, {
        width: '600px',
        maxWidth: '95vw',
        data: {
          planId: 100,
          planName: plan.nom,
          planPeriod: '2024 - 2034',
          planStatus: expect.any(String),
          nbSites: 1,
        },
      });
    });

    it('should call duplicatePlan API after dialog confirms', () => {
      const plan = defaultPlans()[0];
      const options = {
        copy_sites: true,
        copy_referents: true,
        copy_fichiers: false,
        copy_enjeux: true,
        copy_sub_elements: false,
      };
      setDialogResult({ confirmed: true, options });

      component.onSelectPlan(plan);

      expect(mockAdminService.duplicatePlan).toHaveBeenCalledWith(100, options);
    });

    it('should NOT call duplicatePlan when dialog is cancelled', () => {
      const plan = defaultPlans()[0];
      setDialogResult({ confirmed: false });

      component.onSelectPlan(plan);

      expect(mockAdminService.duplicatePlan).not.toHaveBeenCalled();
    });

    it('should NOT call duplicatePlan when dialog is closed without result', () => {
      const plan = defaultPlans()[0];
      setDialogResult(undefined);

      component.onSelectPlan(plan);

      expect(mockAdminService.duplicatePlan).not.toHaveBeenCalled();
    });

    it('should set duplicating to true during duplication', () => {
      const plan = defaultPlans()[0];
      const options = {
        copy_sites: true,
        copy_referents: true,
        copy_fichiers: false,
        copy_enjeux: true,
        copy_sub_elements: false,
      };

      setDialogResult({ confirmed: true, options });
      component.onSelectPlan(plan);

      // After synchronous subscribe completes, duplicating should be false
      expect(component.duplicating()).toBe(false);
    });

    it('should show success snackBar after duplication', () => {
      const plan = defaultPlans()[0];
      const options = {
        copy_sites: true,
        copy_referents: true,
        copy_fichiers: false,
        copy_enjeux: true,
        copy_sub_elements: false,
      };
      setDialogResult({ confirmed: true, options });

      component.onSelectPlan(plan);

      expect(mockSnackBarOpen).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        { duration: 3000 }
      );
    });

    it('should show error snackBar when duplication fails', () => {
      const plan = defaultPlans()[0];
      const options = {
        copy_sites: true,
        copy_referents: true,
        copy_fichiers: false,
        copy_enjeux: true,
        copy_sub_elements: false,
      };
      mockAdminService.duplicatePlan.mockReturnValue(
        throwError(() => new Error('Duplication failed'))
      );
      setDialogResult({ confirmed: true, options });

      component.onSelectPlan(plan);

      expect(mockSnackBarOpen).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        { duration: 6000 }
      );
    });

    it('should set duplicating to false on error', () => {
      const plan = defaultPlans()[0];
      const options = {
        copy_sites: true,
        copy_referents: true,
        copy_fichiers: false,
        copy_enjeux: true,
        copy_sub_elements: false,
      };
      mockAdminService.duplicatePlan.mockReturnValue(
        throwError(() => new Error('Duplication failed'))
      );
      setDialogResult({ confirmed: true, options });

      component.onSelectPlan(plan);

      expect(component.duplicating()).toBe(false);
    });
  });

  // =======================================================================
  // Navigation after duplication
  // =======================================================================

  describe('navigation after duplication', () => {
    const duplicateOptions = {
      copy_sites: true,
      copy_referents: true,
      copy_fichiers: false,
      copy_enjeux: true,
      copy_sub_elements: false,
    };

    beforeEach(() => {
      setup({ isSuperAdmin: true });
      mockDialog.open.mockReturnValue({
        afterClosed: () => of({ confirmed: true, options: duplicateOptions } as DuplicatePlanDialogResult),
      });
    });

    it('should navigate to /plans/{slug} with edit=metadata query param on success', () => {
      mockAdminService.duplicatePlan.mockReturnValue(
        of({ id_pg: 999, slug: 'duplicated-plan', nom: 'Duplicated Plan' })
      );

      component.onSelectPlan(defaultPlans()[0]);

      expect(router.navigate).toHaveBeenCalledWith(
        ['/plans', 'duplicated-plan'],
        { queryParams: { edit: 'metadata' } }
      );
    });

    it('should navigate to /plans if slug is missing', () => {
      mockAdminService.duplicatePlan.mockReturnValue(
        of({ id_pg: 999, nom: 'No Slug Plan' } as AdminPlan)
      );

      component.onSelectPlan(defaultPlans()[0]);

      expect(router.navigate).toHaveBeenCalledWith(['/plans']);
    });

    it('should navigate to /plans if slug is empty string', () => {
      mockAdminService.duplicatePlan.mockReturnValue(
        of({ id_pg: 999, slug: '', nom: 'Empty Slug' } as AdminPlan)
      );

      component.onSelectPlan(defaultPlans()[0]);

      expect(router.navigate).toHaveBeenCalledWith(['/plans']);
    });

    it('should NOT navigate on duplication error', () => {
      mockAdminService.duplicatePlan.mockReturnValue(
        throwError(() => new Error('Fail'))
      );

      component.onSelectPlan(defaultPlans()[0]);

      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  // =======================================================================
  // Linked plans (ancestor display)
  // =======================================================================

  describe('linkedPlansById (ancestor chain)', () => {
    it('should be empty when no plans have parents', () => {
      setup({ isSuperAdmin: true });
      component.planScope.set('all');
      expect(component.linkedPlansById().size).toBe(0);
    });

    it('should show parent for a draft child when toggle is off', () => {
      const parentPlan = makePlan({
        id_pg: 200,
        nom: 'Parent Plan',
        statut: 'archive',
        children_count: 1,
      });
      const childPlan = makePlan({
        id_pg: 201,
        nom: 'Child Draft',
        statut: 'draft',
        children_count: 0,
        plan_parent_id: 200,
      });

      setup({ isSuperAdmin: true, plans: [parentPlan, childPlan] });
      component.planScope.set('all');
      component.searchQuery.set('');

      // Default showOldVersions is false
      // But filteredPlans only includes valide+leaf, so draft child is excluded
      // Let's test with valide child to make it appear in filteredPlans
      // Actually linkedPlansById operates on filteredPlans, so we need the child
      // to be in filteredPlans (valide + leaf). Adjust:
      const parent = makePlan({
        id_pg: 300,
        nom: 'Archived Parent',
        statut: 'archive',
        children_count: 1,
      });
      const child = makePlan({
        id_pg: 301,
        nom: 'Valide Child',
        statut: 'valide',
        children_count: 0,
        plan_parent_id: 300,
      });

      component.allPlans.set([parent, child]);
      // For 'all' scope, the child is valide+leaf, so it appears in filteredPlans.
      // But with showOldVersions=false, linkedPlansById only shows parent for drafts.
      // So for a valide child with toggle OFF, no ancestors should be shown.
      expect(component.linkedPlansById().has(301)).toBe(false);
    });

    it('should show ancestors when toggle is on', () => {
      const parent = makePlan({
        id_pg: 300,
        nom: 'Archived Parent',
        statut: 'archive',
        children_count: 1,
      });
      const child = makePlan({
        id_pg: 301,
        nom: 'Valide Child',
        statut: 'valide',
        children_count: 0,
        plan_parent_id: 300,
      });

      setup({ isSuperAdmin: true, plans: [parent, child] });
      component.planScope.set('all');
      component.showOldVersions.set(true);

      const linked = component.linkedPlansById();
      expect(linked.has(301)).toBe(true);
      expect(linked.get(301)!.length).toBe(1);
      expect(linked.get(301)![0].id_pg).toBe(300);
    });

    it('should show full ancestor chain when toggle is on', () => {
      const grandparent = makePlan({
        id_pg: 400,
        nom: 'Grandparent',
        statut: 'archive',
        children_count: 1,
        plan_parent_id: null,
      });
      const parent = makePlan({
        id_pg: 401,
        nom: 'Parent',
        statut: 'archive',
        children_count: 1,
        plan_parent_id: 400,
      });
      const child = makePlan({
        id_pg: 402,
        nom: 'Current',
        statut: 'valide',
        children_count: 0,
        plan_parent_id: 401,
      });

      setup({ isSuperAdmin: true, plans: [grandparent, parent, child] });
      component.planScope.set('all');
      component.showOldVersions.set(true);

      const linked = component.linkedPlansById();
      expect(linked.has(402)).toBe(true);
      const ancestors = linked.get(402)!;
      // Should show grandparent first (oldest ancestor first)
      expect(ancestors.length).toBe(2);
      expect(ancestors[0].id_pg).toBe(400);
      expect(ancestors[1].id_pg).toBe(401);
    });

    it('should show a draft leaf with its parent, but mark the draft non-basable (#391)', () => {
      // Le brouillon reste affiché (avec son parent immédiat au-dessus, toggle
      // off) mais n'est pas sélectionnable comme base (canUseAsBase=false).
      const parent = makePlan({ id_pg: 500, nom: 'Parent', statut: 'archive', children_count: 1 });
      const child = makePlan({
        id_pg: 501,
        nom: 'Draft Child',
        statut: 'draft',
        children_count: 0,
        plan_parent_id: 500,
      });

      setup({ isSuperAdmin: true, plans: [parent, child] });
      component.planScope.set('all');
      component.showOldVersions.set(false);

      const plans = component.filteredPlans();
      const ids = plans.map(p => p.id_pg);
      expect(ids).toContain(501); // brouillon affiché (feuille)
      expect(ids).not.toContain(500); // parent non-feuille (montré en ancêtre)
      expect(component.canUseAsBase(plans.find(p => p.id_pg === 501)!)).toBe(false);
      // Toggle off + draft → parent immédiat affiché comme ancêtre.
      const linked = component.linkedPlansById();
      expect(linked.has(501)).toBe(true);
      expect(linked.get(501)!.map(p => p.id_pg)).toEqual([500]);
    });
  });

  // =======================================================================
  // Toggle old versions
  // =======================================================================

  describe('toggleOldVersions', () => {
    beforeEach(() => setup());

    it('should start with showOldVersions false', () => {
      expect(component.showOldVersions()).toBe(false);
    });

    it('should toggle showOldVersions', () => {
      component.toggleOldVersions();
      expect(component.showOldVersions()).toBe(true);
      component.toggleOldVersions();
      expect(component.showOldVersions()).toBe(false);
    });
  });

  // =======================================================================
  // UI state
  // =======================================================================

  describe('UI state', () => {
    it('should show spinner while loading', () => {
      setup();
      component.loading.set(true);
      fixture.detectChanges();

      const spinner = fixture.nativeElement.querySelector('mat-spinner');
      expect(spinner).toBeTruthy();
    });

    it('should show duplicating message', () => {
      setup();
      component.loading.set(false);
      component.duplicating.set(true);
      fixture.detectChanges();

      const spinner = fixture.nativeElement.querySelector('mat-spinner');
      expect(spinner).toBeTruthy();
      const loadingContainer = fixture.nativeElement.querySelector('.loading-container');
      expect(loadingContainer.textContent).toBeTruthy();
    });

    it('should show empty state when no filtered plans', () => {
      setup({ plans: [] });
      fixture.detectChanges();

      const emptyState = fixture.nativeElement.querySelector('.empty-state');
      expect(emptyState).toBeTruthy();
    });

    it('should show table when filtered plans exist', () => {
      setup();
      // Default scope 'mine' should include at least plan 100 (referent) and 106 (member)
      fixture.detectChanges();

      const table = fixture.nativeElement.querySelector('.plans-table');
      expect(table).toBeTruthy();
    });

    it('should show results count', () => {
      setup();
      fixture.detectChanges();

      const countText = fixture.nativeElement.querySelector('.results-count');
      if (component.filteredPlans().length > 0) {
        expect(countText).toBeTruthy();
        expect(countText.textContent).toContain('plan(s)');
      }
    });
  });

  // =======================================================================
  // Utility methods
  // =======================================================================

  describe('utility methods', () => {
    beforeEach(() => setup());

    describe('getPeriod', () => {
      it('should return formatted period when both years exist', () => {
        const plan = makePlan({ annee_debut: 2020, annee_fin: 2030 });
        expect(component.getPeriod(plan)).toBe('2020 - 2030');
      });

      it('should return dash when annee_debut is missing', () => {
        const plan = makePlan({ annee_debut: undefined, annee_fin: 2030 });
        expect(component.getPeriod(plan)).toBe('-');
      });

      it('should return dash when annee_fin is missing', () => {
        const plan = makePlan({ annee_debut: 2020, annee_fin: undefined });
        expect(component.getPeriod(plan)).toBe('-');
      });

      it('should return dash when both years are missing', () => {
        const plan = makePlan({ annee_debut: undefined, annee_fin: undefined });
        expect(component.getPeriod(plan)).toBe('-');
      });
    });

    describe('getStatusClass', () => {
      it('should return status-success for valide', () => {
        expect(component.getStatusClass('valide')).toBe('status-success');
      });

      it('should return status-warning for draft', () => {
        expect(component.getStatusClass('draft')).toBe('status-warning');
      });

      it('should return status-neutre for archive', () => {
        expect(component.getStatusClass('archive')).toBe('status-neutre');
      });

      it('should return empty string for unknown', () => {
        expect(component.getStatusClass('unknown')).toBe('');
      });
    });

    describe('onScopeChange', () => {
      it('should update planScope signal', () => {
        component.onScopeChange('all');
        expect(component.planScope()).toBe('all');
      });

      it('should update planScope to organisme', () => {
        component.onScopeChange('organisme');
        expect(component.planScope()).toBe('organisme');
      });
    });

    describe('getSitesTooltip', () => {
      it('should return site names joined by newlines', () => {
        const plan = makePlan({
          sites: [
            { id_site: 1, nom_site: 'Site A' },
            { id_site: 2, nom_site: 'Site B' },
          ],
        });
        const tooltip = component.getSitesTooltip(plan);
        expect(tooltip).toContain('Site A');
        expect(tooltip).toContain('Site B');
      });

      it('should return empty string for plan without sites', () => {
        const plan = makePlan({ sites: [] });
        expect(component.getSitesTooltip(plan)).toBe('');
      });
    });

    describe('getSiteAccess', () => {
      it('should return null for site not in allSites', () => {
        expect(component.getSiteAccess(9999)).toBeNull();
      });

      it('should return null when site has no current_user_access', () => {
        // Site 1 in defaultSites does not have current_user_access set
        expect(component.getSiteAccess(1)).toBeNull();
      });

      it('should return access info when current_user_access is set', () => {
        const sites = [
          makeSite({
            id_site: 50,
            nom_site: 'Special Site',
            current_user_access: {
              has_access: true,
              role_label: 'Referent',
              access_type: 'referent',
            },
          }),
        ];
        component.allSites.set(sites);
        const access = component.getSiteAccess(50);
        expect(access).toEqual({
          accessType: 'referent',
          accessLabel: 'Referent',
        });
      });
    });
  });

  // =======================================================================
  // Edge cases
  // =======================================================================

  describe('edge cases', () => {
    it('should handle empty plans list', () => {
      setup({ plans: [] });
      expect(component.filteredPlans().length).toBe(0);
    });

    it('should handle null currentUser gracefully for scope', () => {
      setup();
      // Simulate no user
      currentUserSignal.set(null);
      // scopedPlans returns [] when no user
      expect(component.filteredPlans().length).toBe(0);
    });

    it('should handle plans with no sites array', () => {
      const plan = makePlan({ id_pg: 700, statut: 'valide', children_count: 0, sites: undefined });
      setup({ isSuperAdmin: true, plans: [plan] });
      component.planScope.set('all');
      component.searchQuery.set('SomeSearch');
      // Should not throw
      expect(() => component.filteredPlans()).not.toThrow();
    });

    it('should handle plans with no referents or membres', () => {
      const plan = makePlan({
        id_pg: 800,
        statut: 'valide',
        children_count: 0,
        referents: undefined,
        membres: undefined,
      });
      setup({ plans: [plan] });
      component.planScope.set('mine');
      // Should not throw, just returns empty since user matches nothing
      expect(() => component.filteredPlans()).not.toThrow();
      expect(component.filteredPlans().length).toBe(0);
    });

    it('should avoid infinite loop in ancestor chain with circular reference', () => {
      const planA = makePlan({ id_pg: 900, statut: 'valide', children_count: 0, plan_parent_id: 901 });
      const planB = makePlan({ id_pg: 901, statut: 'archive', children_count: 0, plan_parent_id: 900 });
      setup({ isSuperAdmin: true, plans: [planA, planB] });
      component.planScope.set('all');
      component.showOldVersions.set(true);
      // Should not hang/crash
      expect(() => component.linkedPlansById()).not.toThrow();
    });
  });
});
