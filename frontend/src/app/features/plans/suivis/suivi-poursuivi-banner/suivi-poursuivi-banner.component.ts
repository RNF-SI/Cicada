import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { SuiviPoursuiviDans } from '../../../../core/models/admin.model';

/**
 * #803 — Un seul suivi par rang : sur une version dont le suivi se poursuit
 * dans une version plus récente du même rang, les pages de suivi ne montrent
 * plus de saisie mais renvoient vers la même page de la version qui le porte.
 */
@Component({
  selector: 'app-suivi-poursuivi-banner',
  standalone: true,
  imports: [RouterLink, TranslateModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (suite(); as s) {
      <div class="lock-banner" role="status" data-testid="suivi-poursuivi">
        <i class="fi fi-rr-arrow-right"></i>
        <div class="lock-banner-content">
          <span class="lock-banner-title">{{ 'plans.suivis.poursuiviBanner.title' | translate }}</span>
          <span class="lock-banner-text">
            {{ 'plans.suivis.poursuiviBanner.text' | translate: { version: s.version, nom: s.nom } }}
          </span>
          <a class="link-default" data-testid="suivi-poursuivi-lien"
             [routerLink]="['/plans', s.slug, page()]">
            {{ 'plans.suivis.poursuiviBanner.link' | translate: { version: s.version } }}
          </a>
        </div>
      </div>
    }
  `,
})
export class SuiviPoursuiviBannerComponent {
  /** Version qui porte le suivi (`plan.suivi_poursuivi_dans`). */
  suite = input<SuiviPoursuiviDans | null | undefined>(null);
  /** Page de suivi de cette version à ouvrir (bilan, suivi-actions…). */
  page = input<string>('suivi-actions');
}
