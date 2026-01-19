/**
 * Service pour la gestion des notifications.
 */
import { Injectable, inject, signal, computed, OnDestroy } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, Subject, interval, takeUntil, switchMap, tap, catchError, of } from 'rxjs';

import {
  Notification,
  NotificationListItem,
  NotificationPollResponse,
  NotificationCountResponse
} from '../models/notification.model';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/notifications';

  // Signals pour l'etat reactif
  private notificationsSignal = signal<NotificationListItem[]>([]);
  private unreadCountSignal = signal<number>(0);
  private pendingValidationsSignal = signal<number>(0);
  private lastPollTimestampSignal = signal<string | null>(null);

  // Signals publics en lecture seule
  readonly notifications = this.notificationsSignal.asReadonly();
  readonly unreadCount = this.unreadCountSignal.asReadonly();
  readonly pendingValidations = this.pendingValidationsSignal.asReadonly();
  readonly hasUnread = computed(() => this.unreadCountSignal() > 0);
  readonly hasPendingValidations = computed(() => this.pendingValidationsSignal() > 0);
  readonly totalBadgeCount = computed(() => this.unreadCountSignal() + this.pendingValidationsSignal());

  // Gestion du polling
  private pollingInterval = 30000; // 30 secondes
  private pollingDestroy$ = new Subject<void>();
  private isPolling = false;

  // Protection contre les race conditions
  // Timestamp de la derniere action de marquage (pour ignorer les polls obsoletes)
  private lastMarkActionTimestamp = 0;

  ngOnDestroy(): void {
    this.stopPolling();
  }

  /**
   * Demarre le polling des notifications.
   */
  startPolling(): void {
    if (this.isPolling) {
      return;
    }

    this.isPolling = true;

    // Premier appel immediat
    this.poll().subscribe();

    // Puis polling regulier
    interval(this.pollingInterval)
      .pipe(
        takeUntil(this.pollingDestroy$),
        switchMap(() => this.poll())
      )
      .subscribe();
  }

  /**
   * Arrete le polling.
   */
  stopPolling(): void {
    this.isPolling = false;
    this.pollingDestroy$.next();
    this.pollingDestroy$.complete();
    this.pollingDestroy$ = new Subject<void>();
  }

  /**
   * Effectue un poll pour les nouvelles notifications.
   * Utilise un timestamp pour eviter les race conditions avec les actions de marquage.
   */
  poll(): Observable<NotificationPollResponse> {
    const pollStartTime = Date.now();
    let params = new HttpParams();
    const lastTimestamp = this.lastPollTimestampSignal();
    if (lastTimestamp) {
      params = params.set('since', lastTimestamp);
    }

    return this.http.get<NotificationPollResponse>(`${this.apiUrl}/poll/`, { params }).pipe(
      tap(response => {
        // Toujours mettre a jour les notifications et le timestamp
        this.notificationsSignal.set(response.notifications);
        this.pendingValidationsSignal.set(response.pending_validations);
        this.lastPollTimestampSignal.set(response.timestamp);

        // Ne mettre a jour le compteur que si ce poll a demarre APRES la derniere action
        // Cela evite qu'un poll obsolete ecrase le compteur apres un markAllAsRead()
        if (pollStartTime > this.lastMarkActionTimestamp) {
          this.unreadCountSignal.set(response.unread_count);
        }
      }),
      catchError(error => {
        console.error('Polling error:', error);
        // En cas d'erreur, conserver les valeurs actuelles (ne pas forcer a 0)
        return of({
          notifications: this.notificationsSignal(),
          unread_count: this.unreadCountSignal(),
          pending_validations: this.pendingValidationsSignal(),
          has_updates: false,
          timestamp: new Date().toISOString()
        });
      })
    );
  }

  /**
   * Recupere la liste paginee des notifications.
   */
  getNotifications(page: number = 1): Observable<PaginatedResponse<NotificationListItem>> {
    const params = new HttpParams().set('page', page.toString());
    return this.http.get<PaginatedResponse<NotificationListItem>>(this.apiUrl + '/', { params });
  }

  /**
   * Recupere une notification par ID.
   */
  getNotification(id: number): Observable<Notification> {
    return this.http.get<Notification>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Recupere les notifications non lues.
   */
  getUnreadNotifications(): Observable<NotificationListItem[]> {
    return this.http.get<NotificationListItem[]>(`${this.apiUrl}/unread/`);
  }

  /**
   * Recupere le compteur de notifications non lues.
   */
  getUnreadCount(): Observable<NotificationCountResponse> {
    return this.http.get<NotificationCountResponse>(`${this.apiUrl}/count/`).pipe(
      tap(response => {
        this.unreadCountSignal.set(response.unread_count);
      })
    );
  }

  /**
   * Marque une notification comme lue.
   * Utilise le compteur retourne par le backend pour garantir la coherence.
   */
  markAsRead(id: number): Observable<{ status: string; unread_count: number }> {
    // Enregistrer le timestamp AVANT l'appel pour bloquer les polls en cours
    this.lastMarkActionTimestamp = Date.now();

    return this.http.post<{ status: string; unread_count: number }>(`${this.apiUrl}/${id}/mark_read/`, {}).pipe(
      tap(response => {
        // Utiliser le compteur reel retourne par le backend
        this.unreadCountSignal.set(response.unread_count);
        // Mettre a jour la liste
        this.notificationsSignal.update(notifications =>
          notifications.map(n => n.id === id ? { ...n, read: true } : n)
        );
      })
    );
  }

  /**
   * Marque toutes les notifications comme lues.
   * Utilise le compteur retourne par le backend pour garantir la coherence.
   */
  markAllAsRead(): Observable<{ status: string; unread_count: number; updated_count: number }> {
    // Enregistrer le timestamp AVANT l'appel pour bloquer les polls en cours
    this.lastMarkActionTimestamp = Date.now();

    return this.http.post<{ status: string; unread_count: number; updated_count: number }>(
      `${this.apiUrl}/mark_all_read/`, {}
    ).pipe(
      tap(response => {
        // Utiliser le compteur reel retourne par le backend (devrait etre 0)
        this.unreadCountSignal.set(response.unread_count);
        this.notificationsSignal.update(notifications =>
          notifications.map(n => ({ ...n, read: true }))
        );
      })
    );
  }

  /**
   * Supprime une notification.
   */
  deleteNotification(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`).pipe(
      tap(() => {
        this.notificationsSignal.update(notifications =>
          notifications.filter(n => n.id !== id)
        );
      })
    );
  }

  /**
   * Met a jour manuellement le compteur de validations en attente.
   */
  updatePendingValidationsCount(count: number): void {
    this.pendingValidationsSignal.set(count);
  }

  /**
   * Rafraichit les notifications (force un nouveau poll).
   */
  refresh(): Observable<NotificationPollResponse> {
    this.lastPollTimestampSignal.set(null);
    return this.poll();
  }
}
