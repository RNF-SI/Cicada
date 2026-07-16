/**
 * Composant pour la page "Mes sites".
 * Affiche les sites avec hero section, carte Leaflet, tableau et pagination.
 * Design inspiré de plans-list.component.
 */
import { Component, inject, signal, OnInit, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
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
import { ConfirmDialogComponent, ConfirmDialogData } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { SiteFormModalComponent, SiteFormModalData, SiteFormModalResult } from '../../shared/components/modals/site-form-modal/site-form-modal.component';
import { FindOrCreateSiteModalComponent } from '../../shared/components/modals/find-or-create-site-modal/find-or-create-site-modal.component';
import { BulkSiteImportModalComponent, BulkSiteImportModalResult } from '../../shared/components/modals/bulk-site-import-modal/bulk-site-import-modal.component';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { SearchBarComponent } from '../../shared/components/search-bar/search-bar.component';
import { TagComponent } from '../../shared/components/tag/tag.component';
import { LeafletMapComponent } from '../../shared/components/leaflet-map/leaflet-map.component';
import { ViewScopeToggleComponent, ViewScope } from '../../shared/components/view-scope-toggle/view-scope-toggle.component';
import { SiteTypeDisplayPipe } from '../../shared/pipes/site-type-display.pipe';

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
  /** Indique si l'utilisateur est directement lie au site (via CorRoleSite) */
  isDirectlyLinked: boolean;
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
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    LeafletMapComponent,
    ViewScopeToggleComponent,
    SiteTypeDisplayPipe,
    SearchBarComponent,
    TagComponent,
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
  readonly pendingSiteCreations = signal<ValidationRequestListItem[]>([]);
  readonly pendingOrgLinks = signal<ValidationRequestListItem[]>([]);
  readonly mapData = signal<GeoJSONFeatureCollection | null>(null);
  readonly loading = signal(false);

  // Scope d'affichage (mes sites / sites OG / tous)
  readonly viewScope = signal<ViewScope>('mine');

  // Permissions pour le toggle
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Afficher le toggle si l'utilisateur est admin_og ou super_admin
  readonly showScopeToggle = computed(() => this.isAdminOrganisme());

  // Recherche
  readonly searchTerm = signal('');

  // Pagination
  readonly currentPage = signal(1);
  readonly pageSize = 10;

  // Colonnes du tableau
  readonly tableColumns = ['name', 'type', 'surface', 'organisme', 'status', 'actions'];

  // Sites auxquels l'utilisateur est directement lie (via CorRoleSite)
  readonly mySites = computed(() => {
    // Filtre les sites où l'utilisateur a un lien direct (CorRoleSite)
    // isDirectlyLinked = true si l'utilisateur a une entrée dans CorRoleSite pour ce site
    return this.allSites().filter(s => s.isDirectlyLinked);
  });

  // Sites de l'organisme de l'utilisateur (tous les sites lies a son OG)
  readonly organismeSites = computed(() => {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) return [];
    const userOrgId = currentUser.organisme.id_organisme;

    return this.allSites().filter(site =>
      site.organismes?.some(o => o.id_organisme === userOrgId)
    );
  });

  // Sites en attente de validation (demandes pending)
  readonly pendingSites = computed(() => {
    return this.allSites().filter(s => s.accessStatus === 'pending');
  });

  // Sites affiches selon le scope selectionne
  readonly scopedSites = computed(() => {
    const scope = this.viewScope();
    switch (scope) {
      case 'mine':
        return this.mySites();
      case 'organisme':
        return this.organismeSites();
      case 'all':
        return this.allSites();
      default:
        return this.mySites();
    }
  });

  // Sites affiches (filtrés par recherche)
  readonly displayedMySites = computed(() => {
    const term = this.normalizeText(this.searchTerm().trim());
    const sites = this.scopedSites();

    if (!term) return sites;

    return sites.filter(site =>
      this.normalizeText(site.nom_site).includes(term) ||
      this.normalizeText(site.type_site_label || '').includes(term) ||
      site.organismes?.some(o => this.normalizeText(o.nom_organisme).includes(term))
    );
  });

  /**
   * Normalise un texte pour la recherche insensible aux accents.
   * Convertit en minuscules et supprime les accents.
   */
  private normalizeText(text: string): string {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

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
      .map(s => ({ id_site: s.id_site, slug: s.slug, nom_site: s.nom_site }));
  });

  // GeoJSON filtré pour la carte (selon le scope sélectionné)
  readonly mapGeoJSON = computed(() => {
    const scopedSiteIds = this.scopedSites().map(s => s.id_site);
    const fullData = this.mapData();

    // Vérifier que fullData existe et que features est bien un tableau
    if (!fullData || !fullData.features || !Array.isArray(fullData.features)) {
      return null;
    }

    return {
      type: 'FeatureCollection' as const,
      features: fullData.features.filter(f =>
        scopedSiteIds.includes(f.properties?.id_site)
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
      sites: this.adminService.getSites({ page_size: 1000 }),
      geojson: this.adminService.getSitesGeoJSON().pipe(catchError(() => of(null))),
      requests: this.validationService.getMyRequests().pipe(catchError(() => of([])))
    }).subscribe({
      next: ({ sites, geojson, requests }) => {
        this.myRequests.set(requests.filter(r => r.request_type === 'site_access'));

        // Filtrer les demandes de création de site en attente
        this.pendingSiteCreations.set(
          requests.filter(r => r.request_type === 'site_creation' && r.status === 'pending')
        );

        // Filtrer les demandes de lien organisme-site en attente
        this.pendingOrgLinks.set(
          requests.filter(r => r.request_type === 'site_org_link' && r.status === 'pending')
        );

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
      // Accès transitif (via plan, organisme, etc.) calculé côté backend
      const hasBackendAccess = site.current_user_access?.has_access === true;

      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      // Super Admin a acces a tous les sites
      if (isSuperAdmin || isUserLinked || hasBackendAccess || approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      return {
        ...site,
        accessStatus,
        isReferent: isSuperAdmin || userLink?.referent || false,
        isDirectlyLinked: !!isUserLinked
      };
    });
  }

  /**
   * Gère le changement de scope d'affichage.
   */
  onScopeChange(scope: ViewScope): void {
    this.viewScope.set(scope);
    // Reset pagination lors du changement de scope
    this.currentPage.set(1);
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

  // Référence carte pour focus programmatique au clic sur une ligne (revue design Amandine)
  @ViewChild(LeafletMapComponent) leafletMap?: LeafletMapComponent;

  /** Id du site sélectionné dans le tableau (focus carte + ligne mise en avant) */
  readonly focusedSiteId = signal<number | null>(null);

  /**
   * Clic sur une feature de la carte.
   * Affiche le popup avec le nom du site (gere par LeafletMapComponent).
   */
  onMapFeatureClick(feature: any): void {
    // Synchronisation : marquer la ligne correspondante comme sélectionnée
    const id = feature?.properties?.id_site ?? feature?.properties?.id;
    if (typeof id === 'number') {
      this.focusedSiteId.set(id);
    }
  }

  /**
   * Clic sur une ligne du tableau → zoome la carte sur le site + sélectionne la ligne
   * (revue design Amandine). Le bouton « Accéder » apparaît sur la ligne sélectionnée.
   */
  selectSiteRow(site: SiteWithAccess): void {
    this.focusedSiteId.set(site.id_site);
    this.leafletMap?.focusFeatureById(site.id_site);
  }

  /**
   * Navigue vers la page detail d'un site.
   */
  viewSite(site: SiteWithAccess): void {
    this.router.navigate(['/sites', site.slug]);
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
   * Formate la surface.
   */
  formatSurface(surface: number | null | undefined): string {
    if (!surface) return '-';
    return `${surface.toLocaleString('fr-FR')} ha`;
  }

  /**
   * Tooltip listant les organismes supplémentaires d'un site (revue design #310).
   */
  getOtherOrganismesNames(site: { organismes?: Array<{ nom_organisme: string }> }): string {
    const orgs = site.organismes || [];
    if (orgs.length <= 1) return '';
    return orgs.slice(1).map(o => o.nom_organisme).join(', ');
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

    // Nouveau site en plein écran (revue design #311 : page plutôt que modale)
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '100vw',
      maxWidth: '100vw',
      height: '100vh',
      maxHeight: '100vh',
      panelClass: 'site-form-page-mode',
      hasBackdrop: false,
      autoFocus: false,
      data: {
        organismeId: currentUser.organisme.id_organisme,
        principal: false,
        isPageMode: true,
      } as SiteFormModalData
    });

    dialogRef.afterClosed().subscribe((result: SiteFormModalResult | undefined) => {
      if (!result) return;

      if (result.site) {
        // Check if site creation is pending validation
        if (result.validationPending) {
          this.snackBar.open(
            result.message || this.translate.instant('sites.createSite.pendingValidation'),
            this.translate.instant('common.actions.close'),
            { duration: 8000 }
          );
        } else {
          this.snackBar.open(
            this.translate.instant('sites.createSite.success'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
        }
        this.loadData();
      } else if (result.duplicateAction && result.duplicateSite) {
        this.handleDuplicateAction(result);
      }
    });
  }

  /**
   * #440 — Rouvre en édition un site que l'utilisateur a créé et qui est
   * encore « en attente de validation ». Le créateur reste autorisé (côté
   * backend) à corriger son site tant que la demande de création n'est pas
   * traitée (ex. ajouter le type oublié). Le site est déjà présent dans
   * `allSites()` (accessible_site_ids inclut les créations en attente).
   */
  editPendingSite(request: ValidationRequestListItem): void {
    const site = this.allSites().find(s => s.id_site === request.target_site_id);
    if (!site?.slug) {
      this.snackBar.open(
        this.translate.instant('common.messages.error'),
        this.translate.instant('common.actions.close'),
        { duration: 3000 }
      );
      return;
    }

    // #440 — l'objet de la liste est allégé (pas de géométrie ni de tous les
    // champs). On récupère le détail complet pour pré-remplir le formulaire
    // (type, géométrie/carte, etc.) ; repli sur l'objet liste en cas d'échec.
    this.adminService.getSite(site.slug).pipe(
      catchError(() => of(site as unknown as AdminSite))
    ).subscribe((fullSite) => this.openSiteEditModal(fullSite));
  }

  /**
   * #536 — Annule la demande de création d'un site encore en attente de validation.
   * L'annulation supprime définitivement le site créé (encore inactif) : on demande
   * une confirmation explicite (destructive), comme dans la page « Mes demandes » (#467).
   */
  cancelPendingSite(request: ValidationRequestListItem): void {
    if (request.status !== 'pending') return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '500px',
      data: {
        title: this.translate.instant('myRequests.cancelSiteConfirm.title'),
        message: this.translate.instant('myRequests.cancelSiteConfirm.message', {
          name: request.target_name || '',
        }),
        warningText: this.translate.instant('myRequests.cancelSiteConfirm.warning'),
        confirmText: this.translate.instant('myRequests.cancelSiteConfirm.confirm'),
        destructive: true,
      } as ConfirmDialogData,
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.validationService.cancelRequest(request.id).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('myRequests.cancelSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.loadData();
        },
        error: (error) => {
          console.error('Erreur annulation demande de création:', error);
          this.snackBar.open(
            this.translate.instant('myRequests.cancelError'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
        },
      });
    });
  }

  /** Ouvre le formulaire de site en mode édition (plein écran) pour un site complet. */
  private openSiteEditModal(site: AdminSite): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '100vw',
      maxWidth: '100vw',
      height: '100vh',
      maxHeight: '100vh',
      panelClass: 'site-form-page-mode',
      hasBackdrop: false,
      autoFocus: false,
      data: {
        site,
        isPageMode: true,
      } as SiteFormModalData,
    });

    dialogRef.afterClosed().subscribe((result: SiteFormModalResult | undefined) => {
      if (!result) return;
      if (result.site) {
        this.snackBar.open(
          this.translate.instant('sites.editSite.success'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadData();
      }
    });
  }

  /**
   * Traite les actions de doublons retournées par le formulaire de création de site.
   */
  private handleDuplicateAction(result: SiteFormModalResult): void {
    const site = result.duplicateSite!;
    const slug = site.slug;

    if (result.duplicateAction === 'request_access') {
      // Demander l'accès au site existant
      this.validationService.requestSiteAccess(slug, {
        justification: this.translate.instant('sites.findOrCreate.autoMessage')
      }).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('sites.findOrCreate.accessRequested', { name: site.nom_site }),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
          this.loadData();
        },
        error: (err: { error?: { error?: string } }) => {
          this.snackBar.open(
            err.error?.error || this.translate.instant('common.messages.error'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        }
      });
    } else if (result.duplicateAction === 'request_org_link') {
      // Demander le lien organisme-site + optionnellement l'accès
      const orgLink$ = this.validationService.requestSiteOrgLink(slug, {
        justification: this.translate.instant('sites.findOrCreate.autoOrgLinkMessage')
      }).pipe(catchError(err => of({ error: true, status: err.status } as const)));

      if (result.alsoRequestAccess) {
        const access$ = this.validationService.requestSiteAccess(slug, {
          justification: this.translate.instant('sites.findOrCreate.autoOrgLinkMessage')
        }).pipe(catchError(err => of({ error: true, status: err.status } as const)));

        forkJoin([orgLink$, access$]).subscribe({
          next: ([orgResult, accessResult]) => {
            const orgOk = !('error' in orgResult);
            const accessOk = !('error' in accessResult);
            if (orgOk || accessOk) {
              const messageKey = orgOk && accessOk
                ? 'sites.findOrCreate.orgLinkAndAccessRequested'
                : orgOk
                  ? 'sites.findOrCreate.orgLinkRequested'
                  : 'sites.findOrCreate.accessRequested';
              this.snackBar.open(
                this.translate.instant(messageKey, { name: site.nom_site }),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
              this.loadData();
            } else {
              this.snackBar.open(
                this.translate.instant('common.messages.error'),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
            }
          }
        });
      } else {
        orgLink$.subscribe({
          next: (result) => {
            if (!('error' in result)) {
              this.snackBar.open(
                this.translate.instant('sites.findOrCreate.orgLinkRequested', { name: site.nom_site }),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
              this.loadData();
            } else {
              this.snackBar.open(
                this.translate.instant('common.messages.error'),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
            }
          }
        });
      }
    }
  }

  /**
   * Ouvre le dialogue unifié pour trouver ou créer un site.
   * Permet de rechercher un site existant et demander l'accès,
   * ou de créer un nouveau site si aucun n'existe.
   */
  /**
   * Ouvre le dialogue d'import en masse de sites.
   * Visible uniquement pour admin_og et super_admin.
   */
  openBulkImportDialog(): void {
    const dialogRef = this.dialog.open(BulkSiteImportModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe((result: BulkSiteImportModalResult | null) => {
      if (result?.imported) {
        this.loadData();
        this.snackBar.open(
          `${result.created} site(s) importé(s) avec succès`,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  openFindOrCreateSiteDialog(): void {
    const dialogRef = this.dialog.open(FindOrCreateSiteModalComponent, {
      width: '1100px',
      maxWidth: '95vw',
      maxHeight: '95vh'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;
      // Le résultat peut être un SiteFormModalResult propagé depuis le SiteFormModal
      if (result.duplicateAction && result.duplicateSite) {
        this.handleDuplicateAction(result);
      } else {
        this.loadData();
      }
    });
  }
}
