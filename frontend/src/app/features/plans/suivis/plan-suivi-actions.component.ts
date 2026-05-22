import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  Enjeu, Indicateur, Operation, OperationAnnee
} from '../../../core/models/enjeu.model';

type ActionStatus = 'planned' | 'planned-realized' | 'planned-partial' | 'realized-unplanned' | 'partial-unplanned';

interface FlatOperation {
  operation: Operation;
  enjeuLibelle: string;
  enjeuId: number;
}

@Component({
  selector: 'app-plan-suivi-actions',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatButtonModule, MatChipsModule, MatMenuModule,
    MatProgressSpinnerModule, MatTooltipModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './plan-suivi-actions.component.html',
  styleUrl: './plan-suivi-actions.component.scss'
})
export class PlanSuiviActionsComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Data
  allOperations = signal<FlatOperation[]>([]);
  planYearStart = signal<number>(new Date().getFullYear());
  planYearEnd = signal<number>(new Date().getFullYear() + 9);

  // Filters
  activeView = signal<'global' | 'annuel'>('global');
  filterCategorieAction = signal<string | null>(null);
  filterEnjeu = signal<number | null>(null);
  filterPriorite = signal<string | null>(null);

  // Computed
  yearColumns = computed(() => {
    const start = this.planYearStart();
    const end = this.planYearEnd();
    const years: number[] = [];
    for (let y = start; y <= end; y++) {
      years.push(y);
    }
    return years;
  });

  filteredOperations = computed(() => {
    let ops = this.allOperations();
    const cat = this.filterCategorieAction();
    const enjeu = this.filterEnjeu();
    const prio = this.filterPriorite();

    if (cat) {
      ops = ops.filter(o => o.operation.type_action_label === cat);
    }
    if (enjeu) {
      ops = ops.filter(o => o.enjeuId === enjeu);
    }
    if (prio) {
      ops = ops.filter(o => o.operation.priorite_label === prio);
    }
    return ops;
  });

  // Unique filter values
  categorieActions = computed(() => {
    const labels = new Set<string>();
    this.allOperations().forEach(o => {
      if (o.operation.type_action_label) labels.add(o.operation.type_action_label);
    });
    return Array.from(labels).sort();
  });

  enjeux = computed(() => {
    const map = new Map<number, string>();
    this.allOperations().forEach(o => {
      if (!map.has(o.enjeuId)) map.set(o.enjeuId, o.enjeuLibelle);
    });
    return Array.from(map.entries()).map(([id, libelle]) => ({ id, libelle }));
  });

  priorites = computed(() => {
    const labels = new Set<string>();
    this.allOperations().forEach(o => {
      if (o.operation.priorite_label) labels.add(o.operation.priorite_label);
    });
    return Array.from(labels).sort();
  });

  private readonly actionIconMap: Record<ActionStatus, string> = {
    'planned': 'assets/images/icons/prevu.png',
    'planned-realized': 'assets/images/icons/prevu-realise.png',
    'planned-partial': 'assets/images/icons/prevu-partiellement-realise.png',
    'realized-unplanned': 'assets/images/icons/realise.png',
    'partial-unplanned': 'assets/images/icons/partiellement-realise.png'
  };

  legendItems: { status: ActionStatus; labelKey: string }[] = [
    { status: 'planned', labelKey: 'plans.suivis.actions.actionPrevue' },
    { status: 'planned-realized', labelKey: 'plans.suivis.actions.actionPrevueRealisee' },
    { status: 'planned-partial', labelKey: 'plans.suivis.actions.actionPrevuePartielle' },
    { status: 'realized-unplanned', labelKey: 'plans.suivis.actions.actionRealiseeNonPrevue' },
    { status: 'partial-unplanned', labelKey: 'plans.suivis.actions.actionPartielleNonPrevue' }
  ];

  getActionIcon(status: ActionStatus): string {
    return this.actionIconMap[status] || '';
  }

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          if (plan.annee_debut && plan.annee_fin) {
            this.planYearStart.set(plan.annee_debut);
            this.planYearEnd.set(plan.annee_fin);
          }
          this.loadData(plan.id_pg);
        }
      });
    }
  }

  private loadData(planId: number): void {
    this.isLoading.set(true);

    // Load enjeux with nested operations
    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        const flatOps: FlatOperation[] = [];
        const seenIds = new Set<number>();
        const allEnjeuxAndFcr = [...response.enjeux, ...response.fcr];

        for (const enjeu of allEnjeuxAndFcr) {
          this.extractOperations(enjeu, flatOps, seenIds);
        }

        this.allOperations.set(flatOps);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Erreur lors du chargement des données');
        this.isLoading.set(false);
      }
    });
  }

  private extractOperations(enjeu: Enjeu, result: FlatOperation[], seenIds: Set<number>): void {
    // Branch 1: OLT → NE → Indicateur → Métrique → Opération
    const olts = enjeu.objectifs_long_terme || [];
    for (const olt of olts) {
      const nes = olt.niveaux_exigence || [];
      for (const ne of nes) {
        this.extractOpsFromIndicateurs(ne.indicateurs || [], enjeu, result, seenIds);
      }
    }

    // Branch 2: Facteur d'influence → Pression → OO → RA → Indicateur → Métrique → Opération
    const facteurs = enjeu.facteurs_influence || [];
    for (const fi of facteurs) {
      for (const pression of fi.pressions || []) {
        const oos = pression.objectifs_operationnels || [];
        for (const oo of oos) {
          const ras = oo.resultats_attendus || [];
          for (const ra of ras) {
            this.extractOpsFromIndicateurs(ra.indicateurs || [], enjeu, result, seenIds);
          }
        }
      }
    }
  }

  private extractOpsFromIndicateurs(indicateurs: Indicateur[], enjeu: Enjeu, result: FlatOperation[], seenIds: Set<number>): void {
    for (const ind of indicateurs) {
      const metriques = ind.metriques || [];
      for (const met of metriques) {
        const operations = met.operations || [];
        for (const op of operations) {
          if (!seenIds.has(op.id_operation)) {
            seenIds.add(op.id_operation);
            result.push({
              operation: op,
              enjeuLibelle: enjeu.intitule_court || enjeu.libelle,
              enjeuId: enjeu.id_enjeu
            });
          }
        }
      }
    }
  }

  getActionStatusForYear(op: Operation, year: number): ActionStatus | null {
    if (!op.operation_annees) return null;
    const annee = op.operation_annees.find(a => a.annee === year);
    if (!annee) return null;

    if (annee.periodicite) {
      return 'planned';
    }
    return null;
  }

  setView(view: 'global' | 'annuel'): void {
    this.activeView.set(view);
  }

  setCategorieFilter(value: string | null): void {
    this.filterCategorieAction.set(value);
  }

  setEnjeuFilter(value: number | null): void {
    this.filterEnjeu.set(value);
  }

  setPrioriteFilter(value: string | null): void {
    this.filterPriorite.set(value);
  }

  clearFilters(): void {
    this.filterCategorieAction.set(null);
    this.filterEnjeu.set(null);
    this.filterPriorite.set(null);
  }

  hasActiveFilters(): boolean {
    return !!(this.filterCategorieAction() || this.filterEnjeu() || this.filterPriorite());
  }

  getPrioriteClass(op: Operation): string {
    if (!op.priorite_label) return '';
    if (op.priorite_label.includes('1')) return 'priority-1';
    if (op.priorite_label.includes('2')) return 'priority-2';
    if (op.priorite_label.includes('3')) return 'priority-3';
    return '';
  }

  /** Ouvre la fiche action en lecture seule (page dédiée, partageable via URL) */
  navigateToViewOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', operationId]);
  }
}
