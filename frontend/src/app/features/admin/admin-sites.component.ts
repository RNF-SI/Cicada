import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminSite as ApiSite, AdminOrganisme } from '../../core/models/admin.model';
import {
  LinkUserSiteModalComponent,
  LinkSiteOrganismeModalComponent,
  SiteFormModalComponent
} from '../../shared/components/modals';

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
    MatProgressSpinnerModule
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
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
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
      isActive: site.active ?? true
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
    const dialogRef = this.dialog.open(LinkUserSiteModalComponent, {
      width: '550px',
      data: {
        site: {
          id: site.id,
          nom_site: site.nom,
          type_site_label: site.type
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open('Referent ajoute au site', 'Fermer', { duration: 3000 });
        this.loadSites();
      }
    });
  }

  openAssignOrganismeModal(site: DisplaySite): void {
    const dialogRef = this.dialog.open(LinkSiteOrganismeModalComponent, {
      width: '550px',
      data: {
        site: {
          id: site.id,
          nom_site: site.nom,
          type_site_label: site.type
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open('Site associe a l\'organisme', 'Fermer', { duration: 3000 });
        this.loadSites();
      }
    });
  }

  viewOnMap(site: DisplaySite): void {
    // TODO: Navigate to map view centered on site
    this.snackBar.open('Vue carte non disponible pour le moment', 'OK', { duration: 3000 });
  }

  deleteSite(site: DisplaySite): void {
    // For now, show a message - site deletion is sensitive
    this.snackBar.open('La suppression de site n\'est pas disponible ici. Utilisez l\'admin Django.', 'OK', { duration: 5000 });
  }
}
