/**
 * Composant pour la liste des plans de gestion.
 * Affiche les plans auxquels l'utilisateur a accès et permet de demander l'accès à d'autres plans.
 */
import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { PlanGaugeComponent, GaugeStatus } from '../../shared/components/plan-gauge/plan-gauge.component';
import { ViewScopeToggleComponent, ViewScope } from '../../shared/components/view-scope-toggle/view-scope-toggle.component';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminPlan, AdminSite } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AccessRequestDialogComponent, AccessRequestDialogData, SelectableSite } from '../../shared/components/access-request-dialog/access-request-dialog.component';

interface PlanWithAccess extends AdminPlan {
  accessStatus: 'granted' | 'pending' | 'rejected' | 'none';
  isReferent: boolean;
  isMember: boolean;
  hasAccessViaSite: boolean;
  isOrgPlan: boolean;
  gaugeStatus: GaugeStatus;
}

@Component({
  selector: 'app-plans-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatMenuModule,
    MatButtonModule,
    MatCardModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    PlanGaugeComponent,
    ViewScopeToggleComponent
  ],
  templateUrl: './plans-list.component.html',
  styleUrl: './plans-list.component.scss'
})
export class PlansListComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  // Données
  readonly allPlans = signal<PlanWithAccess[]>([]);
  readonly allSites = signal<AdminSite[]>([]);
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly userSiteIds = signal<Set<number>>(new Set());
  readonly loading = signal(false);

  // Scope d'affichage (mes plans / plans OG / tous)
  readonly viewScope = signal<ViewScope>('mine');

  // Permissions pour le toggle
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Afficher le toggle si admin_og ou super_admin (sinon seul 'mine' disponible)
  readonly showScopeToggle = computed(() => this.isAdminOrganisme() || this.isSuperAdmin());

  // Tab state pour "Mes plans"
  activeTab = signal<'actifs' | 'inactifs'>('actifs');

  // Search pour "Demander l'accès"
  searchQuery = signal('');

  // Colonnes des tableaux
  readonly myPlansColumns = ['name', 'period', 'status', 'actions'];
  readonly otherPlansColumns = ['name', 'period', 'organisme', 'actions'];

  // Plans où l'utilisateur est membre direct (via CorRolePlan)
  readonly myDirectPlans = computed(() => {
    const currentUser = this.authService.currentUser();
    return this.allPlans().filter(plan =>
      plan.membres?.some(m => m.id_role === currentUser?.id)
    );
  });

  // Plans des sites auxquels l'utilisateur est lié (membre ou référent du site)
  readonly sitePlans = computed(() => {
    const userSiteIds = this.userSiteIds();
    return this.allPlans().filter(plan =>
      plan.sites?.some(s => userSiteIds.has(s.id_site))
    );
  });

  // Plans de l'organisme de l'utilisateur (via les sites de l'organisme)
  readonly organismePlans = computed(() => {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) return [];

    const userOrgId = currentUser.organisme.id_organisme;
    const orgSiteIds = new Set(
      this.allSites()
        .filter(site => site.organismes?.some(o => o.id_organisme === userOrgId))
        .map(site => site.id_site)
    );

    return this.allPlans().filter(plan =>
      plan.sites?.some(s => orgSiteIds.has(s.id_site))
    );
  });

  // Plans affichés selon le scope sélectionné
  // Les admin_og et super_admin voient tous les plans de leur scope (pas besoin de lien direct)
  readonly scopedPlans = computed(() => {
    const scope = this.viewScope();
    const isAdmin = this.isSuperAdmin() || this.isAdminOrganisme();
    switch (scope) {
      case 'mine':
        return this.myDirectPlans();
      case 'organisme':
        return isAdmin
          ? this.organismePlans()
          : this.organismePlans().filter(p => p.accessStatus === 'granted');
      case 'all':
        return isAdmin
          ? this.allPlans()
          : this.allPlans().filter(p => p.accessStatus === 'granted');
      default:
        return this.myDirectPlans();
    }
  });

  // Plans filtrés par onglet actif/inactif
  readonly myPlans = computed(() => {
    const tab = this.activeTab();
    return this.scopedPlans().filter(p => {
      if (tab === 'actifs') {
        return p.statut !== 'archive';
      } else {
        return p.statut === 'archive';
      }
    });
  });

  // Plans en attente de validation d'accès
  readonly pendingPlans = computed(() => {
    return this.allPlans().filter(p => p.accessStatus === 'pending');
  });

  readonly otherPlans = computed(() => {
    const search = this.searchQuery().toLowerCase();
    return this.allPlans()
      .filter(p => p.isOrgPlan)
      .filter(p => p.accessStatus === 'none' || p.accessStatus === 'rejected')
      .filter(p => !search || p.nom.toLowerCase().includes(search));
  });

  // Pagination pour "Mes plans"
  currentPage = signal(1);
  totalPages = signal(1);
  itemsPerPage = 10;
  showPagination = computed(() => this.totalPages() > 1);

  paginationPages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (current > 3) {
        pages.push('...');
      }
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }
      if (current < total - 2) {
        pages.push('...');
      }
      if (!pages.includes(total)) {
        pages.push(total);
      }
    }

    return pages;
  });

  ngOnInit(): void {
    this.loadData();
  }

  /**
   * Charge les données (plans, sites utilisateur et demandes en cours).
   */
  loadData(): void {
    this.loading.set(true);

    // Charger en parallèle : plans, sites de l'utilisateur, et demandes
    forkJoin({
      plans: this.adminService.getPlans(),
      sites: this.adminService.getSites({ page_size: 500 }).pipe(catchError(() => of({ results: [] }))),
      requests: this.validationService.getMyRequests().pipe(catchError(() => of([])))
    }).subscribe({
      next: ({ plans, sites, requests }) => {
        // Stocker tous les sites pour le filtrage par organisme
        this.allSites.set(sites.results as AdminSite[]);

        // Extraire les IDs des sites où l'utilisateur est directement lié
        const currentUser = this.authService.currentUser();
        const userSiteIds = new Set<number>();

        if (currentUser) {
          for (const site of sites.results as AdminSite[]) {
            // Vérifier si l'utilisateur est dans la liste des users du site
            const siteUsers = (site as any).users as Array<{ id_role: number }> | undefined;
            if (siteUsers?.some(u => u.id_role === currentUser.id)) {
              userSiteIds.add(site.id_site);
            }
          }
        }
        this.userSiteIds.set(userSiteIds);

        // Filtrer les demandes de plan_access
        this.myRequests.set(requests.filter(r => r.request_type === 'plan_access'));

        // Enrichir les plans avec le statut d'accès
        const plansWithAccess = this.enrichPlansWithAccess(plans.results, requests, userSiteIds);
        this.allPlans.set(plansWithAccess);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement plans:', error);
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
   * Enrichit les plans avec les informations d'accès.
   * @param plans Liste des plans
   * @param requests Demandes de validation de l'utilisateur
   * @param userSiteIds IDs des sites auxquels l'utilisateur a accès
   */
  private enrichPlansWithAccess(
    plans: AdminPlan[],
    requests: ValidationRequestListItem[],
    userSiteIds: Set<number>
  ): PlanWithAccess[] {
    const currentUser = this.authService.currentUser();
    const isSuperAdmin = this.authService.isSuperAdmin();
    const isAdminOg = this.authService.isAdminOrganisme();

    return plans.map(plan => {
      // Vérifier s'il y a une demande en cours pour ce plan (match par ID)
      const pendingRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'pending' &&
             r.target_plan_id === plan.id_pg
      );
      const rejectedRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'rejected' &&
             r.target_plan_id === plan.id_pg
      );
      const approvedRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'approved' &&
             r.target_plan_id === plan.id_pg
      );

      // Vérifier si l'utilisateur est membre direct du plan (via CorRolePlan)
      const userMembership = plan.membres?.find(m => m.id_role === currentUser?.id);
      const isMember = !!userMembership;
      const isReferent = userMembership?.referent || false;

      // Vérifier si référent via plan.referents M2M
      const isReferentOfPlan = plan.referents?.some(r => r.id_role === currentUser?.id) || false;

      // Vérifier si l'utilisateur a accès via un des sites du plan
      const hasAccessViaSite = plan.sites?.some(s => userSiteIds.has(s.id_site)) || false;

      // Vérifier si le plan appartient à l'organisme de l'utilisateur
      const isOrgPlan = this.isPlanFromUserOrg(plan);

      // accessStatus reflète le lien DIRECT de l'utilisateur au plan
      // (pas le rôle admin qui donne une visibilité globale)
      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      if (isMember || isReferentOfPlan || approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      // Calculer le statut de la jauge
      const gaugeStatus = this.calculateGaugeStatus(plan);

      return {
        ...plan,
        accessStatus,
        isReferent,
        isMember,
        hasAccessViaSite,
        isOrgPlan,
        gaugeStatus
      };
    });
  }

  /**
   * Vérifie si un plan appartient à l'organisme de l'utilisateur.
   */
  private isPlanFromUserOrg(plan: AdminPlan): boolean {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) return false;
    const userOrgId = currentUser.organisme.id_organisme;
    return plan.sites?.some(planSite => {
      const fullSite = this.allSites().find(s => s.id_site === planSite.id_site);
      return fullSite?.organismes?.some(o => o.id_organisme === userOrgId);
    }) || false;
  }

  /**
   * Calcule le statut de la jauge en fonction des dates du plan.
   */
  private calculateGaugeStatus(plan: AdminPlan): GaugeStatus {
    if (!plan.annee_debut || !plan.annee_fin) {
      return 'not-started';
    }

    const currentYear = new Date().getFullYear();
    const startYear = plan.annee_debut;
    const endYear = plan.annee_fin;

    if (currentYear < startYear) {
      return 'not-started';
    } else if (currentYear > endYear) {
      return 'exceeded';
    } else {
      const progress = (currentYear - startYear) / (endYear - startYear);
      if (progress < 0.5) {
        return 'in-progress';
      } else {
        return 'completed';
      }
    }
  }

  /**
   * Ouvre le dialog de demande d'accès.
   */
  openAccessRequestDialog(plan: PlanWithAccess): void {
    // Trouver les sites du plan qui appartiennent à l'organisme de l'utilisateur
    const orgSitesOfPlan = this.getOrgSitesForPlan(plan);
    // Parmi ceux-ci, lesquels l'utilisateur n'est PAS déjà lié
    const sitesNeedingAccess = orgSitesOfPlan.filter(s => !this.userSiteIds().has(s.id_site));

    const dialogRef = this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'plan',
        targetId: plan.id_pg,
        targetName: plan.nom,
        hasAccessViaSite: plan.hasAccessViaSite,
        sitesNeedingAccess: sitesNeedingAccess
      } as AccessRequestDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }

  /**
   * Récupère les sites d'un plan qui appartiennent à l'organisme de l'utilisateur.
   */
  private getOrgSitesForPlan(plan: PlanWithAccess): SelectableSite[] {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) return [];
    const userOrgId = currentUser.organisme.id_organisme;

    return (plan.sites || [])
      .filter(planSite => {
        const fullSite = this.allSites().find(s => s.id_site === planSite.id_site);
        return fullSite?.organismes?.some(o => o.id_organisme === userOrgId);
      })
      .map(planSite => {
        const fullSite = this.allSites().find(s => s.id_site === planSite.id_site);
        return {
          id_site: planSite.id_site,
          slug: fullSite?.slug || '',
          nom_site: planSite.nom_site
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
   * Tabs pour "Mes plans".
   */
  setTab(tab: 'actifs' | 'inactifs'): void {
    this.activeTab.set(tab);
  }

  /**
   * Pagination.
   */
  goToPage(page: number | string): void {
    if (typeof page === 'number' && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
    }
  }

  /**
   * Labels et classes CSS pour les statuts.
   */
  getStatutLabel(statut: string): string {
    const keys: Record<string, string> = {
      'draft': 'plans.status.draft',
      'valide': 'plans.status.valide',
      'archive': 'plans.status.archive'
    };
    const key = keys[statut];
    return key ? this.translate.instant(key) : statut;
  }

  getStatutClass(statut: string): string {
    const classes: Record<string, string> = {
      'draft': 'status-warning',
      'valide': 'status-success',
      'archive': 'status-neutre'
    };
    return classes[statut] || '';
  }

  /**
   * Recherche de plans.
   */
  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
  }

  /**
   * Actions sur les plans.
   */
  editStatus(plan: PlanWithAccess): void {
    console.log('Edit status for plan:', plan.id_pg);
  }

  viewPlan(plan: PlanWithAccess): void {
    this.router.navigate(['/plans', plan.slug]);
  }

  followPlan(plan: PlanWithAccess): void {
    console.log('Follow plan:', plan.id_pg);
  }

  /**
   * Formate la période du plan.
   */
  formatPeriod(plan: PlanWithAccess): string {
    if (plan.annee_debut && plan.annee_fin) {
      return `${plan.annee_debut}-${plan.annee_fin}`;
    } else if (plan.annee_debut) {
      return `${plan.annee_debut}`;
    }
    return '-';
  }

  /**
   * Récupère le premier site du plan (pour affichage).
   */
  getFirstSite(plan: PlanWithAccess): string {
    if (plan.sites && plan.sites.length > 0) {
      return plan.sites[0].nom_site;
    }
    return '-';
  }

  /**
   * Récupère la date de demande d'accès pour un plan en attente.
   */
  getRequestDate(plan: PlanWithAccess): Date | null {
    const request = this.myRequests().find(
      r => r.request_type === 'plan_access' &&
           r.status === 'pending' &&
           r.target_plan_id === plan.id_pg
    );
    return request ? new Date(request.created_at) : null;
  }
}
