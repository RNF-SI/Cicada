import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { SearchBarComponent } from '../../../../shared/components/search-bar/search-bar.component';
import { TagComponent } from '../../../../shared/components/tag/tag.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../../core/services/admin.service';
import { PlanificationAnnuelleService } from '../../../../core/services/planification-annuelle.service';
import {
  LigneTableauAnnuel, ResumeAnnuel, TableauAnnuel,
} from '../../../../core/models/planification-annuelle.model';
import { PLANIFICATION_STATUT_TAG, TagAppearance } from '../../../../shared/utils/tag-icons';

/** Filtre du tableau : statut ajusté, actions à revoir, actions qui divergent. */
export type FiltreAnnuel = 'tous' | 'planifiee' | 'reportee' | 'non_prevue' | 'a_revoir' | 'diverge';

export const FILTRES_ANNUELS: FiltreAnnuel[] = [
  'tous', 'planifiee', 'reportee', 'non_prevue', 'a_revoir', 'diverge',
];

/** Clé de statut d'une année : un report partiel garde l'année planifiée. */
export function statutAnnuelKey(resume: ResumeAnnuel): string {
  if (resume.statut === 'planifiee' && resume.annee_report) {
    return 'reportee_partiel';
  }
  return resume.statut;
}

/** Une ligne passe-t-elle le filtre ? */
export function correspondAuFiltre(ligne: LigneTableauAnnuel, filtre: FiltreAnnuel): boolean {
  switch (filtre) {
    case 'planifiee':
      return ligne.ajuste.statut === 'planifiee';
    case 'reportee':
      return ligne.ajuste.statut === 'reportee' || !!ligne.ajuste.annee_report;
    case 'non_prevue':
      return ligne.ajuste.statut === 'non_prevue';
    case 'a_revoir':
      return !ligne.revue;
    case 'diverge':
      return ligne.diverge;
    default:
      return true;
  }
}

