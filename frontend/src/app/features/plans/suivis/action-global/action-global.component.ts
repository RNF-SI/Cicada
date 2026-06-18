import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Operation, OperationAnnee, Mesure } from '../../../../core/models/enjeu.model';
import {
  ActionStatus, ACTION_LEGEND_ITEMS, getActionIcon, getActionStatusForYear
} from '../action-status.util';

interface YearRow {
  annee: number;
  status: ActionStatus | null;
  budgetPrev: number;
  budgetReal: number;
  etpPrev: number;
  etpReal: number;
}

interface ResponseIndicator {
  id_metrique: number;
  indicateur_nom: string | null;
  nom_metrique: string;
  valeur_cible: string;
  byYear: Map<number, string>;
}

/** Surcharge manuelle proposée sur la page (3 résultats). */
type ManualResult = 'TERMINE' | 'PARTIEL' | 'NON_REALISE';

/**
 * #379 — Page globale d'une action : statut de réalisation global (modifiable),
 * indicateurs de réponse (cible + valeur par année), totaux budget/RH et
 * récapitulatif annuel (icône de réalisation + budget/RH).
 */
@Component({
  selector: 'app-action-global',
  standalone: true,
  imports: [
    CommonModule, FormsModule, RouterModule, MatButtonModule, MatProgressSpinnerModule,
    MatTooltipModule, TranslateModule, HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './action-global.component.html',
  styleUrl: './action-global.component.scss'
})
export class ActionGlobalComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  operation = signal<Operation | null>(null);

  /** #356 — Commentaire global (textarea), non obligatoire. */
  commentaire = signal<string>('');

  /**
   * #356 — L'ajustement manuel de la réalisation globale est une OPTION, pas une
   * action forcée : les contrôles restent repliés tant que l'utilisateur ne clique
   * pas sur « Ajuster manuellement » (déplié d'office si une surcharge ou un
   * commentaire existe déjà).
   */
  showOverride = signal<boolean>(false);

  /**
   * #356 — Section affichée sous la réalisation globale, via un toggle façon
   * tableau de bord : « Indicateurs de réponse » ou « Récapitulatif »
   * (budget/RH + récapitulatif annuel). « Récapitulatif » est l'onglet par défaut.
   */
  activeSection = signal<'reponse' | 'recap'>('recap');
  setSection(s: 'reponse' | 'recap'): void { this.activeSection.set(s); }

  legendItems = ACTION_LEGEND_ITEMS;

  /** Surcharge globale : droits gestionnaire (cf. canManageLifecycle). */
  private planReferentIds = signal<number[]>([]);
  private niveauIdByMnemonique = signal<Map<string, number>>(new Map());
  /** mesures par métrique (indicateurs de réponse). */
  private mesuresByMetrique = signal<Map<number, Mesure[]>>(new Map());
  /** Boutons de résultat proposés. */
  readonly manualResults: { value: ManualResult; labelKey: string }[] = [
    { value: 'TERMINE', labelKey: 'plans.suivis.actionGlobal.statut.realise' },
    { value: 'PARTIEL', labelKey: 'plans.suivis.actionGlobal.statut.partiel' },
    { value: 'NON_REALISE', labelKey: 'plans.suivis.actionGlobal.statut.nonRealise' },
  ];

  canManageGlobal = computed<boolean>(() => {
    if (this.authService.hasGlobalAccess() || this.authService.isAdminOrganisme()) return true;
    const uid = this.authService.currentUser()?.id;
    return uid != null && this.planReferentIds().includes(uid);
  });

  /** Années couvertes par l'action (annee_min..annee_max). */
  years = computed<number[]>(() => {
    const op = this.operation();
    if (!op) return [];
    const min = op.annee_min ?? new Date().getFullYear();
    const max = op.annee_max ?? min;
    const arr: number[] = [];
    for (let y = min; y <= max; y++) arr.push(y);
    return arr;
  });

  /** Indicateurs de réponse de l'action (type REPONSE) + valeurs par année. */
  responseIndicators = computed<ResponseIndicator[]>(() => {
    const op = this.operation();
    if (!op) return [];
    const reps = (op.metriques || []).filter(
      m => (m.indicateur_type || '').toUpperCase() === 'REPONSE');
    const map = this.mesuresByMetrique();
    return reps.map(m => {
      // Une métrique peut avoir plusieurs mesures la même année : on retient la
      // PLUS RÉCENTE (date_mesure), pour être cohérent avec le formulaire de suivi.
      const byYear = new Map<number, string>();
      const bestTs = new Map<number, number>();
      for (const mes of (map.get(m.id_metrique) || [])) {
        if (!mes.date_mesure) continue;
        const d = new Date(mes.date_mesure);
        const y = d.getFullYear();
        const t = d.getTime();
        if (!bestTs.has(y) || t >= (bestTs.get(y) as number)) {
          bestTs.set(y, t);
          byYear.set(y, mes.valeur);
        }
      }
      return {
        id_metrique: m.id_metrique,
        indicateur_nom: m.indicateur_nom ?? null,
        nom_metrique: m.nom_metrique,
        valeur_cible: m.etat_reference || '',
        byYear,
      };
    });
  });

  yearRows = computed<YearRow[]>(() => {
    const op = this.operation();
    if (!op) return [];
    return [...(op.operation_annees || [])]
      .sort((a, b) => a.annee - b.annee)
      .map(oa => ({
        annee: oa.annee,
        status: getActionStatusForYear(op, oa.annee),
        budgetPrev: this.budgetPrev(op, oa),
        budgetReal: this.budgetReal(op, oa),
        etpPrev: Number(oa.etp || 0),
        etpReal: Number(oa.realisation?.etp_realise || 0),
      }));
  });

  budgetTotal = computed(() => {
    const rows = this.yearRows();
    return {
      prev: rows.reduce((s, r) => s + r.budgetPrev, 0),
      real: rows.reduce((s, r) => s + r.budgetReal, 0),
    };
  });

  etpTotal = computed(() => {
    const rows = this.yearRows();
    return {
      prev: rows.reduce((s, r) => s + r.etpPrev, 0),
      real: rows.reduce((s, r) => s + r.etpReal, 0),
    };
  });

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    const opId = Number(this.route.snapshot.paramMap.get('operation_id'));
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planReferentIds.set((plan.referents ?? []).map(r => r.id_role));
        },
      });
    }
    this.adminService.getNomenclaturesByType('NIVEAU_REALISATION').subscribe({
      next: (noms) => {
        const map = new Map<string, number>();
        noms.forEach(n => { if (n.mnemonique) map.set(n.mnemonique, n.id_nomenclature); });
        this.niveauIdByMnemonique.set(map);
      }
    });
    if (opId) {
      this.enjeuService.getOperation(opId).subscribe({
        next: (op) => {
          this.operation.set(op);
          this.commentaire.set((op as any).niveau_realisation_global_commentaire ?? '');
          // Déplier d'office si une surcharge/commentaire existe déjà.
          if (op.niveau_realisation_global_manuel || this.commentaire().trim()) {
            this.showOverride.set(true);
          }
          this.isLoading.set(false);
          this.loadResponseMesures(op);
        },
        error: () => {
          this.errorMessage.set('Erreur lors du chargement de l\'action');
          this.isLoading.set(false);
        },
      });
    } else {
      this.isLoading.set(false);
    }
  }

  /** Charge les mesures des indicateurs de réponse (type REPONSE). */
  private loadResponseMesures(op: Operation): void {
    const reps = (op.metriques || []).filter(
      m => (m.indicateur_type || '').toUpperCase() === 'REPONSE');
    for (const m of reps) {
      this.enjeuService.getMesuresByMetrique(m.id_metrique).subscribe({
        next: (list) => {
          const map = new Map(this.mesuresByMetrique());
          map.set(m.id_metrique, list);
          this.mesuresByMetrique.set(map);
        },
      });
    }
  }

  // --- Statut global ---
  getActionIcon(status: ActionStatus | null): string { return getActionIcon(status); }

  /**
   * État global affiché. La réalisation globale est une appréciation sur TOUTE
   * la période de l'action — pas un avancement « à ce jour ». Les états temporels
   * du calcul (« en cours », « non démarré ») ne concluent donc rien : on renvoie
   * `a_evaluer`, qui invite à une évaluation manuelle plutôt que d'afficher un
   * statut trompeur.
   */
  globalState(): 'realise' | 'partiel' | 'non_realise' | 'a_evaluer' {
    const m = this.operation()?.niveau_realisation_global_mnemonique;
    switch (m) {
      case 'TERMINE': return 'realise';
      case 'PARTIEL': return 'partiel';
      case 'ABANDONNE':
      case 'REPORTE':
      case 'NON_REALISE': return 'non_realise';
      default: return 'a_evaluer'; // NON_DEMARRE, EN_COURS, null → rien de conclu
    }
  }

  /** Vrai quand aucune conclusion automatique n'est possible (à évaluer). */
  isAEvaluer(): boolean { return this.globalState() === 'a_evaluer'; }

  /** Icône du statut global affiché (vide pour « à évaluer »). */
  globalStateIcon(): string {
    switch (this.globalState()) {
      case 'realise': return 'assets/images/icons/realise.png';
      case 'partiel': return 'assets/images/icons/partiellement-realise.png';
      case 'non_realise': return 'assets/images/icons/non-realise-seul.svg';
      default: return '';
    }
  }

  /** Clé i18n du libellé du statut global affiché. */
  globalStateLabelKey(): string {
    switch (this.globalState()) {
      case 'realise': return 'plans.suivis.actionGlobal.statut.realise';
      case 'partiel': return 'plans.suivis.actionGlobal.statut.partiel';
      case 'non_realise': return 'plans.suivis.actionGlobal.statut.nonRealise';
      default: return 'plans.suivis.actionGlobal.statut.aEvaluer';
    }
  }

  /** Bouton actif = surcharge manuelle correspondant au résultat courant. */
  isCurrentResult(value: ManualResult): boolean {
    const op = this.operation();
    return !!op?.niveau_realisation_global_manuel
      && op?.niveau_realisation_global_mnemonique === value;
  }

  /**
   * Pose (value) ou retire (null = automatique) la surcharge du résultat global.
   * Le commentaire courant est préservé (#356).
   */
  setGlobalManuel(value: ManualResult | null): void {
    const op = this.operation();
    if (!op) return;
    const niveauId = value === null ? null : (this.niveauIdByMnemonique().get(value) ?? null);
    if (value !== null && niveauId === null) return;
    const comment = this.commentaire().trim();
    // Auto sans commentaire → suppression complète ; sinon on conserve le commentaire.
    const commentArg = (value === null && !comment) ? undefined : comment;
    this.enjeuService.setGlobalRealisation(op.id_operation, niveauId, commentArg).subscribe({
      next: (res) => this.applyGlobalResponse(res),
    });
  }

  /** #356 — Enregistre le commentaire seul (sans toucher au statut forcé). */
  saveComment(): void {
    const op = this.operation();
    if (!op) return;
    // Conserve le niveau forcé courant le cas échéant (commentaire indépendant).
    const niveauId = op.niveau_realisation_global_manuel
      ? (this.niveauIdByMnemonique().get(op.niveau_realisation_global_mnemonique || '') ?? null)
      : null;
    this.enjeuService.setGlobalRealisation(op.id_operation, niveauId, this.commentaire().trim()).subscribe({
      next: (res) => {
        this.applyGlobalResponse(res);
        this.snackBar.open(
          this.translate.instant('plans.suivis.actionGlobal.commentSaved'),
          this.translate.instant('common.actions.close'),
          { duration: 2500 }
        );
      }
    });
  }

  private applyGlobalResponse(res: { niveau_realisation_global_mnemonique: string | null;
                                     niveau_realisation_global_label: string | null;
                                     niveau_realisation_global_manuel: boolean;
                                     niveau_realisation_global_commentaire?: string | null; }): void {
    this.operation.update(cur => cur ? {
      ...cur,
      niveau_realisation_global_mnemonique: res.niveau_realisation_global_mnemonique,
      niveau_realisation_global_label: res.niveau_realisation_global_label,
      niveau_realisation_global_manuel: res.niveau_realisation_global_manuel,
      niveau_realisation_global_commentaire: res.niveau_realisation_global_commentaire ?? '',
    } as Operation : cur);
  }

  // --- Agrégation budget selon le mode de ventilation ---
  private budgetPrev(op: Operation, oa: OperationAnnee): number {
    const mode = op.ventilation_mode;
    if (mode === 'by_org' || mode === 'by_org_type') {
      return (oa.organismes || []).reduce(
        (s, o) => s + Number(o.budget_fonctionnement || 0) + Number(o.budget_investissement || 0), 0);
    }
    if (mode === 'by_type') {
      return Number(oa.budget_fonctionnement || 0) + Number(oa.budget_investissement || 0);
    }
    return Number(oa.budget || 0);
  }

  private budgetReal(op: Operation, oa: OperationAnnee): number {
    const mode = op.ventilation_mode;
    const r: any = oa.realisation;
    if (mode === 'by_org' || mode === 'by_org_type') {
      return (oa.organismes || []).reduce(
        (s, o: any) => s + Number(o.realisation?.budget_fonctionnement_realise || 0)
          + Number(o.realisation?.budget_investissement_realise || 0), 0);
    }
    if (mode === 'by_type') {
      return Number(r?.budget_fonctionnement_realise || 0) + Number(r?.budget_investissement_realise || 0);
    }
    return Number(r?.budget_realise || 0);
  }

  ecartPct(prev: number, real: number): number | null {
    return prev > 0 ? ((real - prev) / prev) * 100 : null;
  }
}
