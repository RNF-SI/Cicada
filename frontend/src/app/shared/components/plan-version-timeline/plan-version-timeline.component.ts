import { Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem } from '../../../core/models/admin.model';
import { getExtensionBadgeKey, getPlanStatusKey } from '../../utils/plan-status.utils';

/** Groupe de versions du même rang affiché comme une section dans la timeline. */
interface RangGroup {
  rang: number;
  /** Position relative au rang courant : -1 = précédent, 0 = courant, +1 = suivant */
  position: 'previous' | 'current' | 'next';
  items: PlanVersionChainItem[];
  /** Item « représentatif » du rang pour navigation (dernière version validée).
   *  Null pour le rang courant (pas de navigation). */
  navigationTarget: PlanVersionChainItem | null;
}

@Component({
  selector: 'app-plan-version-timeline',
  standalone: true,
  imports: [CommonModule, RouterModule, MatChipsModule, MatTooltipModule, TranslateModule],
  templateUrl: './plan-version-timeline.component.html',
  styleUrl: './plan-version-timeline.component.scss',
})
export class PlanVersionTimelineComponent {
  private _chain = signal<PlanVersionChainItem[]>([]);

  @Input() set chain(value: PlanVersionChainItem[]) {
    this._chain.set(value || []);
  }
  get chain(): PlanVersionChainItem[] {
    return this._chain();
  }

  @Input() currentStatus = 'draft';
  /** Mnémonique du type de site principal (RNN, RNR, PNR, ENS...) — #281 */
  @Input() principalSiteTypeMnemonique: string | null = null;

  /** Items groupés par rang, triés et marqués previous/current/next. */
  rangGroups = computed<RangGroup[]>(() => {
    const chain = this._chain();
    if (!chain.length) return [];
    const current = chain.find(c => c.is_current);
    const currentRang = current?.rang ?? 1;

    const byRang = new Map<number, PlanVersionChainItem[]>();
    for (const item of chain) {
      const r = item.rang ?? 1;
      if (!byRang.has(r)) byRang.set(r, []);
      byRang.get(r)!.push(item);
    }
    // Tri intra-rang par version (entier si possible)
    for (const items of byRang.values()) {
      items.sort((a, b) => {
        const va = parseInt(a.version, 10) || 0;
        const vb = parseInt(b.version, 10) || 0;
        return va - vb;
      });
    }

    return [...byRang.entries()]
      .sort(([ra], [rb]) => ra - rb)
      .map(([r, items]): RangGroup => {
        const position = r < currentRang ? 'previous' : (r > currentRang ? 'next' : 'current');
        return {
          rang: r,
          position,
          items,
          navigationTarget: position === 'current' ? null : this.pickRangNavigationTarget(items),
        };
      });
  });

  /** Sélectionne la « dernière version validée » d'un rang pour la navigation.
   *  Priorité : valide/modifie > archive > draft/csrpn, puis version la plus haute. */
  private pickRangNavigationTarget(items: PlanVersionChainItem[]): PlanVersionChainItem | null {
    if (!items.length) return null;
    const statusPriority: Record<string, number> = {
      valide: 4,
      modifie: 4,
      archive: 3,
      arrete_pref: 2,
      comite_consultatif: 2,
      avis_csrpn: 2,
      draft: 1,
    };
    const sorted = [...items].sort((a, b) => {
      const pa = statusPriority[a.statut] ?? 0;
      const pb = statusPriority[b.statut] ?? 0;
      if (pa !== pb) return pb - pa;
      const va = parseInt(a.version, 10) || 0;
      const vb = parseInt(b.version, 10) || 0;
      return vb - va;
    });
    return sorted[0] ?? null;
  }

  /** Clé i18n du statut du plan. */
  getStatusLabelKey(item: PlanVersionChainItem): string {
    return getPlanStatusKey(item.statut);
  }

  /** #250 / #281 — Clé i18n du badge "Étendu" contextualisée par le type de site. */
  getExtensionBadgeLabelKey(): string {
    return getExtensionBadgeKey(this.principalSiteTypeMnemonique);
  }

  isItemExtended(item: PlanVersionChainItem): boolean {
    return !!((item as any).annees_extension && (item as any).annees_extension > 0);
  }

  getNodeIcon(item: PlanVersionChainItem): string {
    switch (item.type_document_mnemonique) {
      case 'EVAL_MI_PARCOURS':
        return 'fi-rr-time-forward';
      case 'PLAN_REVISE':
        return 'fi-rr-refresh';
      default:
        return 'fi-rr-document';
    }
  }

  getStatusClass(item: PlanVersionChainItem): string {
    const classes: Record<string, string> = {
      draft: 'status-warning',
      // #277 — Statuts intermédiaires CSRPN : couleur "en cours" (warning)
      // pour signaler qu'une étape réglementaire est en attente.
      avis_csrpn: 'status-warning',
      comite_consultatif: 'status-warning',
      arrete_pref: 'status-warning',
      valide: 'status-success',
      modifie: 'status-success',
      archive: 'status-neutre',
    };
    return classes[item.statut] || '';
  }

  /** #278 — Vrai si l'item de la chaîne est en cours de révision. */
  isItemInRevision(item: PlanVersionChainItem): boolean {
    return !!item.en_revision;
  }

  /** #276 — Vrai si l'item porte le drapeau évaluation mi-parcours. */
  isItemMiParcours(item: PlanVersionChainItem): boolean {
    return !!item.is_mi_parcours;
  }

  /**
   * Indique si un nœud représente le brouillon d'un rang ultérieur au plan
   * en cours de consultation (#280). Sert à appliquer un style distinct
   * (cadre pointillé) cf. note Cycle de vie d'un plan de gestion.
   */
  isNextRangDraft(item: PlanVersionChainItem): boolean {
    if (item.statut !== 'draft' || item.rang === undefined) return false;
    const current = this.chain.find(c => c.is_current);
    if (!current || current.rang === undefined) return false;
    return item.rang > current.rang;
  }
}
