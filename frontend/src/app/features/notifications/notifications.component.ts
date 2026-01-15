/**
 * Page de liste des notifications.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';

import { NotificationService } from '../../core/services/notification.service';
import { NotificationListItem } from '../../core/models/notification.model';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatChipsModule
  ],
  template: `
    <div class="notifications-page">
      <div class="page-header">
        <h1>Mes notifications</h1>
        @if (unreadCount() > 0) {
          <button mat-stroked-button color="primary" (click)="markAllAsRead()">
            <i class="fi fi-rr-check-double"></i>
            Tout marquer comme lu
          </button>
        }
      </div>

      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (notifications().length === 0) {
        <div class="empty-state">
          <i class="fi fi-rr-bell-slash"></i>
          <h2>Aucune notification</h2>
          <p>Vous n'avez pas encore de notification.</p>
        </div>
      } @else {
        <div class="notifications-list">
          @for (notification of notifications(); track notification.id) {
            <mat-card
              class="notification-card"
              [class.unread]="!notification.read"
              [class]="'priority-' + notification.priority"
            >
              <mat-card-content>
                <div class="notification-content">
                  <div class="notification-icon" [class]="notification.notification_type">
                    <i class="fi" [class]="getNotificationIcon(notification.notification_type)"></i>
                  </div>
                  <div class="notification-body">
                    <div class="notification-header">
                      <h3 class="notification-title">{{ notification.title }}</h3>
                      <span class="notification-time">{{ formatDate(notification.created_at) }}</span>
                    </div>
                    <p class="notification-message">{{ notification.message }}</p>
                    <div class="notification-meta">
                      <mat-chip [class]="'type-' + notification.notification_type">
                        {{ notification.notification_type_display }}
                      </mat-chip>
                      @if (!notification.read) {
                        <span class="unread-badge">Non lu</span>
                      }
                    </div>
                  </div>
                  <div class="notification-actions">
                    @if (!notification.read) {
                      <button mat-icon-button (click)="markAsRead(notification)" title="Marquer comme lu">
                        <i class="fi fi-rr-check"></i>
                      </button>
                    }
                    @if (notification.action_url) {
                      <a mat-icon-button [routerLink]="notification.action_url" title="Voir">
                        <i class="fi fi-rr-arrow-right"></i>
                      </a>
                    }
                  </div>
                </div>
              </mat-card-content>
            </mat-card>
          }
        </div>

        @if (hasMore()) {
          <div class="load-more">
            <button mat-stroked-button (click)="loadMore()" [disabled]="loadingMore()">
              @if (loadingMore()) {
                <mat-spinner diameter="20"></mat-spinner>
              } @else {
                Charger plus
              }
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .notifications-page {
      max-width: 800px;
      margin: 0 auto;
      padding: 24px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;

      h1 {
        margin: 0;
        font-size: 24px;
        color: #025359;
      }

      button {
        display: flex;
        align-items: center;
        gap: 8px;

        i {
          font-size: 16px;
        }
      }
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .empty-state {
      text-align: center;
      padding: 64px 24px;
      color: #666;

      i {
        font-size: 64px;
        color: #ccc;
        margin-bottom: 16px;
      }

      h2 {
        margin: 0 0 8px 0;
        color: #333;
      }

      p {
        margin: 0;
      }
    }

    .notifications-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .notification-card {
      transition: all 0.2s ease;

      &.unread {
        border-left: 4px solid #025359;
        background-color: rgba(2, 83, 89, 0.03);
      }

      &.priority-high {
        border-left-color: #FA9965;
      }

      &.priority-critical {
        border-left-color: #FF7579;
      }
    }

    .notification-content {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }

    .notification-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: #E8F5F5;
      color: #025359;
      flex-shrink: 0;

      i {
        font-size: 18px;
      }

      &.welcome {
        background-color: #E8F5E9;
        color: #2E7D32;
      }

      &.validation_approved {
        background-color: #E8F5E9;
        color: #2E7D32;
      }

      &.validation_rejected {
        background-color: #FFEBEE;
        color: #C62828;
      }

      &.validation_request {
        background-color: #FFF8E1;
        color: #F57C00;
      }
    }

    .notification-body {
      flex: 1;
      min-width: 0;
    }

    .notification-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 4px;
    }

    .notification-title {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .notification-time {
      font-size: 12px;
      color: #999;
      white-space: nowrap;
    }

    .notification-message {
      margin: 0 0 8px 0;
      color: #666;
      font-size: 14px;
    }

    .notification-meta {
      display: flex;
      align-items: center;
      gap: 8px;

      mat-chip {
        font-size: 11px;
        min-height: 24px;
      }

      .unread-badge {
        font-size: 11px;
        padding: 2px 8px;
        background-color: #025359;
        color: white;
        border-radius: 10px;
      }
    }

    .notification-actions {
      display: flex;
      gap: 4px;

      button, a {
        color: #666;

        &:hover {
          color: #025359;
        }

        i {
          font-size: 16px;
        }
      }
    }

    .load-more {
      display: flex;
      justify-content: center;
      margin-top: 24px;

      button {
        min-width: 150px;
      }
    }
  `]
})
export class NotificationsComponent implements OnInit {
  private readonly notificationService = inject(NotificationService);

  readonly notifications = signal<NotificationListItem[]>([]);
  readonly loading = signal(true);
  readonly loadingMore = signal(false);
  readonly hasMore = signal(false);
  readonly unreadCount = this.notificationService.unreadCount;

  private currentPage = 1;

  ngOnInit(): void {
    this.loadNotifications();
  }

  loadNotifications(): void {
    this.loading.set(true);
    this.notificationService.getNotifications(1).subscribe({
      next: (response) => {
        this.notifications.set(response.results);
        this.hasMore.set(response.next !== null);
        this.currentPage = 1;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  loadMore(): void {
    this.loadingMore.set(true);
    this.currentPage++;

    this.notificationService.getNotifications(this.currentPage).subscribe({
      next: (response) => {
        this.notifications.update(current => [...current, ...response.results]);
        this.hasMore.set(response.next !== null);
        this.loadingMore.set(false);
      },
      error: () => {
        this.loadingMore.set(false);
      }
    });
  }

  markAsRead(notification: NotificationListItem): void {
    this.notificationService.markAsRead(notification.id).subscribe({
      next: () => {
        this.notifications.update(list =>
          list.map(n => n.id === notification.id ? { ...n, read: true } : n)
        );
      }
    });
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead().subscribe({
      next: () => {
        this.notifications.update(list =>
          list.map(n => ({ ...n, read: true }))
        );
      }
    });
  }

  getNotificationIcon(type: string): string {
    const icons: Record<string, string> = {
      'welcome': 'fi-rr-hand-wave',
      'validation_request': 'fi-rr-check-circle',
      'validation_approved': 'fi-rr-check',
      'validation_rejected': 'fi-rr-cross',
      'user_associated_site': 'fi-rr-marker',
      'user_associated_plan': 'fi-rr-document',
      'user_removed_site': 'fi-rr-marker',
      'user_removed_plan': 'fi-rr-document',
      'account_deactivated': 'fi-rr-user-slash',
      'account_activated': 'fi-rr-user-check',
      'site_orphaned': 'fi-rr-exclamation',
      'organisme_no_admin': 'fi-rr-exclamation',
      'system_alert': 'fi-rr-bell',
      'info': 'fi-rr-info',
    };
    return icons[type] || 'fi-rr-bell';
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'A l\'instant';
    if (diffMins < 60) return `Il y a ${diffMins} min`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays < 7) return `Il y a ${diffDays}j`;

    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
