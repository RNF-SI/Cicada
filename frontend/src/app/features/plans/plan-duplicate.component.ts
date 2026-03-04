import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminPlan, AdminSite } from '../../core/models/admin.model';
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
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
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

  displayedColumns = ['nom', 'periode', 'statut', 'sites', 'actions'];

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  /** IDs of sites the current user is directly linked to */
  private userSiteIds = signal<Set<number>>(new Set());

  /** IDs of sites belonging to the user's organisme */
  private orgSiteIds = signal<Set<number>>(new Set());

  /** Plans where the user is a direct member or referent */
  readonly myPlans = computed(() => {
    const user = this.authService.currentUser();
    if (!user) return [];
    return this.applySearch(
      this.allPlans().filter(plan =>
        plan.membres?.some(m => m.id_role === user.id) ||
        plan.referents?.some(r => r.id_role === user.id) ||
        plan.sites?.some(s => this.userSiteIds().has(s.id_site))
      )
    );
  });

  /** Plans from the user's organisme (excluding already in myPlans) */
  readonly orgPlans = computed(() => {
    const user = this.authService.currentUser();
    if (!user) return [];
    const myPlanIds = new Set(this.myPlans().map(p => p.id_pg));
    return this.applySearch(
      this.allPlans().filter(plan =>
        !myPlanIds.has(plan.id_pg) &&
        plan.sites?.some(s => this.orgSiteIds().has(s.id_site))
      )
    );
  });

  /** All remaining plans (for super admin) */
  readonly otherPlans = computed(() => {
    const myPlanIds = new Set(this.myPlans().map(p => p.id_pg));
    const orgPlanIds = new Set(this.orgPlans().map(p => p.id_pg));
    return this.applySearch(
      this.allPlans().filter(plan =>
        !myPlanIds.has(plan.id_pg) && !orgPlanIds.has(plan.id_pg)
      )
    );
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
        this.computeSiteIds(sites.results as AdminSite[]);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private computeSiteIds(sites: AdminSite[]): void {
    const user = this.authService.currentUser();
    if (!user) return;

    const userIds = new Set<number>();
    const orgIds = new Set<number>();
    const userOrgId = user.organisme?.id_organisme;

    for (const site of sites) {
      const siteUsers = (site as any).users as Array<{ id_role: number }> | undefined;
      if (siteUsers?.some(u => u.id_role === user.id)) {
        userIds.add(site.id_site);
      }
      if (userOrgId && site.organismes?.some((o: any) => o.id_organisme === userOrgId)) {
        orgIds.add(site.id_site);
      }
    }

    this.userSiteIds.set(userIds);
    this.orgSiteIds.set(orgIds);
  }

  private applySearch(plans: AdminPlan[]): AdminPlan[] {
    const query = this.searchQuery().toLowerCase().trim();
    if (!query) return plans;
    return plans.filter(
      p =>
        p.nom.toLowerCase().includes(query) ||
        (p.sites || []).some(s => s.nom_site.toLowerCase().includes(query))
    );
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

  getSitesLabel(plan: AdminPlan): string {
    const sites = plan.sites || [];
    if (sites.length === 0) return '-';
    if (sites.length === 1) return sites[0].nom_site;
    return `${sites[0].nom_site} (+${sites.length - 1})`;
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
                this.router.navigate(['/plans', newPlan.slug]);
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
