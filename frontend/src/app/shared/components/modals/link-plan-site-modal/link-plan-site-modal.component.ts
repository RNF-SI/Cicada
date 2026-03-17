import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ValidationService } from '../../../../core/services/validation.service';
import { AdminSite } from '../../../../core/models/admin.model';
import { SiteTypeDisplayPipe } from '../../../pipes/site-type-display.pipe';
import { forkJoin } from 'rxjs';

// Interface for site linked to plan
interface PlanSiteInfo {
  id_site: number;
  nom_site: string;
  type_site_label?: string;
  type_site_precision?: string | null;
  rang?: number;
}

// Interface for a site assignment in the modal
interface SiteAssignment {
  site: PlanSiteInfo;
  isNew?: boolean;
  isDeleted?: boolean;
}

export interface LinkPlanSiteModalData {
  plan: {
    id_pg: number;
    nom: string;
    sites?: PlanSiteInfo[];
  };
}

@Component({
  selector: 'app-link-plan-site-modal',
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
    MatIconModule,
    TranslateModule,
    SiteTypeDisplayPipe
  ],
  templateUrl: './link-plan-site-modal.component.html',
  styleUrl: './link-plan-site-modal.component.scss'
})
export class LinkPlanSiteModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly validationService = inject(ValidationService);
  private readonly dialogRef = inject(MatDialogRef<LinkPlanSiteModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<LinkPlanSiteModalData>(MAT_DIALOG_DATA);

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;
  readonly currentUser = this.authService.currentUser;

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available sites
  allSites = signal<AdminSite[]>([]);

  // Sites currently assigned to plan (with modifications tracking)
  siteAssignments = signal<SiteAssignment[]>([]);

  // For adding new site
  siteControl = new FormControl<AdminSite | string>('');
  filteredSites = signal<AdminSite[]>([]);

  get hasChanges(): boolean {
    return this.siteAssignments().some(a => a.isNew || a.isDeleted);
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
    this.loadSitesAndAssignments();
    this.siteControl.valueChanges.subscribe(value => {
      this.filterAvailableSites(value);
    });
  }

  private loadSitesAndAssignments(): void {
    this.isLoadingData.set(true);

    const currentOrgId = this.currentUser()?.organisme?.id_organisme;
    const filterByOrg = !this.isSuperAdmin() && this.isAdminOrganisme() && currentOrgId;

    // Load sites - if admin_org, only load sites from their organisme
    if (filterByOrg) {
      this.adminService.getOrganismeSites(currentOrgId!).subscribe({
        next: (orgSites) => {
          const sites: AdminSite[] = orgSites.map(os => ({
            id_site: os.id_site,
            nom_site: os.nom_site,
            surf_off: os.surf_off,
            active: true
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
      // Super admin: load all sites
      this.adminService.getSites({ page_size: 500 }).subscribe({
        next: (response) => {
          this.allSites.set(response.results);
          this.initSiteAssignments();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isLoadingData.set(false);
        }
      });
    }
  }

  private initSiteAssignments(): void {
    // Initialize assignments from plan's existing sites
    const existingAssignments: SiteAssignment[] = (this.data.plan.sites || []).map(site => ({
      site: {
        id_site: site.id_site,
        nom_site: site.nom_site,
        type_site_label: site.type_site_label,
        rang: site.rang
      },
      isNew: false,
      isDeleted: false
    }));

    this.siteAssignments.set(existingAssignments);
    this.filterAvailableSites('');
    this.isLoadingData.set(false);
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

  displaySite(site: AdminSite | null): string {
    if (!site) return '';
    let name = site.nom_site;
    if (site.type_site_label) {
      name += ` (${site.type_site_label})`;
    }
    return name;
  }

  // Add a new site to the list
  addSite(site: AdminSite): void {
    const assignments = [...this.siteAssignments()];
    assignments.push({
      site: {
        id_site: site.id_site,
        nom_site: site.nom_site,
        type_site_label: site.type_site_label
      },
      isNew: true,
      isDeleted: false
    });
    this.siteAssignments.set(assignments);

    // Reset the form
    this.siteControl.setValue('');
    this.filterAvailableSites('');

    this.successMessage.set(this.translate.instant('modals.linkPlanSite.messages.siteAdded', { name: site.nom_site }));
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

  // Save all changes
  onSave(): void {
    const planId = this.data.plan.id_pg;
    const toAdd = this.siteAssignments().filter(a => a.isNew && !a.isDeleted);
    const toDelete = this.siteAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process operations
    this.processOperations(planId, toAdd, toDelete);
  }

  private processOperations(
    planId: number,
    toAdd: SiteAssignment[],
    toDelete: SiteAssignment[]
  ): void {
    const totalOperations = toAdd.length + toDelete.length;

    if (totalOperations === 0) {
      this.isLoading.set(false);
      this.dialogRef.close({ success: true, changed: true });
      return;
    }

    // Build all observables
    const addObservables = toAdd.map(a =>
      this.validationService.requestPlanSiteLink(planId, a.site.id_site)
    );
    const deleteObservables = toDelete.map(a =>
      this.adminService.removeSiteFromPlan(planId, a.site.id_site)
    );

    const allObservables = [...addObservables, ...deleteObservables];

    forkJoin(allObservables).subscribe({
      next: (results) => {
        this.isLoading.set(false);

        // Check add results for direct vs validation
        const addResults = results.slice(0, addObservables.length);
        const hasPending = addResults.some((r: any) => r.direct === false);
        const hasDirect = addResults.some((r: any) => r.direct === true);

        let message = '';
        if (hasDirect && hasPending) {
          message = this.translate.instant('plans.detail.siteLinkMixed');
        } else if (hasPending) {
          message = this.translate.instant('plans.detail.siteLinkRequested');
        } else if (hasDirect) {
          message = this.translate.instant('plans.detail.siteLinkDirect');
        }

        this.dialogRef.close({ success: true, changed: true, message, hasPending });
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(this.translate.instant('modals.linkPlanSite.messages.addError', { error: error.message }));
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
