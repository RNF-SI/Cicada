import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { A11yModule } from '@angular/cdk/a11y';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/services/auth.service';
import { SettingsService } from '../../../core/services/settings.service';
import { CheckboxComponent } from '../checkbox/checkbox.component';
import { renderMarkdown } from '../../utils/markdown.utils';

/**
 * #746 — Acceptation des conditions générales d'utilisation.
 *
 * Tant que l'utilisateur connecté n'a pas accepté la version en vigueur des
 * CGU de l'instance, cette fenêtre recouvre l'application : il les accepte ou
 * se déconnecte. Ce n'est pas une MatDialog — `AppComponent` ferme toutes les
 * modales à chaque navigation, et celle-ci ne doit pas pouvoir être écartée.
 * Masquée pendant une impersonation : l'administrateur n'accepte pas à la
 * place de l'utilisateur.
 */
@Component({
  selector: 'app-cgu-gate',
  standalone: true,
  imports: [A11yModule, MatButtonModule, TranslateModule, CheckboxComponent],
  templateUrl: './cgu-gate.component.html',
  styleUrl: './cgu-gate.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CguGateComponent {
  private readonly auth = inject(AuthService);
  private readonly settings = inject(SettingsService);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  readonly coche = signal(false);
  readonly envoi = signal(false);
  readonly erreur = signal<string | null>(null);

  readonly visible = computed(() =>
    this.auth.currentUser()?.cgu_a_accepter === true
    && !this.auth.isImpersonating()
    && !!this.settings.config()?.cgu_version,
  );

  readonly html = computed(() => renderMarkdown(this.settings.config()?.cgu_texte));

  accepter(): void {
    const version = this.settings.config()?.cgu_version;
    if (!this.coche() || !version || this.envoi()) {
      return;
    }
    this.envoi.set(true);
    this.erreur.set(null);
    this.auth.accepterCgu(version).subscribe({
      next: () => {
        this.envoi.set(false);
        this.coche.set(false);
      },
      error: (err: { status?: number }) => {
        this.envoi.set(false);
        if (err?.status === 409) {
          // Le texte a changé pendant la lecture : afficher la nouvelle version.
          this.coche.set(false);
          this.settings.loadSettings().subscribe();
          this.erreur.set(this.translate.instant('cgu.gate.modifiees'));
        } else {
          this.erreur.set(this.translate.instant('cgu.gate.erreur'));
        }
      },
    });
  }

  deconnecter(): void {
    this.auth.logout().subscribe(() => this.router.navigate(['/accueil']));
  }
}
