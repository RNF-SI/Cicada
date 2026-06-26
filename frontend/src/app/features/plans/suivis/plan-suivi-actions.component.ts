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
import { SearchBarComponent } from '../../../shared/components/search-bar/search-bar.component';
import { PlanPlanificationMensuelleComponent } from './plan-planification-mensuelle.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  Enjeu, Indicateur, Operation, OperationAnnee
} from '../../../core/models/enjeu.model';
import {
  ActionStatus, ACTION_LEGEND_ITEMS, getActionIcon, getActionStatusForYear
} from './action-status.util';

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
    CommonModule, RouterModule, MatButtonModule, MatChipsModule, MatMenuModule,
    MatProgressSpinnerModule, MatTooltipModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent, SearchBarComponent,
    PlanPlanificationMensuelleComponent
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

  // Filters
  filterCategorieAction = signal<string | null>(null);
  filterEnjeu = signal<number | null>(null);
  filterPriorite = signal<string | null>(null);
  // #379 — recherche textuelle sur le libellé d'action + filtre organisme.
  filterText = signal<string>('');
  filterOrganisme = signal<number | null>(null);
  // #354 — filtre par année (affiche une seule année) + par réalisation.
  filterYear = signal<number | null>(null);
  filterRealisation = signal<'all' | 'realized' | 'not-realized'>('all');

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
    // #354 — si une année est sélectionnée, on n'affiche que cette colonne.
    const fy = this.filterYear();
    if (fy != null) return [fy];
    return this.allYears();
  });

  /** Filtres communs (catégorie/enjeu/priorité/texte/organisme), hors filtre
   *  « Réalisation ». Sert de base au tableau et à la planification mensuelle. */
  baseFilteredOperations = computed(() => {
    let ops = this.allOperations();
    const cat = this.filterCategorieAction();
    const enjeu = this.filterEnjeu();
    const prio = this.filterPriorite();
    const text = this.normalize(this.filterText());
    const org = this.filterOrganisme();

    if (cat) {
      ops = ops.filter(o => this.getCategorieAction(o.operation) === cat);
    }
    if (enjeu) {
      ops = ops.filter(o => o.enjeuId === enjeu);
    }
    if (prio) {
      ops = ops.filter(o => o.operation.priorite_label === prio);
    }
    if (text) {
      ops = ops.filter(o => this.normalize(o.operation.libelle).includes(text));
    }
    if (org) {
      ops = ops.filter(o => this.getOrganismesForOp(o.operation).some(g => g.id_organisme === org));
    }
    return ops;
  });

  filteredOperations = computed(() => {
    let ops = this.baseFilteredOperations();
    // #354 — filtre par réalisation (sur les années affichées : si une année est
    // sélectionnée, la réalisation est évaluée sur cette année uniquement).
    const real = this.filterRealisation();
    if (real !== 'all') {
      const years = this.yearColumns();
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
    return getActionStatusForYear(op, year);
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

  setOrganismeFilter(value: number | null): void {
    this.filterOrganisme.set(value);
  }

  clearFilters(): void {
    this.filterCategorieAction.set(null);
    this.filterEnjeu.set(null);
    this.filterPriorite.set(null);
    this.filterText.set('');
    this.filterOrganisme.set(null);
    this.filterYear.set(null);
    this.filterRealisation.set('all');
  }

  hasActiveFilters(): boolean {
    return !!(this.filterCategorieAction() || this.filterEnjeu() || this.filterPriorite()
      || this.filterText() || this.filterOrganisme()
      || this.filterYear() != null || this.filterRealisation() !== 'all');
  }

  getPrioriteClass(op: Operation): string {
    if (!op.priorite_label) return '';
    if (op.priorite_label.includes('1')) return 'priority-1';
    if (op.priorite_label.includes('2')) return 'priority-2';
    if (op.priorite_label.includes('3')) return 'priority-3';
    return '';
  }

  /**
   * #354 — Ouvre la fiche synthétique (imprimable/exportable) de l'action.
   * #455 — Ouverture dans un nouvel onglet pour ne pas perdre le suivi en cours.
   */
  navigateToViewOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    const url = this.router.serializeUrl(
      this.router.createUrlTree(['/plans', slug, 'enjeux', 'operations', operationId, 'fiche'])
    );
    window.open(url, '_blank', 'noopener');
  }

  // ===========================================================================
  // #379 — Réalisation GLOBALE : 3 icônes (réalisé / partiellement / non réalisé)
  // ===========================================================================

  /**
   * Ramène le niveau global aux 3 icônes du suivi : TERMINE → réalisé,
   * PARTIEL → partiellement réalisé, tout le reste (EN_COURS, NON_REALISE,
   * NON_DEMARRE, ABANDONNE, REPORTE, aucun) → non réalisé. La surcharge se fait
   * désormais sur la page globale de l'action.
   */
  globalRealisationIcon(mnemonique: string | null | undefined): string {
    switch (mnemonique) {
      case 'TERMINE': return 'assets/images/icons/realise.png';
      case 'PARTIEL': return 'assets/images/icons/partiellement-realise.png';
      default: return 'assets/images/icons/non-realise-seul.svg';
    }
  }

  /** Clé i18n du libellé du statut global (pour alt/tooltip). */
  globalRealisationLabelKey(mnemonique: string | null | undefined): string {
    switch (mnemonique) {
      case 'TERMINE': return 'plans.suivis.actionGlobal.statut.realise';
      case 'PARTIEL': return 'plans.suivis.actionGlobal.statut.partiel';
      default: return 'plans.suivis.actionGlobal.statut.nonRealise';
    }
  }

  // ===========================================================================
  // Phase 3 - Agrégations Budget / RH
  // ===========================================================================

  setTab(tab: SuiviTab): void {
    this.activeTab.set(tab);
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
}
