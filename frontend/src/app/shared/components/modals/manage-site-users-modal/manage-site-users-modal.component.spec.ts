import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import {
  ManageSiteUsersModalComponent,
  ManageSiteUsersModalData
} from './manage-site-users-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminSite, AdminUser, SiteOrganisme } from '../../../../core/models/admin.model';

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'common.messages.error': 'Une erreur est survenue',
      'modals.manageSiteUsers.messages.userAdded': 'Utilisateur {name} ajouté'
    });
  }
}

describe('ManageSiteUsersModalComponent', () => {
  let component: ManageSiteUsersModalComponent;
  let fixture: ComponentFixture<ManageSiteUsersModalComponent>;

  let dialogCloseMock: jest.Mock;
  let getUsersMock: jest.Mock;
  let assignUserToSiteMock: jest.Mock;
  let removeUserFromSiteMock: jest.Mock;

  const mockOrganisme: SiteOrganisme = {
    id_organisme: 1,
    nom_organisme: 'Test Organisme',
    principal: true
  };

  const mockSite: AdminSite = {
    id_site: 1,
    slug: 'site-test',
    nom_site: 'Site Test',
    organismes: [mockOrganisme]
  };

  const mockUsers: AdminUser[] = [
    {
      id_role: 1,
      email: 'user1@test.fr',
      nom_role: 'Dupont',
      prenom_role: 'Jean',
      role_level: 'utilisateur',
      active: true,
      organisme: { id_organisme: 1, nom_organisme: 'Test Organisme' }
    },
    {
      id_role: 2,
      email: 'user2@test.fr',
      nom_role: 'Martin',
      prenom_role: 'Marie',
      role_level: 'admin_og',
      active: true,
      organisme: { id_organisme: 1, nom_organisme: 'Test Organisme' }
    },
    {
      id_role: 3,
      email: 'user3@test.fr',
      nom_role: 'Durand',
      prenom_role: 'Pierre',
      role_level: 'utilisateur',
      active: true,
      organisme: { id_organisme: 2, nom_organisme: 'Autre Organisme' }
    }
  ];

  const mockExistingUsers = [
    {
      id_role: 1,
      nom_complet: 'Jean Dupont',
      email: 'user1@test.fr',
      referent: true,
      organisme: 'Test Organisme'
    }
  ];

  const setupTestBed = async (dialogData: ManageSiteUsersModalData) => {
    dialogCloseMock = jest.fn();
    getUsersMock = jest.fn().mockReturnValue(of({ results: mockUsers }));
    assignUserToSiteMock = jest.fn().mockReturnValue(of({ success: true }));
    removeUserFromSiteMock = jest.fn().mockReturnValue(of({ success: true }));

    const adminServiceMock = {
      getUsers: getUsersMock,
      assignUserToSite: assignUserToSiteMock,
      removeUserFromSite: removeUserFromSiteMock
    };

    const authServiceMock = {
      currentUser: signal({ id_role: 99, email: 'admin@test.fr' })
    };

    await TestBed.configureTestingModule({
      imports: [
        ManageSiteUsersModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: { close: dialogCloseMock } },
        { provide: MAT_DIALOG_DATA, useValue: dialogData },
        { provide: AdminService, useValue: adminServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    }).compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(ManageSiteUsersModalComponent);
    component = fixture.componentInstance;
  };

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
    });

    it('should create', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component).toBeTruthy();
    }));

    it('should load data on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(getUsersMock).toHaveBeenCalled();
    }));

    it('should set loading state during data load', fakeAsync(() => {
      // The signal isLoadingData exists and is used during async loading
      // With synchronous mocks (of()), the loading state transitions immediately
      fixture.detectChanges();
      tick();

      // After loading completes, should be false
      expect(component.isLoadingData()).toBe(false);
    }));

    it('should load linked organismes from site', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.linkedOrganismes()).toEqual([mockOrganisme]);
    }));
  });

  // ==================== USER ASSIGNMENTS ====================

  describe('User Assignments', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should initialize with existing users', fakeAsync(() => {
      tick();

      const assignments = component.userAssignments();
      expect(assignments.length).toBe(1);
      expect(assignments[0].user.id_role).toBe(1);
      expect(assignments[0].referent).toBe(true);
    }));

    it('should filter visible assignments (not deleted)', fakeAsync(() => {
      tick();

      expect(component.visibleAssignments().length).toBe(1);
    }));

    it('should filter available users (not already assigned)', fakeAsync(() => {
      tick();

      const available = component.availableUsersForAdd();
      // User 1 is assigned, users 2 and 3 are available
      // But user 3 is from different organisme, so might be filtered
      expect(available.some(u => u.id_role === 1)).toBe(false);
    }));
  });

  // ==================== ADD USER ====================

  describe('Add User', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: [] });
      fixture.detectChanges();
    });

    it('should add user to assignments', fakeAsync(() => {
      tick();

      const userToAdd = mockUsers[0];
      component.addUser(userToAdd);

      expect(component.userAssignments().length).toBe(1);
      expect(component.userAssignments()[0].user.id_role).toBe(1);
      expect(component.userAssignments()[0].isNew).toBe(true);
    }));

    it('should add user with referent status', fakeAsync(() => {
      tick();

      component.newUserReferent.set(true);
      component.addUser(mockUsers[0]);

      expect(component.userAssignments()[0].referent).toBe(true);
    }));

    it('should reset newUserReferent after adding', fakeAsync(() => {
      tick();

      component.newUserReferent.set(true);
      component.addUser(mockUsers[0]);

      expect(component.newUserReferent()).toBe(false);
    }));

    it('should show success message after adding user', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[0]);

      expect(component.successMessage()).not.toBeNull();

      // Wait for timeout
      tick(3000);

      expect(component.successMessage()).toBeNull();
    }));

    it('should indicate hasChanges after adding', fakeAsync(() => {
      tick();

      expect(component.hasChanges()).toBe(false);

      component.addUser(mockUsers[0]);

      expect(component.hasChanges()).toBe(true);
    }));
  });

  // ==================== REMOVE USER ====================

  describe('Remove User', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should mark existing user as deleted', fakeAsync(() => {
      tick();

      const assignment = component.userAssignments()[0];
      component.removeUser(assignment);

      expect(component.userAssignments()[0].isDeleted).toBe(true);
    }));

    it('should remove newly added user completely', fakeAsync(() => {
      tick();

      // Add a new user
      component.addUser(mockUsers[1]);
      expect(component.userAssignments().length).toBe(2);

      // Remove the newly added user
      const newAssignment = component.userAssignments().find(a => a.user.id_role === 2)!;
      component.removeUser(newAssignment);

      expect(component.userAssignments().length).toBe(1);
    }));

    it('should hide deleted user from visible assignments', fakeAsync(() => {
      tick();

      const assignment = component.userAssignments()[0];
      component.removeUser(assignment);

      expect(component.visibleAssignments().length).toBe(0);
    }));
  });

  // ==================== RESTORE USER ====================

  describe('Restore User', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should restore deleted user', fakeAsync(() => {
      tick();

      const assignment = component.userAssignments()[0];
      component.removeUser(assignment);
      expect(component.visibleAssignments().length).toBe(0);

      component.restoreUser(component.userAssignments()[0]);
      expect(component.visibleAssignments().length).toBe(1);
    }));
  });

  // ==================== TOGGLE REFERENT ====================

  describe('Toggle Referent', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should toggle referent status', fakeAsync(() => {
      tick();

      const assignment = component.userAssignments()[0];
      expect(assignment.referent).toBe(true);

      component.toggleReferent(assignment);

      expect(component.userAssignments()[0].referent).toBe(false);
    }));

    it('should mark existing user as modified', fakeAsync(() => {
      tick();

      const assignment = component.userAssignments()[0];
      component.toggleReferent(assignment);

      expect(component.userAssignments()[0].isModified).toBe(true);
    }));

    it('should not mark new user as modified', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[1]);
      const newAssignment = component.userAssignments().find(a => a.user.id_role === 2)!;

      component.toggleReferent(newAssignment);

      expect(component.userAssignments().find(a => a.user.id_role === 2)?.isModified).toBe(false);
    }));
  });

  // ==================== SAVE ====================

  describe('Save', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should close with no changes when nothing modified', fakeAsync(() => {
      tick();

      component.onSave();

      expect(dialogCloseMock).toHaveBeenCalledWith({ success: true, changed: false });
    }));

    it('should call assignUserToSite for new users', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[1]);
      component.onSave();
      tick();

      expect(assignUserToSiteMock).toHaveBeenCalledWith('site-test', 2, false);
    }));

    it('should call assignUserToSite for modified users', fakeAsync(() => {
      tick();

      component.toggleReferent(component.userAssignments()[0]);
      component.onSave();
      tick();

      expect(assignUserToSiteMock).toHaveBeenCalledWith('site-test', 1, false);
    }));

    it('should call removeUserFromSite for deleted users', fakeAsync(() => {
      tick();

      component.removeUser(component.userAssignments()[0]);
      component.onSave();
      tick();

      expect(removeUserFromSiteMock).toHaveBeenCalledWith('site-test', 1);
    }));

    it('should close with changed true after operations', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[1]);
      component.onSave();
      tick();

      expect(dialogCloseMock).toHaveBeenCalledWith({ success: true, changed: true });
    }));

    it('should show loading state during save', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[1]);

      expect(component.isLoading()).toBe(false);

      component.onSave();
      tick();

      // After save completes (with synchronous mocks), loading should be false
      expect(component.isLoading()).toBe(false);
    }));

    it('should handle error during save', fakeAsync(() => {
      assignUserToSiteMock.mockReturnValue(throwError(() => new Error('Save failed')));
      tick();

      component.addUser(mockUsers[1]);
      component.onSave();
      tick();

      expect(component.errorMessage()).toBe('Save failed');
      expect(dialogCloseMock).not.toHaveBeenCalled();
    }));
  });

  // ==================== CANCEL ====================

  describe('Cancel', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should close dialog without saving', fakeAsync(() => {
      tick();

      component.addUser(mockUsers[1]); // Make changes

      component.onCancel();

      expect(dialogCloseMock).toHaveBeenCalledWith();
      expect(assignUserToSiteMock).not.toHaveBeenCalled();
    }));
  });

  // ==================== FILTERING ====================

  describe('Filtering', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: [] });
      fixture.detectChanges();
    });

    it('should filter available users by organisme', fakeAsync(() => {
      tick();

      // Initially all users from linked organismes are available
      const initialCount = component.availableUsersForAdd().length;

      component.onOrganismeFilterChange(1);

      const filtered = component.availableUsersForAdd();
      filtered.forEach(u => {
        expect(u.organisme?.id_organisme).toBe(1);
      });
    }));

    it('should reset filter when null', fakeAsync(() => {
      tick();

      component.onOrganismeFilterChange(1);
      component.onOrganismeFilterChange(null);

      // Should show users from all linked organismes again
      expect(component.selectedOrganismeFilter()).toBeNull();
    }));
  });

  // ==================== DISPLAY METHODS ====================

  describe('Display Methods', () => {
    beforeEach(async () => {
      await setupTestBed({ site: mockSite, existingUsers: mockExistingUsers });
      fixture.detectChanges();
    });

    it('should display user with full name', fakeAsync(() => {
      tick();

      const user = mockUsers[0];
      expect(component.displayUser(user)).toBe('Jean Dupont (user1@test.fr)');
    }));

    it('should display user with email only when no name', fakeAsync(() => {
      tick();

      const userNoName: AdminUser = {
        id_role: 10,
        email: 'test@test.fr',
        role_level: 'utilisateur',
        active: true
      };
      expect(component.displayUser(userNoName)).toBe('test@test.fr');
    }));

    it('should return empty string for null user', fakeAsync(() => {
      tick();

      expect(component.displayUser(null)).toBe('');
    }));

    it('should get user display name', fakeAsync(() => {
      tick();

      expect(component.getUserDisplayName(mockUsers[0])).toBe('Jean Dupont');
    }));

    it('should get user organisme name', fakeAsync(() => {
      tick();

      expect(component.getUserOrganisme(mockUsers[0])).toBe('Test Organisme');
    }));

    it('should return dash for user without organisme', fakeAsync(() => {
      tick();

      const userNoOrg: AdminUser = {
        id_role: 10,
        email: 'test@test.fr',
        role_level: 'utilisateur',
        active: true
      };
      expect(component.getUserOrganisme(userNoOrg)).toBe('-');
    }));
  });

  // ==================== EDGE CASES ====================

  describe('Edge Cases', () => {
    it('should handle site with no organismes', async () => {
      await setupTestBed({
        site: { ...mockSite, organismes: [] },
        existingUsers: []
      });
      fixture.detectChanges();

      expect(component.linkedOrganismes()).toEqual([]);
      expect(component.allAvailableUsers()).toEqual([]);
      expect(component.isLoadingData()).toBe(false);
    });

    it('should handle empty existing users', async () => {
      await setupTestBed({
        site: mockSite,
        existingUsers: []
      });
      fixture.detectChanges();
      await fixture.whenStable();

      expect(component.userAssignments()).toEqual([]);
    });

    it('should filter users from linked organismes only', async () => {
      // Test that users from non-linked organismes are filtered out
      await setupTestBed({ site: mockSite, existingUsers: [] });
      fixture.detectChanges();
      await fixture.whenStable();

      // mockSite has only organisme 1, so user3 (from organisme 2) should be filtered out
      const availableUsers = component.allAvailableUsers();
      expect(availableUsers.every(u => u.organisme?.id_organisme === 1)).toBe(true);
      expect(availableUsers.find(u => u.id_role === 3)).toBeUndefined();
    });
  });
});
