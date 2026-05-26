import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, debounceTime } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminSite as ApiSite, AdminOrganisme } from '../../core/models/admin.model';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';
import { SearchBarComponent } from '../../shared/components/search-bar/search-bar.component';
import {
  LinkUserSiteModalComponent,
  LinkSiteOrganismeModalComponent,
  SiteFormModalComponent,
  ExistingUserData,
  ExistingOrganismeData
} from '../../shared/components/modals';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';

interface DisplayOrganismeLie {
  id: number;
  nom: string;
  principal: boolean;
}

interface DisplayUserLie {
  id: number;
  nom: string;
  email: string;
  isReferent: boolean;
}

interface DisplaySite {
  id: number;
  slug: string;
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
    TranslateModule,
    PaginationComponent,
    SearchBarComponent,
  ],
  templateUrl: './admin-sites.component.html',
  styleUrl: './admin-sites.component.scss'
})
export class AdminSitesComponent implements OnInit, OnDestroy {
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

  // Pagination state
  currentPage = signal(1);
  totalItems = signal(0);
  readonly pageSize = 20;

  sites = signal<DisplaySite[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);

  private searchSubject = new Subject<void>();
  private destroy$ = new Subject<void>();

  currentOrganismeName = computed(() => {
    return this.currentUser()?.organisme?.nom_organisme || '';
  });

  totalSurface = computed(() => {
    return this.sites().reduce((sum, site) => sum + (site.surface || 0), 0);
  });

  ngOnInit(): void {
    this.searchSubject.pipe(
      debounceTime(300),
    ).subscribe(() => {
      this.currentPage.set(1);
      this.loadSites();
    });

    this.loadData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadData(): void {
    this.isLoading.set(true);

    // Load organismes for filter dropdown (all of them)
    this.adminService.getOrganismes({ page_size: 1000 }).subscribe({
      next: (response) => {
        this.organismes.set(response.results.map(org => ({
          id: org.id_organisme,
          nom: org.nom_organisme
        })));
      }
    });

    this.loadSites();
  }

  loadSites(): void {
    this.isLoading.set(true);
    this.adminService.getSites({
      search: this.searchQuery || undefined,
      page: this.currentPage(),
      page_size: this.pageSize,
      type: this.filterType || undefined,
      organisme: this.filterOrganisme ? parseInt(this.filterOrganisme) : undefined
    }).subscribe({
      next: (response: any) => {
        const mapped = response.results.map((site: ApiSite) => this.mapSite(site));
        this.sites.set(mapped);
        this.totalItems.set(response.pagination?.count ?? response.count ?? 0);

        // Load related data for current page only
        this.loadRelatedDataForSites(mapped);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  onSearchChange(): void {
    this.searchSubject.next();
  }

  onFilterChange(): void {
    this.currentPage.set(1);
    this.loadSites();
  }

  onPageChange(page: number): void {
    this.currentPage.set(page);
    this.loadSites();
  }

  private loadRelatedDataForSites(sites: DisplaySite[]): void {
    if (sites.length === 0) {
      this.isLoading.set(false);
      return;
    }

    const observables = sites.map(site =>
      forkJoin({
        siteId: of(site.id),
        organismes: this.adminService.getSiteOrganismes(site.slug).pipe(
          catchError(() => of([]))
        ),
        users: this.adminService.getSiteUsers(site.slug).pipe(
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
      slug: site.slug,
      nom: site.nom_site,
      type: site.type_site_label || 'N/A',
      organisme: site.organismes?.[0]?.nom_organisme || 'Non assigne',
      organismeId: site.organismes?.[0]?.id_organisme || 0,
      surface: site.surf_off,
      commune: undefined,
      departement: undefined,
      nbPlans: site.plans_count ?? 0,
      isActive: site.active ?? true,
      organismes: [],
      users: []
    };
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
          id_type_site: null,
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
          slug: site.slug,
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
          slug: site.slug,
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
    const planCount = site.nbPlans || 0;
    const userCount = site.users?.length || 0;
    const details: string[] = [];
    if (planCount > 0) {
      details.push(this.translate.instant('admin.sites.delete.plansWarning', { count: planCount }));
    }
    if (userCount > 0) {
      details.push(this.translate.instant('admin.sites.delete.usersWarning', { count: userCount }));
    }
    const message = this.translate.instant('admin.sites.delete.confirmMessage', { name: site.nom })
      + (details.length ? '\n\n' + details.join('\n') : '');

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '500px',
      data: {
        title: this.translate.instant('admin.sites.delete.confirmTitle'),
        message,
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;

      this.adminService.deleteSite(site.slug).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('admin.sites.delete.success', { name: site.nom }),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
          this.loadSites();
        },
        error: (error) => {
          this.snackBar.open(
            error.message || this.translate.instant('admin.sites.delete.error'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        }
      });
    });
  }

  canDeleteSite(site: DisplaySite): boolean {
    if (this.isSuperAdmin()) return true;
    // Le rédacteur principal est exclu (aligné avec la suppression des plans :
    // la suppression d'un site est un acte de cycle de vie)
    if (this.authService.isRedacteurPrincipal()) return false;
    const userId = this.currentUser()?.id;
    if (this.isAdminOrganisme()) {
      const userOrgId = this.currentUser()?.organisme?.id_organisme;
      if (userOrgId && site.organismes.some(o => o.id === userOrgId)) return true;
    }
    return site.users.some(u => u.id === userId && u.isReferent);
  }

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
