import { Component, computed, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { HabitatService, CorrespondanceHabitat } from '../../../core/services/habitat.service';

/** Typologies mises en avant (en tête) avec un libellé court lisible. */
const PRIORITY_TYPOS: Record<number, string> = {
  7: 'EUNIS',
  22: 'Corine biotopes',
  4: "Cahiers d'habitats",
  8: 'Hab. intérêt comm.',
};
const PRIORITY_ORDER = [7, 22, 4, 8];
const MAX_CODES = 10;

interface CorrespGroup {
  typo: number;
  label: string;
  codes: string[];
  extra: number; // nombre de codes masqués au-delà de MAX_CODES
}

/**
 * Puce d'habitat HabRef cliquable. Au clic, charge à la demande les
 * correspondances dans les autres référentiels et les affiche regroupées par
 * typologie (EUNIS / Corine / Cahiers d'habitats / HIC en tête, puis les
 * autres). Réutilisable (liste enjeux, formulaire d'action). #89
 */
@Component({
  selector: 'app-habitat-chip',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './habitat-chip.component.html',
  styleUrl: './habitat-chip.component.scss',
})
export class HabitatChipComponent {
  private readonly habitatService = inject(HabitatService);

  cdHab = input.required<string | number>();
  label = input<string>('');

  expanded = signal(false);
  loading = signal(false);
  private loaded = signal(false);
  private correspondances = signal<CorrespondanceHabitat[]>([]);

  /** Correspondances regroupées par typologie (toutes typologies), prioritaires
   * en tête, codes dédupliqués et plafonnés. */
  groups = computed<CorrespGroup[]>(() => {
    const byTypo = new Map<number, { label: string; codes: Set<string> }>();
    for (const c of this.correspondances()) {
      const code = (c.lb_code_entre || '').trim();
      if (!code) continue;
      if (!byTypo.has(c.cd_typo_entre)) {
        byTypo.set(c.cd_typo_entre, { label: this.typoLabel(c.cd_typo_entre, c.lb_typo), codes: new Set() });
      }
      byTypo.get(c.cd_typo_entre)!.codes.add(code);
    }
    const entries = Array.from(byTypo.entries());
    entries.sort((a, b) => {
      const pa = PRIORITY_ORDER.indexOf(a[0]);
      const pb = PRIORITY_ORDER.indexOf(b[0]);
      if (pa !== -1 || pb !== -1) return (pa === -1 ? 99 : pa) - (pb === -1 ? 99 : pb);
      return a[1].label.localeCompare(b[1].label);
    });
    return entries.map(([typo, v]) => {
      const all = Array.from(v.codes).sort();
      return { typo, label: v.label, codes: all.slice(0, MAX_CODES), extra: Math.max(0, all.length - MAX_CODES) };
    });
  });

  private typoLabel(cdTypo: number, lbTypo?: string): string {
    return PRIORITY_TYPOS[cdTypo] || (lbTypo || '').replace(/_/g, ' ');
  }

  toggle(): void {
    const next = !this.expanded();
    this.expanded.set(next);
    if (next && !this.loaded()) {
      this.loading.set(true);
      this.habitatService.getCorrespondances(Number(this.cdHab())).subscribe({
        next: (res) => {
          this.correspondances.set(res || []);
          this.loaded.set(true);
          this.loading.set(false);
        },
        error: () => {
          this.loaded.set(true);
          this.loading.set(false);
        },
      });
    }
  }
}
