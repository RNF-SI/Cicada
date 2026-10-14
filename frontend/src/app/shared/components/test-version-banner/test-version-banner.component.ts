import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';

/**
 * #709 — CICADA est « en pause » le temps de la phase de test : bandeau global
 * (`variant="banner"`) et encart des pages de connexion / inscription
 * (`variant="accounts"`) préviennent que les nouveaux comptes ne seront pas
 * validés avant l'ouverture.
 *
 * TEMPORAIRE : à retirer au déploiement réel — supprimer ce dossier, ses
 * 3 usages (app.component, login, register) et les clés i18n `testVersion.*`.
 */
@Component({
  selector: 'app-test-version-banner',
  standalone: true,
  imports: [TranslateModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './test-version-banner.component.html',
  styleUrl: './test-version-banner.component.scss',
})
export class TestVersionBannerComponent {
  readonly variant = input<'banner' | 'accounts'>('banner');
}
