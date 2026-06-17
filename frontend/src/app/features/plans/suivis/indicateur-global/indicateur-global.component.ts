import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { ScoreIconComponent, ScoreLevel } from '../../../../shared/components/icons/score-icon.component';
import { AdminService } from '../../../../core/services/admin.service';
import { EnjeuService, IndicateurGlobalResponse, IndicateurMetriqueGlobal } from '../../../../core/services/enjeu.service';

/**
 * #355 — Page globale d'un indicateur d'État/Pression : état courant (dernière
 * année renseignée), moyenne, tendance et série annuelle (graphique), au niveau
 * indicateur et par métrique. Accessible depuis la colonne « Global » du tableau
 * de bord.
 */
@Component({
  selector: 'app-indicateur-global',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatProgressSpinnerModule, MatTooltipModule,
    TranslateModule, HeaderComponent, PlanSidebarComponent, ScoreIconComponent
  ],
  templateUrl: './indicateur-global.component.html',
  styleUrl: './indicateur-global.component.scss'
})
export class IndicateurGlobalComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  data = signal<IndicateurGlobalResponse | null>(null);

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
        next: (plan) => this.planId.set(plan.id_pg)
      });
    }
    if (indId) {
      this.enjeuService.getIndicateurGlobal(indId).subscribe({
        next: (res) => {
          this.data.set(res);
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

  /** Convertit un score 1-5 (ou null) en niveau pour app-score-icon. */
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
