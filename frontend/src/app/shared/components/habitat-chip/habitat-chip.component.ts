import { Component, computed, inject, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { HabitatService, CorrespondanceHabitat, HabitatOwnInfo } from '../../../core/services/habitat.service';

const MAX_RELATED = 12;

interface RelatedHabitat {
  code: string;
  name: string;
}

/**
 * Puce d'habitat HabRef cliquable. Au clic, charge à la demande, depuis HabRef,
 * les **habitats liés** à cet habitat *dans le même référentiel* (sous-types,
 * habitats associés…) — la base importée ne contient pas de correspondances
 * croisées entre référentiels. Affiche aussi la classification d'origine. #89
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
  /** Code propre de l'habitat dans sa typologie d'origine (ex. « G1.6 »). */
  code = input<string | null>(null);
  /** Typologie d'origine (ex. « EUNIS »). */
  typo = input<string | null>(null);
  /** Affiche une croix de suppression intégrée à la puce. */
  removable = input<boolean>(false);
  /** Émis au clic sur la croix de suppression. */
  remove = output<void>();

  expanded = signal(false);
  loading = signal(false);
  private loaded = signal(false);
  private relatedRaw = signal<CorrespondanceHabitat[]>([]);
  /** Classification d'origine récupérée depuis le serveur (via cd_hab seul). */
  private fetchedInfo = signal<HabitatOwnInfo | null>(null);

  /** Code/typologie d'origine : valeur fournie en entrée (instantanée) sinon
   * celle récupérée depuis le serveur — la puce est ainsi identique partout. */
  displayCode = computed<string | null>(() => this.code() || this.fetchedInfo()?.lb_code || null);
  displayTypo = computed<string | null>(() => this.typo() || this.fetchedInfo()?.lb_typo || null);
  /** Vrai si on connaît la classification d'origine de l'habitat. */
  hasOwnInfo = computed(() => !!(this.displayCode() || this.displayTypo()));

  /** Habitats liés (même référentiel) : code + nom, dédupliqués et plafonnés. */
  related = computed<{ items: RelatedHabitat[]; total: number; extra: number }>(() => {
    const seen = new Set<string>();
    const all: RelatedHabitat[] = [];
    for (const c of this.relatedRaw()) {
      const cd = (c.lb_code_entre || '').trim();
      const name = (c.lb_hab_entre || '').trim();
      if (!cd && !name) continue;
      const key = `${cd}|${name}`;
      if (seen.has(key)) continue;
      seen.add(key);
      all.push({ code: cd, name });
    }
    all.sort((a, b) => a.code.localeCompare(b.code) || a.name.localeCompare(b.name));
    return { items: all.slice(0, MAX_RELATED), total: all.length, extra: Math.max(0, all.length - MAX_RELATED) };
  });

  onRemove(event: Event): void {
    event.stopPropagation();
    this.remove.emit();
  }

  toggle(): void {
    const next = !this.expanded();
    this.expanded.set(next);
    if (next && !this.loaded()) {
      this.loading.set(true);
      this.habitatService.getCorrespondances(Number(this.cdHab())).subscribe({
        next: (res) => {
          this.fetchedInfo.set(res?.habitat ?? null);
          this.relatedRaw.set(res?.related ?? []);
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
