import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminSite, AdminUser, UserSiteRelation } from '../../../../core/models/admin.model';

// Interface for a site assignment in the modal
interface SiteAssignment {
  site: AdminSite;
  referent: boolean;
  isNew?: boolean;  // true if just added, not yet saved
  isModified?: boolean;  // true if roles changed
  isDeleted?: boolean;  // true if marked for deletion
}

// Interface for a user assignment (when managing users for a site)
interface UserAssignment {
  user: AdminUser;
  referent: boolean;
  isNew?: boolean;
  isModified?: boolean;
  isDeleted?: boolean;
}

// Interface for existing user data passed to modal
export interface ExistingUserData {
  id_role: number;
  nom_complet?: string;
  email: string;
  referent: boolean;
}

export interface LinkUserSiteModalData {
  user?: AdminUser; // If provided, manage sites for this user
  site?: AdminSite; // If provided, manage users for this site
  existingUsers?: ExistingUserData[]; // Existing users when managing site
}

@Component({
  selector: 'app-link-user-site-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatInputModule,
    MatCheckboxModule,
    MatIconModule,
    TranslateModule
  ],
  templateUrl: './link-user-site-modal.component.html',
  styleUrl: './link-user-site-modal.component.scss'
})
export class LinkUserSiteModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly dialogRef = inject(MatDialogRef<LinkUserSiteModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<LinkUserSiteModalData>(MAT_DIALOG_DATA);

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly currentUser = this.authService.currentUser;

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available sites
  allSites = signal<AdminSite[]>([]);

  // Sites currently assigned to user (with modifications tracking)
  siteAssignments = signal<SiteAssignment[]>([]);

  // For select-user mode (managing multiple users for a site)
  allUsers = signal<AdminUser[]>([]);
  userAssignments = signal<UserAssignment[]>([]);
  userControl = new FormControl<AdminUser | string>('');
  filteredUsers = signal<AdminUser[]>([]);
  newUserReferent = true;

  // For adding new site (select-site mode)
  siteControl = new FormControl<AdminSite | string>('');
  filteredSites = signal<AdminSite[]>([]);
  newSiteReferent = true;

  get mode(): 'select-site' | 'select-user' {
    return this.data?.user ? 'select-site' : 'select-user';
  }

  get hasChanges(): boolean {
    if (this.mode === 'select-site') {
      return this.siteAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
    } else {
      return this.userAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
    }
  }

  get visibleAssignments(): SiteAssignment[] {
    return this.siteAssignments().filter(a => !a.isDeleted);
  }

  get visibleUserAssignments(): UserAssignment[] {
    return this.userAssignments().filter(a => !a.isDeleted);
  }

  get availableSitesForAdd(): AdminSite[] {
    const assignedIds = new Set(this.siteAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.site.id_site));
    return this.allSites().filter(s => !assignedIds.has(s.id_site));
  }

  get availableUsersForAdd(): AdminUser[] {
    const assignedIds = new Set(this.userAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.user.id_role));
    return this.allUsers().filter(u => !assignedIds.has(u.id_role));
  }

  ngOnInit(): void {
    if (this.mode === 'select-site') {
      this.loadSitesAndAssignments();
      this.siteControl.valueChanges.subscribe(value => {
        this.filterAvailableSites(value);
      });
    } else {
      this.loadUsersAndAssignments();
      this.userControl.valueChanges.subscribe(value => {
        this.filterAvailableUsers(value);
      });
    }
  }

  private loadSitesAndAssignments(): void {
    this.isLoadingData.set(true);

    // Filtrer par l'organisme de l'utilisateur CIBLE (pas l'admin connecte)
    // Un utilisateur ne peut etre lie qu'aux sites de son organisme
    const targetUserOrgId = this.data.user?.organisme?.id_organisme;

    if (targetUserOrgId) {
      // Charger uniquement les sites de l'organisme de l'utilisateur cible
      this.adminService.getOrganismeSites(targetUserOrgId).subscribe({
        next: (orgSites) => {
          // Map organisme sites to AdminSite format
          const sites: AdminSite[] = orgSites.map(os => ({
            id_site: os.id_site,
            nom_site: os.nom_site,
            surf_off: os.surf_off,
            type_site_label: os.type_site_label,
            active: os.active !== false
          } as AdminSite));
          this.allSites.set(sites);
          this.initSiteAssignments();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoadingData.set(false);
        }
      });
    } else {
      // L'utilisateur n'a pas d'organisme - pas de sites disponibles
      this.allSites.set([]);
      this.initSiteAssignments();
    }
  }

  private initSiteAssignments(): void {
    // Initialize assignments from user's existing sites
    const existingAssignments: SiteAssignment[] = (this.data.user?.sites_lies || []).map(rel => ({
      site: {
        id_site: rel.site.id_site,
        nom_site: rel.site.nom_site,
        surf_off: rel.site.surf_off,
        active: rel.site.active
      } as AdminSite,
      referent: rel.referent,
      isNew: false,
      isModified: false,
      isDeleted: false
    }));

    this.siteAssignments.set(existingAssignments);
    this.filterAvailableSites('');
    this.isLoadingData.set(false);
  }

  private loadUsersAndAssignments(): void {
    this.isLoadingData.set(true);

    // Recuperer les IDs des organismes gestionnaires du site
    const siteOrganismeIds = this.data.site?.organismes?.map(o => o.id_organisme) || [];

    // Charger les utilisateurs - on charge tous puis on filtre cote client
    // car l'API ne supporte pas le filtre multi-organismes
    this.adminService.getUsers({ page_size: 500 }).subscribe({
      next: (response) => {
        // Filtrer pour ne garder que les utilisateurs des organismes du site
        let filteredUsers = response.results;
        if (siteOrganismeIds.length > 0) {
          filteredUsers = response.results.filter(user =>
            user.organisme && siteOrganismeIds.includes(user.organisme.id_organisme)
          );
        }
        this.allUsers.set(filteredUsers);

        // Initialize assignments from existing users of the site
        const existingAssignments: UserAssignment[] = (this.data.existingUsers || []).map(existingUser => {
          // Try to find the full user object
          const fullUser = response.results.find(u => u.id_role === existingUser.id_role);
          return {
            user: fullUser || {
              id_role: existingUser.id_role,
              email: existingUser.email,
              nom_role: existingUser.nom_complet?.split(' ').slice(1).join(' '),
              prenom_role: existingUser.nom_complet?.split(' ')[0],
              role_level: 'utilisateur' as const,
              active: true
            },
            referent: existingUser.referent,
            isNew: false,
            isModified: false,
            isDeleted: false
          };
        });

        this.userAssignments.set(existingAssignments);
        this.filterAvailableUsers('');
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private filterAvailableSites(value: AdminSite | string | null): void {
    const available = this.availableSitesForAdd;
    if (!value) {
      this.filteredSites.set(available);
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.nom_site.toLowerCase();
    const filtered = available.filter(site =>
      site.nom_site.toLowerCase().includes(query) ||
      (site.id_local?.toLowerCase().includes(query) || '')
    );
    this.filteredSites.set(filtered);
  }

  private filterAvailableUsers(value: AdminUser | string | null): void {
    const available = this.availableUsersForAdd;
    if (!value) {
      this.filteredUsers.set(available);
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.email.toLowerCase();
    const filtered = available.filter(user =>
      (user.nom_role?.toLowerCase().includes(query) || false) ||
      (user.prenom_role?.toLowerCase().includes(query) || false) ||
      user.email.toLowerCase().includes(query)
    );
    this.filteredUsers.set(filtered);
  }

  displaySite(site: AdminSite | null): string {
    if (!site) return '';
    let name = site.nom_site;
    if (site.type_site_label) {
      name += ` (${site.type_site_label})`;
    }
    return name;
  }

  displayUser(user: AdminUser | null): string {
    if (!user) return '';
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role} (${user.email})`;
    }
    return user.email;
  }

  // Add a new user to the list
  addUser(user: AdminUser): void {
    const assignments = [...this.userAssignments()];
    assignments.push({
      user,
      referent: this.newUserReferent,
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.userAssignments.set(assignments);

    // Reset the form
    this.userControl.setValue('');
    this.newUserReferent = true;
    this.filterAvailableUsers('');

    const userName = user.prenom_role && user.nom_role
      ? `${user.prenom_role} ${user.nom_role}`
      : user.email;
    this.successMessage.set(this.translate.instant('modals.linkUserSite.messages.userAdded', { name: userName }));
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Remove a user from the list
  removeUser(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      if (assignment.isNew) {
        // Just remove it from the list
        assignments.splice(index, 1);
      } else {
        // Mark for deletion
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.userAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Restore a user marked for deletion
  restoreUser(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.userAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Toggle referent role for a user
  toggleUserReferent(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);
    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        referent: !assignments[index].referent,
        isModified: !assignments[index].isNew
      };
      this.userAssignments.set(assignments);
    }
  }

  getUserDisplayName(user: AdminUser): string {
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  // Add a new site to the list
  addSite(site: AdminSite): void {
    const assignments = [...this.siteAssignments()];
    assignments.push({
      site,
      referent: this.newSiteReferent,
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.siteAssignments.set(assignments);

    // Reset the form
    this.siteControl.setValue('');
    this.newSiteReferent = true;
    this.filterAvailableSites('');

    this.successMessage.set(this.translate.instant('modals.linkUserSite.messages.siteAdded', { name: site.nom_site }));
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Remove a site from the list
  removeSite(assignment: SiteAssignment): void {
    const assignments = [...this.siteAssignments()];
    const index = assignments.findIndex(a => a.site.id_site === assignment.site.id_site);

    if (index >= 0) {
      if (assignment.isNew) {
        // Just remove it from the list
        assignments.splice(index, 1);
      } else {
        // Mark for deletion
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.siteAssignments.set(assignments);
      this.filterAvailableSites(this.siteControl.value);
    }
  }

  // Restore a site marked for deletion
  restoreSite(assignment: SiteAssignment): void {
    const assignments = [...this.siteAssignments()];
    const index = assignments.findIndex(a => a.site.id_site === assignment.site.id_site);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.siteAssignments.set(assignments);
      this.filterAvailableSites(this.siteControl.value);
    }
  }

  // Toggle referent role for a site
  toggleReferent(assignment: SiteAssignment): void {
    const assignments = [...this.siteAssignments()];
    const index = assignments.findIndex(a => a.site.id_site === assignment.site.id_site);
    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        referent: !assignments[index].referent,
        isModified: !assignments[index].isNew
      };
      this.siteAssignments.set(assignments);
    }
  }

  // Save all changes
  onSave(): void {
    if (this.mode === 'select-user') {
      this.saveSelectUser();
    } else {
      this.saveSelectSite();
    }
  }

  private saveSelectUser(): void {
    if (!this.data.site) return;

    const siteSlug = this.data.site.slug;
    const toAdd = this.userAssignments().filter(a => a.isNew && !a.isDeleted);
    const toUpdate = this.userAssignments().filter(a => a.isModified && !a.isNew && !a.isDeleted);
    const toDelete = this.userAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toUpdate.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process all operations
    this.processUserOperations(siteSlug, toAdd, toUpdate, toDelete);
  }

  private processUserOperations(
    siteSlug: string,
    toAdd: UserAssignment[],
    toUpdate: UserAssignment[],
    toDelete: UserAssignment[]
  ): void {
    const allOperations = [
      ...toAdd.map(a => ({ type: 'add' as const, assignment: a })),
      ...toUpdate.map(a => ({ type: 'update' as const, assignment: a })),
      ...toDelete.map(a => ({ type: 'delete' as const, assignment: a }))
    ];

    if (allOperations.length === 0) {
      this.isLoading.set(false);
      this.dialogRef.close({ success: true, changed: true });
      return;
    }

    let completed = 0;
    let hasError = false;

    allOperations.forEach(op => {
      if (op.type === 'delete') {
        this.adminService.removeUserFromSite(siteSlug, op.assignment.user.id_role).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(this.translate.instant('modals.linkUserSite.messages.removeError', { error: error.message }));
          }
        });
      } else {
        this.adminService.assignUserToSite(
          siteSlug,
          op.assignment.user.id_role,
          op.assignment.referent
        ).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(this.translate.instant('modals.linkUserSite.messages.error', { error: error.message }));
          }
        });
      }
    });
  }

  private saveSelectSite(): void {
    if (!this.data.user) return;

    const userId = this.data.user.id_role;
    const toAdd = this.siteAssignments().filter(a => a.isNew && !a.isDeleted);
    const toUpdate = this.siteAssignments().filter(a => a.isModified && !a.isNew && !a.isDeleted);
    const toDelete = this.siteAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toUpdate.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process all operations sequentially
    this.processOperations(userId, toAdd, toUpdate, toDelete);
  }

  private processOperations(
    userId: number,
    toAdd: SiteAssignment[],
    toUpdate: SiteAssignment[],
    toDelete: SiteAssignment[]
  ): void {
    const allOperations = [
      ...toAdd.map(a => ({ type: 'add' as const, assignment: a })),
      ...toUpdate.map(a => ({ type: 'update' as const, assignment: a })),
      ...toDelete.map(a => ({ type: 'delete' as const, assignment: a }))
    ];

    if (allOperations.length === 0) {
      this.isLoading.set(false);
      this.dialogRef.close({ success: true, changed: true });
      return;
    }

    let completed = 0;
    let hasError = false;

    allOperations.forEach(op => {
      if (op.type === 'delete') {
        this.adminService.removeUserFromSite(op.assignment.site.slug, userId).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(this.translate.instant('modals.linkUserSite.messages.removeError', { error: error.message }));
          }
        });
      } else {
        this.adminService.assignUserToSite(
          op.assignment.site.slug,
          userId,
          op.assignment.referent
        ).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(this.translate.instant('modals.linkUserSite.messages.error', { error: error.message }));
          }
        });
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
