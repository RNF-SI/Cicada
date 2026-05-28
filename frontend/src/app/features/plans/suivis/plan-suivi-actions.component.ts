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

type SuiviTab = 'realisation' | 'budget' | 'rh';

/** Période d'agrégation pour les onglets Budget / RH. */
type AggregationPeriod = 'current' | 'past' | 'total';

/** Cellule prévi/réalisé pour le tableau Budget/RH. */
interface AggregatedCell {
  previsionnel: number;
  realise: number;
  hasRealise: boolean;
  ecartPct: number | null;
}

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

  // Tabs principaux (Phase 3)
  activeTab = signal<SuiviTab>('realisation');
  currentYear = signal<number>(new Date().getFullYear());

  // Filters
  filterCategorieAction = signal<string | null>(null);
  filterEnjeu = signal<number | null>(null);
  filterPriorite = signal<string | null>(null);

  // Computed
  /** Liste des colonnes années entre planYearStart et planYearEnd. */
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

  /** Liste des organismes ventilés sur une opération donnée (déduplication
   * entre années). Pour mode none/by_type, renvoie liste vide. */
  getOrganismesForOp(op: Operation): { id_organisme: number; nom: string }[] {
    if (op.ventilation_mode !== 'by_org' && op.ventilation_mode !== 'by_org_type') return [];
    const seen = new Map<number, string>();
    for (const oa of op.operation_annees || []) {
      for (const oao of oa.organismes || []) {
        if (!seen.has(oao.id_organisme)) {
          seen.set(oao.id_organisme, oao.organisme_nom || `Org #${oao.id_organisme}`);
        }
      }
    }
    return [...seen.entries()].map(([id_organisme, nom]) => ({ id_organisme, nom }));
  }

  /** Groupes d'actions regroupés par organisme. Une action ventilée
   * sur plusieurs organismes apparaît dans chacun. Les ops non-ventilées
   * sont regroupées dans un bucket "Plan général" en fin de liste. */
  operationsByOrganisme = computed<{
    id_organisme: number;
    nom: string;
    operations: FlatOperation[];
  }[]>(() => {
    const ops = this.filteredOperations();
    const groups = new Map<number, { id_organisme: number; nom: string; operations: FlatOperation[] }>();
    const orphans: FlatOperation[] = [];
    for (const item of ops) {
      const orgsForOp = this.getOrganismesForOp(item.operation);
      if (orgsForOp.length === 0) {
        orphans.push(item);
      } else {
        for (const org of orgsForOp) {
          if (!groups.has(org.id_organisme)) {
            groups.set(org.id_organisme, { id_organisme: org.id_organisme, nom: org.nom, operations: [] });
          }
          groups.get(org.id_organisme)!.operations.push(item);
        }
      }
    }
    const result = [...groups.values()].sort((a, b) => a.nom.localeCompare(b.nom));
    if (orphans.length > 0) {
      result.push({ id_organisme: 0, nom: '__plan_general__', operations: orphans });
    }
    return result;
  });

  /** Total budget/ETP agrégé pour un groupe d'organisme sur une période. */
  groupAggregate(
    items: FlatOperation[],
    period: AggregationPeriod,
    metric: 'budget' | 'etp',
  ): AggregatedCell {
    let previsionnel = 0;
    let realise = 0;
    let hasRealise = false;
    for (const item of items) {
      const c = metric === 'budget'
        ? this.aggregateBudget(item.operation, period)
        : this.aggregateEtp(item.operation, period);
      previsionnel += c.previsionnel;
      realise += c.realise;
      if (c.hasRealise) hasRealise = true;
    }
    const ecartPct = previsionnel > 0 ? ((realise - previsionnel) / previsionnel) * 100 : null;
    return { previsionnel, realise, hasRealise, ecartPct };
  }

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

  /**
   * Calcule le statut d'action pour une (opération, année) en combinant
   * la périodicité prévue (planifié) et le niveau de réalisation observé.
   *
   * Matrice prévu × réalisé selon la légende des suivis :
   *   prévu=oui, réalisé=TERMINE        → planned-realized
   *   prévu=oui, réalisé=PARTIEL        → planned-partial
   *   prévu=oui, réalisé=autre/aucun    → planned
   *   prévu=non, réalisé=TERMINE        → realized-unplanned
   *   prévu=non, réalisé=PARTIEL        → partial-unplanned
   *   sinon                              → null (rien à afficher)
   */
  getActionStatusForYear(op: Operation, year: number): ActionStatus | null {
    if (!op.operation_annees) return null;
    const annee = op.operation_annees.find(a => a.annee === year);
    if (!annee) return null;

    const prevu = !!annee.periodicite;
    const niveau = annee.realisation?.niveau_realisation_mnemonique ?? null;
    const realiseTotal = niveau === 'TERMINE';
    const realisePartiel = niveau === 'PARTIEL';

    if (prevu) {
      if (realiseTotal) return 'planned-realized';
      if (realisePartiel) return 'planned-partial';
      return 'planned';
    }
    // Non prévu mais réalisé (totalement ou partiellement)
    if (realiseTotal) return 'realized-unplanned';
    if (realisePartiel) return 'partial-unplanned';
    return null;
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

  // ===========================================================================
  // Phase 3 - Agrégations Budget / RH
  // ===========================================================================

  setTab(tab: SuiviTab): void {
    this.activeTab.set(tab);
  }

  /**
   * Calcule le budget prévi+réalisé pour une opération sur une période donnée.
   * Le mode de ventilation est lu sur l'Operation.
   */
  aggregateBudget(op: Operation, period: AggregationPeriod): AggregatedCell {
    return this.aggregate(op, period, 'budget');
  }

  /** Calcule l'ETP (jours) prévi+réalisé pour une opération sur une période. */
  aggregateEtp(op: Operation, period: AggregationPeriod): AggregatedCell {
    return this.aggregate(op, period, 'etp');
  }

  private aggregate(op: Operation, period: AggregationPeriod, metric: 'budget' | 'etp'): AggregatedCell {
    const cy = this.currentYear();
    const annees = (op.operation_annees || []).filter(oa => {
      if (period === 'current') return oa.annee === cy;
      if (period === 'past') return oa.annee < cy;
      return true; // total
    });

    const mode = op.ventilation_mode || 'none';
    let previsionnel = 0;
    let realise = 0;
    let hasRealise = false;

    for (const oa of annees) {
      // PRÉVISIONNEL ----------------------------------------------------------
      if (metric === 'budget') {
        if (mode === 'none') {
          previsionnel += Number(oa.budget || 0);
        } else if (mode === 'by_type') {
          previsionnel += Number(oa.budget_fonctionnement || 0) + Number(oa.budget_investissement || 0);
        } else {
          for (const o of oa.organismes || []) {
            previsionnel += Number(o.budget_fonctionnement || 0) + Number(o.budget_investissement || 0);
          }
        }
      } else {
        previsionnel += Number(oa.etp || 0);
      }

      // RÉALISÉ ---------------------------------------------------------------
      const r = oa.realisation;
      if (metric === 'budget') {
        if (mode === 'none') {
          if (r?.budget_realise != null) { realise += Number(r.budget_realise); hasRealise = true; }
        } else if (mode === 'by_type') {
          if (r?.budget_fonctionnement_realise != null) { realise += Number(r.budget_fonctionnement_realise); hasRealise = true; }
          if (r?.budget_investissement_realise != null) { realise += Number(r.budget_investissement_realise); hasRealise = true; }
        } else {
          for (const o of oa.organismes || []) {
            const ro = o.realisation;
            if (ro?.budget_fonctionnement_realise != null) { realise += Number(ro.budget_fonctionnement_realise); hasRealise = true; }
            if (ro?.budget_investissement_realise != null) { realise += Number(ro.budget_investissement_realise); hasRealise = true; }
          }
        }
      } else {
        if (mode === 'by_org' || mode === 'by_org_type') {
          for (const o of oa.organismes || []) {
            if (o.realisation?.etp_realise != null) { realise += Number(o.realisation.etp_realise); hasRealise = true; }
          }
        } else {
          if (r?.etp_realise != null) { realise += Number(r.etp_realise); hasRealise = true; }
        }
      }
    }

    const ecartPct = previsionnel > 0 ? ((realise - previsionnel) / previsionnel) * 100 : null;
    return { previsionnel, realise, hasRealise, ecartPct };
  }

  /** Total budget plan : somme du Total de toutes les opérations filtrées (prévi). */
  totalPlanBudget = computed<number>(() => {
    let sum = 0;
    for (const item of this.filteredOperations()) {
      sum += this.aggregateBudget(item.operation, 'total').previsionnel;
    }
    return sum;
  });

  /** Total ETP plan (prévi). */
  totalPlanEtp = computed<number>(() => {
    let sum = 0;
    for (const item of this.filteredOperations()) {
      sum += this.aggregateEtp(item.operation, 'total').previsionnel;
    }
    return sum;
  });
}
