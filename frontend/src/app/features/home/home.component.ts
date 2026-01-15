import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { NavigationTileComponent } from '../../shared/components/navigation-tile/navigation-tile.component';
import { AuthService } from '../../core/services/auth.service';
import { PublicStatsService } from '../../core/services/public-stats.service';
import { ModuleService } from '../../core/services/module.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    NavigationTileComponent
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly publicStatsService = inject(PublicStatsService);
  private readonly moduleService = inject(ModuleService);

  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly currentUser = this.authService.currentUser;

  // Public stats
  readonly stats = this.publicStatsService.stats;
  readonly statsLoading = this.publicStatsService.isLoading;

  // Modules accessibles par l'utilisateur (depuis l'API)
  readonly accessibleModules = this.moduleService.accessibleModules;
  readonly modulesLoading = this.moduleService.isLoading;

  ngOnInit(): void {
    if (!this.isAuthenticated()) {
      // Charger les statistiques publiques pour les visiteurs non connectes
      this.publicStatsService.loadStats().subscribe();
    } else {
      // Charger les modules accessibles pour l'utilisateur connecte
      this.moduleService.getMyAccessibleModules().subscribe();
    }
  }
}
