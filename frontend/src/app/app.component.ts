import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { Router, RouterOutlet, NavigationStart } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Subscription, filter } from 'rxjs';
import { TranslationService } from './core/services/translation.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly translationService = inject(TranslationService);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);

  private routerSubscription?: Subscription;
  title = 'CICADA';

  ngOnInit(): void {
    this.translationService.initialize();

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