import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminPlan, PlanStatut, AdminOrganisme } from '../../core/models/admin.model';
import { LinkPlanSiteModalComponent } from '../../shared/components/modals/link-plan-site-modal/link-plan-site-modal.component';
import { LinkPlanReferentModalComponent } from '../../shared/components/modals/link-plan-referent-modal/link-plan-referent-modal.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';

// Interface for linked site display
interface DisplaySiteLie {
  id: number;
  nom: string;
  type?: string;
  rang?: number;
}

// Interface for linked referent display
interface DisplayReferent {
  id: number;
  nom: string;
  email: string;
}

// Interface for plan member (referent or simple member)
interface DisplayMembre {
  id: number;
  nom: string;
  email: string;
  referent: boolean;
}

// Interface for display (mapping from API model)
interface DisplayPlan {
  id: number;
  nom: string;
  slug?: string;
  statut: PlanStatut;
  statutLabel: string;
  version?: string;
  periodeDebut?: number;
  periodeFin?: number;
  periode: string;
  gestionPartagee: boolean;
  ct88: boolean;
  risqueIncendie: boolean;
  evaluationLabel?: string;
  redacteurNom?: string;
  commentaire?: string;
  dateAjout?: Date;
  dateMaj?: Date;
  sites: DisplaySiteLie[];
  referents: DisplayReferent[];
  membres: DisplayMembre[];
}

interface DisplayOrganisme {
  id: number;
  nom: string;
}

