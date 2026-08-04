import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { SearchBarComponent } from '../../../shared/components/search-bar/search-bar.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import { PriorityBadgeComponent } from '../../../shared/components/priority-badge/priority-badge.component';
import { PlanPlanificationMensuelleComponent } from './plan-planification-mensuelle.component';
import {
  FilterBarComponent,
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
  FilterOption,
  FilterValue,
} from '../../../shared/components/filters';
import { createFilterSet } from '../../../shared/utils/filter-set';
import {
  yearBudgetPrev, yearBudgetReal, yearJoursPrev, yearJoursReal,
} from '../../../shared/utils/operation-budget';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  Enjeu, Indicateur, Operation, OperationAnnee
} from '../../../core/models/enjeu.model';
import {
  ActionStatus, ACTION_LEGEND_ITEMS, getActionIcon, getActionStatusForYear,
  hasActionCellForYear,
  GlobalRealisationKind, getGlobalRealisationKind, getGlobalRealisationLabelKey,
} from './action-status.util';
import { exportFilename } from '../../../shared/utils/csv-export';
import { downloadBlob } from '../../../shared/utils/chart-image-export';
import { GridCell, GridExportPayload, GridRow } from '../../../shared/utils/grid-export';

type SuiviTab = 'planification' | 'realisation' | 'budget' | 'rh';

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
    CommonModule, RouterModule, MatButtonModule, MatMenuModule,
    MatProgressSpinnerModule, MatTooltipModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent, SearchBarComponent,
    PlanPlanificationMensuelleComponent, TagComponent, PriorityBadgeComponent, PaginationComponent,
    FilterBarComponent, FilterDropdownComponent, FilterOptionListComponent, FilterPanelDirective
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
  private readonly snackBar = inject(MatSnackBar);

  planId = signal<number | null>(null);
  /** #637 — le classeur est rendu par le serveur : l'export n'est pas instantané. */
  isExporting = signal(false);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  planStatut = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // #375 — le suivi (réalisations) ne peut être saisi qu'une fois le plan validé.
  // Statuts considérés comme « validés » (suivi pertinent) : valide/modifie/mi_parcours/archive.
  private readonly VALIDATED_STATUSES = ['valide', 'modifie', 'mi_parcours', 'archive'];
  planNotValidated = computed(() => {
    const s = this.planStatut();
    return !!s && !this.VALIDATED_STATUSES.includes(s);
  });

  // Data
  allOperations = signal<FlatOperation[]>([]);
  planYearStart = signal<number>(new Date().getFullYear());
  planYearEnd = signal<number>(new Date().getFullYear() + 9);

  // Tabs principaux (Phase 3)
  activeTab = signal<SuiviTab>('realisation');
  currentYear = signal<number>(new Date().getFullYear());

  // #568 — pagination des tableaux (actions / budget / RH).
  readonly pageSize = 20;
  page = signal<number>(1);

  constructor() {
    // #568 — revenir à la page 1 dès que la liste filtrée change (filtres,
    // recherche, données), pour ne pas rester bloqué sur une page hors bornes.
    effect(() => {
      this.filteredOperations();
      this.page.set(1);
    });
  }

  // Filters
  //
  // #592 — état porté par `createFilterSet` (`reset()` / `hasActive()` dérivés).
  // Les filtres mono-sélection sont stockés en tableau : c'est le contrat unique de
  // `app-filter-option-list`, un tableau vide valant « pas de filtre ». Cela unifie aussi
  // le calcul du compteur de valeurs actives entre mono et multi-sélection.
  readonly filters = createFilterSet({
    categorieAction: [] as string[],
    enjeu: [] as number[],
    priorite: [] as string[],
    // #379 — recherche textuelle sur le libellé d'action + filtre organisme.
    text: '',
    organisme: [] as number[],
    // #354 — filtre par année (affiche une seule année) + par réalisation.
    year: [] as number[],
    realisation: 'all' as 'all' | 'realized' | 'not-realized',
  }, {
    // « all » est la valeur neutre de ce filtre, pas une valeur active.
    isActive: { realisation: (v) => v !== 'all' },
  });

  // Libellés des 9 catégories d'action réserve CT88, indexés par code 2 lettres
  // (SP, CS, IP, PA…). Sert à afficher la catégorie CT88 dans le filtre, même
  // pour les actions sans catégorie réserve explicite (déduite du code). (#98)
  private categorieLabelByPrefix = signal<Map<string, string>>(new Map());

  // Computed
  /** Liste des colonnes années entre planYearStart et planYearEnd. */
  /** Toutes les années du plan (pour le sélecteur de filtre). */
  allYears = computed(() => {
    const start = this.planYearStart();
    const end = this.planYearEnd();
    const years: number[] = [];
    for (let y = start; y <= end; y++) {
      years.push(y);
    }
    return years;
  });

  yearColumns = computed(() => {
    // #459 — le filtre d'année ne réduit plus le tableau à une seule colonne :
    // toutes les années restent affichées, seul l'ensemble des lignes (actions)
    // est filtré (cf. filteredOperations).
    return this.allYears();
  });

  /** Filtres communs (catégorie/enjeu/priorité/texte/organisme), hors filtre
   *  « Réalisation ». Sert de base au tableau et à la planification mensuelle. */
  baseFilteredOperations = computed(() => {
    let ops = this.allOperations();
    // Un tableau vide vaut « pas de filtre » (#592).
    const cat = this.filters.categorieAction();
    const enjeu = this.filters.enjeu();
    const prio = this.filters.priorite();
    const text = this.normalize(this.filters.text());
    const org = this.filters.organisme();

    if (cat.length) {
      ops = ops.filter(o => cat.includes(this.getCategorieAction(o.operation) ?? ''));
    }
    if (enjeu.length) {
      ops = ops.filter(o => enjeu.includes(o.enjeuId));
    }
    if (prio.length) {
      ops = ops.filter(o => prio.includes(o.operation.priorite_label ?? ''));
    }
    if (text) {
      // Recherche sur le libellé ET les codes d'action (code d'affichage CS1 +
      // code de référence REM-BA02).
      ops = ops.filter(o =>
        this.normalize(o.operation.libelle).includes(text)
        || this.normalize(this.actionCodes(o.operation)).includes(text)
      );
    }
    if (org.length) {
      ops = ops.filter(o =>
        this.getOrganismesForOp(o.operation).some(g => org.includes(g.id_organisme)));
    }
    return ops;
  });

  filteredOperations = computed(() => {
    let ops = this.baseFilteredOperations();
    const fy = this.selectedYear();

    // #459 — filtre par année : ne garder que les actions ayant une case non
    // blanche (un statut : prévu, réalisé, partiel, non prévu…) à cette année.
    // Toutes les colonnes d'années restent affichées.
    if (fy != null) {
      ops = ops.filter(o => hasActionCellForYear(o.operation, fy));
    }

    // #354 — filtre par réalisation. Si une année est sélectionnée, la
    // réalisation est évaluée sur cette année uniquement, sinon sur toutes.
    const real = this.filters.realisation();
    if (real !== 'all') {
      const years = fy != null ? [fy] : this.yearColumns();
      ops = ops.filter(o => {
        const realized = years.some(y => this.opYearIsRealized(o.operation, y));
        return real === 'realized' ? realized : !realized;
      });
    }
    return ops;
  });

  /** #354 — vrai si l'action a une réalisation (totale ou partielle) cette année. */
  private opYearIsRealized(op: Operation, year: number): boolean {
    const st = this.getActionStatusForYear(op, year);
    return st === 'planned-realized' || st === 'planned-partial'
        || st === 'realized-unplanned' || st === 'partial-unplanned';
  }

  /** Normalisation pour la recherche : minuscules, sans accents. */
  private normalize(s: string): string {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  /** #379 — Organismes disponibles (ventilés sur au moins une action) pour le filtre. */
  availableOrganismes = computed<{ id_organisme: number; nom: string }[]>(() => {
    const seen = new Map<number, string>();
    for (const o of this.allOperations()) {
      for (const g of this.getOrganismesForOp(o.operation)) {
        if (!seen.has(g.id_organisme)) seen.set(g.id_organisme, g.nom);
      }
    }
    return [...seen.entries()]
      .map(([id_organisme, nom]) => ({ id_organisme, nom }))
      .sort((a, b) => a.nom.localeCompare(b.nom));
  });

  /**
   * Catégorie d'action au sens CT88 (CS, IP, PA, PR, SP…). Le filtre « Catégories
   * d'action » doit refléter ces grandes catégories de la méthode PG, pas les
   * types détaillés / suivis. (#98)
   *
   * On s'appuie sur `op.code_prefix` (déjà calculé côté backend) : il vaut le code
   * de la catégorie d'action réserve si elle est renseignée (#228), sinon le
   * préfixe 2 lettres déduit du code du type d'action (ex. « CS1 » → « CS »). On
   * le traduit ensuite en libellé CT88. Repli sur le libellé brut si le préfixe
   * n'est pas connu (ex. type d'action sans code CT88).
   */
  /**
   * Code(s) d'action affiché(s) dans le tableau, et servant à la recherche :
   * code d'affichage (CS1, IP2 — cohérent avec l'arborescence des enjeux) suivi
   * du code de référence (REM-BA02) quand il est renseigné. Séparés par « · ».
   */
  actionCodes(op: Operation): string {
    const parts: string[] = [];
    const display = op.code_affichage || op.code_prefix;
    if (display) parts.push(display);
    if (op.code_operation) parts.push(op.code_operation);
    return parts.join(' · ');
  }

  getCategorieAction(op: Operation): string | null {
    const prefix = op.code_prefix?.toUpperCase();
    if (prefix) {
      const label = this.categorieLabelByPrefix().get(prefix);
      if (label) return label;
    }
    return op.categorie_action_reserve_label || op.type_action_label || null;
  }

  // Unique filter values
  categorieActions = computed(() => {
    const labels = new Set<string>();
    this.allOperations().forEach(o => {
      const cat = this.getCategorieAction(o.operation);
      if (cat) labels.add(cat);
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

  // ===========================================================================
  // #568 — Pagination
  // ===========================================================================

  /** Onglet Réalisation : page courante de la liste à plat des actions. */
  pagedOperations = computed<FlatOperation[]>(() => {
    const start = (this.page() - 1) * this.pageSize;
    return this.filteredOperations().slice(start, start + this.pageSize);
  });

  /** Nombre total de lignes d'action affichées dans les tableaux groupés
   *  Budget / RH (une action ventilée sur N organismes compte N fois). */
  orgGroupsRowCount = computed<number>(() =>
    this.operationsByOrganisme().reduce((sum, g) => sum + g.operations.length, 0)
  );

  /**
   * Onglets Budget / RH : groupes d'organisme dont seules les lignes de la page
   * courante sont affichées. Les sous-totaux d'en-tête restent calculés sur le
   * groupe COMPLET (`fullOperations`) pour ne pas fausser « Total Plan de gestion ».
   */
  pagedOrgGroups = computed<{
    id_organisme: number;
    nom: string;
    fullOperations: FlatOperation[];
    operations: FlatOperation[];
  }[]>(() => {
    const start = (this.page() - 1) * this.pageSize;
    const end = start + this.pageSize;
    let globalIdx = 0;
    const out: { id_organisme: number; nom: string; fullOperations: FlatOperation[]; operations: FlatOperation[] }[] = [];
    for (const group of this.operationsByOrganisme()) {
      const onPage: FlatOperation[] = [];
      for (const op of group.operations) {
        if (globalIdx >= start && globalIdx < end) onPage.push(op);
        globalIdx++;
      }
      if (onPage.length > 0) {
        out.push({
          id_organisme: group.id_organisme,
          nom: group.nom,
          fullOperations: group.operations,
          operations: onPage,
        });
      }
    }
    return out;
  });

  onPageChange(p: number): void {
    this.page.set(p);
  }

  /**
   * #570 — Choix de l'année de référence des tableaux de synthèse Budget / RH.
   * La colonne « Année en cours » affiche cette année et « Période écoulée » se
   * réajuste aux années strictement antérieures (cf. aggregate).
   */
  setCurrentYear(year: number): void {
    this.currentYear.set(year);
  }

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

  // ============================================
  // #592 — options des filtres, au format du kit UI
  // ============================================

  categorieFilterOptions = computed<FilterOption<string>[]>(() =>
    this.categorieActions().map((c) => ({ value: c, label: c })),
  );

  enjeuFilterOptions = computed<FilterOption<number>[]>(() =>
    this.enjeux().map((e) => ({ value: e.id, label: e.libelle })),
  );

  prioriteFilterOptions = computed<FilterOption<string>[]>(() =>
    this.priorites().map((p) => ({ value: p, label: p })),
  );

  organismeFilterOptions = computed<FilterOption<number>[]>(() =>
    this.availableOrganismes().map((o) => ({ value: o.id_organisme, label: o.nom })),
  );

  yearFilterOptions = computed<FilterOption<number>[]>(() =>
    this.allYears().map((y) => ({ value: y, label: String(y) })),
  );

  /** Année filtrée (mono-sélection stockée en tableau), ou `null` si « toutes ». */
  selectedYear = computed<number | null>(() => this.filters.year()[0] ?? null);

  /** #354 — les trois états de réalisation, libellés traduits. */
  realisationFilterOptions = computed<FilterOption<string>[]>(() => [
    {
      value: 'realized',
      label: this.translate.instant('plans.suivis.actions.realisationDone'),
    },
    {
      value: 'not-realized',
      label: this.translate.instant('plans.suivis.actions.realisationNone'),
    },
  ]);

  /** Le filtre « réalisation » n'est pas un tableau : adaptation vers/depuis la liste. */
  realisationSelection = computed<string[]>(() =>
    this.filters.realisation() === 'all' ? [] : [this.filters.realisation()],
  );

  onRealisationChange(values: string[]): void {
    const next = values[0];
    this.filters.realisation.set(
      next === 'realized' || next === 'not-realized' ? next : 'all',
    );
  }

  // #379 — légende partagée (util action-status)
  legendItems = ACTION_LEGEND_ITEMS;

  getActionIcon(status: ActionStatus | null): string {
    return getActionIcon(status);
  }

  ngOnInit(): void {
    // #379 — restaurer l'onglet depuis l'URL (retour « précédent » depuis la saisie)
    const tabParam = this.route.snapshot.queryParamMap.get('tab');
    if (tabParam === 'planification' || tabParam === 'budget' || tabParam === 'rh') {
      this.activeTab.set(tabParam);
    }

    // Charge les 9 catégories CT88 (mnémonique = code 2 lettres → libellé).
    this.adminService.getNomenclaturesByType('CATEGORIE_ACTION_RESERVE').subscribe({
      next: (noms) => {
        const map = new Map<string, string>();
        noms.forEach(n => { if (n.mnemonique) map.set(n.mnemonique.toUpperCase(), n.label); });
        this.categorieLabelByPrefix.set(map);
      }
    });

    const slug = this.route.snapshot.paramMap.get('slug');
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.planStatut.set(plan.statut ?? null);
          if (plan.annee_debut && plan.annee_fin) {
            this.planYearStart.set(plan.annee_debut);
            this.planYearEnd.set(plan.annee_fin);
            // #570 — année de référence par défaut : l'année courante bornée à
            // la période du plan (pour que « Année en cours » soit pertinente).
            const now = new Date().getFullYear();
            this.currentYear.set(Math.min(Math.max(now, plan.annee_debut), plan.annee_fin));
          }
          this.loadData(plan.id_pg);
        }
      });
    }
  }

  private loadData(planId: number): void {
    this.isLoading.set(true);

    // Load enjeux with nested operations. forceRefresh=true : cette page affiche
    // les réalisations annuelles, qui viennent d'être modifiées dans la saisie ;
    // sans forcer, le cache de getPlanEnjeux renverrait l'état d'avant la saisie
    // (il fallait rafraîchir la page pour voir la mise à jour).
    this.enjeuService.getPlanEnjeux(planId, true).subscribe({
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
    const push = (op: Operation) => {
      if (!seenIds.has(op.id_operation)) {
        seenIds.add(op.id_operation);
        result.push({
          operation: op,
          enjeuLibelle: enjeu.intitule_court || enjeu.libelle,
          enjeuId: enjeu.id_enjeu
        });
      }
    };

    for (const ind of indicateurs) {
      // Actions rattachées via une métrique de l'indicateur.
      for (const met of ind.metriques || []) {
        for (const op of met.operations || []) {
          push(op);
        }
      }
      // #540 — actions rattachées directement à l'indicateur (sans métrique,
      // #367/#539). Sans cela, une action liée à un indicateur sans métrique
      // n'apparaissait pas dans le suivi des actions.
      for (const op of ind.operations || []) {
        push(op);
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
    return getActionStatusForYear(op, year);
  }

  /**
   * #354 — Ouvre la fiche synthétique (imprimable/exportable) de l'action.
   * #455 — Ouverture dans un nouvel onglet pour ne pas perdre le suivi en cours.
   */
  navigateToViewOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    const url = this.router.serializeUrl(
      this.router.createUrlTree(['/plans', slug, 'enjeux', 'operations', operationId, 'fiche'], {
        queryParams: { from: 'suivi' }, // #529 — retour vers le suivi des actions
      })
    );
    window.open(url, '_blank', 'noopener');
  }

  // ===========================================================================
  // #379 — Réalisation GLOBALE : 3 icônes (réalisé / partiellement / non réalisé)
  // ===========================================================================

  /**
   * #460 — « Kind » d'affichage du statut global : réalisé / partiel /
   * en-cours (sablier) / non-commencée / non-réalisé. Distingue désormais
   * EN_COURS et NON_DEMARRE (auparavant fondus dans « non réalisé »).
   */
  globalRealisationKind(mnemonique: string | null | undefined): GlobalRealisationKind {
    return getGlobalRealisationKind(mnemonique);
  }

  /**
   * Icône image du statut global pour les kinds rendus via <img>
   * (réalisé / partiel / non réalisé). En-cours et non-commencée utilisent
   * une icône Flaticon (cf. template).
   */
  globalRealisationIcon(mnemonique: string | null | undefined): string {
    switch (this.globalRealisationKind(mnemonique)) {
      case 'realise': return 'assets/images/icons/realise.png';
      case 'partiel': return 'assets/images/icons/partiellement-realise.png';
      default: return 'assets/images/icons/non-realise-seul.svg';
    }
  }

  /** Clé i18n du libellé du statut global (pour alt/tooltip). */
  globalRealisationLabelKey(mnemonique: string | null | undefined): string {
    return getGlobalRealisationLabelKey(mnemonique);
  }

  // ===========================================================================
  // Phase 3 - Agrégations Budget / RH
  // ===========================================================================

  setTab(tab: SuiviTab): void {
    this.activeTab.set(tab);
    this.page.set(1); // #568 — repartir en page 1 en changeant d'onglet
    // #379 — persister l'onglet dans l'URL pour le retrouver après « précédent »
    // depuis la saisie (sinon on revenait toujours sur Réalisation).
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab: tab === 'realisation' ? null : tab },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
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

    let previsionnel = 0;
    let realise = 0;
    let hasRealise = false;

    // #616 — budget et RH sont DÉRIVÉS de ce qui est réellement saisi (détail
    // des coûts, coût salarial des lignes RH), quel que soit le mode de
    // ventilation : la vue globale lisait les seules enveloppes
    // `budget_fonctionnement` / `_investissement`, jamais alimentées dans les
    // modes « + type de poste », et affichait donc 0 € partout.
    for (const oa of annees) {
      if (metric === 'budget') {
        previsionnel += yearBudgetPrev(op, oa).total ?? 0;
        const real = yearBudgetReal(op, oa);
        if (real.hasValue) {
          realise += real.total ?? 0;
          hasRealise = true;
        }
      } else {
        previsionnel += yearJoursPrev(oa, true) ?? 0;
        const jours = yearJoursReal(oa);
        if (jours != null) {
          realise += jours;
          hasRealise = true;
        }
      }
    }

    const ecartPct = previsionnel > 0 ? ((realise - previsionnel) / previsionnel) * 100 : null;
    return { previsionnel, realise, hasRealise, ecartPct };
  }

  // ===========================================================================
  // #637 — Export CSV du tableau, dans l'état où il est affiché
  // ===========================================================================

  /**
   * Exporte l'onglet courant en classeur Excel mis en forme.
   *
   * L'export part des mêmes signaux que le rendu (`filteredOperations()` /
   * `operationsByOrganisme()`) : filtres, recherche et onglet sont donc repris
   * tels quels. Seule la pagination est ignorée — on exporte l'intégralité des
   * lignes filtrées, pas la page visible.
   *
   * La mise en forme est faite par le serveur : un CSV ne porte ni couleur
   * d'en-tête ni ligne de total détachée du reste.
   */
  exportTable(): void {
    const planId = this.planId();
    if (!planId || this.isExporting()) return;

    this.isExporting.set(true);
    this.adminService.downloadSuiviActionsXlsx(planId, this.buildExportPayload())
      .subscribe({
        next: (blob) => {
          this.isExporting.set(false);
          downloadBlob(
            exportFilename(['suivi-actions', this.activeTab(), this.planSlug()], 'xlsx'),
            blob,
          );
        },
        error: () => {
          this.isExporting.set(false);
          this.snackBar.open(
            this.t('plans.suivis.actions.export.error'),
            this.t('common.actions.close'),
            { duration: 4000 },
          );
        },
      });
  }

  private buildExportPayload(): GridExportPayload {
    const { entetes, lignes } = this.activeTab() === 'planification'
      ? this.buildPlanificationGrid()
      : this.activeTab() === 'realisation'
        ? this.buildRealisationGrid()
        : this.buildAggregationGrid(this.activeTab() === 'budget' ? 'budget' : 'etp');

    const isAggregation = this.activeTab() === 'budget' || this.activeTab() === 'rh';
    return {
      titre: `${this.t('plans.suivis.actions.title')} — ${this.planNom()}`,
      onglet: this.t(`plans.suivis.actions.tabs.${this.activeTab()}`),
      meta: this.buildExportMeta(),
      entetes,
      // Colonnes d'identification à garder sous les yeux quand on fait défiler
      // les années ou les périodes (l'onglet agrégé ouvre sur l'organisme).
      gel: this.identityHeaders().length + (isAggregation ? 1 : 0),
      lignes,
    };
  }

  /**
   * Rappel des filtres actifs, en tête du classeur : sans lui, deux exports du
   * même plan sont indiscernables une fois le fichier détaché de l'écran.
   */
  private buildExportMeta(): [string, string][] {
    const meta: [string, string][] = [
      [this.t('plans.suivis.actions.export.onglet'),
       this.t(`plans.suivis.actions.tabs.${this.activeTab()}`)],
    ];
    const ajouter = (cle: string, valeurs: string[]) => {
      if (valeurs.length) meta.push([this.t(cle), valeurs.join(', ')]);
    };
    const libelles = <T extends FilterValue>(options: FilterOption<T>[], choisis: T[]) =>
      options.filter(o => choisis.includes(o.value)).map(o => o.label);

    ajouter('plans.suivis.actions.categorieAction', this.filters.categorieAction());
    ajouter('plans.suivis.actions.enjeu',
      libelles(this.enjeuFilterOptions(), this.filters.enjeu()));
    ajouter('plans.suivis.actions.priorite', this.filters.priorite());
    ajouter('plans.suivis.actions.organisme',
      libelles(this.organismeFilterOptions(), this.filters.organisme()));
    if (this.selectedYear() != null) {
      meta.push([this.t('plans.suivis.actions.export.annee'), String(this.selectedYear())]);
    }
    if (this.filters.realisation() !== 'all') {
      meta.push([
        this.t('plans.suivis.actions.filterRealisation'),
        this.t(this.filters.realisation() === 'realized'
          ? 'plans.suivis.actions.realisationDone'
          : 'plans.suivis.actions.realisationNone'),
      ]);
    }
    if (this.filters.text().trim()) {
      meta.push([this.t('common.actions.search'), this.filters.text().trim()]);
    }
    return meta;
  }

  private t(key: string): string {
    return this.translate.instant(key);
  }

  /**
   * En-têtes d'identification de l'action, communs à tous les onglets.
   *
   * Retour de recette : « Code » portait à la fois le code d'affichage calculé
   * par CICADA (« IP1 ») et le code d'opération saisi librement par la
   * structure — deux identifiants distincts, donc deux colonnes.
   */
  private identityHeaders(): string[] {
    return [
      this.t('plans.suivis.actions.export.code'),
      this.t('plans.suivis.actions.export.codeOperation'),
      this.t('plans.suivis.actions.export.action'),
      this.t('plans.suivis.actions.enjeu'),
      this.t('plans.suivis.actions.categorieAction'),
      this.t('plans.suivis.actions.priorite'),
    ];
  }

  private identityCells(item: FlatOperation): GridCell[] {
    const op = item.operation;
    return [
      op.code_affichage || op.code_prefix || '',
      op.code_operation || '',
      op.libelle,
      item.enjeuLibelle,
      this.getCategorieAction(op) ?? '',
      op.priorite_label ?? '',
    ];
  }

  /** Cellules d'identification vides, pour une ligne de total. */
  private emptyIdentityCells(): GridCell[] {
    return this.identityHeaders().map(() => '');
  }

  /** Libellé traduit du statut annuel (case du tableau Réalisation). */
  private yearStatusLabel(op: Operation, year: number): string {
    const status = this.getActionStatusForYear(op, year);
    if (!status) return '';
    const item = ACTION_LEGEND_ITEMS.find(i => i.status === status);
    return item ? this.t(item.labelKey) : '';
  }

  /** Onglet Réalisation : une ligne par action, une colonne par année. */
  private buildRealisationGrid(): { entetes: string[]; lignes: GridRow[] } {
    const years = this.yearColumns();
    const entetes = [
      ...this.identityHeaders(),
      ...years.map(String),
      this.t('plans.suivis.actions.globalStatus.columnHeader'),
    ];
    const lignes: GridRow[] = this.filteredOperations().map(item => ({
      cellules: [
        ...this.identityCells(item),
        ...years.map(y => this.yearStatusLabel(item.operation, y)),
        this.t(this.globalRealisationLabelKey(item.operation.niveau_realisation_global_mnemonique)),
      ],
    }));
    return { entetes, lignes };
  }

  /**
   * Onglets Budget / RH : groupés par organisme comme à l'écran, chaque groupe
   * clos par sa ligne de total.
   *
   * Retour de recette : le total ouvrait le groupe et son libellé occupait la
   * colonne « Code », qui n'est pas la sienne. Il ferme désormais le groupe,
   * dans une ligne typée `total` que le serveur détache par un aplat — comme
   * un pied de tableau, où on le cherche naturellement.
   */
  private buildAggregationGrid(metric: 'budget' | 'etp'): { entetes: string[]; lignes: GridRow[] } {
    const unit = metric === 'budget' ? '€' : this.t('plans.suivis.actions.tabs.jours');
    const periods: AggregationPeriod[] = ['current', 'past', 'total'];
    const periodLabels = [
      `${this.t('plans.suivis.actions.tabs.col.current')} (${this.currentYear()})`,
      this.t('plans.suivis.actions.tabs.col.past'),
      this.t('plans.suivis.actions.tabs.col.total'),
    ];
    const prev = this.t('plans.suivis.actions.export.previsionnel');
    const real = this.t('plans.suivis.actions.export.realise');

    const entetes = [
      this.t('plans.suivis.actions.organisme'),
      ...this.identityHeaders(),
      ...periodLabels.flatMap(p => [`${p} — ${prev} (${unit})`, `${p} — ${real} (${unit})`]),
    ];

    const lignes: GridRow[] = [];
    for (const group of this.operationsByOrganisme()) {
      const orgName = group.nom === '__plan_general__'
        ? this.t('plans.suivis.actions.planGeneral')
        : group.nom;

      for (const item of group.operations) {
        const cells = periods.map(p => metric === 'budget'
          ? this.aggregateBudget(item.operation, p)
          : this.aggregateEtp(item.operation, p));
        lignes.push({
          cellules: [
            orgName,
            ...this.identityCells(item),
            ...cells.flatMap(c => [c.previsionnel, c.hasRealise ? c.realise : null]),
          ],
        });
      }

      // Le libellé du total va dans la colonne « Organisme », celle qui
      // identifie le groupe — pas dans « Code », qui n'est pas la sienne.
      const totals = periods.map(p => this.groupAggregate(group.operations, p, metric));
      lignes.push({
        type: 'total',
        cellules: [
          `${this.t('plans.suivis.actions.export.totalGroupe')} ${orgName}`,
          ...this.emptyIdentityCells(),
          ...totals.flatMap(c => [c.previsionnel, c.hasRealise ? c.realise : null]),
        ],
      });
    }
    return { entetes, lignes };
  }

  /**
   * Onglet Planification : une ligne par (action, année programmée), avec les
   * mois prévus et les mois effectivement réalisés. Indépendant de la vue
   * agenda/calendrier, qui n'est qu'une mise en forme de ces mêmes données.
   */
  private buildPlanificationGrid(): { entetes: string[]; lignes: GridRow[] } {
    const months = this.t('plans.suivis.planification.monthsShort').split(',');
    const monthNames = (map: Record<string, boolean> | null | undefined): string =>
      Object.entries(map || {})
        .filter(([, v]) => !!v)
        .map(([k]) => Number(k))
        .filter(n => n >= 1 && n <= 12)
        .sort((a, b) => a - b)
        .map(n => (months[n - 1] ?? String(n)).trim())
        .join(' ');

    const entetes = [
      ...this.identityHeaders(),
      this.t('plans.suivis.actions.export.annee'),
      this.t('plans.suivis.actions.export.moisPrevus'),
      this.t('plans.suivis.actions.export.moisRealises'),
    ];

    const lignes: GridRow[] = [];
    const filterYear = this.selectedYear();
    for (const item of this.baseFilteredOperations()) {
      const annees = (item.operation.operation_annees || [])
        .filter((oa: OperationAnnee) => filterYear == null || oa.annee === filterYear)
        .sort((a: OperationAnnee, b: OperationAnnee) => a.annee - b.annee);
      for (const oa of annees) {
        lignes.push({
          cellules: [
            ...this.identityCells(item),
            oa.annee,
            monthNames(oa.periodicite_mensuelle),
            monthNames(oa.realisation?.periodicite_mensuelle_realisee),
          ],
        });
      }
    }
    return { entetes, lignes };
  }

}
