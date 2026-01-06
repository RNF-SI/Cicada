import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
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
  isConservateur: boolean;
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
    MatTooltipModule
  ],
  templateUrl: './admin-sites.component.html',
  styleUrl: './admin-sites.component.scss'
})
export class AdminSitesComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

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
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
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
                isReferent: user.referent || false,
                isConservateur: user.conservateur || false
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
      nbPlans: 0, // Will need to be added to API
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

    // Filter by organisme (super admin only)
    if (this.filterOrganisme) {
      result = result.filter(site => site.organismeId === parseInt(this.filterOrganisme));
    }

    // For non-super admin, only show sites from their organisme
    if (!this.isSuperAdmin()) {
      const currentOrgId = this.currentUser()?.organisme?.id;
      if (currentOrgId) {
        result = result.filter(site => site.organismeId === currentOrgId);
      }
    }

    this.filteredSites.set(result);
  }

  openAddSiteModal(): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '600px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open('Site cree avec succes', 'Fermer', { duration: 3000 });
        this.loadSites();
      }
    });
  }

  editSite(site: DisplaySite): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '600px',
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
      if (result) {
        this.snackBar.open('Site modifie avec succes', 'Fermer', { duration: 3000 });
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
      referent: u.isReferent,
      conservateur: u.isConservateur
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
        this.snackBar.open('Utilisateurs du site mis a jour', 'Fermer', { duration: 3000 });
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
        this.snackBar.open('Organismes du site mis a jour', 'Fermer', { duration: 3000 });
        this.loadSites();
      }
    });
  }

  deleteSite(site: DisplaySite): void {
    // For now, show a message - site deletion is sensitive
    this.snackBar.open('La suppression de site n\'est pas disponible ici. Utilisez l\'admin Django.', 'OK', { duration: 5000 });
  }

  // Helper methods for display
  getUserRoles(user: DisplayUserLie): string {
    const roles: string[] = [];
    if (user.isReferent) roles.push('Referent');
    if (user.isConservateur) roles.push('Conservateur');
    return roles.join(', ');
  }

  getOtherOrganismesNames(organismes: DisplayOrganismeLie[]): string {
    return organismes.slice(2).map(org => org.nom).join(', ');
  }

  getOtherUsersNames(users: DisplayUserLie[]): string {
    return users.slice(2).map(u => u.nom).join(', ');
  }
}