@Component({
  selector: 'app-admin-plans',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule,
    PaginationComponent
  ],
  templateUrl: './admin-plans.component.html',
  styleUrl: './admin-plans.component.scss'
})
export class AdminPlansComponent implements OnInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;
  readonly hasGlobalAccess = this.authService.hasGlobalAccess;

  /** Vérifie si l'utilisateur peut gérer un plan (référent du plan, admin_og ou super_admin). */
  canManagePlan(plan: DisplayPlan): boolean {
    if (this.isSuperAdmin() || this.isAdminOrganisme()) return true;
    const userId = this.currentUser()?.id;
    return !!userId && plan.membres.some(m => m.id === userId && m.referent);
  }

  // Filter state
  searchQuery = '';
  filterStatut: PlanStatut | '' = '';
  filterOrganisme = '';
  isLoading = signal(false);

  // Pagination state
  currentPage = signal(1);
  totalItems = signal(0);
  readonly pageSize = 20;

  plans = signal<DisplayPlan[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);

  private searchSubject = new Subject<void>();
  private destroy$ = new Subject<void>();

  // Statistiques agrégées renvoyées par /api/plans/plans/stats/ (#184).
  // Avant ce fix, les vignettes comptaient les plans visibles dans la page
  // courante, donc ne reflétaient ni le filtre organisme ni le total.
  private statsSignal = signal<{ total: number; par_statut: Record<string, number> }>({
    total: 0,
    par_statut: {},
  });
  totalPlans = computed(() => this.statsSignal().total);
  plansValides = computed(() => this.statsSignal().par_statut['valide'] || 0);
  plansBrouillon = computed(() => this.statsSignal().par_statut['draft'] || 0);
  plansArchives = computed(() => this.statsSignal().par_statut['archive'] || 0);

  ngOnInit(): void {
    this.searchSubject.pipe(
      debounceTime(300),
    ).subscribe(() => {
      this.currentPage.set(1);
      this.loadPlans();
    });

    this.loadData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadData(): void {
    this.isLoading.set(true);

    // Load organismes for filter dropdown
    this.adminService.getOrganismes({ page_size: 1000 }).subscribe({
      next: (response) => {
        this.organismes.set(response.results.map(org => ({
          id: org.id_organisme,
          nom: org.nom_organisme
        })));
      }
    });

    this.loadPlans();
  }

  loadPlans(): void {
    this.isLoading.set(true);

    const currentOrgId = this.currentUser()?.organisme?.id_organisme;
    // Priorité au filtre sélectionné par l'utilisateur, sinon scoping par rôle
    const organismeFilter = this.filterOrganisme
      ? parseInt(this.filterOrganisme, 10)
      : (!this.hasGlobalAccess() && this.isAdminOrganisme() && currentOrgId
        ? currentOrgId
        : undefined);

    const scope = !this.isSuperAdmin() && !this.isAdminOrganisme() ? 'mine' as const : undefined;
    const commonFilters = {
      search: this.searchQuery || undefined,
      statut: this.filterStatut || undefined,
      organisme: organismeFilter,
      scope,
    };

    this.adminService.getPlans({
      ...commonFilters,
      page: this.currentPage(),
      page_size: this.pageSize,
    }).subscribe({
      next: (response: any) => {
        const mapped = response.results.map((plan: any) => this.mapPlan(plan));
        this.plans.set(mapped);
        this.totalItems.set(response.pagination?.count ?? response.count ?? 0);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });

    // #184 — recharger les vignettes selon le filtre courant.
    this.adminService.getPlanStats(commonFilters).subscribe({
      next: (stats) => this.statsSignal.set(stats),
      error: () => { /* ignore — les compteurs gardent leur dernière valeur */ },
    });
  }

  private mapPlan(plan: AdminPlan): DisplayPlan {
    const periode = plan.annee_debut && plan.annee_fin
      ? `${plan.annee_debut} - ${plan.annee_fin}`
      : plan.annee_debut
        ? this.translate.instant('admin.plans.periode.since', { year: plan.annee_debut })
        : this.translate.instant('admin.plans.periode.undefined');

    return {
      id: plan.id_pg,
      nom: plan.nom,
      slug: plan.slug,
      statut: plan.statut,
      statutLabel: this.translate.instant('admin.plans.status.' + plan.statut),
      version: plan.version,
      periodeDebut: plan.annee_debut,
      periodeFin: plan.annee_fin,
      periode,
      gestionPartagee: plan.gestion_partagee,
      ct88: plan.ct88,
      risqueIncendie: plan.risque_incendie,
      evaluationLabel: plan.evaluation_display,
      redacteurNom: plan.redacteur_nom,
      commentaire: plan.commentaire,
      dateAjout: plan.date_ajout ? new Date(plan.date_ajout) : undefined,
      dateMaj: plan.date_maj ? new Date(plan.date_maj) : undefined,
      sites: (plan.sites || []).map(s => ({
        id: s.id_site,
        nom: s.nom_site,
        type: s.type_site_label,
        rang: s.rang
      })),
      referents: (plan.referents || []).map(r => ({
        id: r.id_role,
        nom: r.nom_complet || `${r.prenom_role || ''} ${r.nom_role || ''}`.trim() || r.email,
        email: r.email
      })),
      membres: (plan.membres || []).map(m => ({
        id: m.id_role,
        nom: m.nom_complet || `${m.prenom_role || ''} ${m.nom_role || ''}`.trim() || m.email,
        email: m.email,
        referent: m.referent
      }))
    };
  }

  onSearchChange(): void {
    this.searchSubject.next();
  }

  onFilterChange(): void {
    this.currentPage.set(1);
    this.loadPlans();
  }

  onPageChange(page: number): void {
    this.currentPage.set(page);
    this.loadPlans();
  }

  // Actions
  managePlanSites(plan: DisplayPlan): void {
    const dialogRef = this.dialog.open(LinkPlanSiteModalComponent, {
      width: '650px',
      maxHeight: '85vh',
      data: {
        plan: {
          id_pg: plan.id,
          nom: plan.nom,
          sites: plan.sites.map(s => ({
            id_site: s.id,
            nom_site: s.nom,
            type_site_label: s.type,
            rang: s.rang
          }))
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success && result?.changed) {
        this.snackBar.open(this.translate.instant('admin.plans.messages.sitesUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadPlans();
      }
    });
  }

  managePlanReferents(plan: DisplayPlan): void {
    const dialogRef = this.dialog.open(LinkPlanReferentModalComponent, {
      width: '650px',
      maxHeight: '85vh',
      data: {
        plan: {
          id_pg: plan.id,
          nom: plan.nom,
          referents: plan.referents.map(r => ({
            id_role: r.id,
            email: r.email,
            nom_complet: r.nom
          })),
          membres: plan.membres.map(m => ({
            id_role: m.id,
            email: m.email,
            nom_complet: m.nom,
            referent: m.referent
          }))
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success && result?.changed) {
        this.snackBar.open(this.translate.instant('admin.plans.messages.referentsUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadPlans();
      }
    });
  }

  viewPlan(plan: DisplayPlan): void {
    this.router.navigate(['/plans', plan.slug || plan.id]);
  }

  validerPlan(plan: DisplayPlan): void {
    if (plan.statut !== 'draft') {
      this.snackBar.open(this.translate.instant('admin.plans.messages.onlyDraftCanBeValidated'), 'OK', { duration: 3000 });
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'valide').subscribe({
      next: () => {
        this.snackBar.open(this.translate.instant('admin.plans.messages.validated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  archiverPlan(plan: DisplayPlan): void {
    if (plan.statut === 'archive') {
      this.snackBar.open(this.translate.instant('admin.plans.messages.alreadyArchived'), 'OK', { duration: 3000 });
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'archive').subscribe({
      next: () => {
        this.snackBar.open(this.translate.instant('admin.plans.messages.archived'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  restaurerPlan(plan: DisplayPlan): void {
    if (plan.statut !== 'archive') {
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'draft').subscribe({
      next: () => {
        this.snackBar.open(this.translate.instant('admin.plans.messages.restored'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  deletePlan(plan: DisplayPlan): void {
    const siteCount = plan.sites.length;
    const referentCount = plan.referents.length;
    const memberCount = plan.membres.length;
    const details: string[] = [];
    if (siteCount > 0) {
      details.push(this.translate.instant('admin.plans.delete.sitesWarning', { count: siteCount }));
    }
    if (referentCount > 0) {
      details.push(this.translate.instant('admin.plans.delete.referentsWarning', { count: referentCount }));
    }
    if (memberCount > 0) {
      details.push(this.translate.instant('admin.plans.delete.membersWarning', { count: memberCount }));
    }
    const message = this.translate.instant('admin.plans.delete.confirmMessage', { name: plan.nom })
      + (details.length ? '\n\n' + details.join('\n') : '');

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '500px',
      data: {
        title: this.translate.instant('admin.plans.delete.confirmTitle'),
        message,
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;

      this.adminService.deletePlan(plan.id).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('admin.plans.delete.success', { name: plan.nom }),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
          this.loadPlans();
        },
        error: (error: Error) => {
          this.snackBar.open(
            error.message || this.translate.instant('admin.plans.delete.error'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        }
      });
    });
  }

  // Helper methods for display
  getStatutClass(statut: PlanStatut): string {
    const classes: Record<PlanStatut, string> = {
      'draft': 'statut-draft',
      'valide': 'statut-valide',
      'etendu': 'statut-etendu',
      'archive': 'statut-archive'
    };
    return classes[statut] || '';
  }

  getOtherSitesNames(sites: DisplaySiteLie[]): string {
    return sites.slice(2).map(s => s.nom).join(', ');
  }

  getOtherReferentsNames(referents: DisplayReferent[]): string {
    return referents.slice(2).map(r => r.nom).join(', ');
  }

  getOtherMembresNames(membres: DisplayMembre[]): string {
    return membres.slice(3).map(m => `${m.nom} (${m.referent ? 'Référent' : 'Membre'})`).join(', ');
  }

  formatDate(date?: Date): string {
    if (!date) return '-';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  }
}
