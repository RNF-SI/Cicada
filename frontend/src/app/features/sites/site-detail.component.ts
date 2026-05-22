/**
 * Composant pour la page detail d'un site.
 * Layout style GeoNature: carte a gauche, contenu a droite.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AnchorNavComponent, AnchorNavItem } from '../../shared/components/anchor-nav/anchor-nav.component';
import { forkJoin, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { ValidationService } from '../../core/services/validation.service';
import { AdminSite, GeoJSONFeature, AdminPlan } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { LeafletMapComponent } from '../../shared/components/leaflet-map/leaflet-map.component';
import { SiteFormModalComponent, SiteFormModalData } from '../../shared/components/modals/site-form-modal/site-form-modal.component';
import { ManageSiteUsersModalComponent, ManageSiteUsersModalData } from '../../shared/components/modals/manage-site-users-modal/manage-site-users-modal.component';
import { InviteModalComponent, InviteModalData } from '../../shared/components/modals/invite-modal/invite-modal.component';
import { SiteTypeDisplayPipe } from '../../shared/pipes/site-type-display.pipe';
import {
  LinkPlanToSiteDialogComponent,
  LinkPlanToSiteDialogData,
} from '../../shared/components/modals/link-plan-to-site-dialog/link-plan-to-site-dialog.component';
import {
  AccessRequestDialogComponent,
  AccessRequestDialogData,
} from '../../shared/components/access-request-dialog/access-request-dialog.component';

// Interface pour les utilisateurs assignes au site (depuis SiteDetailSerializer)
interface SiteUserAssignment {
  user: {
    id_role: number;
    nom_complet: string;
    email: string;
    role_level: string;
    organisme: string | null;
  };
  referent: boolean;
  referent_valid: boolean;
  conservateur: boolean;
}


@Component({
  selector: 'app-site-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    LeafletMapComponent,
    SiteTypeDisplayPipe,
    AnchorNavComponent,
  ],
  templateUrl: './site-detail.component.html',
  styleUrl: './site-detail.component.scss'
})
export class SiteDetailComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly dialog = inject(MatDialog);

  // Donnees
  readonly site = signal<AdminSite | null>(null);
  readonly siteGeoJSON = signal<GeoJSONFeature | null>(null);
  readonly associatedPlans = signal<AdminPlan[]>([]);
  readonly siteUsers = signal<SiteUserAssignment[]>([]);
  readonly loading = signal(false);
  readonly requestingReferent = signal(false);
  readonly hasPendingReferentRequest = signal(false);
  readonly pendingPlanRequests = signal<ValidationRequestListItem[]>([]);

  // Navigation interne par ancres (#304 — choix design : option 2 boutons tertiaires)
  // Toutes les sections sont toujours visibles ; les ancres scrollent vers la section.
  readonly anchorNavItems: AnchorNavItem[] = [
    { id: 'site-info', label: 'sites.detail.menu.info' },
    { id: 'site-organismes', label: 'sites.detail.menu.organismes' },
    { id: 'site-users', label: 'sites.detail.menu.users' },
    { id: 'site-plans', label: 'sites.detail.menu.plans' },
  ];
  readonly activeAnchorId = signal<string>('site-info');

  // GeoJSON pour la carte
  readonly mapGeoJSON = computed(() => {
    const geojson = this.siteGeoJSON();
    if (!geojson) return null;
    return {
      type: 'FeatureCollection' as const,
      features: [geojson]
    };
  });

  // Pipe for site type display
  private readonly siteTypePipe = new SiteTypeDisplayPipe();

  // Informations formatees
  readonly siteInfo = computed(() => {
    const s = this.site();
    if (!s) return [];

    return [
      { label: 'sites.detail.fields.type', value: this.siteTypePipe.transform(s), icon: 'fi-rr-apps' },
      { label: 'sites.detail.fields.surface', value: this.formatSurface(s.surf_off), icon: 'fi-rr-map' },
      { label: 'sites.detail.fields.idLocal', value: s.id_local || '-', icon: 'fi-rr-key' },
      { label: 'sites.detail.fields.idInpn', value: s.id_inpn || '-', icon: 'fi-rr-database' },
      { label: 'sites.detail.fields.marin', value: s.marin ? 'Oui' : 'Non', icon: 'fi-rr-water' },
      { label: 'sites.detail.fields.outreMer', value: s.outre_mer ? 'Oui' : 'Non', icon: 'fi-rr-globe' }
    ];
  });

  ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => {
        const slug = params.get('slug');
        if (slug) {
          return of(slug);
        }
        return of(null);
      })
    ).subscribe(slug => {
      if (slug) {
        this.loadSiteData(slug);
      } else {
        this.router.navigate(['/sites']);
      }
    });
  }

  /**
   * Charge les donnees du site.
   */
  loadSiteData(siteSlug: string): void {
    this.loading.set(true);

    forkJoin({
      site: this.adminService.getSite(siteSlug),
      geojson: this.adminService.getSiteGeoJSON(siteSlug).pipe(catchError(() => of(null))),
      myRequests: this.validationService.getMyRequests().pipe(catchError(() => of([])))
    }).subscribe({
      next: ({ site, geojson, myRequests }) => {
        this.site.set(site);

        if (geojson) {
          this.siteGeoJSON.set(geojson);
        }

        // Charger les plans associés au site (utilise id_site pour le filtre)
        this.adminService.getPlans({ site: site.id_site, page_size: 50 }).pipe(
          catchError(() => of({ results: [] }))
        ).subscribe(plans => {
          this.associatedPlans.set(plans.results || []);
        });

        // Extraire les utilisateurs assignes depuis la reponse du site detail
        const users = (site as any).users_assignes || [];
        this.siteUsers.set(users);

        // Verifier si une demande de referent est en attente
        const pendingReferent = myRequests.some(
          r => r.request_type === 'referent_validation' &&
               r.target_site_id === site.id_site &&
               r.status === 'pending'
        );
        this.hasPendingReferentRequest.set(pendingReferent);

        // Charger les demandes plan-site en attente pour ce site
        this.loadPendingPlanRequests(site.id_site);

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement site:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loading.set(false);
        this.router.navigate(['/sites']);
      }
    });
  }

  /**
   * Mise à jour de l'ancre active (visuel uniquement, scroll géré par AnchorNav).
   */
  onAnchorClick(item: AnchorNavItem): void {
    this.activeAnchorId.set(item.id);
  }

  /**
   * Navigation vers la page de retour.
   */
  goBack(): void {
    this.router.navigate(['/sites']);
  }

  /**
   * Navigation vers un plan.
   */
  viewPlan(plan: AdminPlan): void {
    this.router.navigate(['/plans', plan.slug || plan.id_pg]);
  }

  /**
   * Formate la surface.
   */
  formatSurface(surface: number | null | undefined): string {
    if (!surface) return '-';
    return `${surface.toLocaleString('fr-FR')} ha`;
  }

  /**
   * Formate la periode d'un plan.
   */
  formatPlanPeriod(plan: AdminPlan): string {
    if (plan.annee_debut && plan.annee_fin) {
      return `${plan.annee_debut} - ${plan.annee_fin}`;
    }
    if (plan.annee_debut) {
      return `Depuis ${plan.annee_debut}`;
    }
    return '-';
  }

  /**
   * Obtient la classe CSS du statut d'un plan.
   */
  getPlanStatusClass(statut: string): string {
    switch (statut) {
      case 'valide': return 'status-success';
      case 'draft': return 'status-warning';
      case 'archive': return 'status-neutre';
      default: return 'status-neutre';
    }
  }

  /**
   * Obtient le label du statut d'un plan.
   */
  getPlanStatusLabel(statut: string): string {
    switch (statut) {
      case 'valide': return 'Valide';
      case 'draft': return 'Brouillon';
      case 'archive': return 'Archive';
      default: return statut;
    }
  }

  /**
   * Signal indiquant si l'utilisateur courant est *réellement* référent du site
   * (ou super_admin). Sert au rendu de l'indicateur de statut.
   */
  readonly isReferent = computed(() => {
    // Super admin peut tout faire
    if (this.authService.isSuperAdmin()) {
      return true;
    }
    const s = this.site();
    return s?.current_user_is_referent === true;
  });

  /**
   * Signal indiquant si l'utilisateur courant peut gérer le site (édition,
   * gestion utilisateurs, etc.). Plus permissif que `isReferent` (#235) :
   * inclut les admin_organisme dont l'organisme est lié au site, et les
   * rédacteurs principaux (accès global).
   */
  readonly canManageSite = computed(() => {
    if (this.authService.hasGlobalAccess()) {
      return true;
    }
    const s = this.site();
    if (!s) return false;
    if (s.current_user_is_referent === true) {
      return true;
    }
    // #235 — admin_organisme dont l'organisme est gestionnaire du site.
    if (this.authService.currentUser()?.niveau_role === 'admin_og') {
      const userOgId = this.authService.currentUser()?.organisme?.id_organisme;
      if (userOgId && s.organismes?.some(og => og.id_organisme === userOgId)) {
        return true;
      }
    }
    return false;
  });

  /**
   * Verifie si l'utilisateur peut demander a devenir referent.
   * Conditions: a acces au site mais n'est pas encore referent.
   */
  canRequestReferent(): boolean {
    const s = this.site();
    if (!s?.current_user_access) return false;
    // A acces mais n'est pas referent
    return s.current_user_access.has_access && !s.current_user_access.is_referent;
  }

  /**
   * Demande a devenir referent du site.
   */
  requestReferent(): void {
    const s = this.site();
    if (!s) return;

    this.requestingReferent.set(true);

    this.validationService.requestReferent(s.slug).subscribe({
      next: () => {
        this.requestingReferent.set(false);
        this.hasPendingReferentRequest.set(true);
        this.snackBar.open(
          this.translate.instant('sites.detail.referentRequestSent'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
      error: (error: { error?: { error?: string } }) => {
        this.requestingReferent.set(false);
        const errorMessage = error.error?.error || this.translate.instant('common.messages.error');
        this.snackBar.open(
          errorMessage,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /**
   * Ouvre le modal d'edition du site (pour les referents).
   */
  editSite(): void {
    const s = this.site();
    if (!s) return;

    // Preparer les geometries existantes depuis le GeoJSON
    const geojson = this.siteGeoJSON();
    let existingPolygon = null;
    let existingPoint = null;

    if (geojson?.geometry) {
      existingPolygon = geojson.geometry;
    }

    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        site: s,
        existingPolygon,
        existingPoint
      } as SiteFormModalData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.site) {
        // Recharger les donnees du site
        this.loadSiteData(s.slug);
        this.snackBar.open(
          this.translate.instant('admin.sites.messages.updated'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  /**
   * Ouvre le modal unifie de gestion des utilisateurs du site (pour les referents).
   * Permet d'ajouter des utilisateurs de tous les organismes lies au site.
   */
  manageUsers(): void {
    const s = this.site();
    if (!s) return;

    // Preparer les utilisateurs existants
    const existingUsers = this.siteUsers().map(ua => ({
      id_role: ua.user.id_role,
      nom_complet: ua.user.nom_complet,
      email: ua.user.email,
      referent: ua.referent,
      organisme: ua.user.organisme
    }));

    const dialogRef = this.dialog.open(ManageSiteUsersModalComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        site: s,
        existingUsers
      } as ManageSiteUsersModalData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.changed) {
        // Recharger les donnees du site
        this.loadSiteData(s.slug);
        this.snackBar.open(
          this.translate.instant('admin.sites.messages.usersUpdated'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  /**
   * Obtient le nom complet d'un utilisateur.
   */
  getUserDisplayName(user: SiteUserAssignment['user']): string {
    return user.nom_complet || user.email;
  }

  /**
   * Obtient le role label d'un utilisateur dans le site.
   */
  getUserRoleLabel(ua: SiteUserAssignment): string {
    if (ua.conservateur) return 'Conservateur';
    if (ua.referent && ua.referent_valid) return 'Referent';
    return 'Utilisateur';
  }

  /**
   * Obtient la classe CSS du role.
   */
  getUserRoleClass(ua: SiteUserAssignment): string {
    if (ua.conservateur) return 'role-conservateur';
    if (ua.referent && ua.referent_valid) return 'role-referent';
    return 'role-user';
  }

  // ===================
  // Plans management
  // ===================

  /**
   * Signal: true si l'utilisateur peut lier un plan au site (référent du site,
   * admin_og du site, rédacteur principal, super_admin).
   */
  readonly canLinkPlan = computed(() => this.canManageSite());

  /**
   * Charge les demandes plan-site en attente pour ce site.
   */
  loadPendingPlanRequests(siteId: number): void {
    this.validationService.getValidationRequests({
      request_type: 'plan_site_link',
      status: 'pending'
    }).subscribe({
      next: (response) => {
        const siteRequests = response.results.filter(
          r => r.target_site_id === siteId
        );
        this.pendingPlanRequests.set(siteRequests);
      },
      error: () => {
        this.pendingPlanRequests.set([]);
      }
    });
  }

  /**
   * Ouvre le dialog pour lier un plan existant au site.
   */
  linkPlanToSite(): void {
    const s = this.site();
    if (!s) return;

    const pendingPlanIds = this.pendingPlanRequests().map(r => r.target_plan_id).filter(Boolean) as number[];
    const existingPlanIds = [...this.associatedPlans().map(p => p.id_pg), ...pendingPlanIds];

    const dialogRef = this.dialog.open(LinkPlanToSiteDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        siteId: s.id_site,
        siteName: s.nom_site,
        existingPlanIds,
      } as LinkPlanToSiteDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.loadSiteData(s.slug);
        let message: string;
        if (result.direct === false) {
          message = this.translate.instant('plans.detail.siteLinkRequested');
        } else {
          message = result.message || this.translate.instant('sites.detail.planLinked');
        }
        this.snackBar.open(
          message,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /**
   * Ouvre le dialog de demande d'acces a un plan.
   */
  requestPlanAccess(): void {
    const s = this.site();
    if (!s) return;

    this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'plan',
        targetSlug: s.slug,
        targetName: s.nom_site,
      } as AccessRequestDialogData,
    });
  }

  // ===================
  // Invitations
  // ===================

  /**
   * Ouvre le modal pour inviter un organisme a rejoindre le site.
   */
  inviteOrganisme(): void {
    const s = this.site();
    if (!s) return;

    const dialogRef = this.dialog.open(InviteModalComponent, {
      width: '500px',
      maxHeight: '90vh',
      data: {
        site: s,
        mode: 'organisme'
      } as InviteModalData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        // Recharger les donnees du site pour afficher le nouvel organisme/utilisateur
        this.loadSiteData(s.slug);
        this.snackBar.open(
          result.message || this.translate.instant('modals.invite.success'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

}
