import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { SearchBarComponent } from '../../../shared/components/search-bar/search-bar.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  Enjeu, ObjectifLongTerme, NiveauExigence, Indicateur, Metrique, Mesure
} from '../../../core/models/enjeu.model';

type ScoreLevel = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

/**
 * #389 — Un groupe du tableau de bord. Pour les indicateurs d'État, le groupe
 * est un Objectif Long Terme (OLT → NE → indicateur). Pour les indicateurs de
 * Pression, c'est un Objectif Opérationnel (OO → RA → indicateur). Le `kind`
 * détermine l'en-tête affiché (« OLT N » vs « OO N ») et le libellé de la
 * première colonne (Niveau d'exigence vs Résultat attendu).
 */
interface DashboardGroup {
  kind: 'olt' | 'oo';
  id: number;
  index: number;
  label: string;
  enjeuId: number;
  enjeuLibelle: string;
  /** #356 — slug de l'enjeu, pour le deep-link de l'œil vers la page détail. */
  enjeuSlug: string;
  rows: IndicatorRow[];
}

interface IndicatorRow {
  /** Sous-entité de regroupement : NE (état) ou RA (pression). */
  subId: number;
  subLabel: string;
  indicateur: Indicateur;
  expanded: boolean;
  metriques: Metrique[];
}

