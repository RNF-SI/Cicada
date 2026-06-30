/**
 * Page de saisie d'un suivi d'indicateur (Phase Tableau de bord).
 *
 * Route : /plans/:slug/tableau-de-bord/saisie/:indicateur_id/:annee
 *
 * Conforme aux maquettes Figma 4132-21663, 4148-19285, 4140-24568, 4132-22057.
 *
 * Modes :
 *  - 'recap'         : vue tableau read-only (indicateur + métriques avec pastilles)
 *  - 'edit-auto'     : saisie des valeurs des métriques, score auto calculé
 *  - 'edit-override' : override manuel du score, message info + textarea raisons
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of, Subscription } from 'rxjs';
import { map } from 'rxjs/operators';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { CheckboxComponent } from '../../../../shared/components/checkbox/checkbox.component';
import { AdminService } from '../../../../core/services/admin.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Indicateur, Metrique, Mesure, MesureCreatePayload } from '../../../../core/models/enjeu.model';
import { formatScoreRange, isMetriqueIndetermine, computeMetriqueScore } from '../metrique-seuils.util';

// #510 — un seul mode d'édition cohérent (les anciens 'edit-auto'/'edit-override'
// sont fusionnés : auto par défaut, forçage manuel optionnel via une case).
type DisplayMode = 'recap' | 'edit';
type ScoreLevel = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

const SCORE_LEVELS: ScoreLevel[] = ['very-bad', 'bad', 'neutral', 'good', 'very-good'];

@Component({
  selector: 'app-indicateur-saisie',
  standalone: true,
  imports: [
    CommonModule, RouterModule, FormsModule, ReactiveFormsModule,
    MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent, CheckboxComponent,
  ],
  templateUrl: './indicateur-saisie.component.html',
  styleUrl: './indicateur-saisie.component.scss',
})
export class IndicateurSaisieComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly snack = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);

  planSlug = signal<string | null>(null);
  planId = signal<number | null>(null);
  planNom = signal<string>('');
  indicateurId = signal<number | null>(null);
  selectedYear = signal<number>(new Date().getFullYear());

  indicateur = signal<Indicateur | null>(null);
  isLoading = signal(true);
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  mode = signal<DisplayMode>('edit');
  scoreAuto = signal<number | null>(null);
  scoreOverride = signal<number | null>(null);
  commentaireOverride = signal<string>('');
  isOverridden = signal(false);
  overrideId = signal<number | null>(null);

  // #510 — Forçage manuel du résultat (case « Forcer le résultat manuellement »).
  // Décoché = résultat auto ; coché = override manuel. Indépendant de la saisie
  // des métriques (toujours possible).
  manualOverride = signal(false);

  // #510 — Tick incrémenté à chaque changement de valeur du formulaire pour
  // rendre `liveAutoScore` réellement réactif (les FormControl ne sont pas des
  // signals : sans cette dépendance, le computed restait figé).
  private formTick = signal(0);
  private formSub?: Subscription;

  /** Liste des années (annee_debut → annee_fin du plan). */
  planYearStart = signal<number>(new Date().getFullYear() - 5);
  planYearEnd = signal<number>(new Date().getFullYear() + 5);
  years = computed<number[]>(() => {
    const out: number[] = [];
    for (let y = this.planYearStart(); y <= this.planYearEnd(); y++) out.push(y);
    return out;
  });

  /** FormArray des valeurs par métrique. */
  form: FormGroup = this.fb.group({});

  /** Mesures préexistantes pour l'année active, indexées par id_metrique. */
  private mesuresByMetrique = new Map<number, Mesure>();

  // ---- Score helpers ----------------------------------------------------

  scoreLabels: Record<ScoreLevel, string> = {
    'very-bad': 'Très mauvais',
    'bad': 'Mauvais',
    'neutral': 'Moyen',
    'good': 'Bon',
    'very-good': 'Très bon',
    // #519 — un résultat sans donnée est désormais un état « indéterminé »
    // explicitement sélectionnable en saisie manuelle (rond gris conservé).
    'no-data': 'Indéterminé',
  };

  scoreToLevel(score: number | null | undefined): ScoreLevel {
    if (score === null || score === undefined) return 'no-data';
    const map: ScoreLevel[] = ['no-data', 'very-bad', 'bad', 'neutral', 'good', 'very-good'];
    return map[score] || 'no-data';
  }

  /** Score 1-5 d'une valeur selon la grille d'une métrique. Délègue à l'utilitaire
   *  partagé qui gère les 3 types (NUMERIQUE par seuils, CHIFFRE par valeur,
   *  TEXTE par libellé) — #464/#465 (avant : seuils NUMERIQUE uniquement). */
  valueToScore(value: any, met: Metrique): number | null {
    return computeMetriqueScore(met, value);
  }

  // #464/#465 — Saisie d'une métrique CHIFFRE/TEXTE : choix parmi les options de
  // la grille (libellés / valeurs), au lieu d'un champ texte libre.
  metricSaisieMode(met: Metrique): 'text-select' | 'chiffre-select' | 'free' {
    const type = (met as any).type_metrique_mnemonique;
    if ((type === 'TEXTE' || type === 'CHIFFRE') && this.metricGridOptions(met).length > 0) {
      return type === 'TEXTE' ? 'text-select' : 'chiffre-select';
    }
    return 'free';
  }

  /** Options sélectionnables d'une métrique CHIFFRE/TEXTE (niveaux actifs). */
  metricGridOptions(met: Metrique): string[] {
    const inactive: number[] = Array.isArray((met as any).inactive_levels) ? (met as any).inactive_levels : [];
    const type = (met as any).type_metrique_mnemonique;
    const out: string[] = [];
    for (let lvl = 1; lvl <= 5; lvl++) {
      if (inactive.includes(lvl)) continue;
      if (type === 'TEXTE') {
        const label = ((met as any)[`score_${lvl}_label`] ?? '').toString().trim();
        if (label) out.push(label);
      } else if (type === 'CHIFFRE') {
        const val = (met as any)[`score_${lvl}_val`];
        if (val !== null && val !== undefined) out.push(String(val));
      }
    }
    return out;
  }

  /** Score auto recalculé à partir des valeurs saisies (en live, #510).
   *  Lit `formTick()` pour se réévaluer à chaque modification du formulaire. */
  liveAutoScore = computed<number | null>(() => {
    this.formTick(); // dépendance réactive (valueChanges du formulaire)
    const ind = this.indicateur();
    if (!ind?.metriques?.length) return null;
    let sum = 0;
    let weight = 0;
    for (const met of ind.metriques) {
      const ctrl = this.form.get(`m_${met.id_metrique}`);
      const score = this.valueToScore(ctrl?.value, met);
      if (score !== null) {
        const w = Number(met.ponderation || 1);
        sum += score * w;
        weight += w;
      }
    }
    if (weight === 0) return null;
    return Math.max(1, Math.min(5, Math.round(sum / weight)));
  });

  /** Score effectif affiché en récap (override sauvegardé prioritaire). */
  effectiveScore = computed<number | null>(() => {
    return this.isOverridden() ? this.scoreOverride() : this.scoreAuto();
  });

  scoreLevelsList: ScoreLevel[] = SCORE_LEVELS;

  /** Bornes seuil d'une métrique pour un score donné (1-5). */
  /** #421 — intervalle d'un palier formaté comme dans la saisie PG ([50 ; 200], ]30 ; 50]…). */
  scoreRange(met: Metrique, level: number): string {
    return formatScoreRange(met, level);
  }

  /** #421 — vrai si la métrique est de type indéterminé. */
  isMetriqueIndetermine(met: Metrique): boolean {
    return isMetriqueIndetermine(met);
  }

  getScoreBound(met: Metrique, scoreIdx: number, kind: 'inf' | 'sup'): string {
    const key = `score_${scoreIdx}_${kind}` as keyof Metrique;
    const v = (met as any)[key];
    if (v === null || v === undefined || v === '') return '—';
    // Les seuils sont stockés en DecimalField(4 décimales) → « 50.0000 ».
    // On retire les zéros superflus (jusqu'à 4 décimales utiles), format fr-FR.
    const num = Number(v);
    return Number.isNaN(num)
      ? String(v)
      : num.toLocaleString('fr-FR', { maximumFractionDigits: 4 });
  }

  /**
   * Libellé « unité » d'une métrique pour le tableau des seuils.
   * - Mono-bloc : l'unité de la métrique (ou « — »).
   * - Multi-blocs : la liste « intitulé (unité) » de chaque bloc (principal +
   *   complémentaires), séparée par « / » (ex: « hauteur (m) / recouvrement (%) »).
   */
  metriqueUniteLabel(met: Metrique): string {
    const blocks = met.score_blocks || [];
    if (blocks.length === 0) {
      return (met.unite || '').trim() || '—';
    }
    const fmt = (intitule?: string | null, unite?: string | null, fallback = '') => {
      const i = (intitule ?? '').trim();
      const u = (unite ?? '').trim();
      if (!i) return fallback;
      return u ? `${i} (${u})` : i;
    };
    const labels = [
      fmt(met.bloc_intitule, met.unite, met.nom_metrique),
      ...blocks.map((b, idx) => fmt(b.intitule, b.unite, `Bloc ${idx + 2}`)),
    ].filter(Boolean);
    return labels.length ? labels.join(' / ') : '—';
  }

  /** Getter/setter pour ngModel du commentaire (basé sur signal). */
  get commentaireOverrideModel(): string { return this.commentaireOverride(); }
  set commentaireOverrideModel(v: string) { this.commentaireOverride.set(v); }

  // ---- Init -------------------------------------------------------------

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const slug = p.get('slug');
      const idStr = p.get('indicateur_id');
      const yStr = p.get('annee');
      if (slug) this.planSlug.set(slug);
      if (idStr) this.indicateurId.set(Number(idStr));
      if (yStr) this.selectedYear.set(Number(yStr));
      this.loadAll();
    });
  }

  private loadAll(): void {
    const slug = this.planSlug();
    const indId = this.indicateurId();
    if (!slug || !indId) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Plan
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
        if (plan.annee_debut && plan.annee_fin) {
          this.planYearStart.set(plan.annee_debut);
          this.planYearEnd.set(plan.annee_fin);
        }
      },
    });

    // Indicateur
    this.enjeuService.getIndicateur(indId).subscribe({
      next: (ind: Indicateur) => {
        this.indicateur.set(ind);
        this.hydrateForm();
        this.loadResolvedAndMesures();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.indicateur.errors.indicateurNotFound'));
        this.isLoading.set(false);
      },
    });
  }

  private hydrateForm(): void {
    const ind = this.indicateur();
    const fb = this.fb;
    const group: any = {};
    for (const met of ind?.metriques || []) {
      group[`m_${met.id_metrique}`] = [''];
    }
    this.form = fb.group(group);
    // #510 — réactivité du score auto : chaque saisie de métrique bumpe le tick
    // dont dépend `liveAutoScore`. On résouscrit à chaque (ré)hydratation du form.
    this.formSub?.unsubscribe();
    this.formSub = this.form.valueChanges.subscribe(() => this.formTick.update(v => v + 1));
  }

  /** Charge le score résolu (auto + override) + les Mesures existantes. */
  private loadResolvedAndMesures(): void {
    const indId = this.indicateurId();
    const year = this.selectedYear();
    if (!indId) return;

    forkJoin({
      resolved: this.enjeuService.getIndicatorResolved(indId, year),
      mesures: this.fetchAllMesures(),
    }).subscribe({
      next: ({ resolved, mesures }) => {
        // Hydrate mesures map
        this.mesuresByMetrique.clear();
        for (const [metId, ms] of mesures) {
          this.mesuresByMetrique.set(metId, ms);
          this.form.get(`m_${metId}`)?.setValue(ms.valeur);
        }
        // Hydrate scores
        this.scoreAuto.set(resolved.score_auto);
        this.scoreOverride.set(resolved.score_override);
        this.commentaireOverride.set(resolved.commentaire_override || '');
        this.isOverridden.set(resolved.is_overridden);
        // #510 — l'état « forçage manuel » de l'éditeur reflète l'override
        // sauvegardé (réinitialisé à chaque (ré)chargement d'année).
        this.manualOverride.set(resolved.is_overridden);
        // #424 — l'API resolved renvoie désormais l'id de l'override : on le
        // mémorise pour pouvoir le supprimer lors du repassage en auto.
        this.overrideId.set(resolved.id_indicateur_mesure ?? null);
        // Mode initial : recap si on a déjà au moins une mesure ou un override
        const hasAnyData = mesures.length > 0 || resolved.is_overridden;
        this.mode.set(hasAnyData ? 'recap' : 'edit');
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.indicateur.errors.loadFailed'));
        this.isLoading.set(false);
      },
    });
  }

  /** Fetch des Mesures de chaque métrique pour l'année active. */
  private fetchAllMesures() {
    const ind = this.indicateur();
    const year = this.selectedYear();
    const mets = ind?.metriques || [];
    if (!mets.length) return of([] as Array<[number, Mesure]>);
    return forkJoin(
      mets.map((m: Metrique) => this.enjeuService.getMesuresByMetrique(m.id_metrique)),
    ).pipe(
      map((arr: Mesure[][]) => {
        const out: Array<[number, Mesure]> = [];
        const yearOf = (m: Mesure) => m.date_mesure ? new Date(m.date_mesure).getFullYear() : null;
        arr.forEach((list, idx) => {
          const met = mets[idx];
          const exact = list.find(m => yearOf(m) === year);
          if (exact) out.push([met.id_metrique, exact]);
        });
        return out;
      }),
    );
  }

  // ---- Actions UI -------------------------------------------------------

  selectYear(year: number): void {
    this.selectedYear.set(year);
    this.loadResolvedAndMesures();
  }

  /** #510 — « Modifier » depuis le récap : ouvre l'éditeur unique en
   *  préservant l'état de forçage manuel précédemment enregistré. */
  editFromRecap(): void {
    this.manualOverride.set(this.isOverridden());
    this.mode.set('edit');
  }

  /** #510 — Bascule de la case « Forcer le résultat manuellement ». À
   *  l'activation, on initialise le score forcé sur le score auto courant
   *  (point de départ cohérent) s'il n'y en a pas déjà un. */
  setManualOverride(force: boolean): void {
    this.manualOverride.set(force);
    if (force && this.scoreOverride() === null) {
      this.scoreOverride.set(this.liveAutoScore());
    }
  }

  /** #510 — le bloc « résultat automatique » est grisé (non retenu) dès que le
   *  forçage manuel est actif, pour ne pas perdre l'utilisateur. */
  autoResultDimmed(): boolean {
    return this.manualOverride();
  }

  goBack(): void {
    this.router.navigate(['/plans', this.planSlug(), 'tableau-de-bord']);
  }

  pickManualScore(score: number): void {
    this.scoreOverride.set(score);
  }

  /** Sauvegarde Mesures (mode auto) + override éventuel. */
  validate(): void {
    const ind = this.indicateur();
    const indId = this.indicateurId();
    const year = this.selectedYear();
    if (!ind || !indId) return;

    this.isSaving.set(true);

    // 1) Mesures par métrique — toujours enregistrées (la saisie des métriques
    //    reste possible que le résultat soit auto ou forcé manuellement, #510).
    const mesureCalls: any[] = [];
    for (const met of ind.metriques || []) {
      const ctrl = this.form.get(`m_${met.id_metrique}`);
      const value = ctrl?.value;
      if (value === null || value === undefined || String(value).trim() === '') continue;
      const existing = this.mesuresByMetrique.get(met.id_metrique);
      const payload: MesureCreatePayload = {
        id_metrique: met.id_metrique,
        valeur: String(value).replace(',', '.'),
        date_mesure: `${year}-12-31`,
      };
      mesureCalls.push(
        existing
          ? this.enjeuService.updateMesure(existing.id_mesure, payload)
          : this.enjeuService.createMesure(payload),
      );
    }

    // 2) Override du RÉSULTAT de l'indicateur (#510) : piloté par la case
    //    « Forcer le résultat manuellement », indépendamment des métriques.
    //    - cochée + score choisi → upsert de l'override ;
    //    - décochée → suppression de l'override existant (retour à l'auto,
    //      action explicite de l'utilisateur, plus d'effet de bord silencieux).
    let indMesCall: any;
    if (this.manualOverride() && this.scoreOverride() !== null) {
      indMesCall = this.enjeuService.upsertIndicateurMesure({
        id_indicateur: indId,
        annee: year,
        score_override: this.scoreOverride(),
        commentaire_override: this.commentaireOverride() || null,
      });
    } else if (this.overrideId()) {
      indMesCall = this.enjeuService.deleteIndicateurMesure(this.overrideId()!);
    } else {
      indMesCall = of(null);
    }

    const mesuresObs = mesureCalls.length ? forkJoin(mesureCalls) : of([]);

    forkJoin([mesuresObs, indMesCall]).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.snack.open(
          this.translate.instant('plans.suivis.indicateur.messages.saved'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 },
        );
        this.loadResolvedAndMesures();
        this.mode.set('recap');
      },
      error: () => {
        this.isSaving.set(false);
        this.snack.open(
          this.translate.instant('plans.suivis.indicateur.errors.saveFailed'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
      },
    });
  }
}
