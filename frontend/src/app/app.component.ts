import { Component, inject, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';
import { Router, RouterOutlet, NavigationStart } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Subscription, filter } from 'rxjs';
import { TranslationService } from './core/services/translation.service';
import { SettingsService } from './core/services/settings.service';
import { MatomoService } from './core/services/matomo.service';
import { ExplorationRetourService } from './core/services/exploration-retour.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly translationService = inject(TranslationService);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly settings = inject(SettingsService);
  // #670 — Instancié ici pour suivre les navigations dès le démarrage.
  private readonly matomo = inject(MatomoService);
  /** #683 — Instancié ici pour retenir la dernière recherche d'exploration, quel que soit l'écran. */
  private readonly explorationRetour = inject(ExplorationRetourService);

  private routerSubscription?: Subscription;
  title = 'CICADA';

  ngOnInit(): void {
    this.translationService.initialize();

    // #670 — La mesure d'audience dépend des réglages de l'instance : ils
    // doivent être chargés sur toutes les pages, y compris celles sans bandeau.
    if (!this.settings.config()) {
      this.settings.loadSettings().subscribe();
    }

    // Fermer toutes les modales lors d'un changement de route (global)
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationStart))
      .subscribe(() => {
        this.dialog.closeAll();
      });
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
  }
}