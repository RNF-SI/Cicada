import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, tap, of } from 'rxjs';

export interface PublicStats {
  sites_count: number;
  plans_count: number;
  organismes_count: number;
}

@Injectable({
  providedIn: 'root'
})
export class PublicStatsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/auth/stats/';

  // State management with signals
  private statsSignal = signal<PublicStats | null>(null);
  private isLoadingSignal = signal<boolean>(false);
  private errorSignal = signal<string | null>(null);

  // Public readonly signals
  readonly stats = this.statsSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();

  /**
   * Charge les statistiques publiques depuis l'API.
   * Cette methode peut etre appelee sans authentification.
   */
  loadStats(): Observable<PublicStats> {
    this.isLoadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.get<PublicStats>(this.apiUrl).pipe(
      tap(stats => {
        this.statsSignal.set(stats);
        this.isLoadingSignal.set(false);
      }),
      catchError(error => {
        console.error('Erreur lors du chargement des statistiques:', error);
        this.errorSignal.set('Impossible de charger les statistiques');
        this.isLoadingSignal.set(false);
        return of({
          sites_count: 0,
          plans_count: 0,
          organismes_count: 0
        });
      })
    );
  }
}
