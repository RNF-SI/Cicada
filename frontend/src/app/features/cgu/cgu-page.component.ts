import { ChangeDetectionStrategy, Component, computed, inject, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { SettingsService } from '../../core/services/settings.service';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { renderMarkdown } from '../../shared/utils/markdown.utils';

/** #746 — Conditions générales d'utilisation de l'instance, consultables sans connexion. */
@Component({
  selector: 'app-cgu-page',
  standalone: true,
  imports: [DatePipe, TranslateModule, HeaderComponent],
  templateUrl: './cgu-page.component.html',
  styleUrl: './cgu-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CguPageComponent implements OnInit {
  private readonly settings = inject(SettingsService);
  private readonly auth = inject(AuthService);

  readonly isAuthenticated = this.auth.isAuthenticated;
  readonly config = this.settings.config;
  readonly html = computed(() => renderMarkdown(this.config()?.cgu_texte));

  ngOnInit(): void {
    if (!this.config()) {
      this.settings.loadSettings().subscribe();
    }
  }
}