function sansAccents(texte: string): string {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

/**
 * #794 — « Ajustement planification annuelle » : pour une année, chaque action
 * du plan avec sa programmation du plan de gestion (référence, jamais
 * modifiée) et sa programmation ajustée, son statut, ses mois, les reports
 * reçus et l'avancement de la revue (« X / Y actions revues »).
 */
@Component({
  selector: 'app-plan-planification-annuelle',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatMenuModule, MatProgressSpinnerModule, MatTooltipModule,
    TranslateModule, HeaderComponent, PlanSidebarComponent, SearchBarComponent, TagComponent,
  ],
  templateUrl: './plan-planification-annuelle.component.html',
  styleUrl: './plan-planification-annuelle.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class PlanPlanificationAnnuelleComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly service = inject(PlanificationAnnuelleService);
  private readonly translate = inject(TranslateService);

  readonly filtres = FILTRES_ANNUELS;

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal('');
  planStatut = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  tableau = signal<TableauAnnuel | null>(null);
  annee = computed(() => this.tableau()?.annee ?? null);
  annees = computed(() => this.tableau()?.annees ?? []);

  recherche = signal('');
  filtre = signal<FiltreAnnuel>('tous');

  /** Le suivi ne s'ajuste qu'une fois le plan validé (comme la saisie du suivi). */
  planNonValide = computed(() => {
    const s = this.planStatut();
    return !!s && !['valide', 'modifie', 'mi_parcours', 'archive'].includes(s);
  });
  lectureSeule = computed(() => !this.planNonValide() && this.tableau()?.peut_saisir === false);

  lignes = computed(() => {
    const t = this.tableau();
    if (!t) return [];
    const q = sansAccents(this.recherche().trim());
    return t.actions.filter(l =>
      correspondAuFiltre(l, this.filtre())
      && (!q || sansAccents(`${l.code} ${l.libelle}`).includes(q)));
  });

  progression = computed(() => {
    const t = this.tableau();
    if (!t || !t.total) return 0;
    return Math.round((t.revues / t.total) * 100);
  });

  /** Totaux des lignes affichées. Le plan de gestion ne compte pas les actions
   *  programmées globalement : elles n'ont pas de montant annuel (#735). */
  totaux = computed(() => {
    let pgBudget = 0, pgJours = 0, ajBudget = 0, ajJours = 0, globales = 0;
    for (const l of this.lignes()) {
      if (l.programmation_globale) {
        globales++;
      } else {
        pgBudget += Number(l.pg.budget);
        pgJours += Number(l.pg.jours);
      }
      ajBudget += Number(l.ajuste.budget);
      ajJours += Number(l.ajuste.jours);
    }
    return { pgBudget, pgJours, ajBudget, ajJours, globales };
  });

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) return;
    this.planSlug.set(slug);
    const annee = Number(this.route.snapshot.queryParamMap.get('annee')) || null;
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
        this.planStatut.set(plan.statut ?? null);
        this.charger(annee);
      },
      error: () => {
        this.isLoading.set(false);
        this.errorMessage.set(this.translate.instant('plans.suivis.planificationAnnuelle.erreurChargement'));
      },
    });
  }

  charger(annee: number | null): void {
    const planId = this.planId();
    if (!planId) return;
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.service.tableau(planId, annee).subscribe({
      next: (tableau) => {
        this.tableau.set(tableau);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err?.status === 403
          ? this.translate.instant('plans.suivis.planificationAnnuelle.accesRefuse')
          : this.translate.instant('plans.suivis.planificationAnnuelle.erreurChargement'));
      },
    });
  }

  choisirAnnee(annee: number): void {
    if (annee === this.annee()) return;
    this.router.navigate([], {
      relativeTo: this.route, queryParams: { annee }, queryParamsHandling: 'merge', replaceUrl: true,
    });
    this.charger(annee);
  }

  anneePrecedente(): number | null {
    const a = this.annee(), annees = this.annees();
    return a !== null && annees.includes(a - 1) ? a - 1 : null;
  }

  anneeSuivante(): number | null {
    const a = this.annee(), annees = this.annees();
    return a !== null && annees.includes(a + 1) ? a + 1 : null;
  }

  // --- Affichage -------------------------------------------------------------

  tag(resume: ResumeAnnuel): TagAppearance {
    return PLANIFICATION_STATUT_TAG[statutAnnuelKey(resume)] ?? PLANIFICATION_STATUT_TAG['non_prevue'];
  }

  statutLabel(resume: ResumeAnnuel): string {
    return this.translate.instant(
      `plans.suivis.planificationAnnuelle.statut.${statutAnnuelKey(resume)}`,
      { annee: resume.annee_report });
  }

  moisLabel(mois: number[]): string {
    if (!mois.length) return '—';
    if (mois.length === 12) {
      return this.translate.instant('plans.suivis.planification.wholeYear');
    }
    const noms = this.translate.instant('plans.suivis.planification.monthsShort').split(',');
    return mois.map(m => noms[m - 1]).join(', ');
  }

  /** Le statut ou les mois du plan diffèrent de l'ajusté : rappel du plan. */
  rappelPg(ligne: LigneTableauAnnuel): string | null {
    const pg = ligne.pg, aj = ligne.ajuste;
    if (!ligne.ajustee) return null;
    const parts: string[] = [];
    if (statutAnnuelKey(pg) !== statutAnnuelKey(aj)) {
      parts.push(this.statutLabel(pg));
    }
    if (pg.mois.join(',') !== aj.mois.join(',')) {
      parts.push(this.moisLabel(pg.mois));
    }
    return parts.length
      ? this.translate.instant('plans.suivis.planificationAnnuelle.rappelPg', { valeur: parts.join(' · ') })
      : null;
  }

  ecart(ligne: LigneTableauAnnuel, champ: 'budget' | 'jours'): number | null {
    if (ligne.programmation_globale) return null;
    const ecart = Number(ligne.ajuste[champ]) - Number(ligne.pg[champ]);
    return Math.abs(ecart) < 0.005 ? null : ecart;
  }

  num(valeur: string | number | null | undefined): number {
    return Number(valeur ?? 0);
  }

  filtreLabel(filtre: FiltreAnnuel): string {
    return this.translate.instant(`plans.suivis.planificationAnnuelle.filtres.${filtre}`);
  }

  compte(filtre: FiltreAnnuel): number {
    return (this.tableau()?.actions ?? []).filter(l => correspondAuFiltre(l, filtre)).length;
  }
}
