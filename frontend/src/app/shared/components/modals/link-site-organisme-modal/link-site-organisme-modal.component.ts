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
import { AdminOrganisme, AdminSite, OrganismeSite } from '../../../../core/models/admin.model';

// Interface for a site assignment in the modal
interface SiteAssignment {
  site: AdminSite;
  principal: boolean;
  isNew?: boolean;  // true if just added, not yet saved
  isModified?: boolean;  // true if principal changed
  isDeleted?: boolean;  // true if marked for deletion
}

// Interface for an organisme assignment (when managing organismes for a site)
interface OrganismeAssignment {
  organisme: AdminOrganisme;
  principal: boolean;
  isNew?: boolean;
  isModified?: boolean;
  isDeleted?: boolean;
}

// Interface for existing organisme data passed to modal
export interface ExistingOrganismeData {
  id_organisme: number;
  nom_organisme: string;
  ville_organisme?: string;
  principal: boolean;
}

export interface LinkSiteOrganismeModalData {
  site?: AdminSite; // If provided, manage organismes for this site
  organisme?: AdminOrganisme; // If provided, manage sites for this organisme
  existingOrganismes?: ExistingOrganismeData[]; // Existing organismes when managing site
}

@Component({
  selector: 'app-link-site-organisme-modal',
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
  templateUrl: './link-site-organisme-modal.component.html',
  styleUrl: './link-site-organisme-modal.component.scss'
})
export class LinkSiteOrganismeModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<LinkSiteOrganismeModalComponent>);
  readonly data = inject<LinkSiteOrganismeModalData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available sites
  allSites = signal<AdminSite[]>([]);

  // Sites currently assigned to organisme (with modifications tracking)
  siteAssignments = signal<SiteAssignment[]>([]);

  // For select-organisme mode (managing multiple organismes for a site)
  allOrganismes = signal<AdminOrganisme[]>([]);
  organismeAssignments = signal<OrganismeAssignment[]>([]);
  organismeControl = new FormControl<AdminOrganisme | string>('');
  filteredOrganismes = signal<AdminOrganisme[]>([]);
  newOrganismePrincipal = false;

  // For adding new site (select-site mode)
  siteControl = new FormControl<AdminSite | string>('');
  filteredSites = signal<AdminSite[]>([]);
  newSitePrincipal = false;

  get mode(): 'select-organisme' | 'select-site' {
    return this.data?.site ? 'select-organisme' : 'select-site';
  }

  get hasChanges(): boolean {
    if (this.mode === 'select-site') {
      return this.siteAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
    } else {
      return this.organismeAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
    }
  }

  get visibleAssignments(): SiteAssignment[] {
    return this.siteAssignments().filter(a => !a.isDeleted);
  }

  get visibleOrganismeAssignments(): OrganismeAssignment[] {
    return this.organismeAssignments().filter(a => !a.isDeleted);
  }

  get availableSitesForAdd(): AdminSite[] {
    const assignedIds = new Set(this.siteAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.site.id_site));
    return this.allSites().filter(s => !assignedIds.has(s.id_site));
  }

  get availableOrganismesForAdd(): AdminOrganisme[] {
    const assignedIds = new Set(this.organismeAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.organisme.id_organisme));
    return this.allOrganismes().filter(o => !assignedIds.has(o.id_organisme));
  }

  ngOnInit(): void {
    if (this.mode === 'select-site') {
      this.loadSitesAndAssignments();
      this.siteControl.valueChanges.subscribe(value => {
        this.filterAvailableSites(value);
      });
    } else {
      this.loadOrganismesAndAssignments();
      this.organismeControl.valueChanges.subscribe(value => {
        this.filterAvailableOrganismes(value);
      });
    }
  }

  private loadSitesAndAssignments(): void {
    this.isLoadingData.set(true);

    // Load all sites available for assignment (no organisme filtering)
    this.adminService.getSitesAvailableForAssignment().subscribe({
      next: (response) => {
        this.allSites.set(response.results);

        // Load existing assignments from organisme
        if (this.data.organisme?.id_organisme) {
          this.adminService.getOrganismeSites(this.data.organisme.id_organisme).subscribe({
            next: (sites) => {
              const existingAssignments: SiteAssignment[] = sites.map(orgSite => ({
                site: {
                  id_site: orgSite.id_site,
                  nom_site: orgSite.nom_site,
                  surf_off: orgSite.surf_off,
                  type_site_label: orgSite.type_site,
                  active: orgSite.active
                } as AdminSite,
                principal: orgSite.principal || false,
                isNew: false,
                isModified: false,
                isDeleted: false
              }));

              this.siteAssignments.set(existingAssignments);
              this.filterAvailableSites('');
              this.isLoadingData.set(false);
            },
            error: (error: Error) => {
              // If no sites yet, that's OK
              this.siteAssignments.set([]);
              this.filterAvailableSites('');
              this.isLoadingData.set(false);
            }
          });
        } else {
          this.filterAvailableSites('');
          this.isLoadingData.set(false);
        }
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private loadOrganismesAndAssignments(): void {
    this.isLoadingData.set(true);

    // Load all organismes
    this.adminService.getOrganismes().subscribe({
      next: (response) => {
        this.allOrganismes.set(response.results);

        // Initialize assignments from existing organismes of the site
        const existingAssignments: OrganismeAssignment[] = (this.data.existingOrganismes || []).map(existingOrg => {
          // Try to find the full organisme object
          const fullOrg = response.results.find(o => o.id_organisme === existingOrg.id_organisme);
          return {
            organisme: fullOrg || {
              id_organisme: existingOrg.id_organisme,
              nom_organisme: existingOrg.nom_organisme,
              ville_organisme: existingOrg.ville_organisme,
              active: true
            } as AdminOrganisme,
            principal: existingOrg.principal,
            isNew: false,
            isModified: false,
            isDeleted: false
          };
        });

        this.organismeAssignments.set(existingAssignments);
        this.filterAvailableOrganismes('');
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

  private filterAvailableOrganismes(value: AdminOrganisme | string | null): void {
    const available = this.availableOrganismesForAdd;
    if (!value) {
      this.filteredOrganismes.set(available);
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.nom_organisme.toLowerCase();
    const filtered = available.filter(org =>
      org.nom_organisme.toLowerCase().includes(query) ||
      (org.ville_organisme?.toLowerCase().includes(query) || '')
    );
    this.filteredOrganismes.set(filtered);
  }

  displaySite(site: AdminSite | null): string {
    if (!site) return '';
    let name = site.nom_site;
    if (site.type_site_label) {
      name += ` (${site.type_site_label})`;
    }
    return name;
  }

  displayOrganisme(org: AdminOrganisme | null): string {
    if (!org) return '';
    let name = org.nom_organisme;
    if (org.ville_organisme) {
      name += ` (${org.ville_organisme})`;
    }
    return name;
  }

  // Add a new organisme to the list
  addOrganisme(org: AdminOrganisme): void {
    const assignments = [...this.organismeAssignments()];
    assignments.push({
      organisme: org,
      principal: this.newOrganismePrincipal,
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.organismeAssignments.set(assignments);

    // Reset the form
    this.organismeControl.setValue('');
    this.newOrganismePrincipal = false;
    this.filterAvailableOrganismes('');

    this.successMessage.set(`Organisme "${org.nom_organisme}" ajoute a la liste`);
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Remove an organisme from the list
  removeOrganisme(assignment: OrganismeAssignment): void {
    const assignments = [...this.organismeAssignments()];
    const index = assignments.findIndex(a => a.organisme.id_organisme === assignment.organisme.id_organisme);

    if (index >= 0) {
      if (assignment.isNew) {
        // Just remove it from the list
        assignments.splice(index, 1);
      } else {
        // Mark for deletion
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.organismeAssignments.set(assignments);
      this.filterAvailableOrganismes(this.organismeControl.value);
    }
  }

  // Restore an organisme marked for deletion
  restoreOrganisme(assignment: OrganismeAssignment): void {
    const assignments = [...this.organismeAssignments()];
    const index = assignments.findIndex(a => a.organisme.id_organisme === assignment.organisme.id_organisme);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.organismeAssignments.set(assignments);
      this.filterAvailableOrganismes(this.organismeControl.value);
    }
  }

  // Toggle principal for an organisme
  toggleOrganismePrincipal(assignment: OrganismeAssignment): void {
    const assignments = [...this.organismeAssignments()];
    const index = assignments.findIndex(a => a.organisme.id_organisme === assignment.organisme.id_organisme);
    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        principal: !assignments[index].principal,
        isModified: !assignments[index].isNew
      };
      this.organismeAssignments.set(assignments);
    }
  }

  // Add a new site to the list
  addSite(site: AdminSite): void {
    const assignments = [...this.siteAssignments()];
    assignments.push({
      site,
      principal: this.newSitePrincipal,
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.siteAssignments.set(assignments);

    // Reset the form
    this.siteControl.setValue('');
    this.newSitePrincipal = false;
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

  // Toggle principal for a site
  togglePrincipal(assignment: SiteAssignment): void {
    const assignments = [...this.siteAssignments()];
    const index = assignments.findIndex(a => a.site.id_site === assignment.site.id_site);
    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        principal: !assignments[index].principal,
        isModified: !assignments[index].isNew
      };
      this.siteAssignments.set(assignments);
    }
  }

  // Save all changes
  onSave(): void {
    if (this.mode === 'select-organisme') {
      this.saveSelectOrganisme();
    } else {
      this.saveSelectSite();
    }
  }

  private saveSelectOrganisme(): void {
    if (!this.data.site) return;

    const siteId = this.data.site.id_site;
    const toAdd = this.organismeAssignments().filter(a => a.isNew && !a.isDeleted);
    const toUpdate = this.organismeAssignments().filter(a => a.isModified && !a.isNew && !a.isDeleted);
    const toDelete = this.organismeAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toUpdate.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process all operations
    this.processOrganismeOperations(siteId, toAdd, toUpdate, toDelete);
  }

  private processOrganismeOperations(
    siteId: number,
    toAdd: OrganismeAssignment[],
    toUpdate: OrganismeAssignment[],
    toDelete: OrganismeAssignment[]
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
        this.adminService.removeSiteFromOrganisme(op.assignment.organisme.id_organisme, siteId).subscribe({
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
        this.adminService.assignSiteToOrganisme(
          op.assignment.organisme.id_organisme,
          siteId,
          op.assignment.principal
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

  private saveSelectSite(): void {
    if (!this.data.organisme) return;

    const organismeId = this.data.organisme.id_organisme;
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
    this.processOperations(organismeId, toAdd, toUpdate, toDelete);
  }

  private processOperations(
    organismeId: number,
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
        this.adminService.removeSiteFromOrganisme(organismeId, op.assignment.site.id_site).subscribe({
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
        this.adminService.assignSiteToOrganisme(
          organismeId,
          op.assignment.site.id_site,
          op.assignment.principal
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
