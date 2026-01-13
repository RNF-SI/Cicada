import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { NavigationTileComponent, TileColor } from '../../shared/components/navigation-tile/navigation-tile.component';
import { AuthService } from '../../core/services/auth.service';
import { PublicStatsService } from '../../core/services/public-stats.service';
import { ValidationService } from '../../core/services/validation.service';

/**
 * Definition d'un module accessible sur la page d'accueil.
 */
interface HomeModule {
  code: string;
  titleKey: string;
  icon: string;
  link: string;
  color: TileColor;
  requiresAccess: boolean;
}

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
  private readonly validationService = inject(ValidationService);

  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly currentUser = this.authService.currentUser;

  // Public stats
  readonly stats = this.publicStatsService.stats;
  readonly statsLoading = this.publicStatsService.isLoading;

  // Modules accessibles par l'utilisateur
  readonly userModuleAccess = signal<string[]>([]);

  /**
   * Definition de tous les modules disponibles.
   * Les modules avec requiresAccess=true ne s'affichent que si l'utilisateur a l'acces.
   */
  readonly allModules: HomeModule[] = [
    // Modules de base (accessibles a tous les utilisateurs connectes)
    {
      code: 'plans',
      titleKey: 'home.tiles.plans',
      icon: 'fi-rr-document',
      link: '/plans',
      color: 'primary',
      requiresAccess: false
    },
    {
      code: 'sites',
      titleKey: 'home.tiles.sites',
      icon: 'fi-rr-map-marker',
      link: '/sites',
      color: 'salmon',
      requiresAccess: false
    },
    {
      code: 'inventaires',
      titleKey: 'home.tiles.inventaires',
      icon: 'fi-rr-test-tube',
      link: '/inventaires',
      color: 'yellow',
      requiresAccess: false
    },
    // Modules necessitant un acces specifique
    {
      code: 'zonages',
      titleKey: 'home.tiles.zonages',
      icon: 'fi-rr-map',
      link: '/zonages',
      color: 'terra-cotta',
      requiresAccess: true
    }
  ];

  /**
   * Retourne les modules visibles pour l'utilisateur.
   */
  get visibleModules(): HomeModule[] {
    const access = this.userModuleAccess();
    return this.allModules.filter(module => {
      if (!module.requiresAccess) {
        return true; // Module de base, toujours visible
      }
      return access.includes(module.code); // Module necessitant acces
    });
  }

  ngOnInit(): void {
    if (!this.isAuthenticated()) {
      // Charger les statistiques publiques pour les visiteurs non connectes
      this.publicStatsService.loadStats().subscribe();
    } else {
      // Charger les modules accessibles pour l'utilisateur connecte
      this.loadUserModuleAccess();
    }
  }

  /**
   * Charge les modules auxquels l'utilisateur a acces.
   */
  private loadUserModuleAccess(): void {
    this.validationService.getMyModuleAccess().subscribe({
      next: (response) => {
        this.userModuleAccess.set(response.modules);
      },
      error: (error) => {
        console.error('Erreur chargement acces modules:', error);
        this.userModuleAccess.set([]);
      }
    });
  }
}
