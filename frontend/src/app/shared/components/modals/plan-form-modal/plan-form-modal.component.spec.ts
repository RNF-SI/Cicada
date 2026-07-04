import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { signal, WritableSignal } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';

import { PlanFormModalComponent, PlanFormModalData } from './plan-form-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminPlan, AdminSite, AdminUser } from '../../../../core/models/admin.model';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({});
  }
}

describe('PlanFormModalComponent', () => {
  let component: PlanFormModalComponent;
  let fixture: ComponentFixture<PlanFormModalComponent>;

  let dialogCloseMock: jest.Mock;
  let getEvaluationTypesMock: jest.Mock;
  let getRedacteurTypesMock: jest.Mock;
  let getSitesMock: jest.Mock;
  let getOrganismeSitesMock: jest.Mock;
  let getUsersMock: jest.Mock;
  let createPlanMock: jest.Mock;
  let updatePlanMock: jest.Mock;
  let getPlansForSitesMock: jest.Mock;

  let isSuperAdminSignal: WritableSignal<boolean>;
  let currentUserSignal: WritableSignal<any>;

  const mockEvaluationTypes = [
    { id_nomenclature: 1, cd_nomenclature: 'EVAL1', label: 'Evaluation 1' },
    { id_nomenclature: 2, cd_nomenclature: 'EVAL2', label: 'Evaluation 2' }
  ];

  const mockRedacteurTypes = [
    { id_nomenclature: 10, cd_nomenclature: 'RED1', label: 'Redacteur 1' },
    { id_nomenclature: 11, cd_nomenclature: 'RED2', label: 'Redacteur 2' }
  ];

  const mockSites: AdminSite[] = [
    { id_site: 1, slug: 'site-1', nom_site: 'Site Alpha', type_site_label: 'RNN', current_user_access: { has_access: true, role_label: 'Référent', access_type: 'referent' } },
    { id_site: 2, slug: 'site-2', nom_site: 'Site Beta', type_site_label: 'RNR', current_user_access: { has_access: true, role_label: 'Membre', access_type: 'membre' } },
    { id_site: 3, slug: 'site-3', nom_site: 'Site Gamma', type_site_label: 'PNR', current_user_access: { has_access: true, role_label: 'Membre', access_type: 'membre' } }
  ];

  const mockUsers: AdminUser[] = [
    { id_role: 1, email: 'user1@test.fr', nom_role: 'Dupont', prenom_role: 'Jean', role_level: 'utilisateur', active: true },
    { id_role: 2, email: 'user2@test.fr', nom_role: 'Martin', prenom_role: 'Marie', role_level: 'admin_og', active: true }
  ];

  const mockPlan: AdminPlan = {
    id_pg: 1,
    nom: 'Plan Test',
    statut: 'valide',
    version: '2',
    annee_debut: 2020,
    annee_fin: 2030,
    gestion_partagee: true,
    ct88: false,
    risque_incendie: true,
    id_evaluation: 1,
    id_redacteur_type: 10,
    redacteur_nom: 'John Doe',
    commentaire: 'Test comment',
    sites: [{ id_site: 1, nom_site: 'Site Alpha' }],
    referents: [{ id_role: 1, nom_role: 'Dupont', prenom_role: 'Jean', email: 'user1@test.fr' }]
  };

  const mockCurrentUser = {
    id_role: 99,
    email: 'admin@test.fr',
    organisme: { id_organisme: 1, nom_organisme: 'Test Org' }
  };

  const setupTestBed = async (dialogData: PlanFormModalData | null = null, isSuperAdmin = false) => {
    dialogCloseMock = jest.fn();
    getEvaluationTypesMock = jest.fn().mockReturnValue(of(mockEvaluationTypes));
    getRedacteurTypesMock = jest.fn().mockReturnValue(of(mockRedacteurTypes));
    getSitesMock = jest.fn().mockReturnValue(of({ results: mockSites }));
    getOrganismeSitesMock = jest.fn().mockReturnValue(of(mockSites.slice(0, 2)));
    getUsersMock = jest.fn().mockReturnValue(of({ results: mockUsers }));
    createPlanMock = jest.fn().mockReturnValue(of(mockPlan));
    updatePlanMock = jest.fn().mockReturnValue(of(mockPlan));
    getPlansForSitesMock = jest.fn().mockReturnValue(of({ sites: [] }));

    isSuperAdminSignal = signal(isSuperAdmin);
    currentUserSignal = signal(mockCurrentUser);

    const adminServiceMock = {
      getEvaluationTypes: getEvaluationTypesMock,
      getRedacteurTypes: getRedacteurTypesMock,
      getSites: getSitesMock,
      getOrganismeSites: getOrganismeSitesMock,
      getUsers: getUsersMock,
      getOrganismes: jest.fn().mockReturnValue(of({ count: 0, results: [] })),
      // #433 — contexte chaîne de versions chargé en mode édition.
      getPlansForSites: getPlansForSitesMock,
      createPlan: createPlanMock,
      updatePlan: updatePlanMock
    };

    const authServiceMock = {
      isSuperAdmin: isSuperAdminSignal.asReadonly(),
      isAdminOrganisme: signal(false).asReadonly(),
      currentUser: currentUserSignal.asReadonly()
    };

    await TestBed.configureTestingModule({
      imports: [
        PlanFormModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: { close: dialogCloseMock } },
        { provide: MAT_DIALOG_DATA, useValue: dialogData },
        { provide: AdminService, useValue: adminServiceMock },
        { provide: AuthService, useValue: authServiceMock },
        { provide: ActivatedRoute, useValue: { snapshot: { params: {} } } }
      ]
    }).compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(PlanFormModalComponent);
    component = fixture.componentInstance;
  };

  // ==================== CREATE MODE ====================

  describe('Create Mode', () => {
    beforeEach(async () => {
      await setupTestBed(null);
    });

    it('should create', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component).toBeTruthy();
    }));

    it('should be in create mode when no plan provided', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.isEditMode).toBe(false);
    }));

    it('should have correct modal title for create', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.modalTitle).toBe('Nouveau plan de gestion');
    }));

    it('should initialize form with default values', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.form.get('nom')?.value).toBe('');
      expect(component.form.get('statut')?.value).toBe('draft');
      expect(component.form.get('version')?.value).toBe('1');
      expect(component.form.get('gestion_partagee')?.value).toBe(false);
    }));

    it('should set default year values', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const currentYear = new Date().getFullYear();
      expect(component.form.get('annee_debut')?.value).toBe(currentYear);
      expect(component.form.get('annee_fin')?.value).toBe(currentYear + 5);
    }));

    it('should load nomenclatures on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getEvaluationTypesMock).toHaveBeenCalled();
      expect(getRedacteurTypesMock).toHaveBeenCalled();
      expect(component.evaluationTypes()).toEqual(mockEvaluationTypes);
      expect(component.redacteurTypes()).toEqual(mockRedacteurTypes);
    }));

    // #509 — Les champs requis ne doivent afficher qu'un seul astérisque :
    // celui rendu par <app-form-field [required]="true">. Le libellé ne doit
    // PAS suffixer un « * » manuel (sinon double astérisque, cf « Rang »).
    it('should render a single required asterisk per required field', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const requiredLabels = Array.from(
        fixture.nativeElement.querySelectorAll('.app-form-field__label')
      ).filter((label: any) => label.querySelector('.app-form-field__required'));

      expect(requiredLabels.length).toBeGreaterThan(0);
      requiredLabels.forEach((label: any) => {
        const asterisks = (label.textContent || '').match(/\*/g) || [];
        expect(asterisks.length).toBe(1);
      });
    }));

    it('should call createPlan on submit', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      component.form.patchValue({ nom: 'New Plan' });
      // Must select at least one site for the form to submit
      component.toggleSite(1);
      component.onSubmit();
      tick();

      expect(createPlanMock).toHaveBeenCalled();
      expect(dialogCloseMock).toHaveBeenCalledWith({ success: true, plan: mockPlan });
    }));
  });

  // ==================== EDIT MODE ====================

  describe('Edit Mode', () => {
    beforeEach(async () => {
      await setupTestBed({ plan: mockPlan });
    });

    it('should be in edit mode when plan provided', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.isEditMode).toBe(true);
    }));

    it('should have correct modal title for edit', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.modalTitle).toBe('Modifier le plan de gestion');
    }));

    it('should initialize form with plan values', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.form.get('nom')?.value).toBe('Plan Test');
      expect(component.form.get('statut')?.value).toBe('valide');
      expect(component.form.get('version')?.value).toBe('2');
      expect(component.form.get('annee_debut')?.value).toBe(2020);
      expect(component.form.get('annee_fin')?.value).toBe(2030);
      expect(component.form.get('gestion_partagee')?.value).toBe(true);
    }));

    it('should pre-select plan sites', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.selectedSiteIds()).toContain(1);
    }));

    it('should pre-select plan referents', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.selectedReferentIds()).toContain(1);
    }));

    it('should call updatePlan on submit', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      component.form.patchValue({ nom: 'Updated Plan' });
      component.onSubmit();
      tick();

      expect(updatePlanMock).toHaveBeenCalledWith(1, expect.objectContaining({
        nom: 'Updated Plan'
      }));
    }));
  });

  // ==================== FORM VALIDATION ====================

  describe('Form Validation', () => {
    beforeEach(async () => {
      await setupTestBed(null);
      fixture.detectChanges();
    });

    it('should require nom', fakeAsync(() => {
      tick();

      const control = component.form.get('nom');
      control?.setValue('');
      expect(control?.valid).toBe(false);

      control?.setValue('Valid Name');
      expect(control?.valid).toBe(true);
    }));

    it('should validate year range', fakeAsync(() => {
      tick();

      const debutControl = component.form.get('annee_debut');
      debutControl?.setValue(1800);
      expect(debutControl?.valid).toBe(false);

      debutControl?.setValue(2020);
      expect(debutControl?.valid).toBe(true);

      debutControl?.setValue(2200);
      expect(debutControl?.valid).toBe(false);
    }));

    it('should not submit when form is invalid', fakeAsync(() => {
      tick();

      component.form.get('nom')?.setValue('');
      component.onSubmit();

      expect(createPlanMock).not.toHaveBeenCalled();
    }));

    // #527 — les messages d'erreur du rang ne doivent s'afficher que si le champ
    // est invalide ET touché (avant : ils s'affichaient toujours, ce qui cassait
    // aussi l'alignement de la colonne « Surface »).
    // Le FakeTranslateLoader renvoie {} → le pipe translate affiche la CLÉ i18n.
    it('should not render rang error messages when the field is valid', fakeAsync(() => {
      tick();

      const rang = component.form.get('rang');
      rang?.setValue(2);
      rang?.markAsTouched();
      fixture.detectChanges();
      tick();

      const html: string = fixture.nativeElement.textContent;
      expect(html).not.toContain('modals.planForm.validation.rangRequired');
      expect(html).not.toContain('modals.planForm.validation.rangMin');
    }));

    it('should render the required error only after the rang field is touched', fakeAsync(() => {
      tick();

      const rang = component.form.get('rang');
      rang?.setValue(null);
      fixture.detectChanges();
      tick();
      expect(fixture.nativeElement.textContent).not.toContain('modals.planForm.validation.rangRequired');

      rang?.markAsTouched();
      fixture.detectChanges();
      tick();
      expect(fixture.nativeElement.textContent).toContain('modals.planForm.validation.rangRequired');
    }));
  });

  // ==================== SITE SELECTION ====================

  describe('Site Selection', () => {
    beforeEach(async () => {
      await setupTestBed(null, true); // Super admin to see all sites
      fixture.detectChanges();
    });

    it('should load available sites', fakeAsync(() => {
      tick();

      expect(getSitesMock).toHaveBeenCalled();
      expect(component.availableSites().length).toBeGreaterThan(0);
    }));

    it('should toggle site selection', fakeAsync(() => {
      tick();

      expect(component.selectedSiteIds()).not.toContain(1);

      component.toggleSite(1);
      expect(component.selectedSiteIds()).toContain(1);

      component.toggleSite(1);
      expect(component.selectedSiteIds()).not.toContain(1);
    }));

    it('should check if site is selected', fakeAsync(() => {
      tick();

      component.toggleSite(1);
      expect(component.isSiteSelected(1)).toBe(true);
      expect(component.isSiteSelected(2)).toBe(false);
    }));

    it('should select all filtered sites', fakeAsync(() => {
      tick();

      component.selectAllSites();

      const filteredIds = component.filteredSites().map(s => s.id);
      filteredIds.forEach(id => {
        expect(component.selectedSiteIds()).toContain(id);
      });
    }));

    it('should deselect all filtered sites', fakeAsync(() => {
      tick();

      component.selectAllSites();
      component.deselectAllSites();

      expect(component.selectedSiteIds().length).toBe(0);
    }));

    it('should get selected sites count', fakeAsync(() => {
      tick();

      expect(component.getSelectedSitesCount()).toBe(0);

      component.toggleSite(1);
      component.toggleSite(2);

      expect(component.getSelectedSitesCount()).toBe(2);
    }));

    it('should filter sites by search query', fakeAsync(() => {
      tick();

      component.siteSearchQuery = 'Alpha';
      component.filterSites();

      const filtered = component.filteredSites();
      expect(filtered.some(s => s.nom === 'Site Alpha')).toBe(true);
      expect(filtered.some(s => s.nom === 'Site Beta')).toBe(false);
    }));
  });

  // ==================== REFERENT SELECTION ====================

  describe('Referent Selection', () => {
    beforeEach(async () => {
      await setupTestBed(null, true);
      fixture.detectChanges();
    });

    it('should load available users', fakeAsync(() => {
      tick();

      expect(getUsersMock).toHaveBeenCalled();
      expect(component.availableUsers().length).toBeGreaterThan(0);
    }));

    it('should toggle referent selection', fakeAsync(() => {
      tick();

      expect(component.selectedReferentIds()).not.toContain(1);

      component.toggleReferent(1);
      expect(component.selectedReferentIds()).toContain(1);

      component.toggleReferent(1);
      expect(component.selectedReferentIds()).not.toContain(1);
    }));

    it('should check if referent is selected', fakeAsync(() => {
      tick();

      component.toggleReferent(1);
      expect(component.isReferentSelected(1)).toBe(true);
      expect(component.isReferentSelected(2)).toBe(false);
    }));

    it('should select all filtered referents', fakeAsync(() => {
      tick();

      component.selectAllReferents();

      const filteredIds = component.filteredUsers().map(u => u.id);
      filteredIds.forEach(id => {
        expect(component.selectedReferentIds()).toContain(id);
      });
    }));

    it('should deselect all filtered referents', fakeAsync(() => {
      tick();

      component.selectAllReferents();
      component.deselectAllReferents();

      expect(component.selectedReferentIds().length).toBe(0);
    }));

    it('should get selected referents count', fakeAsync(() => {
      tick();

      expect(component.getSelectedReferentsCount()).toBe(0);

      component.toggleReferent(1);
      component.toggleReferent(2);

      expect(component.getSelectedReferentsCount()).toBe(2);
    }));

    it('should filter users by search query', fakeAsync(() => {
      tick();

      component.userSearchQuery = 'Dupont';
      component.filterUsers();

      const filtered = component.filteredUsers();
      // nom is the full name "Jean Dupont", so use includes
      expect(filtered.some(u => u.nom.includes('Dupont'))).toBe(true);
      expect(filtered.some(u => u.nom.includes('Martin'))).toBe(false);
    }));
  });

  // ==================== ADMIN ORG FILTERING ====================

  describe('Admin Organisme Filtering', () => {
    beforeEach(async () => {
      await setupTestBed(null, false); // Not super admin
    });

    it('should load sites for admin org', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getSitesMock).toHaveBeenCalledWith(expect.objectContaining({
        page: 1, page_size: 200
      }));
    }));

    it('should filter users by organisme', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getUsersMock).toHaveBeenCalledWith(expect.objectContaining({
        organisme: 1
      }));
    }));
  });

  // ==================== LOADING STATES ====================

  describe('Loading States', () => {
    beforeEach(async () => {
      await setupTestBed(null);
    });

    it('should show loading data state initially', fakeAsync(() => {
      // The isLoadingData signal exists and is managed by the component
      fixture.detectChanges();
      tick();

      // After data loads (synchronous mocks), loading should be false
      expect(component.isLoadingData()).toBe(false);
    }));

    it('should show loading state during submission', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      component.form.patchValue({ nom: 'Test' });

      expect(component.isLoading()).toBe(false);

      component.onSubmit();
      tick();

      // With synchronous mocks, loading transitions immediately
      // After submission completes, loading should be false
      expect(component.isLoading()).toBe(false);
    }));
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setupTestBed(null);
      fixture.detectChanges();
    });

    it('should handle create error', fakeAsync(() => {
      createPlanMock.mockReturnValue(throwError(() => new Error('Creation failed')));
      tick();

      component.form.patchValue({ nom: 'Test' });
      // Must select at least one site for the form to submit
      component.toggleSite(1);
      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Creation failed');
      expect(dialogCloseMock).not.toHaveBeenCalled();
    }));

    it('should continue working with empty nomenclatures', fakeAsync(() => {
      tick();

      // Even if nomenclatures are empty, form should still work
      component.form.patchValue({ nom: 'Test Plan' });
      // Must select at least one site for the form to submit
      component.toggleSite(1);
      expect(component.form.valid).toBe(true);

      component.onSubmit();
      tick();

      // Should still create plan even without nomenclature selections
      expect(createPlanMock).toHaveBeenCalled();
    }));
  });

  // ==================== CANCEL ====================

  describe('Cancel', () => {
    beforeEach(async () => {
      await setupTestBed(null);
      fixture.detectChanges();
    });

    it('should close dialog on cancel', fakeAsync(() => {
      tick();

      component.onCancel();

      expect(dialogCloseMock).toHaveBeenCalledWith();
    }));
  });

  // ==================== PAYLOAD ====================

  describe('Payload', () => {
    beforeEach(async () => {
      await setupTestBed(null, true);
      fixture.detectChanges();
    });

    it('should include selected sites and referents in payload', fakeAsync(() => {
      tick();

      component.form.patchValue({ nom: 'Test Plan' });
      component.toggleSite(1);
      component.toggleSite(2);
      component.toggleReferent(1);

      component.onSubmit();
      tick();

      expect(createPlanMock).toHaveBeenCalledWith(expect.objectContaining({
        sites_ids: [1, 2],
        referents_ids: [1]
      }));
    }));

    it('should send undefined for empty optional fields', fakeAsync(() => {
      tick();

      component.form.patchValue({
        nom: 'Test',
        version: '',
        redacteur_nom: '',
        commentaire: ''
      });
      // Must select at least one site for the form to submit
      component.toggleSite(1);

      component.onSubmit();
      tick();

      expect(createPlanMock).toHaveBeenCalledWith(expect.objectContaining({
        version: undefined,
        redacteur_nom: undefined,
        commentaire: undefined
      }));
    }));
  });

  // ==================== VERSION CHAIN — PARENT LINK (#506) ====================

  describe('Version chain — parent link (#506)', () => {
    const editPlan: AdminPlan = {
      ...mockPlan,
      id_pg: 5,
      rang: 2,
      plan_parent_id: null,
      sites: [{ id_site: 1, nom_site: 'Site Alpha' }]
    };

    const sitePlans = {
      sites: [{
        site_id: 1,
        site_nom: 'Site Alpha',
        plans: [
          { id_pg: 10, nom: 'PG rang 1', slug: 'pg-1', statut: 'valide', statut_display: 'Validé', rang: 1, version: '1', annee_debut: 2010, annee_fin: 2020, is_mi_parcours: false },
          { id_pg: 5, nom: 'Plan Test', slug: 'pg-5', statut: 'draft', statut_display: 'Brouillon', rang: 2, version: '1', annee_debut: 2020, annee_fin: 2030, is_mi_parcours: false },
          { id_pg: 20, nom: 'PG rang 3', slug: 'pg-3', statut: 'draft', statut_display: 'Brouillon', rang: 3, version: '1', annee_debut: 2030, annee_fin: 2040, is_mi_parcours: false }
        ]
      }]
    };

    it('exposes only lower-rang plans (excluding self) as candidate parents', async () => {
      await setupTestBed({ plan: editPlan });
      getPlansForSitesMock.mockReturnValue(of(sitePlans));
      fixture.detectChanges();

      const ids = component.candidateParents().map(p => p.id_pg);
      expect(ids).toEqual([10]); // rang 1 only; self (5) and rang 3 (20) excluded
    });

    it('sends the selected parent in the update payload', async () => {
      await setupTestBed({ plan: editPlan });
      getPlansForSitesMock.mockReturnValue(of(sitePlans));
      fixture.detectChanges();

      component.onParentChange('10');
      component.onSubmit();

      expect(updatePlanMock).toHaveBeenCalledWith(5, expect.objectContaining({ plan_parent_id: 10 }));
    });

    it('shows the parent selector only for a plan without an existing link (#501)', async () => {
      await setupTestBed({ plan: editPlan }); // plan_parent_id: null
      getPlansForSitesMock.mockReturnValue(of(sitePlans));
      fixture.detectChanges();

      expect(component.hasInitialParent).toBe(false);
      expect(fixture.nativeElement.querySelector('.version-chain-info select')).not.toBeNull();
    });

    it('hides the parent selector and preserves the link when the plan already has a parent (#501)', async () => {
      await setupTestBed({ plan: { ...editPlan, plan_parent_id: 10 } });
      getPlansForSitesMock.mockReturnValue(of(sitePlans));
      fixture.detectChanges();

      // Après duplication : lien acquis → la question « Aucun / indépendant » disparaît.
      expect(component.hasInitialParent).toBe(true);
      expect(fixture.nativeElement.querySelector('.version-chain-info select')).toBeNull();

      // Le rattachement d'origine est conservé à l'enregistrement.
      component.onSubmit();
      expect(updatePlanMock).toHaveBeenCalledWith(5, expect.objectContaining({ plan_parent_id: 10 }));
    });
  });

  // ============ VERSION CHAIN — CONTEXTE RÉACTIF (RANG / VERSION / PARENT) (#501) ============

  describe('Version chain — reactive context (#501)', () => {
    // Chaîne : rang 1 (v1, v2), rang 2 (self v1). La version prédite doit
    // suivre le rang courant, cohérente avec le backend get_next_version().
    const chainPlan: AdminPlan = {
      ...mockPlan,
      id_pg: 5,
      rang: 2,
      version: '1',
      plan_parent_id: 11,
      plan_parent_nom: 'PG rang 1 v2',
      plan_parent_rang: 1,
      plan_parent_version: '2',
      sites: [{ id_site: 1, nom_site: 'Site Alpha' }],
      version_chain: [
        { id_pg: 10, nom: 'PG rang 1 v1', slug: 'pg-10', version: '1', statut: 'archive', rang: 1, is_current: false },
        { id_pg: 11, nom: 'PG rang 1 v2', slug: 'pg-11', version: '2', statut: 'valide', rang: 1, is_current: false },
        { id_pg: 5, nom: 'Plan Test', slug: 'pg-5', version: '1', statut: 'draft', rang: 2, is_current: true },
      ],
    };

    it('predicts version 1 for a brand-new rang (no other plan in that rang)', async () => {
      await setupTestBed({ plan: chainPlan });
      fixture.detectChanges();

      // Rang 2 : self est la seule version → repart à 1.
      expect(component.currentRang()).toBe(2);
      expect(component.predictedVersion()).toBe('1');
    });

    it('recomputes the predicted version when the rang changes', async () => {
      await setupTestBed({ plan: chainPlan });
      fixture.detectChanges();

      // Passer au rang 1 (déjà v1 et v2, hors self) → prochaine version = 3.
      component.form.get('rang')?.setValue(1);
      expect(component.predictedVersion()).toBe('3');
    });

    it('saves the version recomputed from the rang (displayed = persisted)', async () => {
      await setupTestBed({ plan: chainPlan });
      fixture.detectChanges();

      component.form.get('rang')?.setValue(1);
      component.onSubmit();

      expect(updatePlanMock).toHaveBeenCalledWith(5, expect.objectContaining({ rang: 1, version: '3' }));
    });

    it('exposes the linked parent (falls back to the plan original parent)', async () => {
      await setupTestBed({ plan: chainPlan });
      fixture.detectChanges();

      expect(component.selectedParent()).toEqual({ nom: 'PG rang 1 v2', rang: 1, version: '2' });
    });

    it('reports an independent plan when no parent is linked', async () => {
      await setupTestBed({ plan: { ...chainPlan, plan_parent_id: null } });
      fixture.detectChanges();

      expect(component.selectedParent()).toBeNull();
    });
  });
});
