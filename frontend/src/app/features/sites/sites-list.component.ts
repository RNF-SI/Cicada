/**
 * Composant pour la page "Mes sites".
 * Affiche les sites avec hero section, carte Leaflet, tableau et pagination.
 * Design inspiré de plans-list.component.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminSite, GeoJSONFeatureCollection } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AccessRequestDialogComponent, AccessRequestDialogData, SelectableSite } from '../../shared/components/access-request-dialog/access-request-dialog.component';
import { SiteFormModalComponent, SiteFormModalData } from '../../shared/components/modals/site-form-modal/site-form-modal.component';
import { FindOrCreateSiteModalComponent } from '../../shared/components/modals/find-or-create-site-modal/find-or-create-site-modal.component';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { LeafletMapComponent } from '../../shared/components/leaflet-map/leaflet-map.component';

interface SiteUserRelation {
  id_role: number;
  email?: string;
  nom_role?: string;
  prenom_role?: string;
  referent?: boolean;
}

interface SiteWithUsers extends Omit<AdminSite, 'users'> {
  users?: SiteUserRelation[];
}

interface SiteWithAccess extends SiteWithUsers {
  accessStatus: 'granted' | 'pending' | 'rejected' | 'none';
  isReferent: boolean;
}

@Component({
  selector: 'app-sites-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    LeafletMapComponent
  ],
  templateUrl: './sites-list.component.html',
  styleUrl: './sites-list.component.scss'
})
export class SitesListComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);

  // Donnees
  readonly allSites = signal<SiteWithAccess[]>([]);
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly mapData = signal<GeoJSONFeatureCollection | null>(null);
  readonly loading = signal(false);

  // Recherche
  readonly searchTerm = signal('');

  // Pagination
  readonly currentPage = signal(1);
  readonly pageSize = 10;

  // Colonnes du tableau
  readonly tableColumns = ['name', 'type', 'surface', 'organisme', 'status', 'actions'];

  // Sites auxquels l'utilisateur a acces
  readonly mySites = computed(() => {
    return this.allSites().filter(s => s.accessStatus === 'granted');
  });

  // Sites en attente de validation (demandes pending)
  readonly pendingSites = computed(() => {
    return this.allSites().filter(s => s.accessStatus === 'pending');
  });

  // Sites affiches (filtrés par recherche)
  readonly displayedMySites = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const sites = this.mySites();

    if (!term) return sites;

    return sites.filter(site =>
      site.nom_site.toLowerCase().includes(term) ||
      site.type_site_label?.toLowerCase().includes(term) ||
      site.organismes?.some(o => o.nom_organisme.toLowerCase().includes(term))
    );
  });

  // Pagination pour mes sites
  readonly paginatedMySites = computed(() => {
    const sites = this.displayedMySites();
    const start = (this.currentPage() - 1) * this.pageSize;
    const end = start + this.pageSize;
    return sites.slice(start, end);
  });

  readonly totalPages = computed(() => {
    return Math.ceil(this.displayedMySites().length / this.pageSize) || 1;
  });

  readonly paginationPages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) pages.push(i);
    } else {
      pages.push(1);
      if (current > 3) pages.push('...');
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(i);
      }
      if (current < total - 2) pages.push('...');
      pages.push(total);
    }

    return pages;
  });

  // Sites disponibles pour demande d'acces (de l'organisme de l'utilisateur, sans acces)
  readonly availableSitesForRequest = computed((): SelectableSite[] => {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) return [];

    const userOrgId = currentUser.organisme.id_organisme;
    return this.allSites()
      .filter(s => s.accessStatus === 'none' || s.accessStatus === 'rejected')
      .filter(s => s.organismes?.some(o => o.id_organisme === userOrgId))
      .map(s => ({ id_site: s.id_site, nom_site: s.nom_site }));
  });

  // GeoJSON filtré pour la carte (mes sites uniquement)
  readonly mapGeoJSON = computed(() => {
    const mySiteIds = this.mySites().map(s => s.id_site);
    const fullData = this.mapData();

    // Vérifier que fullData existe et que features est bien un tableau
    if (!fullData || !fullData.features || !Array.isArray(fullData.features)) {
      return null;
    }

    return {
      type: 'FeatureCollection' as const,
      features: fullData.features.filter(f =>
        mySiteIds.includes(f.properties?.id_site)
      )
    };
  });

  // Indique si la carte a des features à afficher
  readonly hasMapFeatures = computed(() => {
    const geojson = this.mapGeoJSON();
    return geojson !== null && geojson.features && geojson.features.length > 0;
  });

  ngOnInit(): void {
    this.loadData();
  }

  /**
   * Charge les donnees (sites, GeoJSON et demandes).
   */
  loadData(): void {
    this.loading.set(true);

    forkJoin({
      sites: this.adminService.getSites({ page_size: 100 }),
      geojson: this.adminService.getSitesGeoJSON().pipe(catchError(() => of(null))),
      requests: this.validationService.getMyRequests().pipe(catchError(() => of([])))
    }).subscribe({
      next: ({ sites, geojson, requests }) => {
        this.myRequests.set(requests.filter(r => r.request_type === 'site_access'));

        if (geojson) {
          this.mapData.set(geojson);
        }

        const sitesWithAccess = this.enrichSitesWithAccess(
          sites.results as SiteWithUsers[],
          requests
        );
        this.allSites.set(sitesWithAccess);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement sites:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loading.set(false);
      }
    });
  }

  /**
   * Enrichit les sites avec les informations d'acces.
   */
  private enrichSitesWithAccess(
    sites: SiteWithUsers[],
    requests: ValidationRequestListItem[]
  ): SiteWithAccess[] {
    const currentUser = this.authService.currentUser();
    const isSuperAdmin = this.authService.isSuperAdmin();

    return sites.map(site => {
      const pendingRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'pending' &&
             r.target_name === site.nom_site
      );
      const rejectedRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'rejected' &&
             r.target_name === site.nom_site
      );
      const approvedRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'approved' &&
             r.target_name === site.nom_site
      );

      const isUserLinked = site.users?.some(u => u.id_role === currentUser?.id);
      const userLink = site.users?.find(u => u.id_role === currentUser?.id);

      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      // Super Admin a acces a tous les sites
      if (isSuperAdmin || isUserLinked || approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      return {
        ...site,
        accessStatus,
        isReferent: isSuperAdmin || userLink?.referent || false
      };
    });
  }

  /**
   * Gère le changement de recherche.
   */
  onSearchChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchTerm.set(value);
    // Reset pagination lors de la recherche
    this.currentPage.set(1);
  }

  /**
   * Efface la recherche.
   */
  clearSearch(): void {
    this.searchTerm.set('');
    this.currentPage.set(1);
  }

  /**
   * Change de page.
   */
  goToPage(page: number | string): void {
    if (typeof page === 'number' && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  /**
   * Page precedente.
   */
  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
    }
  }

  /**
   * Page suivante.
   */
  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
    }
  }

  /**
   * Clic sur une feature de la carte.
   * Affiche le popup avec le nom du site (gere par LeafletMapComponent).
   */
  onMapFeatureClick(feature: any): void {
    // Le popup est automatiquement affiche par LeafletMapComponent
    // Pas de navigation automatique
  }

  /**
   * Navigue vers la page detail d'un site.
   */
  viewSite(site: SiteWithAccess): void {
    this.router.navigate(['/sites', site.id_site]);
  }

  /**
   * Ouvre le dialog de demande d'acces avec selection de site.
   */
  openSiteAccessRequestDialog(): void {
    const sites = this.availableSitesForRequest();
    if (sites.length === 0) return;

    const dialogRef = this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'site',
        selectableSites: sites
      } as AccessRequestDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }

  /**
   * Obtient la classe CSS du statut.
   */
  getStatusClass(site: SiteWithAccess): string {
    if (site.isReferent) return 'status-success';
    if (site.accessStatus === 'granted') return 'status-info';
    return 'status-neutre';
  }

  /**
   * Formate la surface.
   */
  formatSurface(surface: number | null | undefined): string {
    if (!surface) return '-';
    return `${surface.toLocaleString('fr-FR')} ha`;
  }

  /**
   * Verifie si une page est un nombre.
   */
  isPageNumber(page: number | string): boolean {
    return typeof page === 'number';
  }

  /**
   * Ouvre le modal de creation d'un nouveau site.
   * Le site sera automatiquement lie a l'organisme de l'utilisateur.
   */
  createSite(): void {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) {
      this.snackBar.open(
        this.translate.instant('sites.createSite.noOrganisme'),
        this.translate.instant('common.actions.close'),
        { duration: 3000 }
      );
      return;
    }

    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1100px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        organismeId: currentUser.organisme.id_organisme,
        principal: false
      } as SiteFormModalData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open(
          this.translate.instant('sites.createSite.success'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadData();
      }
    });
  }

  /**
   * Ouvre le dialogue unifié pour trouver ou créer un site.
   * Permet de rechercher un site existant et demander l'accès,
   * ou de créer un nouveau site si aucun n'existe.
   */
  openFindOrCreateSiteDialog(): void {
    const dialogRef = this.dialog.open(FindOrCreateSiteModalComponent, {
      width: '850px',
      maxWidth: '95vw',
      maxHeight: '90vh'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }
}
