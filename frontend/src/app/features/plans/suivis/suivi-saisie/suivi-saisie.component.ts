/**
 * Page de saisie d'un suivi de réalisation (Phase 2 - Suivis).
 *
 * Route : /plans/:slug/suivis/saisie/:operation_id/:annee
 *
 * Modes de ventilation gérés :
 *   - 'none'        : budget + ETP saisis au niveau de l'année (un seul jeu de champs)
 *   - 'by_type'     : split fonctionnement / investissement au niveau de l'année
 *   - 'by_org'      : un sous-tableau par organisme, budget total par organisme
 *   - 'by_org_type' : un sous-tableau par organisme avec fonct + invest
 * Dans les deux modes ventilés par organisme, une ligne TOTAL agrège les organismes.
 *
 * La carte SIG et les indicateurs de réponse seront ajoutés en itération suivante.
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  FormArray, FormBuilder, FormGroup, FormsModule, ReactiveFormsModule,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { LeafletMapComponent } from '../../../../shared/components/leaflet-map/leaflet-map.component';
import { AdminService } from '../../../../core/services/admin.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { RealisationService } from '../../../../core/services/realisation.service';
import { Mesure, MesureCreatePayload } from '../../../../core/models/enjeu.model';
import {
  Operation,
  OperationAnnee,
  OperationAnneeOrganisme,
  RealisationUpsertPayload,
  RealisationOrganismeUpsertPayload,
} from '../../../../core/models/enjeu.model';

interface Niveau {
  id_nomenclature: number;
  mnemonique: string;
  label: string;
}

@Component({
  selector: 'app-suivi-saisie',
  standalone: true,
  imports: [
    CommonModule, RouterModule, FormsModule, ReactiveFormsModule,
    MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule,
    TranslateModule,
    HeaderComponent, PlanSidebarComponent, FormFieldComponent, LeafletMapComponent,
  ],
  templateUrl: './suivi-saisie.component.html',
  styleUrl: './suivi-saisie.component.scss',
})
export class SuiviSaisieComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly snack = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly realisationService = inject(RealisationService);

  // -------- Routing / context --------
  planSlug = signal<string | null>(null);
  planId = signal<number | null>(null);
  planNom = signal<string>('');
  operationId = signal<number | null>(null);
  selectedYear = signal<number>(new Date().getFullYear());

  // -------- Data --------
  operation = signal<Operation | null>(null);
  niveaux = signal<Niveau[]>([]);
  isLoading = signal(true);
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  // -------- Form --------
  form: FormGroup = this.fb.group({
    id_niveau_realisation: [null],
    periodicite_realisee: [false],
    budget_realise: [null],
    budget_fonctionnement_realise: [null],
    budget_investissement_realise: [null],
    etp_realise: [null],
    commentaires: [''],
    /** Une ligne par organisme quand ventilation_mode ∈ {by_org, by_org_type}. */
    organismes: this.fb.array<FormGroup>([]),
    /** Une ligne par métrique liée à l'opération (indicateurs de réponse). */
    indicateurs: this.fb.array<FormGroup>([]),
  });

  /** Helper d'accès typé aux FormArrays. */
  get organismesFA(): FormArray<FormGroup> {
    return this.form.get('organismes') as FormArray<FormGroup>;
  }
  get indicateursFA(): FormArray<FormGroup> {
    return this.form.get('indicateurs') as FormArray<FormGroup>;
  }

  /** Mesures existantes par metrique_id, pré-chargées au load. */
  private mesuresByMetrique = new Map<number, Mesure[]>();

  // -------- Computed --------
  ventilationMode = computed<'none' | 'by_org' | 'by_type' | 'by_org_type'>(() => {
    return this.operation()?.ventilation_mode ?? 'none';
  });

  /** Mode supporté par le MVP : pas de ventilation par organisme. */
  isOrgVentilation = computed(() => {
    const mode = this.ventilationMode();
    return mode === 'by_org' || mode === 'by_org_type';
  });

  /** Affiche la décomposition fonctionnement/investissement. */
  isByType = computed(() => this.ventilationMode() === 'by_type');

  /** Années sur lesquelles l'opération est programmée. */
  years = computed<number[]>(() => {
    const op = this.operation();
    if (!op || op.annee_min == null || op.annee_max == null) return [];
    const out: number[] = [];
    for (let y = op.annee_min; y <= op.annee_max; y++) out.push(y);
    return out;
  });

  /** Programmation de l'année active (prévisionnel). */
  currentOperationAnnee = computed<OperationAnnee | null>(() => {
    const op = this.operation();
    const year = this.selectedYear();
    return op?.operation_annees?.find(oa => oa.annee === year) ?? null;
  });

  /** Retourne l'OperationAnnee pour une année donnée (ou null). */
  getOaForYear(year: number): OperationAnnee | null {
    return this.operation()?.operation_annees?.find(oa => oa.annee === year) ?? null;
  }

  /** Liste des organismes ventilés pour le mode by_org/by_org_type (déduplication entre années). */
  organismesList = computed<{ id_organisme: number; nom: string }[]>(() => {
    if (!this.isOrgVentilation()) return [];
    const op = this.operation();
    const seen = new Map<number, string>();
    for (const oa of op?.operation_annees || []) {
      for (const oao of oa.organismes || []) {
        if (!seen.has(oao.id_organisme)) {
          seen.set(oao.id_organisme, oao.organisme_nom || `Org #${oao.id_organisme}`);
        }
      }
    }
    return [...seen.entries()].map(([id_organisme, nom]) => ({ id_organisme, nom }));
  });

  /** Retourne l'OperationAnneeOrganisme pour un (year, organisme_id). */
  getOaoForYearOrg(year: number, orgId: number) {
    const oa = this.getOaForYear(year);
    return oa?.organismes?.find(o => o.id_organisme === orgId) ?? null;
  }

  /** Helper d'affichage pour les cellules numériques (€/jours). */
  formatNumber(value: any, suffix: string = ''): string {
    if (value === null || value === undefined || value === '') return '—';
    const num = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(num)) return '—';
    return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(num) + suffix;
  }

  /** Totaux ventilés par année — pour ligne TOTAL en mode by_org/by_org_type. */
  getTotalForYear(year: number, key: 'prev_fonct' | 'prev_invest' | 'prev_etp'
                                  | 'real_fonct' | 'real_invest' | 'real_etp'): number {
    const oa = this.getOaForYear(year);
    if (!oa) return 0;
    let sum = 0;
    for (const oao of oa.organismes || []) {
      switch (key) {
        case 'prev_fonct':  sum += Number(oao.budget_fonctionnement || 0); break;
        case 'prev_invest': sum += Number(oao.budget_investissement || 0); break;
        case 'prev_etp':    sum += Number(oao.etp || 0); break;
        case 'real_fonct':  sum += Number(oao.realisation?.budget_fonctionnement_realise || 0); break;
        case 'real_invest': sum += Number(oao.realisation?.budget_investissement_realise || 0); break;
        case 'real_etp':    sum += Number(oao.realisation?.etp_realise || 0); break;
      }
    }
    return sum;
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      const opId = params.get('operation_id');
      const annee = params.get('annee');

      this.planSlug.set(slug);
      if (opId) this.operationId.set(Number(opId));
      if (annee) this.selectedYear.set(Number(annee));

      this.loadData();
    });
  }

  private loadData(): void {
    const slug = this.planSlug();
    const opId = this.operationId();
    if (!slug || !opId) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Plan (pour breadcrumb + sidebar) — slug → plan via AdminService
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
      },
      error: (err) => {
        this.errorMessage.set(this.translate.instant('plans.suivis.saisie.errors.planNotFound'));
        this.isLoading.set(false);
      },
    });

    // Nomenclature niveaux de réalisation
    this.adminService.getNomenclaturesByType('NIVEAU_REALISATION').subscribe({
      next: (list) => this.niveaux.set(list),
      error: () => this.niveaux.set([]),
    });

    // Opération + sa programmation annuelle et ses réalisations
    this.enjeuService.getOperation(opId).subscribe({
      next: (op) => {
        this.operation.set(op);
        this.loadMesuresForMetriques(op);
        this.hydrateFormFromCurrentYear();
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.saisie.errors.operationNotFound'));
        this.isLoading.set(false);
      },
    });
  }

  /** Charge les Mesures existantes pour chaque métrique de l'opération. */
  private loadMesuresForMetriques(op: Operation): void {
    this.mesuresByMetrique.clear();
    const metriques = op.metriques || [];
    if (!metriques.length) {
      this.hydrateIndicateursArray();
      return;
    }
    let remaining = metriques.length;
    for (const m of metriques) {
      this.enjeuService.getMesuresByMetrique(m.id_metrique).subscribe({
        next: (list) => this.mesuresByMetrique.set(m.id_metrique, list),
        error: () => this.mesuresByMetrique.set(m.id_metrique, []),
        complete: () => {
          if (--remaining === 0) this.hydrateIndicateursArray();
        },
      });
    }
  }

  /** Reconstruit le FormArray des indicateurs depuis les métriques liées. */
  private hydrateIndicateursArray(): void {
    const fa = this.indicateursFA;
    while (fa.length) fa.removeAt(0);

    const op = this.operation();
    const year = this.selectedYear();
    if (!op?.metriques?.length) return;

    for (const met of op.metriques) {
      const mesures = this.mesuresByMetrique.get(met.id_metrique) ?? [];
      const existing = mesures.find(mm => mm.date_mesure && new Date(mm.date_mesure).getFullYear() === year);

      fa.push(this.fb.group({
        id_metrique: [met.id_metrique],
        nom_metrique: [met.nom_metrique],
        indicateur_nom: [met.indicateur_nom],
        id_mesure: [existing?.id_mesure ?? null],
        valeur: [existing?.valeur ?? ''],
      }));
    }
  }

  private hydrateFormFromCurrentYear(): void {
    const oa = this.currentOperationAnnee();
    const r = oa?.realisation;
    this.form.patchValue({
      id_niveau_realisation: r?.id_niveau_realisation ?? null,
      periodicite_realisee: r?.periodicite_realisee ?? false,
      budget_realise: r?.budget_realise ?? null,
      budget_fonctionnement_realise: r?.budget_fonctionnement_realise ?? null,
      budget_investissement_realise: r?.budget_investissement_realise ?? null,
      etp_realise: r?.etp_realise ?? null,
      commentaires: r?.commentaires ?? '',
    });
    this.hydrateOrganismesArray(oa);
  }

  /** Reconstruit le FormArray des organismes à partir de l'OperationAnnee active. */
  private hydrateOrganismesArray(oa: OperationAnnee | null): void {
    const fa = this.organismesFA;
    while (fa.length) fa.removeAt(0);

    if (!this.isOrgVentilation() || !oa?.organismes?.length) return;

    for (const oao of oa.organismes) {
      const r = oao.realisation;
      fa.push(this.fb.group({
        id_operation_annee_organisme: [oao.id_operation_annee_organisme],
        id_organisme: [oao.id_organisme],
        organisme_nom: [oao.organisme_nom ?? ''],
        // Planifié (lecture seule, exposé au template)
        plan_budget_fonctionnement: [oao.budget_fonctionnement],
        plan_budget_investissement: [oao.budget_investissement],
        plan_etp: [oao.etp],
        // Réalisé (éditable)
        budget_fonctionnement_realise: [r?.budget_fonctionnement_realise ?? null],
        budget_investissement_realise: [r?.budget_investissement_realise ?? null],
        etp_realise: [r?.etp_realise ?? null],
      }));
    }
  }

  // --- Totaux calculés pour le tableau ventilé (figma écran 05) ---

  totalPlanFonct = computed<number>(() => this.sumOrg('plan_budget_fonctionnement'));
  totalPlanInvest = computed<number>(() => this.sumOrg('plan_budget_investissement'));
  totalPlanEtp = computed<number>(() => this.sumOrg('plan_etp'));
  totalRealFonct = computed<number>(() => this.sumOrg('budget_fonctionnement_realise'));
  totalRealInvest = computed<number>(() => this.sumOrg('budget_investissement_realise'));
  totalRealEtp = computed<number>(() => this.sumOrg('etp_realise'));

  private sumOrg(controlName: string): number {
    return this.organismesFA.controls
      .map(c => Number(c.get(controlName)?.value || 0))
      .reduce((a, b) => a + b, 0);
  }

  selectYear(year: number): void {
    this.selectedYear.set(year);
    this.hydrateFormFromCurrentYear();
  }

  goBack(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'suivi-actions']);
    } else {
      this.router.navigate(['/plans']);
    }
  }

  goEditOperation(): void {
    const opId = this.operationId();
    if (!opId) return;
    this.router.navigate(['/plans', this.planSlug(), 'enjeux', 'operations', opId, 'modifier']);
  }

  submit(): void {
    const oa = this.currentOperationAnnee();
    if (!oa?.id_operation_annee) {
      this.snack.open(
        this.translate.instant('plans.suivis.saisie.errors.missingProgrammation'),
        this.translate.instant('common.actions.close'),
        { duration: 4000 },
      );
      return;
    }
    const v = this.form.value;
    const orgVentilation = this.isOrgVentilation();

    // 1) Payload annuel : niveau, périodicité, commentaires toujours.
    //    Budget/ETP au niveau année uniquement si pas de ventilation par org.
    const annualPayload: RealisationUpsertPayload = {
      id_operation_annee: oa.id_operation_annee,
      id_niveau_realisation: v.id_niveau_realisation || null,
      periodicite_realisee: !!v.periodicite_realisee,
      commentaires: v.commentaires || null,
    };
    if (!orgVentilation) {
      annualPayload.etp_realise = v.etp_realise ?? null;
      if (this.isByType()) {
        annualPayload.budget_fonctionnement_realise = v.budget_fonctionnement_realise ?? null;
        annualPayload.budget_investissement_realise = v.budget_investissement_realise ?? null;
      } else {
        annualPayload.budget_realise = v.budget_realise ?? null;
      }
    }

    // 2) Payloads par organisme (mode by_org / by_org_type).
    const orgPayloads: RealisationOrganismeUpsertPayload[] = orgVentilation
      ? this.organismesFA.controls
          .filter(c => c.get('id_operation_annee_organisme')?.value)
          .map(c => {
            const val = c.value as any;
            const p: RealisationOrganismeUpsertPayload = {
              id_operation_annee_organisme: val.id_operation_annee_organisme,
              budget_fonctionnement_realise: val.budget_fonctionnement_realise ?? null,
              etp_realise: val.etp_realise ?? null,
            };
            if (this.ventilationMode() === 'by_org_type') {
              p.budget_investissement_realise = val.budget_investissement_realise ?? null;
            }
            return p;
          })
      : [];

    // 3) Mesures (Indicateurs de réponse) : créer/mettre à jour pour l'année active.
    const yearActive = this.selectedYear();
    const measureCalls = this.indicateursFA.controls
      .map(c => c.value as any)
      .filter(v => (v.valeur ?? '').toString().trim() !== '')
      .map(v => {
        const payload: MesureCreatePayload = {
          id_metrique: v.id_metrique,
          valeur: String(v.valeur),
          date_mesure: `${yearActive}-12-31`,
        };
        return v.id_mesure
          ? this.enjeuService.updateMesure(v.id_mesure, payload)
          : this.enjeuService.createMesure(payload);
      });

    this.isSaving.set(true);
    const annualCall = this.realisationService.upsert(annualPayload);
    const orgCalls = orgPayloads.length
      ? forkJoin(orgPayloads.map(p => this.realisationService.upsertOrganisme(p)))
      : of([]);
    const mesureCallsObs = measureCalls.length ? forkJoin(measureCalls) : of([]);

    forkJoin([annualCall, orgCalls, mesureCallsObs]).subscribe({
      next: ([savedAnnual, savedOrgs, _savedMesures]) => {
        this.isSaving.set(false);
        this.snack.open(
          this.translate.instant('plans.suivis.saisie.messages.saved'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 },
        );
        // Synchroniser le signal `operation` avec les réponses serveur.
        const op = this.operation();
        if (op?.operation_annees) {
          const idx = op.operation_annees.findIndex(
            o => o.id_operation_annee === savedAnnual.id_operation_annee,
          );
          if (idx >= 0) {
            const target = op.operation_annees[idx];
            target.realisation = savedAnnual;
            if (target.organismes && (savedOrgs as any[])?.length) {
              for (const so of savedOrgs as any[]) {
                const idxOrg = target.organismes.findIndex(
                  (oao: OperationAnneeOrganisme) =>
                    oao.id_operation_annee_organisme === so.id_operation_annee_organisme,
                );
                if (idxOrg >= 0) target.organismes[idxOrg].realisation = so;
              }
            }
            this.operation.set({ ...op });
          }
        }
      },
      error: () => {
        this.isSaving.set(false);
        this.snack.open(
          this.translate.instant('plans.suivis.saisie.errors.saveFailed'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
      },
    });
  }
}
