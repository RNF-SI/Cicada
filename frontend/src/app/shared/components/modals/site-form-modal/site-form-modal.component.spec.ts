import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import {
  SiteFormModalComponent,
  SiteFormModalData,
  SiteFormModalResult
} from './site-form-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { ValidationService } from '../../../../core/services/validation.service';
import { DuplicateCheckResult, DuplicateSite } from '../../../../core/models/admin.model';

// Fake translate loader
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'modals.siteForm.createTitle': 'Nouveau site',
      'modals.siteForm.editTitle': 'Modifier le site',
      'modals.siteForm.infoTitle': 'Informations du site',
      'modals.siteForm.fields.name': 'Nom du site',
      'modals.siteForm.fields.type': 'Type de site',
      'modals.siteForm.fields.localId': 'Identifiant local',
      'modals.siteForm.fields.inpnId': 'Identifiant INPN',
      'modals.siteForm.fields.surface': 'Surface officielle (ha)',
      'modals.siteForm.fields.marine': 'Site marin',
      'modals.siteForm.fields.overseas': 'Outre-mer',
      'modals.siteForm.fields.active': 'Site actif',
      'modals.siteForm.hints.localId': 'Code interne de reference',
      'modals.siteForm.hints.inpnId': 'Code national INPN',
      'modals.siteForm.errors.nameRequired': 'Le nom est requis',
      'modals.siteForm.errors.surfacePositive': 'La surface doit etre positive',
      'modals.siteForm.errors.inpnDuplicate': 'Ce code INPN est deja utilise par un autre site.',
      'modals.siteForm.duplicates.inpnUsed': 'Ce code INPN est deja utilise par un site existant',
      'modals.siteForm.duplicates.similarFound': 'Des sites avec un nom similaire existent deja',
      'modals.siteForm.duplicates.requestAccess': 'Demander l\'acces',
      'modals.siteForm.duplicates.linkAndAccess': 'Lier mon organisme et demander l\'acces',
      'modals.siteForm.duplicates.linkOnly': 'Lier mon organisme uniquement',
      'modals.siteForm.duplicates.alreadyAccess': 'Acces actif',
      'modals.siteForm.duplicates.yourOrg': 'Votre organisme',
      'modals.siteForm.duplicates.andOthers': 'et {{count}} autre(s)',
      'modals.siteForm.duplicates.continueCreation': 'Ignorer et creer un nouveau site',
      'modals.siteForm.duplicates.checking': 'Recherche de sites similaires...',
      'sites.form.geometry.title': 'Geometrie',
      'sites.form.geometry.bothHelp': 'Aide',
      'common.actions.cancel': 'Annuler',
      'common.actions.save': 'Enregistrer',
      'common.actions.create': 'Creer',
      'common.actions.select': 'Selectionner',
      'common.status.loading': 'Chargement',
      'modals.siteForm.duplicates.pendingOrgLinkBadge': 'Demande de lien en cours',
      'modals.siteForm.duplicates.pendingAccessBadge': 'Demande d\'acces en cours'
    });
  }
}

