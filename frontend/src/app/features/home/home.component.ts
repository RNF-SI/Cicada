import { Component, inject, OnInit, computed, ChangeDetectionStrategy } from '@angular/core';

import { RouterModule } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs/operators';
import { TranslateModule } from '@ngx-translate/core';
import { MatButtonModule } from '@angular/material/button';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { NavigationTileComponent } from '../../shared/components/navigation-tile/navigation-tile.component';
import { AuthService } from '../../core/services/auth.service';
import { PublicStatsService } from '../../core/services/public-stats.service';
import { ModuleService } from '../../core/services/module.service';
import { SettingsService } from '../../core/services/settings.service';
import { EuFundingNoticeComponent } from '../../shared/components/eu-funding-notice/eu-funding-notice.component';
import { PartnersBandComponent } from '../../shared/components/partners-band/partners-band.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    RouterModule,
    TranslateModule,
    HeaderComponent,
    NavigationTileComponent,
    MatButtonModule,
    EuFundingNoticeComponent,
    PartnersBandComponent
],
  templateUrl: './home.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly publicStatsService = inject(PublicStatsService);
  private readonly moduleService = inject(ModuleService);
  private readonly settingsService = inject(SettingsService);

  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly anneeCourante = new Date().getFullYear();
  /** #689 — pas d'inscription CICADA quand l'instance se connecte par un GeoNature. */
  readonly inscriptionOuverte = toSignal(
    this.authService.getLoginMode().pipe(map(mode => mode.mode === 'local')),
    { initialValue: false }
  );
  readonly currentUser = this.authService.currentUser;

  // Public stats
  readonly stats = this.publicStatsService.stats;
  readonly statsLoading = this.publicStatsService.isLoading;

  // Modules accessibles par l'utilisateur (depuis l'API)
  readonly accessibleModules = this.moduleService.accessibleModules;
  readonly modulesLoading = this.moduleService.isLoading;
  readonly modulesError = this.moduleService.loadError;

  // Homepage image (for guest view)
  readonly homepageImage = computed(() => this.settingsService.getHomepageImageUrl());

  /** #710 — Logo de la structure qui déploie l'instance (null si aucun). */
  readonly structureLogoUrl = computed(() => this.settingsService.getStructureLogoUrl());
  /** #724 — Inscription confiée à une plateforme externe (null = formulaire local). */
  readonly inscriptionExterne = computed(() => this.settingsService.inscriptionUrlExterne());
  /** #710 — Textes d'accueil personnalisés ; vides → textes par défaut (fr.json). */
  readonly accueilTitre = computed(() => this.settingsService.config()?.accueil_titre || '');
  readonly accueilSousTitre = computed(() => this.settingsService.config()?.accueil_sous_titre || '');

  // Homepage image position (top, center, bottom)
  readonly homepageImagePosition = computed(() => {
    const config = this.settingsService.config();
    const position = config?.homepage_image_position || 'top';
    switch (position) {
      case 'top': return 'center top';
      case 'bottom': return 'center bottom';
      default: return 'center center';
    }
  });

  ngOnInit(): void {
    if (!this.isAuthenticated()) {
      // Load site settings for guest view (homepage image)
      this.settingsService.loadSettings().subscribe();
      // Charger les statistiques publiques pour les visiteurs non connectes
      this.publicStatsService.loadStats().subscribe();
    } else {
      // Charger les modules accessibles pour l'utilisateur connecte
      this.moduleService.getMyAccessibleModules().subscribe();
    }
  }

  retryLoadModules(): void {
    this.moduleService.getMyAccessibleModules().subscribe();
  }
}
