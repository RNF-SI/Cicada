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
   */
  poll(): Observable<NotificationPollResponse> {
    let params = new HttpParams();
    const lastTimestamp = this.lastPollTimestampSignal();
    if (lastTimestamp) {
      params = params.set('since', lastTimestamp);
    }

    return this.http.get<NotificationPollResponse>(`${this.apiUrl}/poll/`, { params }).pipe(
      tap(response => {
        this.notificationsSignal.set(response.notifications);
        this.unreadCountSignal.set(response.unread_count);
        this.pendingValidationsSignal.set(response.pending_validations);
        this.lastPollTimestampSignal.set(response.timestamp);
      }),
      catchError(error => {
        console.error('Polling error:', error);
        return of({
          notifications: [],
          unread_count: 0,
          pending_validations: 0,
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
   */
  markAsRead(id: number): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(`${this.apiUrl}/${id}/mark_read/`, {}).pipe(
      tap(() => {
        // Mettre a jour le compteur
        this.unreadCountSignal.update(count => Math.max(0, count - 1));
        // Mettre a jour la liste
        this.notificationsSignal.update(notifications =>
          notifications.map(n => n.id === id ? { ...n, read: true } : n)
        );
      })
    );
  }

  /**
   * Marque toutes les notifications comme lues.
   */
  markAllAsRead(): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(`${this.apiUrl}/mark_all_read/`, {}).pipe(
      tap(() => {
        this.unreadCountSignal.set(0);
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