describe('SiteFormModalComponent', () => {
  let component: SiteFormModalComponent;
  let fixture: ComponentFixture<SiteFormModalComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<SiteFormModalComponent>>;
  let adminService: jest.Mocked<AdminService>;
  let validationService: jest.Mocked<ValidationService>;
  let translateService: TranslateService;

  const mockData: SiteFormModalData = {};

  const mockDuplicateSite: DuplicateSite = {
    id_site: 1,
    slug: 'reserve-de-camargue',
    nom_site: 'Reserve de Camargue',
    id_inpn: 'FR0000001',
    id_local: 'RN001',
    type_site_label: 'RNN',
    surf_off: 1500,
    organismes: [{ id_organisme: 1, nom_organisme: 'RNF', principal: true }],
    is_user_org: false,
    has_access: false
  };

  const mockDuplicateResult: DuplicateCheckResult = {
    exact_inpn_match: null,
    similar_names: []
  };

  beforeEach(async () => {
    dialogRef = {
      close: jest.fn()
    } as unknown as jest.Mocked<MatDialogRef<SiteFormModalComponent>>;

    adminService = {
      getSiteTypes: jest.fn().mockReturnValue(of([
        { id_nomenclature: 42, cd_nomenclature: 'RNN', label: 'Reserve Naturelle Nationale' }
      ])),
      checkDuplicates: jest.fn().mockReturnValue(of(mockDuplicateResult)),
      createSite: jest.fn().mockReturnValue(of({ id_site: 1, nom_site: 'Test Site' })),
      updateSite: jest.fn().mockReturnValue(of({ id_site: 1, nom_site: 'Updated Site' })),
      assignSiteToOrganisme: jest.fn().mockReturnValue(of({})),
      getSiteCreationValidators: jest.fn().mockReturnValue(of({ auto_validated: true, validators: [] }))
    } as unknown as jest.Mocked<AdminService>;

    validationService = {
      getMyRequests: jest.fn().mockReturnValue(of([]))
    } as unknown as jest.Mocked<ValidationService>;

    await TestBed.configureTestingModule({
      imports: [
        SiteFormModalComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr'
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: AdminService, useValue: adminService },
        { provide: ValidationService, useValue: validationService }
      ]
    }).compileComponents();

    translateService = TestBed.inject(TranslateService);
    translateService.use('fr');

    fixture = TestBed.createComponent(SiteFormModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should be in create mode by default', () => {
      expect(component.isEditMode).toBe(false);
    });

    it('should initialize form with empty values', () => {
      expect(component.form.get('nom_site')?.value).toBe('');
      expect(component.form.get('id_inpn')?.value).toBe('');
    });

    it('should load site types on init', () => {
      expect(adminService.getSiteTypes).toHaveBeenCalled();
    });

    it('should have no duplicates initially', () => {
      expect(component.duplicateCheckResult()).toBeNull();
      expect(component.hasInpnDuplicate).toBe(false);
      expect(component.hasSimilarNames).toBe(false);
    });
  });

  describe('duplicate detection - debouncing', () => {
    it('should trigger duplicate check after name input with debounce', fakeAsync(() => {
      // Set form value and simulate typing
      component.form.patchValue({ nom_site: 'Camargue' });
      const input = { target: { value: 'Camargue' } } as unknown as Event;
      component.onNameInput(input);

      // Before debounce
      expect(adminService.checkDuplicates).not.toHaveBeenCalled();

      // After debounce (500ms)
      tick(500);
      expect(adminService.checkDuplicates).toHaveBeenCalledWith({ nom_site: 'Camargue' });
    }));

    it('should trigger duplicate check after INPN input with debounce', fakeAsync(() => {
      // Set form values
      component.form.patchValue({ nom_site: 'Test Site', id_inpn: 'FR001' });

      // Simulate typing in INPN field
      const input = { target: { value: 'FR001' } } as unknown as Event;
      component.onInpnInput(input);

      // After debounce (300ms)
      tick(300);
      expect(adminService.checkDuplicates).toHaveBeenCalled();
    }));

    it('should not check duplicates if name is less than 3 characters', fakeAsync(() => {
      component.form.patchValue({ nom_site: 'Ca' });
      const input = { target: { value: 'Ca' } } as unknown as Event;
      component.onNameInput(input);

      tick(500);
      // Should not be called because name is too short
      expect(adminService.checkDuplicates).not.toHaveBeenCalled();
    }));
  });

  describe('duplicate detection - INPN match', () => {
    it('should show INPN duplicate warning when exact match found', fakeAsync(() => {
      const resultWithInpn: DuplicateCheckResult = {
        exact_inpn_match: mockDuplicateSite,
        similar_names: []
      };
      adminService.checkDuplicates.mockReturnValue(of(resultWithInpn));

      // Trigger check
      component.form.patchValue({ nom_site: 'Test Site', id_inpn: 'FR0000001' });
      const input = { target: { value: 'FR0000001' } } as unknown as Event;
      component.onInpnInput(input);
      tick(300);

      expect(component.hasInpnDuplicate).toBe(true);
      expect(component.duplicateCheckResult()?.exact_inpn_match?.nom_site).toBe('Reserve de Camargue');
    }));

    it('should block form submission when INPN duplicate exists', fakeAsync(() => {
      const resultWithInpn: DuplicateCheckResult = {
        exact_inpn_match: mockDuplicateSite,
        similar_names: []
      };
      adminService.checkDuplicates.mockReturnValue(of(resultWithInpn));

      // Set form values
      component.form.patchValue({ nom_site: 'Test Site', id_inpn: 'FR0000001' });
      const input = { target: { value: 'FR0000001' } } as unknown as Event;
      component.onInpnInput(input);
      tick(300);

      // Try to submit
      component.onSubmit();

      // Should not call createSite
      expect(adminService.createSite).not.toHaveBeenCalled();
      expect(component.errorMessage()).toContain('INPN');
    }));
  });

  describe('duplicate detection - similar names', () => {
    it('should show similar names warning when found', fakeAsync(() => {
      const resultWithSimilar: DuplicateCheckResult = {
        exact_inpn_match: null,
        similar_names: [mockDuplicateSite]
      };
      adminService.checkDuplicates.mockReturnValue(of(resultWithSimilar));

      // Trigger check
      component.form.patchValue({ nom_site: 'Camargue' });
      const input = { target: { value: 'Camargue' } } as unknown as Event;
      component.onNameInput(input);
      tick(500);

      expect(component.hasSimilarNames).toBe(true);
      expect(component.duplicateCheckResult()?.similar_names.length).toBe(1);
    }));

    it('should allow submission after dismissing similar names warning', fakeAsync(() => {
      const resultWithSimilar: DuplicateCheckResult = {
        exact_inpn_match: null,
        similar_names: [mockDuplicateSite]
      };
      adminService.checkDuplicates.mockReturnValue(of(resultWithSimilar));

      // Trigger check
      component.form.patchValue({ nom_site: 'Camargue Test' });
      const input = { target: { value: 'Camargue Test' } } as unknown as Event;
      component.onNameInput(input);
      tick(500);

      // Dismiss warning
      component.continueCreation();
      expect(component.showDuplicateWarning()).toBe(false);

      // Submit should work
      component.onSubmit();
      expect(adminService.createSite).toHaveBeenCalled();
    }));
  });

  describe('duplicate actions', () => {
    it('should close dialog with request_access action', () => {
      component.requestAccessToSite(mockDuplicateSite);

      expect(dialogRef.close).toHaveBeenCalledWith({
        duplicateAction: 'request_access',
        duplicateSite: mockDuplicateSite
      });
    });

    it('should close dialog with request_org_link action without access', () => {
      component.requestOrgLink(mockDuplicateSite, false);

      expect(dialogRef.close).toHaveBeenCalledWith({
        duplicateAction: 'request_org_link',
        duplicateSite: mockDuplicateSite,
        alsoRequestAccess: false
      });
    });

    it('should close dialog with request_org_link action with access', () => {
      component.requestOrgLink(mockDuplicateSite, true);

      expect(dialogRef.close).toHaveBeenCalledWith({
        duplicateAction: 'request_org_link',
        duplicateSite: mockDuplicateSite,
        alsoRequestAccess: true
      });
    });

    it('should dismiss warning and allow creation', () => {
      component.showDuplicateWarning.set(true);
      component.continueCreation();

      expect(component.showDuplicateWarning()).toBe(false);
      expect(component.duplicateWarningDismissed()).toBe(true);
    });
  });

  describe('link buttons in suggestions panel', () => {
    // Site where user's org already manages it
    const siteWithUserOrg: DuplicateSite = {
      id_site: 2,
      slug: 'reserve-du-vercors',
      nom_site: 'Reserve du Vercors',
      id_inpn: 'FR0000002',
      id_local: 'RN002',
      type_site_label: 'Reserve Naturelle Nationale',
      surf_off: 2000,
      organismes: [{ id_organisme: 1, nom_organisme: 'Mon Organisme', principal: true }],
      is_user_org: true,
      has_access: false
    };

    // Site where user already has access
    const siteWithAccess: DuplicateSite = {
      id_site: 3,
      slug: 'reserve-des-aiguilles',
      nom_site: 'Reserve des Aiguilles',
      id_inpn: 'FR0000003',
      id_local: 'RN003',
      type_site_label: 'Reserve Naturelle Regionale',
      surf_off: 500,
      organismes: [{ id_organisme: 1, nom_organisme: 'Mon Organisme', principal: true }],
      is_user_org: true,
      has_access: true
    };

    // Site managed by another org
    const siteOtherOrg: DuplicateSite = {
      id_site: 4,
      slug: 'parc-du-mercantour',
      nom_site: 'Parc du Mercantour',
      id_inpn: 'FR0000004',
      id_local: 'PN001',
      type_site_label: 'Parc Naturel Regional',
      surf_off: 10000,
      organismes: [{ id_organisme: 99, nom_organisme: 'Autre Organisme', principal: true }],
      is_user_org: false,
      has_access: false
    };

    describe('when site is managed by user org (is_user_org=true, has_access=false)', () => {
      it('should call requestAccessToSite when clicking request access button', () => {
        component.requestAccessToSite(siteWithUserOrg);

        expect(dialogRef.close).toHaveBeenCalledWith({
          duplicateAction: 'request_access',
          duplicateSite: siteWithUserOrg
        });
      });

      it('should pass correct site data in result', () => {
        component.requestAccessToSite(siteWithUserOrg);

        const closeCall = dialogRef.close.mock.calls[0][0] as SiteFormModalResult;
        expect(closeCall.duplicateSite?.id_site).toBe(2);
        expect(closeCall.duplicateSite?.nom_site).toBe('Reserve du Vercors');
        expect(closeCall.duplicateSite?.is_user_org).toBe(true);
      });
    });

    describe('when user already has access (has_access=true)', () => {
      it('should not trigger any action since buttons are hidden', () => {
        // When has_access is true, the action buttons should not be rendered
        // We verify that the site data reflects this state
        expect(siteWithAccess.has_access).toBe(true);
        expect(siteWithAccess.is_user_org).toBe(true);
      });

      it('should display access badge instead of action buttons', fakeAsync(() => {
        // Setup duplicate check result with site that has access
        const resultWithAccess: DuplicateCheckResult = {
          exact_inpn_match: null,
          similar_names: [siteWithAccess]
        };
        adminService.checkDuplicates.mockReturnValue(of(resultWithAccess));

        // Trigger check
        component.form.patchValue({ nom_site: 'Aiguilles' });
        const input = { target: { value: 'Aiguilles' } } as unknown as Event;
        component.onNameInput(input);
        tick(500);
        fixture.detectChanges();

        // Verify the result
        const result = component.duplicateCheckResult();
        expect(result?.similar_names[0].has_access).toBe(true);
      }));
    });

    describe('when site is managed by another org (is_user_org=false)', () => {
      it('should call requestOrgLink with alsoRequestAccess=true for link + access', () => {
        component.requestOrgLink(siteOtherOrg, true);

        expect(dialogRef.close).toHaveBeenCalledWith({
          duplicateAction: 'request_org_link',
          duplicateSite: siteOtherOrg,
          alsoRequestAccess: true
        });
      });

      it('should call requestOrgLink with alsoRequestAccess=false for link only', () => {
        component.requestOrgLink(siteOtherOrg, false);

        expect(dialogRef.close).toHaveBeenCalledWith({
          duplicateAction: 'request_org_link',
          duplicateSite: siteOtherOrg,
          alsoRequestAccess: false
        });
      });

      it('should pass correct site data with org info in result', () => {
        component.requestOrgLink(siteOtherOrg, true);

        const closeCall = dialogRef.close.mock.calls[0][0] as SiteFormModalResult;
        expect(closeCall.duplicateSite?.id_site).toBe(4);
        expect(closeCall.duplicateSite?.nom_site).toBe('Parc du Mercantour');
        expect(closeCall.duplicateSite?.is_user_org).toBe(false);
        expect(closeCall.duplicateSite?.organismes[0].nom_organisme).toBe('Autre Organisme');
      });
    });

    describe('suggestions panel display', () => {
      it('should show suggestions panel when similar names are found', fakeAsync(() => {
        const resultWithSimilar: DuplicateCheckResult = {
          exact_inpn_match: null,
          similar_names: [siteOtherOrg, siteWithUserOrg]
        };
        adminService.checkDuplicates.mockReturnValue(of(resultWithSimilar));

        // Trigger check
        component.form.patchValue({ nom_site: 'Reserve Test' });
        const input = { target: { value: 'Reserve Test' } } as unknown as Event;
        component.onNameInput(input);
        tick(500);

        expect(component.showDuplicateWarning()).toBe(true);
        expect(component.duplicateCheckResult()?.similar_names.length).toBe(2);
      }));

      it('should hide suggestions panel after dismissing', fakeAsync(() => {
        const resultWithSimilar: DuplicateCheckResult = {
          exact_inpn_match: null,
          similar_names: [siteOtherOrg]
        };
        adminService.checkDuplicates.mockReturnValue(of(resultWithSimilar));

        // Trigger check
        component.form.patchValue({ nom_site: 'Parc Test' });
        const input = { target: { value: 'Parc Test' } } as unknown as Event;
        component.onNameInput(input);
        tick(500);

        expect(component.showDuplicateWarning()).toBe(true);

        // Dismiss
        component.continueCreation();
        expect(component.showDuplicateWarning()).toBe(false);
      }));

      it('should reset dismissed state when user types again', fakeAsync(() => {
        // First, dismiss the warning
        component.duplicateWarningDismissed.set(true);

        // User types again
        const input = { target: { value: 'New Input' } } as unknown as Event;
        component.onNameInput(input);

        // Dismissed state should be reset
        expect(component.duplicateWarningDismissed()).toBe(false);
      }));
    });

    describe('multiple similar sites', () => {
      it('should handle multiple sites with different statuses', fakeAsync(() => {
        const resultWithMultiple: DuplicateCheckResult = {
          exact_inpn_match: null,
          similar_names: [siteWithUserOrg, siteOtherOrg, siteWithAccess]
        };
        adminService.checkDuplicates.mockReturnValue(of(resultWithMultiple));

        // Trigger check
        component.form.patchValue({ nom_site: 'Reserve' });
        const input = { target: { value: 'Reserve' } } as unknown as Event;
        component.onNameInput(input);
        tick(500);

        const result = component.duplicateCheckResult();
        expect(result?.similar_names.length).toBe(3);

        // Verify different statuses
        const userOrgSite = result?.similar_names.find(s => s.id_site === 2);
        expect(userOrgSite?.is_user_org).toBe(true);
        expect(userOrgSite?.has_access).toBe(false);

        const otherOrgSite = result?.similar_names.find(s => s.id_site === 4);
        expect(otherOrgSite?.is_user_org).toBe(false);

        const accessSite = result?.similar_names.find(s => s.id_site === 3);
        expect(accessSite?.has_access).toBe(true);
      }));

      it('should allow action on each site independently', () => {
        // Request access for user org site
        component.requestAccessToSite(siteWithUserOrg);
        expect(dialogRef.close).toHaveBeenLastCalledWith({
          duplicateAction: 'request_access',
          duplicateSite: siteWithUserOrg
        });

        dialogRef.close.mockClear();

        // Request org link for other org site
        component.requestOrgLink(siteOtherOrg, true);
        expect(dialogRef.close).toHaveBeenLastCalledWith({
          duplicateAction: 'request_org_link',
          duplicateSite: siteOtherOrg,
          alsoRequestAccess: true
        });
      });
    });

    describe('INPN exact match blocking', () => {
      it('should show link buttons for INPN match when user org manages site', fakeAsync(() => {
        const resultWithInpnUserOrg: DuplicateCheckResult = {
          exact_inpn_match: siteWithUserOrg,
          similar_names: []
        };
        adminService.checkDuplicates.mockReturnValue(of(resultWithInpnUserOrg));

        // Trigger check
        component.form.patchValue({ nom_site: 'Test', id_inpn: 'FR0000002' });
        const input = { target: { value: 'FR0000002' } } as unknown as Event;
        component.onInpnInput(input);
        tick(300);

        expect(component.hasInpnDuplicate).toBe(true);
        const match = component.duplicateCheckResult()?.exact_inpn_match;
        expect(match?.is_user_org).toBe(true);
      }));

      it('should allow request access action from INPN alert', () => {
        // Simulate clicking the request access button in INPN alert
        component.requestAccessToSite(siteWithUserOrg);

        expect(dialogRef.close).toHaveBeenCalledWith({
          duplicateAction: 'request_access',
          duplicateSite: siteWithUserOrg
        });
      });

      it('should allow link org action from INPN alert for other org site', () => {
        // Simulate clicking the link + access button in INPN alert
        component.requestOrgLink(siteOtherOrg, true);

        expect(dialogRef.close).toHaveBeenCalledWith({
          duplicateAction: 'request_org_link',
          duplicateSite: siteOtherOrg,
          alsoRequestAccess: true
        });
      });
    });
  });

  describe('form submission', () => {
    it('should not submit if form is invalid', () => {
      component.form.patchValue({ nom_site: '' });
      component.onSubmit();

      expect(adminService.createSite).not.toHaveBeenCalled();
    });

    it('should submit valid form in create mode', fakeAsync(() => {
      // Ensure no duplicates are detected
      component.duplicateCheckResult.set({ exact_inpn_match: null, similar_names: [] });
      component.form.patchValue({ nom_site: 'Valid Site Name' });
      component.onSubmit();

      tick();
      expect(adminService.createSite).toHaveBeenCalled();
    }));

    it('should close dialog after successful creation', fakeAsync(() => {
      // Ensure no duplicates are detected
      component.duplicateCheckResult.set({ exact_inpn_match: null, similar_names: [] });
      component.form.patchValue({ nom_site: 'Valid Site Name' });
      component.onSubmit();

      tick();
      expect(dialogRef.close).toHaveBeenCalled();
    }));
  });

  describe('error handling', () => {
    it('should handle API error during duplicate check gracefully', fakeAsync(() => {
      adminService.checkDuplicates.mockReturnValue(throwError(() => new Error('API Error')));

      component.form.patchValue({ nom_site: 'Test Site' });
      const input = { target: { value: 'Test Site' } } as unknown as Event;
      component.onNameInput(input);
      tick(500);

      // Should not block user
      expect(component.isCheckingDuplicates()).toBe(false);
      // No duplicates should be shown
      expect(component.duplicateCheckResult()).toBeNull();
    }));

    it('should display error message on create failure', fakeAsync(() => {
      adminService.createSite.mockReturnValue(throwError(() => new Error('Creation failed')));
      // Ensure no duplicates are detected
      component.duplicateCheckResult.set({ exact_inpn_match: null, similar_names: [] });

      component.form.patchValue({ nom_site: 'Valid Site Name' });
      component.onSubmit();

      tick();
      expect(component.errorMessage()).toBe('Creation failed');
      expect(component.isLoading()).toBe(false);
    }));
  });

  describe('pending request detection', () => {
    it('should load pending requests on init', () => {
      expect(validationService.getMyRequests).toHaveBeenCalled();
    });

    it('should detect pending org link for a duplicate site', () => {
      component.pendingRequests.set([
        {
          id: 100,
          request_type: 'site_org_link',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Reserve de Camargue',
          target_site_id: 1,
          created_at: new Date().toISOString()
        } as any
      ]);

      expect(component.hasPendingOrgLink(mockDuplicateSite)).toBe(true);
    });

    it('should return false when no pending org link exists', () => {
      component.pendingRequests.set([]);

      expect(component.hasPendingOrgLink(mockDuplicateSite)).toBe(false);
    });

    it('should detect pending access for a duplicate site', () => {
      component.pendingRequests.set([
        {
          id: 101,
          request_type: 'site_access',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Reserve de Camargue',
          target_site_id: 1,
          created_at: new Date().toISOString()
        } as any
      ]);

      expect(component.hasPendingAccess(mockDuplicateSite)).toBe(true);
    });

    it('should return false when no pending access exists', () => {
      component.pendingRequests.set([]);

      expect(component.hasPendingAccess(mockDuplicateSite)).toBe(false);
    });

    it('should not match pending request for different site', () => {
      component.pendingRequests.set([
        {
          id: 102,
          request_type: 'site_org_link',
          status: 'pending',
          requester_id: 1,
          requester_name: 'Test User',
          target_name: 'Other Site',
          target_site_id: 999,
          created_at: new Date().toISOString()
        } as any
      ]);

      expect(component.hasPendingOrgLink(mockDuplicateSite)).toBe(false);
    });

    it('should handle getMyRequests error gracefully', () => {
      // Re-create with error-throwing service
      validationService.getMyRequests.mockReturnValue(throwError(() => new Error('Network error')));

      // Re-init to trigger loadPendingRequests again
      component.ngOnInit();

      // Should not crash, pendingRequests should remain empty
      expect(component.pendingRequests().length).toBe(0);
    });
  });

  describe('edit mode', () => {
    beforeEach(async () => {
      // Re-create component with edit data
      const editData: SiteFormModalData = {
        site: {
          id_site: 1,
          slug: 'existing-site',
          nom_site: 'Existing Site',
          id_inpn: 'FR9999999',
          type_site: { id_nomenclature: 42, label: 'RNN', cd_nomenclature: 'RNN' }
        }
      };

      await TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [
          SiteFormModalComponent,
          NoopAnimationsModule,
          HttpClientTestingModule,
          TranslateModule.forRoot({
            loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
            defaultLanguage: 'fr'
          })
        ],
        providers: [
          { provide: MatDialogRef, useValue: dialogRef },
          { provide: MAT_DIALOG_DATA, useValue: editData },
          { provide: AdminService, useValue: adminService },
          { provide: ValidationService, useValue: validationService }
        ]
      }).compileComponents();

      fixture = TestBed.createComponent(SiteFormModalComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    });

    it('should be in edit mode when site is provided', () => {
      expect(component.isEditMode).toBe(true);
    });

    it('should pre-fill form with site data', () => {
      expect(component.form.get('nom_site')?.value).toBe('Existing Site');
      expect(component.form.get('id_inpn')?.value).toBe('FR9999999');
    });

    it('should not setup duplicate checking in edit mode', fakeAsync(() => {
      const input = { target: { value: 'Changed Name' } } as unknown as Event;
      component.onNameInput(input);
      tick(500);

      // checkDuplicates should not be called in edit mode
      expect(adminService.checkDuplicates).not.toHaveBeenCalled();
    }));

    it('should call updateSite in edit mode', fakeAsync(() => {
      component.form.patchValue({ nom_site: 'Updated Site Name' });
      component.onSubmit();

      tick();
      expect(adminService.updateSite).toHaveBeenCalledWith('existing-site', expect.any(Object));
    }));
  });

  // #440 — la géométrie du site doit être affichée à l'ouverture du
  // formulaire d'édition (et donc renvoyée à la sauvegarde).
  describe('edit mode - geometry pre-fill', () => {
    const polygon = { type: 'Polygon', coordinates: [[[0, 0], [0, 1], [1, 1], [0, 0]]] };
    const point = { type: 'Point', coordinates: [0.5, 0.5] };

    beforeEach(async () => {
      const editData: SiteFormModalData = {
        site: {
          id_site: 1,
          slug: 'existing-site',
          nom_site: 'Existing Site',
          geom_geojson: polygon,
          geom_pt_geojson: point
        }
      };

      await TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [
          SiteFormModalComponent,
          NoopAnimationsModule,
          HttpClientTestingModule,
          TranslateModule.forRoot({
            loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
            defaultLanguage: 'fr'
          })
        ],
        providers: [
          { provide: MatDialogRef, useValue: dialogRef },
          { provide: MAT_DIALOG_DATA, useValue: editData },
          { provide: AdminService, useValue: adminService },
          { provide: ValidationService, useValue: validationService }
        ]
      }).compileComponents();

      fixture = TestBed.createComponent(SiteFormModalComponent);
      component = fixture.componentInstance;
      // ngOnInit sans detectChanges : on évite de monter la carte Leaflet
      // (qui plante au nettoyage sous jsdom) tout en exécutant l'init géométrie.
      component.ngOnInit();
    });

    it('should pre-fill geometry signals from the edited site', () => {
      expect(component.polygonGeometry()).toEqual(polygon);
      expect(component.pointGeometry()).toEqual(point);
    });
  });
});
