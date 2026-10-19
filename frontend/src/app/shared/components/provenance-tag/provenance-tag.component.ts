import { ChangeDetectionStrategy, Component, LOCALE_ID, computed, inject, input } from '@angular/core';
import { formatDate } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateService } from '@ngx-translate/core';

/**
 * Pastille de provenance (#692) : la structure CICADA d'où vient une donnée
 * de l'exploration.
 *
 * Même rendu partout (tuile de plan, ligne de contenu, fiche), en local comme
 * en exploration fédérée : l'utilisateur ne sait pas toujours dans quel mode il
 * cherche, et une URL de recherche partagée s'ouvre d'une instance à l'autre.
 * Aplat pastel et texte noir (kit UI « Tags ») ; au survol, l'identifiant
 * technique et, pour un instantané déposé sur le hub, sa date de publication.
 *
 * @example
 * <app-provenance-tag [libelle]="plan.instance_libelle" [instanceId]="plan.instance_id" />
 */
@Component({
  selector: 'app-provenance-tag',
  standalone: true,
  imports: [MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="provenance-tag" [matTooltip]="infobulle()" data-testid="exploration-source">
      <i class="fi fi-rr-globe" aria-hidden="true"></i>
      {{ libelle() }}
    </span>
  `,
  styleUrl: './provenance-tag.component.scss',
})
export class ProvenanceTagComponent {
  private readonly translate = inject(TranslateService);
  private readonly locale = inject(LOCALE_ID);

  /** Nom de la structure d'origine. */
  readonly libelle = input.required<string>();
  /** Identifiant technique de l'instance (« rnf »). */
  readonly instanceId = input<string | null | undefined>(null);
  /** Date de publication de l'instantané sur le hub ; nulle en lecture directe. */
  readonly datePublication = input<string | null | undefined>(null);

  readonly infobulle = computed(() => {
    const parties: string[] = [];
    const id = this.instanceId();
    if (id) parties.push(this.translate.instant('exploration.provenance.identifiant', { id }));
    const date = this.datePublication();
    if (date) {
      parties.push(this.translate.instant('exploration.provenance.publication', {
        date: formatDate(date, 'dd/MM/yyyy', this.locale),
      }));
    }
    return parties.join(' · ');
  });
}
