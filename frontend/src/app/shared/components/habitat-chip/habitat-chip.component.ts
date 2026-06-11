import { Component, computed, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { HabitatService, CorrespondanceHabitat } from '../../../core/services/habitat.service';

/** Typologies affichées (code cd_typo HabRef → libellé court lisible). #89 */
const DISPLAY_TYPOS: Record<number, string> = {
  7: 'EUNIS',
  22: 'Corine',
  4: "Cahiers d'habitats",
  8: 'Hab. intérêt comm.',
};

interface CorrespGroup {
  typo: number;
  label: string;
  codes: string[];
}

/**
 * Puce d'habitat HabRef cliquable. Au clic, charge à la demande les
 * correspondances dans les autres référentiels (EUNIS / Corine / Cahiers
 * d'habitats / HIC) et les affiche. Réutilisable (liste enjeux, accordéon). #89
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

  /** Correspondances regroupées par typologie d'affichage (codes dédupliqués). */
  groups = computed<CorrespGroup[]>(() => {
    const byTypo = new Map<number, Set<string>>();
    for (const c of this.correspondances()) {
      if (!(c.cd_typo_entre in DISPLAY_TYPOS)) continue;
      const code = (c.lb_code_entre || '').trim();
      if (!code) continue;
      if (!byTypo.has(c.cd_typo_entre)) byTypo.set(c.cd_typo_entre, new Set());
      byTypo.get(c.cd_typo_entre)!.add(code);
    }
    return Object.keys(DISPLAY_TYPOS)
      .map(Number)
      .filter(t => byTypo.has(t))
      .map(t => ({ typo: t, label: DISPLAY_TYPOS[t], codes: Array.from(byTypo.get(t)!).sort() }));
  });

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