@Component({
  selector: 'app-plan-tableau-de-bord',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatButtonModule, MatMenuModule,
    MatProgressSpinnerModule, MatTooltipModule, TranslateModule,
    HeaderComponent, PlanSidebarComponent, SearchBarComponent
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
  planStatut = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // #375 — la saisie du tableau de bord (états/scores) n'est possible qu'une fois le plan validé.
  private readonly VALIDATED_STATUSES = ['valide', 'modifie', 'mi_parcours', 'archive'];
  planNotValidated = computed(() => {
    const s = this.planStatut();
    return !!s && !this.VALIDATED_STATUSES.includes(s);
  });

  // Data
  dashboardGroups = signal<DashboardGroup[]>([]);

  /**
   * #389/#356 — Groupes affichés selon l'onglet et les filtres :
   * - État    : groupes OLT (OLT → NE) + indicateurs d'État,
   * - Pression : groupes OO (OO → RA) + indicateurs de Pression,
   * - Ensemble : les deux, regroupés par enjeu (en-tête enjeu dans le template).
   * Filtres : nom d'objectif (OLT/OO), recherche libre (objectif/sous-entité/
   * indicateur) et enjeu (mode ensemble uniquement).
   */
  filteredGroups = computed<DashboardGroup[]>(() => {
    const tab = this.activeTab();
    const objectifs = this.filterObjectifs();
    const name = this.normalize(this.filterName());
    const enjeuIds = this.filterEnjeuIds();

    return this.dashboardGroups()
      .filter(g => tab === 'ensemble' ? true : (tab === 'etat' ? g.kind === 'olt' : g.kind === 'oo'))
      .filter(g => !(tab === 'ensemble' && enjeuIds.length) || enjeuIds.includes(g.enjeuId))
      .filter(g => !objectifs.length || objectifs.includes(g.label))
      .map(g => {
        // #422 — ne pas filtrer par type d'indicateur : le chemin du groupe
        // (OLT = état, OO = pression/réponse) suffit à le qualifier. Le filtre
        // par libellé de type masquait les indicateurs de réponse (saisis dans
        // les fiches action) et les indicateurs sans type renseigné.
        let rows = g.rows;
        if (name) {
          const groupMatch = this.normalize(g.label).includes(name);
          if (!groupMatch) {
            rows = rows.filter(r =>
              this.normalize(r.subLabel).includes(name)
              || this.normalize(r.indicateur.nom_indicateur).includes(name));
          }
        }
        return { ...g, rows };
      })
      .filter(g => g.rows.length > 0);
  });

  /** Liste des noms d'objectif (OLT/OO) pour le filtre, selon l'onglet. */
  objectifNames = computed<string[]>(() => {
    const tab = this.activeTab();
    const names = new Set<string>();
    for (const g of this.dashboardGroups()) {
      if (tab === 'etat' && g.kind !== 'olt') continue;
      if (tab === 'pression' && g.kind !== 'oo') continue;
      names.add(g.label);
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  });

  /** Enjeux présents (pour le filtre du mode ensemble). */
  enjeuOptions = computed<{ id: number; libelle: string }[]>(() => {
    const map = new Map<number, string>();
    for (const g of this.dashboardGroups()) {
      if (!map.has(g.enjeuId)) map.set(g.enjeuId, g.enjeuLibelle);
    }
    return [...map.entries()]
      .map(([id, libelle]) => ({ id, libelle }))
      .sort((a, b) => a.libelle.localeCompare(b.libelle));
  });

  private normalize(s: string): string {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }
  planYearStart = signal<number>(new Date().getFullYear());
  planYearEnd = signal<number>(new Date().getFullYear() + 9);

  // Filters
  // #356 — 3e option « Ensemble » (état + pression simultanés).
  activeTab = signal<'etat' | 'pression' | 'ensemble'>('etat');
  // #356 — filtres : nom d'objectif (OLT/OO), recherche libre, enjeu (mode ensemble).
  // #426 — filtres multi-sélection (plusieurs objectifs / enjeux à la fois).
  filterObjectifs = signal<string[]>([]);
  filterName = signal<string>('');
  filterEnjeuIds = signal<number[]>([]);

  yearColumns = computed(() => {
    const start = this.planYearStart();
    const end = this.planYearEnd();
    const years: number[] = [];
    for (let y = start; y <= end; y++) {
      years.push(y);
    }
    return years;
  });

  hasData = computed(() => this.dashboardGroups().length > 0);

  private readonly scoreIconsBasePath = 'assets/images/icons/score-badges/';

  /** Mapping vers les SVG fournis depuis Figma (cercles colorés autoporteurs). */
  private readonly scoreIconMap: Record<ScoreLevel, string> = {
    'very-bad': 'score-very-bad.svg',
    'bad': 'score-bad.svg',
    'neutral': 'score-neutral.svg',
    'good': 'score-good.svg',
    'very-good': 'score-very-good.svg',
    'no-data': 'score-no-data.svg',
  };

  legendItems: { level: ScoreLevel; labelKey: string }[] = [
    { level: 'very-bad', labelKey: 'plans.suivis.tableauDeBord.tresMauvais' },
    { level: 'bad', labelKey: 'plans.suivis.tableauDeBord.mauvais' },
    { level: 'neutral', labelKey: 'plans.suivis.tableauDeBord.moyen' },
    { level: 'good', labelKey: 'plans.suivis.tableauDeBord.bon' },
    { level: 'very-good', labelKey: 'plans.suivis.tableauDeBord.tresBon' },
    { level: 'no-data', labelKey: 'plans.suivis.tableauDeBord.sansDonnee' }
  ];

  /** Retourne l'unique icône (SVG) pour un niveau de score donné. */
  getScoreIcon(level: ScoreLevel): string {
    return this.scoreIconsBasePath + this.scoreIconMap[level];
  }

  /** Libellé du score pour tooltip (revue design #317). */
  getScoreLabel(level: ScoreLevel): string {
    const item = this.legendItems.find(i => i.level === level);
    return item ? this.translate.instant(item.labelKey) : '';
  }

  ngOnInit(): void {
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

    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        const groups: DashboardGroup[] = [];
        const allEnjeux = [...response.enjeux, ...response.fcr];
        let oltCounter = 0;
        let ooCounter = 0;

        for (const enjeu of allEnjeux) {
          const enjeuLibelle = enjeu.intitule_court || enjeu.libelle;
          const enjeuId = enjeu.id_enjeu;
          const enjeuSlug = (enjeu as any).slug || '';

          // --- États : OLT → NE → indicateur ---
          for (const olt of enjeu.objectifs_long_terme || []) {
            oltCounter++;
            const rows: IndicatorRow[] = [];
            for (const ne of olt.niveaux_exigence || []) {
              for (const ind of ne.indicateurs || []) {
                rows.push({
                  subId: ne.id_ne,
                  subLabel: ne.libelle,
                  indicateur: ind,
                  // #462 — indicateurs repliés par défaut (métriques masquées) pour alléger le visuel à l'arrivée
                  expanded: false,
                  metriques: ind.metriques || []
                });
              }
            }
            if (rows.length > 0) {
              groups.push({ kind: 'olt', id: olt.id_olt, index: oltCounter, label: olt.libelle, enjeuId, enjeuLibelle, enjeuSlug, rows });
            }
          }

          // --- Pressions : OO → RA → indicateur (#389). Un OO peut être
          //     rattaché via plusieurs pressions ou directement à l'enjeu ;
          //     on déduplique par id_oo. ---
          const ooMap = new Map<number, any>();
          for (const fi of enjeu.facteurs_influence || []) {
            for (const pr of fi.pressions || []) {
              for (const oo of pr.objectifs_operationnels || []) {
                if (!ooMap.has(oo.id_oo)) ooMap.set(oo.id_oo, oo);
              }
            }
          }
          for (const oo of enjeu.objectifs_operationnels || []) {
            if (!ooMap.has(oo.id_oo)) ooMap.set(oo.id_oo, oo);
          }
          for (const oo of ooMap.values()) {
            ooCounter++;
            const rows: IndicatorRow[] = [];
            for (const ra of oo.resultats_attendus || []) {
              for (const ind of ra.indicateurs || []) {
                rows.push({
                  subId: ra.id_ra,
                  subLabel: ra.libelle,
                  indicateur: ind,
                  // #462 — indicateurs repliés par défaut (métriques masquées) pour alléger le visuel à l'arrivée
                  expanded: false,
                  metriques: ind.metriques || []
                });
              }
            }
            if (rows.length > 0) {
              groups.push({ kind: 'oo', id: oo.id_oo, index: ooCounter, label: oo.libelle, enjeuId, enjeuLibelle, enjeuSlug, rows });
            }
          }
        }

        this.dashboardGroups.set(groups);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Erreur lors du chargement des données');
        this.isLoading.set(false);
      }
    });
  }

  setTab(tab: 'etat' | 'pression' | 'ensemble'): void {
    this.activeTab.set(tab);
    // Le filtre objectif dépend de l'onglet ; le filtre enjeu n'existe qu'en
    // mode ensemble → on réinitialise pour éviter un filtrage fantôme.
    this.filterObjectifs.set([]);
    if (tab !== 'ensemble') this.filterEnjeuIds.set([]);
  }

  // #426 — bascule la présence d'une valeur dans le filtre multi-sélection.
  toggleObjectifFilter(value: string): void {
    this.filterObjectifs.update(arr =>
      arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value]);
  }
  isObjectifSelected(value: string): boolean { return this.filterObjectifs().includes(value); }

  toggleEnjeuFilter(value: number): void {
    this.filterEnjeuIds.update(arr =>
      arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value]);
  }
  isEnjeuSelected(value: number): boolean { return this.filterEnjeuIds().includes(value); }

  clearFilters(): void {
    this.filterObjectifs.set([]);
    this.filterName.set('');
    this.filterEnjeuIds.set([]);
  }

  hasActiveFilters(): boolean {
    return !!(this.filterObjectifs().length || this.filterName() || this.filterEnjeuIds().length);
  }

  /** #356 — Début d'un bloc enjeu (en-tête enjeu) en mode ensemble. */
  isFirstGroupOfEnjeu(idx: number): boolean {
    if (this.activeTab() !== 'ensemble') return false;
    const groups = this.filteredGroups();
    if (idx === 0) return true;
    return groups[idx].enjeuId !== groups[idx - 1].enjeuId;
  }

  /**
   * #356 — Actions liées à un indicateur (via ses métriques), dédupliquées.
   * `code` = code compact (code réserve si forcé, sinon gestref + rang ;
   * ex. CS1, SP2), `libelle` complet pour le survol.
   */
  actionsForIndicator(row: IndicatorRow): { id: number; code: string; libelle: string; annee: number }[] {
    const seen = new Map<number, { id: number; code: string; libelle: string; annee: number }>();
    for (const m of row.metriques) {
      for (const op of ((m as any).operations || [])) {
        if (!seen.has(op.id_operation)) {
          seen.set(op.id_operation, {
            id: op.id_operation,
            code: op.code_affichage || op.code_prefix || op.libelle,
            libelle: op.libelle,
            annee: this.actionYear(op),
          });
        }
      }
    }
    return [...seen.values()];
  }

  /** Année cible pour le lien vers le suivi annuel d'une action. */
  private actionYear(op: any): number {
    const cy = new Date().getFullYear();
    const min = op.annee_min ?? cy;
    const max = op.annee_max ?? cy;
    return (cy >= min && cy <= max) ? cy : min;
  }

  toggleIndicator(group: DashboardGroup, row: IndicatorRow): void {
    // On identifie le groupe (kind + id) et la ligne (indicateur + sous-entité)
    // par leur identité plutôt que par index, car le template itère des groupes
    // filtrés dont l'index ne correspond pas à dashboardGroups.
    this.dashboardGroups.update(groups => groups.map(g => {
      if (g.kind !== group.kind || g.id !== group.id) return g;
      return {
        ...g,
        rows: g.rows.map(r =>
          (r.indicateur.id_indicateur === row.indicateur.id_indicateur && r.subId === row.subId)
            ? { ...r, expanded: !r.expanded }
            : r),
      };
    }));
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
        return this.valueToScoreLevel(metrique, parseFloat(String(mesure.valeur).replace(',', '.')));
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
    return this.valueToScoreLevel(metrique, parseFloat(String(mesure.valeur).replace(',', '.')));
  }

  /**
   * #355 — Score « global » (état courant) d'un indicateur = score de la
   * dernière année renseignée. La « globale partielle » découle naturellement :
   * seules les années déjà saisies comptent. La page globale de l'indicateur
   * (colonne « Global » cliquable) détaille moyenne et tendance.
   */
  getGlobalScoreForRow(row: IndicatorRow): ScoreLevel | null {
    const years = [...this.yearColumns()].sort((a, b) => b - a);
    for (const y of years) {
      const s = this.getScoreForYear(row, y);
      if (s && s !== 'no-data') return s;
    }
    return null;
  }

  private valueToScoreLevel(metrique: Metrique, value: number): ScoreLevel {
    if (isNaN(value)) return 'no-data';

    // Check score ranges from 1 (very-bad) to 5 (very-good)
    for (let level = 1; level <= 5; level++) {
      const inf = (metrique as any)[`score_${level}_inf`];
      const sup = (metrique as any)[`score_${level}_sup`];
      const hasInf = inf != null;
      const hasSup = sup != null;
      if (!hasInf && !hasSup) continue;
      // #423 — inclusivité des bornes (cohérent avec la notation par crochets).
      const infIncl = level <= 1 ? true : (metrique as any)[`score_${level - 1}_sup_inclusive`] === false;
      const supIncl = level >= 5 ? true : (metrique as any)[`score_${level}_sup_inclusive`] !== false;
      const lowerOk = !hasInf || (infIncl ? value >= Number(inf) : value > Number(inf));
      const upperOk = !hasSup || (supIncl ? value <= Number(sup) : value < Number(sup));
      if (lowerOk && upperOk) {
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
  isFirstIndicatorOfNe(group: DashboardGroup, rowIdx: number): boolean {
    if (rowIdx === 0) return true;
    return group.rows[rowIdx].subId !== group.rows[rowIdx - 1].subId;
  }

  getNeRowspan(group: DashboardGroup, rowIdx: number): number {
    const subId = group.rows[rowIdx].subId;
    let count = 0;
    for (let i = rowIdx; i < group.rows.length; i++) {
      if (group.rows[i].subId !== subId) break;
      // Ligne indicateur
      count += 1;
      // Sous-lignes métriques (uniquement quand l'indicateur est déplié)
      if (group.rows[i].expanded) {
        count += group.rows[i].metriques.length;
      }
    }
    return count;
  }
}

