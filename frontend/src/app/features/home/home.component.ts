import { Component, inject, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { MatButtonModule } from '@angular/material/button';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { NavigationTileComponent } from '../../shared/components/navigation-tile/navigation-tile.component';
import { AuthService } from '../../core/services/auth.service';
import { PublicStatsService } from '../../core/services/public-stats.service';
import { ModuleService } from '../../core/services/module.service';
import { SettingsService } from '../../core/services/settings.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    NavigationTileComponent,
    MatButtonModule
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly publicStatsService = inject(PublicStatsService);
  private readonly moduleService = inject(ModuleService);
  private readonly settingsService = inject(SettingsService);

  readonly isAuthenticated = this.authService.isAuthenticated;
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
