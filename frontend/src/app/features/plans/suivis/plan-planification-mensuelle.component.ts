import { Component, inject, input, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import { Operation } from '../../../core/models/enjeu.model';
import { ActionStatus, ACTION_LEGEND_ITEMS, getActionIcon, getActionStatusForYear } from './action-status.util';

/** Action « à plat » : opération + contexte enjeu (fourni par la page parente). */
export interface PlanifOperation {
  operation: Operation;
  enjeuLibelle: string;
  enjeuId: number;
}

type PlanifView = 'agenda' | 'calendrier';
type AgendaTab = 'thisMonth' | 'nextMonth' | 'thisYear';

/** Statut affiché : réutilise les icônes de la page Réalisation (prévu,
 *  prévu+réalisé, prévu+partiel, non réalisé, réalisé/partiel non prévu).
 *  La réalisation est saisie à l'année (niveau), donc tous les mois prévus
 *  d'une même année partagent le statut de cette année. */
type MonthStatus = ActionStatus;

interface AgendaItem {
  fop: PlanifOperation;
  year: number;
  month: number | null; // null = prévu à l'année (sans détail mensuel)
  status: MonthStatus | null;
}

/** Bande de mois consécutifs prévus (avec, pour chaque mois, son icône). */
interface CalendarBand {
  start: number; // 1-12
  end: number;   // 1-12 (inclus)
  cells: { month: number; status: MonthStatus }[];
}

interface CalendarRow {
  fop: PlanifOperation;
  bands: CalendarBand[];
  /** Mois réalisés mais non prévus (marqueurs isolés). */
  unplanned: { month: number; status: MonthStatus }[];
}

/**
 * Planification mensuelle d'un plan de gestion (#xxx).
 *
 * Vue présentationnelle (sans header/sidebar/filtres : fournis par la page
 * « Suivi des actions » qui l'héberge en premier onglet). Deux vues : un agenda
 * (ce mois-ci / le mois prochain / cette année) tourné vers les prochaines
 * actions, et un calendrier mensuel réutilisant les icônes de Réalisation, avec
 * des bandes continues pour les mois consécutifs.
 */
@Component({
  selector: 'app-plan-planification-mensuelle',
  standalone: true,
  imports: [CommonModule, MatMenuModule, MatTooltipModule, TranslateModule, TagComponent],
  templateUrl: './plan-planification-mensuelle.component.html',
  styleUrl: './plan-planification-mensuelle.component.scss'
})
export class PlanPlanificationMensuelleComponent {
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  // Inputs fournis par la page « Suivi des actions »
  operations = input.required<PlanifOperation[]>();
  planYearStart = input.required<number>();
  planYearEnd = input.required<number>();
  planSlug = input.required<string>();
  /** Filtre « Année » de la barre partagée : pilote l'année du calendrier. */
  filterYear = input<number | null>(null);

  private readonly now = new Date();
  currentYear = signal<number>(this.now.getFullYear());
  currentMonth = signal<number>(this.now.getMonth() + 1); // 1-12

  view = signal<PlanifView>('agenda');
  agendaTab = signal<AgendaTab>('thisMonth');
  calendarYear = signal<number>(this.now.getFullYear());
  /** Filtre mois du calendrier (#459 décliné aux mois) : null = tous les mois. */
  calendarMonth = signal<number | null>(null);

  // Pagination de l'agenda.
  readonly pageSize = 15;
  agendaPage = signal<number>(1);

  constructor() {
    // Le filtre « Année » (parent) pilote l'année affichée par le calendrier.
    effect(() => {
      const fy = this.filterYear();
      if (fy != null) this.calendarYear.set(fy);
    });
  }

  setView(v: PlanifView): void { this.view.set(v); }
  setAgendaTab(t: AgendaTab): void { this.agendaTab.set(t); this.agendaPage.set(1); }

  // ===========================================================================
  // Helpers temporels
  // ===========================================================================

  private monthsShort(): string[] {
    return this.translate.instant('plans.suivis.planification.monthsShort').split(',');
  }
  monthLabels(): string[] { return this.monthsShort(); }

  /** Mois cochés (true) d'une map mensuelle, triés. */
  private trueMonths(map: Record<string, boolean> | null | undefined): number[] {
    if (!map) return [];
    return Object.entries(map)
      .filter(([, v]) => !!v)
      .map(([k]) => Number(k))
      .filter(n => n >= 1 && n <= 12)
      .sort((a, b) => a - b);
  }

  /** Mois prévus d'une opération pour une année (repli sur les 12 mois si la
   *  programmation est posée à l'année sans détail mensuel). */
  private plannedMonths(op: Operation, year: number): number[] {
    const oa = (op.operation_annees || []).find(a => a.annee === year && a.periodicite);
    if (!oa) return [];
    const months = this.trueMonths(oa.periodicite_mensuelle);
    return months.length > 0 ? months : Array.from({ length: 12 }, (_, i) => i + 1);
  }

  /** Mois réalisés d'une opération pour une année (saisie mensuelle de réalisation,
   *  si renseignée — sinon vide, la réalisation étant suivie à l'année). */
  private realizedMonths(op: Operation, year: number): number[] {
    const oa = (op.operation_annees || []).find(a => a.annee === year);
    return this.trueMonths(oa?.realisation?.periodicite_mensuelle_realisee);
  }

  /** Niveau de réalisation annuel (mnémonique) d'une opération pour une année. */
  private annualNiveau(op: Operation, year: number): string | null {
    const oa = (op.operation_annees || []).find(a => a.annee === year);
    return oa?.realisation?.niveau_realisation_mnemonique ?? null;
  }

  /**
   * Statut d'un mois, avec les icônes de la page Réalisation. Pour un mois
   * prévu, on réutilise le statut annuel (prévu × niveau) — la réalisation
   * étant saisie à l'année. Pour un mois réalisé hors programmation (donnée
   * mensuelle), on renvoie « réalisé/partiel non prévu ».
   */
  private monthlyStatus(op: Operation, year: number, month: number): MonthStatus | null {
    if (this.plannedMonths(op, year).includes(month)) {
      return getActionStatusForYear(op, year) ?? 'planned';
    }
    if (this.realizedMonths(op, year).includes(month)) {
      return this.annualNiveau(op, year) === 'PARTIEL' ? 'partial-unplanned' : 'realized-unplanned';
    }
    return null;
  }

  /** Mois suivant (gère le passage à l'année suivante en décembre). */
  nextMonthInfo = computed<{ year: number; month: number }>(() => {
    const cy = this.currentYear();
    const cm = this.currentMonth();
    return cm === 12 ? { year: cy + 1, month: 1 } : { year: cy, month: cm + 1 };
  });

  // ===========================================================================
  // AGENDA
  // ===========================================================================

  /** Actions prévues un mois donné (avec leur statut prévu × réalisé). */
  private itemsForMonth(year: number, month: number): AgendaItem[] {
    const out: AgendaItem[] = [];
    for (const fop of this.operations()) {
      if (!this.plannedMonths(fop.operation, year).includes(month)) continue;
      out.push({ fop, year, month, status: this.monthlyStatus(fop.operation, year, month) });
    }
    return this.sortItems(out);
  }

  /** Toutes les actions prévues dans l'année (détail mensuel si dispo). */
  private itemsForYear(year: number): AgendaItem[] {
    const out: AgendaItem[] = [];
    for (const fop of this.operations()) {
      const oa = (fop.operation.operation_annees || []).find(a => a.annee === year && a.periodicite);
      if (!oa) continue;
      const months = this.trueMonths(oa.periodicite_mensuelle);
      if (months.length === 0) {
        out.push({ fop, year, month: null, status: getActionStatusForYear(fop.operation, year) ?? 'planned' });
      } else {
        for (const m of months) {
          out.push({ fop, year, month: m, status: this.monthlyStatus(fop.operation, year, m) });
        }
      }
    }
    return this.sortItems(out);
  }

  /** Tri : priorité (1 d'abord) puis mois puis libellé. */
  private sortItems(items: AgendaItem[]): AgendaItem[] {
    return items.sort((a, b) =>
      this.prioRank(a.fop.operation) - this.prioRank(b.fop.operation)
      || ((a.month ?? 13) - (b.month ?? 13))
      || a.fop.operation.libelle.localeCompare(b.fop.operation.libelle));
  }

  private prioRank(op: Operation): number {
    const l = op.priorite_label || '';
    if (l.includes('1')) return 1;
    if (l.includes('2')) return 2;
    if (l.includes('3')) return 3;
    return 9;
  }

  agendaItems = computed<AgendaItem[]>(() => {
    switch (this.agendaTab()) {
      case 'thisMonth': return this.itemsForMonth(this.currentYear(), this.currentMonth());
      case 'nextMonth': { const n = this.nextMonthInfo(); return this.itemsForMonth(n.year, n.month); }
      case 'thisYear': return this.itemsForYear(this.currentYear());
    }
  });

  // Pagination de la liste de l'agenda.
  agendaTotalPages = computed(() => Math.max(1, Math.ceil(this.agendaItems().length / this.pageSize)));

  pagedAgendaItems = computed<AgendaItem[]>(() => {
    const page = Math.min(this.agendaPage(), this.agendaTotalPages());
    const start = (page - 1) * this.pageSize;
    return this.agendaItems().slice(start, start + this.pageSize);
  });

  agendaRangeStart = computed(() => this.agendaItems().length === 0 ? 0 : (Math.min(this.agendaPage(), this.agendaTotalPages()) - 1) * this.pageSize + 1);
  agendaRangeEnd = computed(() => Math.min(Math.min(this.agendaPage(), this.agendaTotalPages()) * this.pageSize, this.agendaItems().length));

  prevAgendaPage(): void { this.agendaPage.update(p => Math.max(1, p - 1)); }
  nextAgendaPage(): void { this.agendaPage.update(p => Math.min(this.agendaTotalPages(), p + 1)); }

  countThisMonth = computed(() => this.itemsForMonth(this.currentYear(), this.currentMonth()).length);
  countNextMonth = computed(() => { const n = this.nextMonthInfo(); return this.itemsForMonth(n.year, n.month).length; });
  countThisYear = computed(() => this.itemsForYear(this.currentYear()).length);

  /** Libellé du mois prochain (pour l'onglet). */
  nextMonthLabel = computed(() => {
    const n = this.nextMonthInfo();
    return this.monthsShort()[n.month - 1];
  });

  // ===========================================================================
  // CALENDRIER
  // ===========================================================================

  calendarRows = computed<CalendarRow[]>(() => {
    const year = this.calendarYear();
    const rows: CalendarRow[] = [];

    for (const fop of this.operations()) {
      const oa = (fop.operation.operation_annees || []).find(a => a.annee === year && a.periodicite);
      const realiseMonths = this.realizedMonths(fop.operation, year);
      const hasPlan = !!oa;
      if (!hasPlan && realiseMonths.length === 0) continue;

      const prevuMonths = hasPlan ? this.plannedMonths(fop.operation, year) : [];
      const prevuSet = new Set(prevuMonths);

      // Statut annuel partagé par tous les mois prévus (réalisation suivie à l'année).
      const plannedStatus = getActionStatusForYear(fop.operation, year) ?? 'planned';

      // Bandes : suites de mois consécutifs prévus.
      const bands: CalendarBand[] = [];
      let cur: CalendarBand | null = null;
      for (let m = 1; m <= 12; m++) {
        if (prevuSet.has(m)) {
          const status = plannedStatus;
          if (cur && cur.end === m - 1) {
            cur.end = m;
            cur.cells.push({ month: m, status });
          } else {
            cur = { start: m, end: m, cells: [{ month: m, status }] };
            bands.push(cur);
          }
        } else {
          cur = null;
        }
      }

      // Mois réalisés mais non prévus (marqueurs isolés, donnée mensuelle).
      const unplannedStatus: MonthStatus =
        this.annualNiveau(fop.operation, year) === 'PARTIEL' ? 'partial-unplanned' : 'realized-unplanned';
      const unplanned = realiseMonths
        .filter(m => !prevuSet.has(m))
        .map(m => ({ month: m, status: unplannedStatus }));

      if (bands.length === 0 && unplanned.length === 0) continue;
      rows.push({ fop, bands, unplanned });
    }

    // #459 décliné aux mois : si un mois est sélectionné, ne garder que les
    // actions ayant une réponse (statut non vide) à ce mois — la grille des
    // 12 mois reste affichée.
    const month = this.calendarMonth();
    if (month != null) return rows.filter(r => this.rowHasMonth(r, month));
    return rows;
  });

  /** Vrai si la ligne a une réponse (bande ou marqueur) au mois donné. */
  private rowHasMonth(row: CalendarRow, month: number): boolean {
    return row.bands.some(b => month >= b.start && month <= b.end)
        || row.unplanned.some(u => u.month === month);
  }

  isFilterMonthCol(month: number): boolean {
    return this.calendarMonth() === month;
  }

  prevCalendarYear(): void {
    const y = this.calendarYear() - 1;
    if (y >= this.planYearStart()) this.calendarYear.set(y);
  }
  nextCalendarYear(): void {
    const y = this.calendarYear() + 1;
    if (y <= this.planYearEnd()) this.calendarYear.set(y);
  }

  isCurrentMonthCol(month: number): boolean {
    return this.calendarYear() === this.currentYear() && month === this.currentMonth();
  }

  // ===========================================================================
  // Affichage
  // ===========================================================================

  /** Légende partagée avec la page Réalisation (mêmes statuts/icônes). */
  legendItems = ACTION_LEGEND_ITEMS;
  private readonly statusLabelKeys: Record<string, string> =
    Object.fromEntries(ACTION_LEGEND_ITEMS.map(i => [i.status, i.labelKey]));

  icon(status: MonthStatus | null): string {
    return status ? getActionIcon(status) : '';
  }

  statusLabelKey(status: MonthStatus | null): string {
    return status ? (this.statusLabelKeys[status] ?? 'plans.suivis.actions.actionPrevue') : '';
  }

  deadlineLabel(item: AgendaItem): string {
    if (item.month != null) return this.monthsShort()[item.month - 1] + ' ' + item.year;
    return this.translate.instant('plans.suivis.planification.wholeYear') + ' ' + item.year;
  }

  prioriteVariant(op: Operation): 'error' | 'warning' | 'neutral' {
    const l = op.priorite_label || '';
    if (l.includes('1')) return 'error';
    if (l.includes('2')) return 'warning';
    return 'neutral';
  }

  getOrganismesForOp(op: Operation): string {
    if (op.ventilation_mode !== 'by_org' && op.ventilation_mode !== 'by_org_type') return '';
    const seen = new Map<number, string>();
    for (const oa of op.operation_annees || []) {
      for (const oao of oa.organismes || []) {
        if (!seen.has(oao.id_organisme)) seen.set(oao.id_organisme, oao.organisme_nom || `Org #${oao.id_organisme}`);
      }
    }
    return [...seen.values()].join(', ');
  }

  navigateToViewOperation(operationId: number): void {
    this.router.navigate(['/plans', this.planSlug(), 'enjeux', 'operations', operationId, 'fiche']);
  }
}
