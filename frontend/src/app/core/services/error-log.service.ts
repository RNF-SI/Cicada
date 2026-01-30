/**
 * Service pour la gestion des logs d'erreur.
 * Permet aux super admins de consulter et acquitter les erreurs.
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap, catchError } from 'rxjs';
import {
  ErrorLog,
  ErrorLogDetail,
  ErrorLogStats,
  ErrorLogPaginatedResponse,
  ErrorLogFilters,
  AcknowledgeResponse
} from '../models/error-log.model';

@Injectable({
  providedIn: 'root'
})
export class ErrorLogService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/admin/error-logs';

  // Signals pour l'etat
  readonly unacknowledgedCount = signal<number>(0);
  readonly isLoading = signal<boolean>(false);

  // Timer pour le rafraichissement automatique du count
  private refreshInterval: ReturnType<typeof setInterval> | null = null;

  /**
   * Demarre le rafraichissement automatique du count.
   * Appele depuis le layout admin.
   */
  startAutoRefresh(intervalMs: number = 60000): void {
    this.stopAutoRefresh();
    this.refreshUnacknowledgedCount();

    this.refreshInterval = setInterval(() => {
      this.refreshUnacknowledgedCount();
    }, intervalMs);
  }

  /**
   * Arrete le rafraichissement automatique.
   */
  stopAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Rafraichit le nombre de logs non acquittes.
   */
  refreshUnacknowledgedCount(): void {
    this.getUnacknowledgedCount().subscribe({
      next: (count) => this.unacknowledgedCount.set(count),
      error: () => {} // Ignorer silencieusement les erreurs
    });
  }

  /**
   * Recupere la liste paginee des logs d'erreur.
   */
  getErrorLogs(filters: ErrorLogFilters = {}): Observable<ErrorLogPaginatedResponse> {
    let params = new HttpParams();

    if (filters.level) {
      params = params.set('level', filters.level);
    }
    if (filters.acknowledged !== undefined) {
      params = params.set('acknowledged', filters.acknowledged.toString());
    }
    if (filters.date_from) {
      params = params.set('date_from', filters.date_from);
    }
    if (filters.date_to) {
      params = params.set('date_to', filters.date_to);
    }
    if (filters.exception_type) {
      params = params.set('exception_type', filters.exception_type);
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }
    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.ordering) {
      params = params.set('ordering', filters.ordering);
    }

    this.isLoading.set(true);

    return this.http.get<ErrorLogPaginatedResponse>(this.baseUrl + '/', { params }).pipe(
      tap(() => this.isLoading.set(false)),
      catchError((error) => {
        this.isLoading.set(false);
        throw error;
      })
    );
  }

  /**
   * Recupere le detail d'un log d'erreur.
   */
  getErrorLog(id: number): Observable<ErrorLogDetail> {
    return this.http.get<ErrorLogDetail>(`${this.baseUrl}/${id}/`);
  }

  /**
   * Acquitte un log d'erreur.
   */
  acknowledge(id: number): Observable<AcknowledgeResponse> {
    return this.http.post<AcknowledgeResponse>(`${this.baseUrl}/${id}/acknowledge/`, {}).pipe(
      tap(() => {
        // Mettre a jour le count
        const currentCount = this.unacknowledgedCount();
        if (currentCount > 0) {
          this.unacknowledgedCount.set(currentCount - 1);
        }
      })
    );
  }

  /**
   * Acquitte tous les logs non acquittes.
   */
  acknowledgeAll(filters: ErrorLogFilters = {}): Observable<AcknowledgeResponse> {
    let params = new HttpParams();

    // Appliquer les memes filtres que la liste
    if (filters.level) {
      params = params.set('level', filters.level);
    }
    if (filters.date_from) {
      params = params.set('date_from', filters.date_from);
    }
    if (filters.date_to) {
      params = params.set('date_to', filters.date_to);
    }
    if (filters.exception_type) {
      params = params.set('exception_type', filters.exception_type);
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }

    return this.http.post<AcknowledgeResponse>(`${this.baseUrl}/acknowledge_all/`, {}, { params }).pipe(
      tap((response) => {
        // Mettre a jour le count
        const currentCount = this.unacknowledgedCount();
        const acknowledged = response.acknowledged_count || 0;
        this.unacknowledgedCount.set(Math.max(0, currentCount - acknowledged));
      })
    );
  }

  /**
   * Recupere les statistiques des logs.
   */
  getStats(): Observable<ErrorLogStats> {
    return this.http.get<ErrorLogStats>(`${this.baseUrl}/stats/`);
  }

  /**
   * Recupere le nombre de logs non acquittes.
   */
  getUnacknowledgedCount(): Observable<number> {
    return new Observable<number>(subscriber => {
      this.http.get<{ count: number }>(`${this.baseUrl}/unacknowledged_count/`).subscribe({
        next: (response) => {
          this.unacknowledgedCount.set(response.count);
          subscriber.next(response.count);
          subscriber.complete();
        },
        error: () => {
          subscriber.next(0);
          subscriber.complete();
        }
      });
    });
  }
}
