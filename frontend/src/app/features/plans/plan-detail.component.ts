import { Component, signal, computed, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { SectionTitleComponent } from '../../shared/components/section-title/section-title.component';
import { PlanSidebarComponent } from './shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { EnjeuService } from '../../core/services/enjeu.service';
import { AdminPlan, PlanStatut, PlanVersionChainItem } from '../../core/models/admin.model';
import { PlanVersionTimelineComponent } from '../../shared/components/plan-version-timeline/plan-version-timeline.component';
import { Enjeu } from '../../core/models/enjeu.model';
import {
  DuplicatePlanDialogComponent,
  DuplicatePlanDialogData,
  DuplicatePlanDialogResult,
} from '../../shared/components/modals/duplicate-plan-dialog/duplicate-plan-dialog.component';

interface SyntheseAccordion {
  id: string;
  title: string;
  colorClass: 'terra-cotta' | 'orange';
  expanded: boolean;
  hasSubItems?: boolean;
  subItems?: SubAccordion[];
}

interface SubAccordion {
  id: string;
  title: string;
  expanded: boolean;
  items?: string[];
}

@Component({
  selector: 'app-plan-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    SectionTitleComponent,
    PlanSidebarComponent,
    PlanVersionTimelineComponent,
  ],
  templateUrl: './plan-detail.component.html',
  styleUrl: './plan-detail.component.scss'
})
export class PlanDetailComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  private routeSub?: Subscription;

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Plan data from API
  plan = signal<AdminPlan | null>(null);

  // Version chain for timeline
  versionChain = computed(() => {
    const p = this.plan();
    return (p?.version_chain || []) as PlanVersionChainItem[];
  });

  // Enjeux/FCR data for synthèse and sidebar
  enjeuxData = signal<Enjeu[]>([]);
  fcrData = signal<Enjeu[]>([]);
  enjeuxLoading = signal(false);

  // Aggregated OLT/OO across all enjeux
  allOlts = computed(() => {
    return this.enjeuxData().flatMap(enjeu =>
      (enjeu.objectifs_long_terme || []).map(olt => ({
        ...olt,
        enjeu_libelle: enjeu.libelle,
        enjeu_id: enjeu.id_enjeu
      }))
    );
  });

  allOos = computed(() => {
    return this.enjeuxData().flatMap(enjeu =>
      (enjeu.objectifs_operationnels || []).map(oo => ({
        ...oo,
        enjeu_libelle: enjeu.libelle,
        enjeu_id: enjeu.id_enjeu
      }))
    );
  });

  // Operations loading state
  operationsLoading = signal(false);

  // Permissions: référent du plan, admin_og ou super_admin
  canManageLifecycle = computed(() => {
    if (this.authService.isSuperAdmin() || this.authService.isAdminOrganisme()) {
      return true;
    }
    const p = this.plan();
    const currentUser = this.authService.currentUser();
    if (!p || !currentUser) return false;
    return p.referents?.some(r => r.id_role === currentUser.id) || false;
  });

  // Accordéons de la section Synthèse
  syntheseAccordions = signal<SyntheseAccordion[]>([
    {
      id: 'enjeux',
      title: 'Enjeux et Facteurs clés de réussite',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-lt',
      title: 'Objectifs long terme',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-op',
      title: 'Objectifs opérationnels',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'actions',
      title: 'Actions et suivis',
      colorClass: 'orange',
      expanded: true,
      hasSubItems: true,
      subItems: []
    }
  ]);

  ngOnInit(): void {
    // S'abonner aux changements de paramètre slug (gère aussi la navigation intra-composant)
    this.routeSub = this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      if (slug && slug !== this.planSlug()) {
        this.planSlug.set(slug);
        this.loadPlan();
      }
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
  }

  loadPlan(): void {
    const slug = this.planSlug();
    if (!slug) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.planId.set(plan.id_pg);
        this.isLoading.set(false);
        this.loadEnjeux(plan.id_pg);
        this.loadOperations(plan.id_pg);
      },
      error: (error) => {
        this.errorMessage.set(error.message || 'Erreur lors du chargement du plan');
        this.isLoading.set(false);
      }
    });
  }

  loadEnjeux(planId: number): void {
    this.enjeuxLoading.set(true);
    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        this.enjeuxData.set(response.enjeux);
        this.fcrData.set(response.fcr);
        this.enjeuxLoading.set(false);
      },
      error: () => {
        this.enjeuxLoading.set(false);
      }
    });
  }

  loadOperations(planId: number): void {
    this.operationsLoading.set(true);
    this.enjeuService.getOperationsByPlan(planId).subscribe({
      next: (response) => {
        const subItems: SubAccordion[] = (response.groups || []).map((group: any, index: number) => ({
          id: `action-group-${index}`,
          title: `${group.type_action} (${group.count})`,
          expanded: index === 0,
          items: (group.operations || []).map((op: any) => {
            const code = op.code_operation ? `${op.code_operation} : ` : '';
            return `${code}${op.libelle}`;
          })
        }));

        this.syntheseAccordions.update(accordions =>
          accordions.map(acc => {
            if (acc.id === 'actions') {
              return { ...acc, hasSubItems: subItems.length > 0, subItems };
            }
            return acc;
          })
        );
        this.operationsLoading.set(false);
      },
      error: () => {
        this.operationsLoading.set(false);
      }
    });
  }

  navigateToEnjeux(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'enjeux']);
    }
  }

  navigateToEnjeuDetail(enjeu: Enjeu): void {
    const slug = this.planSlug();
    if (slug && enjeu.slug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeu.slug]);
    }
  }

  navigateToEnjeuByOltOo(enjeuId: number): void {
    const enjeu = this.enjeuxData().find(e => e.id_enjeu === enjeuId);
    if (enjeu) {
      this.navigateToEnjeuDetail(enjeu);
    }
  }

  navigateToMindmap(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'mindmap']);
    }
  }

  duplicatePlan(): void {
    const p = this.plan();
    if (!p) return;

    const data: DuplicatePlanDialogData = {
      planId: p.id_pg,
      planName: p.nom,
      planPeriod: p.annee_debut && p.annee_fin ? `${p.annee_debut} - ${p.annee_fin}` : '',
      planStatus: this.translate.instant(`plans.status.${p.statut}`),
      nbSites: (p.sites || []).length,
    };

    const dialogRef = this.dialog.open(DuplicatePlanDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data,
    });

    dialogRef.afterClosed().subscribe((result: DuplicatePlanDialogResult) => {
      if (result?.confirmed && result.options) {
        this.adminService.duplicatePlan(p.id_pg, result.options).subscribe({
          next: (newPlan) => {
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

  onTimelineStatusChange(newStatus: PlanStatut): void {
    const p = this.plan();
    if (!p) return;

    this.adminService.changePlanStatus(p.id_pg, newStatus).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusChanged'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlan();
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
    });
  }

  onTimelineCreateEvaluation(): void {
    const p = this.plan();
    if (!p) return;

    this.adminService.createEvaluation(p.id_pg).subscribe({
      next: (newPlan) => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.evaluationCreated'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        if (newPlan.slug) {
          this.router.navigate(['/plans', newPlan.slug]);
        }
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.evaluationError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/plans']);
  }

  toggleAccordion(accordionId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => ({
        ...acc,
        expanded: acc.id === accordionId ? !acc.expanded : acc.expanded
      }))
    );
  }

  toggleSubAccordion(parentId: string, subId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => {
        if (acc.id === parentId && acc.subItems) {
          return {
            ...acc,
            subItems: acc.subItems.map(sub => ({
              ...sub,
              expanded: sub.id === subId ? !sub.expanded : sub.expanded
            }))
          };
        }
        return acc;
      })
    );
  }
}
