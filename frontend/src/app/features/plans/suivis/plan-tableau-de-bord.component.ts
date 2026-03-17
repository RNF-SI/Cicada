import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  Enjeu, ObjectifLongTerme, NiveauExigence, Indicateur, Metrique, Mesure
} from '../../../core/models/enjeu.model';

type ScoreLevel = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

interface OltGroup {
  olt: ObjectifLongTerme;
  oltIndex: number;
  enjeuLibelle: string;
  rows: IndicatorRow[];
}

interface IndicatorRow {
  ne: NiveauExigence;
  indicateur: Indicateur;
  expanded: boolean;
  metriques: Metrique[];
}

@Component({
  selector: 'app-plan-tableau-de-bord',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatButtonModule, MatMenuModule,
    MatProgressSpinnerModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './plan-tableau-de-bord.component.html',
  styleUrl: './plan-tableau-de-bord.component.scss'
})
export class PlanTableauDeBordComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Data
  oltGroups = signal<OltGroup[]>([]);
  planYearStart = signal<number>(new Date().getFullYear());
  planYearEnd = signal<number>(new Date().getFullYear() + 9);

  // Filters
  activeTab = signal<'etat' | 'pression'>('etat');

  yearColumns = computed(() => {
    const start = this.planYearStart();
    const end = this.planYearEnd();
    const years: number[] = [];
    for (let y = start; y <= end; y++) {
      years.push(y);
    }
    return years;
  });

  hasData = computed(() => this.oltGroups().length > 0);

  private readonly scoreIconsBasePath = 'assets/images/icons/smileys/';

  private readonly scoreIconMap: Record<ScoreLevel, string[]> = {
    'very-bad': ['fi-rr-minus-small-red-trait.png', 'fi-rr-minus-small-red-trait.png'],
    'bad': ['fi-rr-minus-small-orange-trait.png'],
    'neutral': ['moyen-trait.png'],
    'good': ['fi-rr-plus-small-green-trait.png'],
    'very-good': ['fi-rr-plus-small-blue-trait.png', 'fi-rr-plus-small-blue-trait.png'],
    'no-data': ['sans-donnee-trait.png']
  };

  legendItems: { level: ScoreLevel; labelKey: string }[] = [
    { level: 'very-bad', labelKey: 'plans.suivis.tableauDeBord.tresMauvais' },
    { level: 'bad', labelKey: 'plans.suivis.tableauDeBord.mauvais' },
    { level: 'neutral', labelKey: 'plans.suivis.tableauDeBord.moyen' },
    { level: 'good', labelKey: 'plans.suivis.tableauDeBord.bon' },
    { level: 'very-good', labelKey: 'plans.suivis.tableauDeBord.tresBon' },
    { level: 'no-data', labelKey: 'plans.suivis.tableauDeBord.sansDonnee' }
  ];

  getScoreIcons(level: ScoreLevel): string[] {
    return (this.scoreIconMap[level] || []).map(f => this.scoreIconsBasePath + f);
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

    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        const groups: OltGroup[] = [];
        const allEnjeux = [...response.enjeux, ...response.fcr];
        let oltCounter = 0;

        for (const enjeu of allEnjeux) {
          const etats = enjeu.etats_actuels || [];
          for (const ea of etats) {
            const olts = ea.objectifs_long_terme || [];
            for (const olt of olts) {
              oltCounter++;
              const rows: IndicatorRow[] = [];

              const nes = olt.niveaux_exigence || [];
              for (const ne of nes) {
                const indicateurs = ne.indicateurs || [];
                for (const ind of indicateurs) {
                  rows.push({
                    ne,
                    indicateur: ind,
                    expanded: false,
                    metriques: ind.metriques || []
                  });
                }
              }

              if (rows.length > 0) {
                groups.push({
                  olt,
                  oltIndex: oltCounter,
                  enjeuLibelle: enjeu.intitule_court || enjeu.libelle,
                  rows
                });
              }
            }
          }
        }

        this.oltGroups.set(groups);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Erreur lors du chargement des données');
        this.isLoading.set(false);
      }
    });
  }

  setTab(tab: 'etat' | 'pression'): void {
    this.activeTab.set(tab);
  }

  toggleIndicator(groupIdx: number, rowIdx: number): void {
    this.oltGroups.update(groups => {
      const updated = [...groups];
      const group = { ...updated[groupIdx] };
      group.rows = [...group.rows];
      group.rows[rowIdx] = { ...group.rows[rowIdx], expanded: !group.rows[rowIdx].expanded };
      updated[groupIdx] = group;
      return updated;
    });
  }

  /**
   * Get score level for an indicateur in a given year.
   * Uses mesures data from metriques when available.
   */
  getScoreForYear(row: IndicatorRow, year: number): ScoreLevel | null {
    for (const metrique of row.metriques) {
      const mesures = metrique.mesures || [];
      const mesure = mesures.find(m => {
        if (!m.date_mesure) return false;
        return new Date(m.date_mesure).getFullYear() === year;
      });
      if (mesure) {
        return this.valueToScoreLevel(metrique, parseFloat(mesure.valeur));
      }
    }
    return null;
  }

  /**
   * Get score level for a specific metrique in a given year.
   */
  getMetriqueScoreForYear(metrique: Metrique, year: number): ScoreLevel | null {
    const mesures = metrique.mesures || [];
    const mesure = mesures.find(m => {
      if (!m.date_mesure) return false;
      return new Date(m.date_mesure).getFullYear() === year;
    });
    if (!mesure) return null;
    return this.valueToScoreLevel(metrique, parseFloat(mesure.valeur));
  }

  private valueToScoreLevel(metrique: Metrique, value: number): ScoreLevel {
    if (isNaN(value)) return 'no-data';

    // Check score ranges from 1 (very-bad) to 5 (very-good)
    for (let level = 1; level <= 5; level++) {
      const inf = (metrique as any)[`score_${level}_inf`];
      const sup = (metrique as any)[`score_${level}_sup`];

      if (inf != null && sup != null) {
        if (value >= inf && value <= sup) {
          return this.levelToScoreLevel(level);
        }
      } else if (inf != null && value >= inf) {
        return this.levelToScoreLevel(level);
      } else if (sup != null && value <= sup) {
        return this.levelToScoreLevel(level);
      }
    }

    return 'no-data';
  }

  private levelToScoreLevel(level: number): ScoreLevel {
    const map: Record<number, ScoreLevel> = {
      1: 'very-bad',
      2: 'bad',
      3: 'neutral',
      4: 'good',
      5: 'very-good'
    };
    return map[level] || 'no-data';
  }

  /**
   * Get the rowspan for the NE cell (how many indicators share this NE).
   */
  isFirstIndicatorOfNe(group: OltGroup, rowIdx: number): boolean {
    if (rowIdx === 0) return true;
    return group.rows[rowIdx].ne.id_ne !== group.rows[rowIdx - 1].ne.id_ne;
  }

  getNeRowspan(group: OltGroup, rowIdx: number): number {
    const neId = group.rows[rowIdx].ne.id_ne;
    let count = 0;
    for (let i = rowIdx; i < group.rows.length; i++) {
      if (group.rows[i].ne.id_ne === neId) count++;
      else break;
    }
    return count;
  }
}
