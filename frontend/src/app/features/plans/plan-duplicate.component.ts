import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { ViewScopeToggleComponent, ViewScope } from '../../shared/components/view-scope-toggle/view-scope-toggle.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminPlan, AdminSite } from '../../core/models/admin.model';
import { FormFieldComponent } from '../../shared/components/form-field/form-field.component';
import {
  DuplicatePlanDialogComponent,
  DuplicatePlanDialogData,
  DuplicatePlanDialogResult,
} from '../../shared/components/modals/duplicate-plan-dialog/duplicate-plan-dialog.component';

@Component({
  selector: 'app-plan-duplicate',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatTooltipModule,
    TranslateModule,
    HeaderComponent,
    ViewScopeToggleComponent,
    FormFieldComponent,
  ],
  templateUrl: './plan-duplicate.component.html',
  styleUrl: './plan-duplicate.component.scss',
})
export class PlanDuplicateComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  allPlans = signal<AdminPlan[]>([]);
  allSites = signal<AdminSite[]>([]);
  loading = signal(true);
  duplicating = signal(false);
  searchQuery = signal('');

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Scope toggle
  planScope = signal<ViewScope>('mine');
  readonly showScopeToggle = computed(() => this.isAdminOrganisme() || this.isSuperAdmin());

  // Toggle anciennes versions
  readonly showOldVersions = signal(false);

  /** IDs of sites belonging to the user's organisme */
  private orgSiteIds = signal<Set<number>>(new Set());

  /** Map of all plans by id for parent chain lookup */
  private readonly plansById = computed(() => {
    const map = new Map<number, AdminPlan>();
    for (const p of this.allPlans()) {
      map.set(p.id_pg, p);
    }
    return map;
  });

  /** Plans filtered by scope */
  private readonly scopedPlans = computed(() => {
    const scope = this.planScope();
    const user = this.authService.currentUser();
    if (!user) return [];

    const plans = this.allPlans();

    if (scope === 'mine') {
      return plans.filter(plan =>
        plan.membres?.some(m => m.id_role === user.id) ||
        plan.referents?.some(r => r.id_role === user.id)
      );
    }

    if (scope === 'organisme') {
      return plans.filter(plan =>
        plan.membres?.some(m => m.id_role === user.id) ||
        plan.referents?.some(r => r.id_role === user.id) ||
        plan.sites?.some(s => this.orgSiteIds().has(s.id_site))
      );
    }

    // scope === 'all'
    return plans;
  });

  /**
   * Statuts exploitables comme base de duplication (#391). Auparavant restreint
   * au seul statut `valide`, ce qui affichait « Aucun plan trouvé » dès que les
   * plans de l'utilisateur étaient en brouillon, modifiés ou archivés (cas
   * fréquent : baser un nouveau plan sur le précédent, souvent archivé). On
   * accepte tout le cycle de vie courant (on exclut seulement les statuts
   * transitoires du workflow CSRPN).
   */
  private static readonly BASABLE_STATUSES = new Set([
    'draft', 'valide', 'modifie', 'mi_parcours', 'archive',
  ]);

  /** Final filtered list: scope + basable status + leaf only (children_count === 0) + search */
  readonly filteredPlans = computed(() => {
    const search = this.searchQuery().toLowerCase().trim();
    return this.scopedPlans().filter(p => {
      // Plans exploitables comme base (#391)
      const isBasable = PlanDuplicateComponent.BASABLE_STATUSES.has(p.statut);
      // Only show leaf plans (not replaced by a newer version)
      const isLeaf = !p.children_count || p.children_count === 0;
      const searchMatch = !search ||
        p.nom.toLowerCase().includes(search) ||
        (p.sites || []).some(s => s.nom_site.toLowerCase().includes(search));
      return isBasable && isLeaf && searchMatch;
    });
  });

  /**
   * Linked parent plans displayed ABOVE each child plan.
   * Same logic as plans-list:
   * - Toggle OFF: show immediate parent only for drafts
   * - Toggle ON: show full ancestor chain
   */
  readonly linkedPlansById = computed(() => {
    const result = new Map<number, AdminPlan[]>();
    const byId = this.plansById();
    const showAll = this.showOldVersions();

    for (const plan of this.filteredPlans()) {
      if (!plan.plan_parent_id) continue;

      // Toggle OFF: show parent only for drafts
      if (!showAll && plan.statut !== 'draft') continue;

      const ancestors: AdminPlan[] = [];
      const visited = new Set<number>([plan.id_pg]);
      let currentId: number | null | undefined = plan.plan_parent_id;

      while (currentId && !visited.has(currentId)) {
        visited.add(currentId);
        const parent = byId.get(currentId);
        if (!parent) break;
        ancestors.push(parent);
        // Toggle OFF: only immediate parent
        if (!showAll) break;
        currentId = parent.plan_parent_id ?? null;
      }

      if (ancestors.length > 0) {
        // Reverse: oldest ancestor first (displayed on top)
        result.set(plan.id_pg, ancestors.reverse());
      }
    }
    return result;
  });

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    this.loading.set(true);
    forkJoin({
      plans: this.adminService.getPlans({ page_size: 500 }),
      sites: this.adminService.getSites({ page_size: 500 }).pipe(catchError(() => of({ results: [] }))),
    }).subscribe({
      next: ({ plans, sites }) => {
        this.allPlans.set(plans.results);
        this.allSites.set(sites.results as AdminSite[]);
        this.computeOrgSiteIds(sites.results as AdminSite[]);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private computeOrgSiteIds(sites: AdminSite[]): void {
    const user = this.authService.currentUser();
    if (!user) return;

    const orgIds = new Set<number>();
    const userOrgId = user.organisme?.id_organisme;

    for (const site of sites) {
      if (userOrgId && site.organismes?.some((o: any) => o.id_organisme === userOrgId)) {
        orgIds.add(site.id_site);
      }
    }

    this.orgSiteIds.set(orgIds);
  }

  onScopeChange(scope: ViewScope): void {
    this.planScope.set(scope);
  }

  toggleOldVersions(): void {
    this.showOldVersions.update(v => !v);
  }

  getPeriod(plan: AdminPlan): string {
    if (plan.annee_debut && plan.annee_fin) {
      return `${plan.annee_debut} - ${plan.annee_fin}`;
    }
    return '-';
  }

  getStatusLabel(statut: string): string {
    return this.translate.instant(`plans.status.${statut}`);
  }

  getStatusClass(statut: string): string {
    switch (statut) {
      case 'valide':
        return 'status-success';
      case 'draft':
        return 'status-warning';
      case 'archive':
        return 'status-neutre';
      default:
        return '';
    }
  }

  /** Tooltip listant tous les sites d'un plan */
  getSitesTooltip(plan: AdminPlan): string {
    const sites = plan.sites || [];
    return sites.map(s => {
      const access = this.getSiteAccess(s.id_site);
      return access?.accessLabel ? `${s.nom_site} (${access.accessLabel})` : s.nom_site;
    }).join('\n');
  }

  /** Retourne l'info d'accès pour un site donné (depuis allSites qui a current_user_access) */
  getSiteAccess(siteId: number): { accessType?: string; accessLabel?: string } | null {
    const site = this.allSites().find(s => s.id_site === siteId);
    if (!site?.current_user_access) return null;
    return {
      accessType: site.current_user_access.access_type,
      accessLabel: site.current_user_access.role_label,
    };
  }

  onSelectPlan(plan: AdminPlan): void {
    const data: DuplicatePlanDialogData = {
      planId: plan.id_pg,
      planName: plan.nom,
      planPeriod: this.getPeriod(plan),
      planStatus: this.getStatusLabel(plan.statut),
      nbSites: (plan.sites || []).length,
    };

    const dialogRef = this.dialog.open(DuplicatePlanDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data,
    });

    dialogRef.afterClosed().subscribe((result: DuplicatePlanDialogResult) => {
      if (result?.confirmed && result.options) {
        this.duplicating.set(true);
        this.adminService
          .duplicatePlan(plan.id_pg, result.options)
          .subscribe({
            next: (newPlan) => {
              this.duplicating.set(false);
              this.snackBar.open(
                this.translate.instant('plans.duplicate.success'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              if (newPlan.slug) {
                this.router.navigate(['/plans', newPlan.slug], {
                  queryParams: { edit: 'metadata' },
                });
              } else {
                this.router.navigate(['/plans']);
              }
            },
            error: () => {
              this.duplicating.set(false);
              this.snackBar.open(
                this.translate.instant('plans.duplicate.error'),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
            },
          });
      }
    });
  }
}
