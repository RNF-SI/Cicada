import { Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem } from '../../../core/models/admin.model';
import { getExtensionBadgeKey, getPlanStatusKey } from '../../utils/plan-status.utils';
import { TagAppearance, getPlanStatusTag } from '../../utils/tag-icons';
import { TagComponent } from '../tag/tag.component';

/** Groupe de versions du même rang affiché comme une section dépliable. */
interface RangGroup {
  rang: number;
  items: PlanVersionChainItem[];
  /** Vrai si le plan en cours de consultation appartient à ce rang. */
  hasCurrent: boolean;
}

/**
 * Cycle de vie d'un plan — accordéon par rang.
 *
 * Design : Figma « ⏳ Cycle de vie » (node 4487:31081).
 * - Rangs et versions affichés du plus récent au plus ancien.
 * - Chaque rang est une section dépliable (« Rang 3 — 2 versions »).
 * - Le rang du plan consulté est ouvert par défaut ; les autres rangs peuvent
 *   être dépliés pour visualiser leurs versions, puis atteints via la flèche.
 */
@Component({
  selector: 'app-plan-version-timeline',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule, TagComponent],
  templateUrl: './plan-version-timeline.component.html',
  styleUrl: './plan-version-timeline.component.scss',
})
export class PlanVersionTimelineComponent {
  private _chain = signal<PlanVersionChainItem[]>([]);

  @Input() set chain(value: PlanVersionChainItem[]) {
    this._chain.set(value || []);
    this.expandedRangs.set(null);
  }
  get chain(): PlanVersionChainItem[] {
    return this._chain();
  }

  @Input() currentStatus = 'draft';
  /** Mnémonique du type de site principal (RNN, RNR, PNR, ENS...) — #281 */
  @Input() principalSiteTypeMnemonique: string | null = null;

  /**
   * Rangs dépliés. `null` = pas encore de choix utilisateur, on retombe sur le
   * défaut (rang du plan consulté ouvert).
   */
  private readonly expandedRangs = signal<Set<number> | null>(null);

  /** Items groupés par rang, du plus récent au plus ancien. */
  readonly rangGroups = computed<RangGroup[]>(() => {
    const chain = this._chain();
    if (!chain.length) return [];

    const byRang = new Map<number, PlanVersionChainItem[]>();
    for (const item of chain) {
      const r = item.rang ?? 1;
      if (!byRang.has(r)) byRang.set(r, []);
      byRang.get(r)!.push(item);
    }

    return [...byRang.entries()]
      // Rang décroissant : le plus récent en premier
      .sort(([ra], [rb]) => rb - ra)
      .map(([rang, items]): RangGroup => ({
        rang,
        // Version décroissante : la plus récente en premier
        items: [...items].sort(
          (a, b) => (parseInt(b.version, 10) || 0) - (parseInt(a.version, 10) || 0),
        ),
        hasCurrent: items.some(i => i.is_current),
      }));
  });

  /** Rang du plan consulté — ouvert par défaut. */
  private readonly currentRang = computed<number | null>(
    () => this.rangGroups().find(g => g.hasCurrent)?.rang ?? null,
  );

  isExpanded(rang: number): boolean {
    const explicit = this.expandedRangs();
    if (explicit) return explicit.has(rang);
    return rang === this.currentRang();
  }

  toggleRang(rang: number): void {
    const next = new Set(
      this.expandedRangs() ?? (this.currentRang() !== null ? [this.currentRang()!] : []),
    );
    if (next.has(rang)) {
      next.delete(rang);
    } else {
      next.add(rang);
    }
    this.expandedRangs.set(next);
  }

  /** Couleur + icône du tag statut (source Figma, cf. `tag-icons.ts`). */
  statusTag(item: PlanVersionChainItem): TagAppearance {
    return getPlanStatusTag(item.statut);
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
    return !!(item.annees_extension && item.annees_extension > 0);
  }

  /** #278 — Vrai si l'item de la chaîne est en cours de révision. */
  isItemInRevision(item: PlanVersionChainItem): boolean {
    return !!item.en_revision;
  }

  /** #276 — Vrai si l'item porte le drapeau évaluation mi-parcours. */
  isItemMiParcours(item: PlanVersionChainItem): boolean {
    return !!item.is_mi_parcours;
  }
}
