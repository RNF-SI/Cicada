import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminSite as ApiSite, AdminOrganisme } from '../../core/models/admin.model';
import {
  LinkUserSiteModalComponent,
  LinkSiteOrganismeModalComponent,
  SiteFormModalComponent,
  ExistingUserData,
  ExistingOrganismeData
} from '../../shared/components/modals';

// Interface for linked organisme display
interface DisplayOrganismeLie {
  id: number;
  nom: string;
  principal: boolean;
}

// Interface for linked user display
interface DisplayUserLie {
  id: number;
  nom: string;
  email: string;
  isReferent: boolean;
}

// Interface for display (mapping from API model)
interface DisplaySite {
  id: number;
  nom: string;
  type: string;
  organisme: string;
  organismeId: number;
  surface?: number;
  commune?: string;
  departement?: string;
  nbPlans: number;
  isActive: boolean;
  organismes: DisplayOrganismeLie[];
  users: DisplayUserLie[];
}

interface DisplayOrganisme {
  id: number;
  nom: string;
}

@Component({
  selector: 'app-admin-sites',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule
  ],
  templateUrl: './admin-sites.component.html',
  styleUrl: './admin-sites.component.scss'
})
export class AdminSitesComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Filter state
  searchQuery = '';
  filterType = '';
  filterOrganisme = '';
  isLoading = signal(false);

  sites = signal<DisplaySite[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);
  filteredSites = signal<DisplaySite[]>([]);

  currentOrganismeName = computed(() => {
    return this.currentUser()?.organisme?.nom_organisme || '';
  });

  totalSurface = computed(() => {
    return this.filteredSites().reduce((sum, site) => sum + (site.surface || 0), 0);
  });

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);

    // Load organismes first (for filter dropdown)
    this.adminService.getOrganismes().subscribe({
      next: (response) => {
        this.organismes.set(response.results.map(org => ({
          id: org.id_organisme,
          nom: org.nom_organisme
        })));
      }
    });

    // Load sites
    this.loadSites();
  }

  loadSites(): void {
    this.isLoading.set(true);
    this.adminService.getSites({ search: this.searchQuery || undefined }).subscribe({
      next: (response) => {
        const mapped = response.results.map(site => this.mapSite(site));
        this.sites.set(mapped);
        this.applyFilters();

        // Load related data for each site
        this.loadRelatedDataForSites(mapped);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  private loadRelatedDataForSites(sites: DisplaySite[]): void {
    if (sites.length === 0) {
      this.isLoading.set(false);
      return;
    }

    // Create observables for all sites
    const observables = sites.map(site =>
      forkJoin({
        siteId: of(site.id),
        organismes: this.adminService.getSiteOrganismes(site.id).pipe(
          catchError(() => of([]))
        ),
        users: this.adminService.getSiteUsers(site.id).pipe(
          catchError(() => of([]))
        )
      })
    );

    forkJoin(observables).subscribe({
      next: (results) => {
        const currentSites = [...this.sites()];

        results.forEach(result => {
          const siteIndex = currentSites.findIndex(s => s.id === result.siteId);
          if (siteIndex >= 0) {
            currentSites[siteIndex] = {
              ...currentSites[siteIndex],
              organismes: result.organismes.map((org: any) => ({
                id: org.id_organisme,
                nom: org.nom_organisme,
                principal: org.principal || false
              })),
              users: result.users.map((user: any) => ({
                id: user.id_role,
                nom: user.nom_complet || user.email,
                email: user.email,
                isReferent: user.referent || false
              }))
            };
          }
        });

        this.sites.set(currentSites);
        this.applyFilters();
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  private mapSite(site: ApiSite): DisplaySite {
    return {
      id: site.id_site,
      nom: site.nom_site,
      type: site.type_site_label || 'N/A',
      organisme: site.organismes?.[0]?.nom_organisme || 'Non assigne',
      organismeId: site.organismes?.[0]?.id_organisme || 0,
      surface: site.surf_off,
      commune: undefined, // Will need to be added to API if needed
      departement: undefined,
      nbPlans: site.plans_count ?? 0,
      isActive: site.active ?? true,
      organismes: [],
      users: []
    };
  }

  filterSites(): void {
    this.applyFilters();
  }

  private applyFilters(): void {
    let result = this.sites();

    // Filter by search query
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      result = result.filter(site =>
        site.nom.toLowerCase().includes(query) ||
        site.commune?.toLowerCase().includes(query)
      );
    }

    // Filter by type
    if (this.filterType) {
      result = result.filter(site => site.type === this.filterType);
    }

    // Filter by organisme (super admin filter dropdown)
    if (this.filterOrganisme) {
      const filterOrgId = parseInt(this.filterOrganisme);
      result = result.filter(site =>
        site.organismeId === filterOrgId ||
        site.organismes.some(org => org.id === filterOrgId)
      );
    }

    // For admin_og (not super_admin), filter by their organisme
    // Note: The backend already filters sites, but this ensures consistency
    // For referents (is_referent && niveau_role === 'utilisateur'), the backend
    // returns only their assigned sites, so no additional filtering needed
    if (!this.isSuperAdmin() && this.isAdminOrganisme()) {
      const currentOrgId = this.currentUser()?.organisme?.id_organisme;
      if (currentOrgId) {
        result = result.filter(site =>
          site.organismeId === currentOrgId ||
          site.organismes.some(org => org.id === currentOrgId)
        );
      }
    }

    this.filteredSites.set(result);
  }

  openAddSiteModal(): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.site) {
        if (result.validationPending) {
          this.snackBar.open(
            result.message || this.translate.instant('sites.createSite.pendingValidation'),
            this.translate.instant('common.actions.close'),
            { duration: 8000 }
          );
        } else {
          this.snackBar.open(this.translate.instant('admin.sites.messages.created'), this.translate.instant('common.actions.close'), { duration: 3000 });
        }
        this.loadSites();
      }
    });
  }

  editSite(site: DisplaySite): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        site: {
          id_site: site.id,
          nom_site: site.nom,
          id_type_site: null, // We would need to store this in DisplaySite
          surf_off: site.surface,
          active: site.isActive
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.site) {
        this.snackBar.open(this.translate.instant('admin.sites.messages.updated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadSites();
      }
    });
  }

  openAddReferentModal(site: DisplaySite): void {
    // Convert existing users to the format expected by the modal
    const existingUsers: ExistingUserData[] = site.users.map(u => ({
      id_role: u.id,
      nom_complet: u.nom,
      email: u.email,
      referent: u.isReferent
    }));

    const dialogRef = this.dialog.open(LinkUserSiteModalComponent, {
      width: '600px',
      data: {
        site: {
          id_site: site.id,
          nom_site: site.nom,
          type_site_label: site.type
        },
        existingUsers
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success && result?.changed) {
        this.snackBar.open(this.translate.instant('admin.sites.messages.usersUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadSites();
      }
    });
  }

  openAssignOrganismeModal(site: DisplaySite): void {
    // Convert existing organismes to the format expected by the modal
    const existingOrganismes: ExistingOrganismeData[] = site.organismes.map(o => ({
      id_organisme: o.id,
      nom_organisme: o.nom,
      principal: o.principal
    }));

    const dialogRef = this.dialog.open(LinkSiteOrganismeModalComponent, {
      width: '600px',
      data: {
        site: {
          id_site: site.id,
          nom_site: site.nom,
          type_site_label: site.type
        },
        existingOrganismes
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success && result?.changed) {
        this.snackBar.open(this.translate.instant('admin.sites.messages.organismesUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadSites();
      }
    });
  }

  deleteSite(site: DisplaySite): void {
    // For now, show a message - site deletion is sensitive
    this.snackBar.open(this.translate.instant('admin.sites.messages.deletionNotAvailable'), 'OK', { duration: 5000 });
  }

  // Helper methods for display
  getUserRoles(user: DisplayUserLie): string {
    return user.isReferent ? 'Referent' : '';
  }

  getOtherOrganismesNames(organismes: DisplayOrganismeLie[]): string {
    return organismes.slice(2).map(org => org.nom).join(', ');
  }

  getOtherUsersNames(users: DisplayUserLie[]): string {
    return users.slice(2).map(u => u.nom).join(', ');
  }
}
