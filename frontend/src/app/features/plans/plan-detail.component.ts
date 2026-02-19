import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { SectionTitleComponent } from '../../shared/components/section-title/section-title.component';
import { PlanSidebarComponent } from './shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../core/services/admin.service';
import { EnjeuService } from '../../core/services/enjeu.service';
import { AdminPlan } from '../../core/models/admin.model';
import { Enjeu } from '../../core/models/enjeu.model';

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
    MatProgressSpinnerModule,
    TranslateModule,
    HeaderComponent,
    SectionTitleComponent,
    PlanSidebarComponent
  ],
  templateUrl: './plan-detail.component.html',
  styleUrl: './plan-detail.component.scss'
})
export class PlanDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Plan data from API
  plan = signal<AdminPlan | null>(null);

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
    // Récupérer le slug du plan depuis l'URL
    const slug = this.route.snapshot.paramMap.get('slug');
    if (slug) {
      this.planSlug.set(slug);
      this.loadPlan();
    }
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
