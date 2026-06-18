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
import { EnjeuService, IndicateurGlobalResponse, IndicateurMetriqueGlobal } from '../../../../core/services/enjeu.service';

/** Niveaux des badges de score (réutilisés du tableau de bord). */
type ScoreLevel = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

/**
 * #355 / #356 — Page globale d'un indicateur d'État/Pression : état courant
 * (dernière année renseignée), moyenne, tendance et série annuelle (graphique),
 * au niveau indicateur et par métrique. Accessible depuis la colonne « Global »
 * du tableau de bord.
 *
 * #356 — Un gestionnaire peut attribuer une icône d'interprétation forcée
 * (++ / + / neutre / − / −−) qui prime sur le calcul auto pour l'affichage,
 * et enregistrer un commentaire global (indépendant du forçage). Les badges
 * smileys sont ceux de la légende du tableau de bord. Les années des métriques
 * sont cliquables (→ formulaire de saisie de l'indicateur pour l'année).
 */
@Component({
  selector: 'app-indicateur-global',
  standalone: true,
  imports: [
    CommonModule, FormsModule, RouterModule, MatButtonModule,
    MatProgressSpinnerModule, MatTooltipModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './indicateur-global.component.html',
  styleUrl: './indicateur-global.component.scss'
})
export class IndicateurGlobalComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  indicateurId = signal<number | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  data = signal<IndicateurGlobalResponse | null>(null);

  /** Commentaire global (textarea), non obligatoire. */
  commentaire = signal<string>('');

  /**
   * #356 — L'ajustement manuel est une OPTION, pas une action forcée : les
   * contrôles d'interprétation restent repliés tant que l'utilisateur ne clique
   * pas sur « Ajuster manuellement » (déplié d'office s'il existe déjà une
   * surcharge ou un commentaire).
   */
  showOverride = signal<boolean>(false);

  /** Droits gestionnaire (cf. canManageLifecycle). */
  private planReferentIds = signal<number[]>([]);

  /** Badges smileys de score (mêmes assets que la légende du tableau de bord). */
  private readonly scoreIconsBasePath = 'assets/images/icons/score-badges/';
  private readonly scoreIconMap: Record<ScoreLevel, string> = {
    'very-bad': 'score-very-bad.svg',
    'bad': 'score-bad.svg',
    'neutral': 'score-neutral.svg',
    'good': 'score-good.svg',
    'very-good': 'score-very-good.svg',
    'no-data': 'score-no-data.svg',
  };

  /** Boutons d'interprétation forcée : icône (score 5..1) + libellé. */
  readonly evalButtons: { score: number; level: ScoreLevel; labelKey: string }[] = [
    { score: 5, level: 'very-good', labelKey: 'plans.suivis.indicateurGlobal.eval.tresBon' },
    { score: 4, level: 'good', labelKey: 'plans.suivis.indicateurGlobal.eval.bon' },
    { score: 3, level: 'neutral', labelKey: 'plans.suivis.indicateurGlobal.eval.moyen' },
    { score: 2, level: 'bad', labelKey: 'plans.suivis.indicateurGlobal.eval.mauvais' },
    { score: 1, level: 'very-bad', labelKey: 'plans.suivis.indicateurGlobal.eval.tresMauvais' },
  ];

  canManageGlobal = computed<boolean>(() => {
    if (this.authService.hasGlobalAccess() || this.authService.isAdminOrganisme()) return true;
    const uid = this.authService.currentUser()?.id;
    return uid != null && this.planReferentIds().includes(uid);
  });

  /** Score effectif affiché pour l'état courant (surcharge si posée, sinon calcul). */
  etatCourantEffectif = computed<number | null>(() => {
    const d = this.data();
    if (!d) return null;
    return d.etat_courant_effectif != null ? d.etat_courant_effectif : d.etat_courant_score;
  });

  /** Points de la polyline SVG pour la série indicateur (graphique de tendance). */
  sparkline = computed<{ points: string; dots: { x: number; y: number; score: number; annee: number }[] } | null>(() => {
    const d = this.data();
    if (!d || d.serie.length === 0) return null;
    const W = 100, H = 40, pad = 4;
    const n = d.serie.length;
    const xStep = n > 1 ? (W - 2 * pad) / (n - 1) : 0;
    const dots = d.serie.map((pt, i) => {
      const x = pad + i * xStep;
      // score 1..5 → y inversé (5 en haut)
      const y = pad + (H - 2 * pad) * (1 - (pt.score - 1) / 4);
      return { x, y, score: pt.score, annee: pt.annee };
    });
    return { points: dots.map(p => `${p.x},${p.y}`).join(' '), dots };
  });

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    const indId = Number(this.route.snapshot.paramMap.get('indicateur_id'));
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planReferentIds.set((plan.referents ?? []).map(r => r.id_role));
        }
      });
    }
    if (indId) {
      this.indicateurId.set(indId);
      this.enjeuService.getIndicateurGlobal(indId).subscribe({
        next: (res) => {
          this.data.set(res);
          this.commentaire.set(res.commentaire ?? '');
          // Déplier d'office si une interprétation manuelle/commentaire existe déjà.
          if (res.manuel || (res.commentaire ?? '').trim()) this.showOverride.set(true);
          this.isLoading.set(false);
        },
        error: () => {
          this.errorMessage.set('Erreur lors du chargement de l\'indicateur');
          this.isLoading.set(false);
        }
      });
    } else {
      this.isLoading.set(false);
    }
  }

  /** Chemin du badge SVG pour un niveau de score. */
  getScoreIcon(level: ScoreLevel): string {
    return this.scoreIconsBasePath + this.scoreIconMap[level];
  }

  /** Badge SVG correspondant à un score 1-5 (ou no-data). */
  getScoreBadge(score: number | null | undefined): string {
    return this.getScoreIcon(this.scoreToLevel(score));
  }

  /** Convertit un score 1-5 (ou null) en niveau de badge. */
  scoreToLevel(score: number | null | undefined): ScoreLevel {
    switch (Math.round(score ?? 0)) {
      case 1: return 'very-bad';
      case 2: return 'bad';
      case 3: return 'neutral';
      case 4: return 'good';
      case 5: return 'very-good';
      default: return 'no-data';
    }
  }

  /** Bouton actif = surcharge correspondant au score forcé courant. */
  isCurrentEval(score: number): boolean {
    return this.data()?.score_override === score;
  }

  /**
   * #356 — Pose (score) ou retire (null = automatique) l'icône d'interprétation.
   * Le commentaire courant est préservé.
   */
  setGlobalEval(score: number | null): void {
    const id = this.indicateurId();
    if (id == null) return;
    const comment = this.commentaire().trim();
    this.enjeuService.setIndicateurGlobalEval(id, score, comment).subscribe({
      next: (res) => {
        this.data.update(cur => cur ? {
          ...cur,
          score_override: res.score_override,
          manuel: res.manuel,
          commentaire: res.commentaire,
          etat_courant_effectif: res.score_override != null
            ? res.score_override : cur.etat_courant_score,
        } : cur);
        this.snackBar.open(
          this.translate.instant('plans.suivis.indicateurGlobal.saved'),
          this.translate.instant('common.actions.close'),
          { duration: 2500 }
        );
      }
    });
  }

  /** #356 — Enregistre le commentaire seul (sans toucher au forçage). */
  saveComment(): void {
    const id = this.indicateurId();
    if (id == null) return;
    const score = this.data()?.score_override ?? null;
    const comment = this.commentaire().trim();
    this.enjeuService.setIndicateurGlobalEval(id, score, comment).subscribe({
      next: (res) => {
        this.data.update(cur => cur ? { ...cur, commentaire: res.commentaire } : cur);
        this.snackBar.open(
          this.translate.instant('plans.suivis.indicateurGlobal.commentSaved'),
          this.translate.instant('common.actions.close'),
          { duration: 2500 }
        );
      }
    });
  }

  /** Icône Flaticon pour la tendance. */
  tendanceIcon(t: 'hausse' | 'baisse' | 'stable' | undefined): string {
    switch (t) {
      case 'hausse': return 'fi-rr-arrow-trend-up';
      case 'baisse': return 'fi-rr-arrow-trend-down';
      default: return 'fi-rr-minus-small';
    }
  }

  /** Clé i18n du libellé de tendance. */
  tendanceLabelKey(t: 'hausse' | 'baisse' | 'stable' | undefined): string {
    return 'plans.suivis.indicateurGlobal.tendance.' + (t ?? 'stable');
  }

  trackMetrique(_: number, m: IndicateurMetriqueGlobal): number {
    return m.id_metrique;
  }
}
