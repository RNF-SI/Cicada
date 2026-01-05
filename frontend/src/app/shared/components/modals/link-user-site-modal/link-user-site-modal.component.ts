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
import { AdminService } from '../../../../core/services/admin.service';
import { AdminSite, AdminUser, UserSiteRelation } from '../../../../core/models/admin.model';

// Interface for a site assignment in the modal
interface SiteAssignment {
  site: AdminSite;
  referent: boolean;
  conservateur: boolean;
  isNew?: boolean;  // true if just added, not yet saved
  isModified?: boolean;  // true if roles changed
  isDeleted?: boolean;  // true if marked for deletion
}

export interface LinkUserSiteModalData {
  user?: AdminUser; // If provided, manage sites for this user
  site?: AdminSite; // If provided, select user for this site
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
    MatIconModule
  ],
  templateUrl: './link-user-site-modal.component.html',
  styleUrl: './link-user-site-modal.component.scss'
})
export class LinkUserSiteModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<LinkUserSiteModalComponent>);
  readonly data = inject<LinkUserSiteModalData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available sites
  allSites = signal<AdminSite[]>([]);

  // Sites currently assigned to user (with modifications tracking)
  siteAssignments = signal<SiteAssignment[]>([]);

  // For select-user mode
  users = signal<AdminUser[]>([]);
  filteredUsers = signal<AdminUser[]>([]);
  userControl = new FormControl<AdminUser | string>('');
  selectedUser: AdminUser | null = null;
  isReferent = true;
  isConservateur = false;

  // For adding new site (select-site mode)
  siteControl = new FormControl<AdminSite | string>('');
  filteredSites = signal<AdminSite[]>([]);
  newSiteReferent = true;
  newSiteConservateur = false;

  get mode(): 'select-site' | 'select-user' {
    return this.data?.user ? 'select-site' : 'select-user';
  }

  get hasChanges(): boolean {
    return this.siteAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
  }

  get visibleAssignments(): SiteAssignment[] {
    return this.siteAssignments().filter(a => !a.isDeleted);
  }

  get availableSitesForAdd(): AdminSite[] {
    const assignedIds = new Set(this.siteAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.site.id_site));
    return this.allSites().filter(s => !assignedIds.has(s.id_site));
  }

  ngOnInit(): void {
    if (this.mode === 'select-site') {
      this.loadSitesAndAssignments();
      this.siteControl.valueChanges.subscribe(value => {
        this.filterAvailableSites(value);
      });
    } else {
      this.loadUsers();
      this.userControl.valueChanges.subscribe(value => {
        this.filterUsers(value);
      });
    }
  }

  private loadSitesAndAssignments(): void {
    this.isLoadingData.set(true);

    // Load all sites
    this.adminService.getSites().subscribe({
      next: (response) => {
        this.allSites.set(response.results);

        // Initialize assignments from user's existing sites
        const existingAssignments: SiteAssignment[] = (this.data.user?.sites_lies || []).map(rel => ({
          site: {
            id_site: rel.site.id_site,
            nom_site: rel.site.nom_site,
            surf_off: rel.site.surf_off,
            active: rel.site.active
          } as AdminSite,
          referent: rel.referent,
          conservateur: rel.conservateur,
          isNew: false,
          isModified: false,
          isDeleted: false
        }));

        this.siteAssignments.set(existingAssignments);
        this.filterAvailableSites('');
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private loadUsers(): void {
    this.isLoadingData.set(true);
    this.adminService.getUsers().subscribe({
      next: (response) => {
        this.users.set(response.results);
        this.filteredUsers.set(response.results);
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

  private filterUsers(value: AdminUser | string | null): void {
    if (!value) {
      this.filteredUsers.set(this.users());
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.email.toLowerCase();
    const filtered = this.users().filter(user =>
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

  // Add a new site to the list
  addSite(site: AdminSite): void {
    const assignments = [...this.siteAssignments()];
    assignments.push({
      site,
      referent: this.newSiteReferent,
      conservateur: this.newSiteConservateur,
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.siteAssignments.set(assignments);

    // Reset the form
    this.siteControl.setValue('');
    this.newSiteReferent = true;
    this.newSiteConservateur = false;
    this.filterAvailableSites('');

    this.successMessage.set(`Site "${site.nom_site}" ajoute a la liste`);
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

  // Toggle conservateur role for a site
  toggleConservateur(assignment: SiteAssignment): void {
    const assignments = [...this.siteAssignments()];
    const index = assignments.findIndex(a => a.site.id_site === assignment.site.id_site);
    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        conservateur: !assignments[index].conservateur,
        isModified: !assignments[index].isNew
      };
      this.siteAssignments.set(assignments);
    }
  }

  onUserSelected(user: AdminUser): void {
    this.selectedUser = user;
  }

  isValidForSelectUser(): boolean {
    return this.selectedUser !== null;
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
    if (!this.selectedUser || !this.data.site) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.assignUserToSite(
      this.data.site.id_site,
      this.selectedUser.id_role,
      this.isReferent,
      this.isConservateur
    ).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, changed: true });
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.message);
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
        this.adminService.removeUserFromSite(op.assignment.site.id_site, userId).subscribe({
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
            this.errorMessage.set(`Erreur lors de la suppression: ${error.message}`);
          }
        });
      } else {
        this.adminService.assignUserToSite(
          op.assignment.site.id_site,
          userId,
          op.assignment.referent,
          op.assignment.conservateur
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
            this.errorMessage.set(`Erreur: ${error.message}`);
          }
        });
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
