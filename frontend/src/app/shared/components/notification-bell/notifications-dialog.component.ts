/**
 * Dialog pour afficher toutes les notifications.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';

import { NotificationService } from '../../../core/services/notification.service';
import { NotificationListItem } from '../../../core/models/notification.model';

@Component({
  selector: 'app-notifications-dialog',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule
  ],
  template: `
    <div class="notifications-dialog">
      <div class="dialog-header">
        <h2>Mes notifications</h2>
        <div class="header-actions">
          @if (unreadCount() > 0) {
            <button class="mark-all-btn" (click)="markAllAsRead()">
              <i class="fi fi-rr-check-double"></i>
              Tout marquer lu
            </button>
          }
          <button class="close-btn" (click)="close()">
            <i class="fi fi-rr-cross"></i>
          </button>
        </div>
      </div>

      <mat-divider></mat-divider>

      <div class="dialog-content">
        @if (loading()) {
          <div class="loading-container">
            <mat-spinner diameter="32"></mat-spinner>
          </div>
        } @else if (notifications().length === 0) {
          <div class="empty-state">
            <i class="fi fi-rr-bell-slash"></i>
            <p>Aucune notification</p>
          </div>
        } @else {
          <div class="notifications-list">
            @for (notification of notifications(); track notification.id) {
              <div
                class="notification-item"
                [class.unread]="!notification.read"
                [class.expanded]="isExpanded(notification.id)"
                [class.priority-high]="notification.priority === 'high'"
                [class.priority-critical]="notification.priority === 'critical'"
                (click)="onNotificationClick(notification, $event)"
              >
                <div class="notification-icon" [class]="notification.notification_type">
                  <i class="fi" [class]="getNotificationIcon(notification.notification_type)"></i>
                </div>
                <div class="notification-body">
                  <div class="notification-header">
                    <span class="notification-title">{{ notification.title }}</span>
                    <span class="notification-time">{{ formatDate(notification.created_at) }}</span>
                  </div>
                  <p class="notification-message" [class.truncated]="!isExpanded(notification.id)">
                    {{ notification.message }}
                  </p>
                  @if (isExpanded(notification.id)) {
                    <div class="notification-expanded-actions">
                      @if (notification.action_url) {
                        <button class="action-btn primary" (click)="goToAction(notification, $event)">
                          <i class="fi fi-rr-arrow-right"></i>
                          Voir les details
                        </button>
                      }
                      @if (!notification.read) {
                        <button class="action-btn" (click)="markAsRead(notification, $event)">
                          <i class="fi fi-rr-check"></i>
                          Marquer lu
                        </button>
                      }
                    </div>
                  }
                </div>
                <div class="expand-indicator">
                  <i class="fi" [class.fi-rr-angle-down]="!isExpanded(notification.id)" [class.fi-rr-angle-up]="isExpanded(notification.id)"></i>
                </div>
              </div>
            }
          </div>

          @if (hasMore()) {
            <div class="load-more">
              <button class="load-more-btn" (click)="loadMore()" [disabled]="loadingMore()">
                @if (loadingMore()) {
                  <mat-spinner diameter="16"></mat-spinner>
                } @else {
                  Charger plus
                }
              </button>
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [`
    .notifications-dialog {
      width: 500px;
      max-width: 90vw;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;

      h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #025359;
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .mark-all-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border: 1px solid #025359;
        border-radius: 20px;
        background: transparent;
        color: #025359;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: #025359;
          color: white;
        }

        i {
          font-size: 12px;
        }
      }

      .close-btn {
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 50%;
        background: #f5f5f5;
        color: #666;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;

        &:hover {
          background: #e0e0e0;
          color: #333;
        }

        i {
          font-size: 14px;
        }
      }
    }

    .dialog-content {
      flex: 1;
      overflow-y: auto;
      padding: 0;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .empty-state {
      text-align: center;
      padding: 48px 24px;
      color: #999;

      i {
        font-size: 48px;
        margin-bottom: 12px;
        display: block;
      }

      p {
        margin: 0;
        font-size: 14px;
      }
    }

    .notifications-list {
      display: flex;
      flex-direction: column;
    }

    .notification-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 14px 20px;
      cursor: pointer;
      transition: background-color 0.2s;
      border-bottom: 1px solid #f0f0f0;

      &:hover {
        background-color: #f9f9f9;
      }

      &.unread {
        background-color: rgba(2, 83, 89, 0.04);
        border-left: 3px solid #025359;
      }

      &.priority-high {
        border-left-color: #FA9965;
      }

      &.priority-critical {
        border-left-color: #FF7579;
      }
    }

    .notification-icon {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: #E8F5F5;
      color: #025359;
      flex-shrink: 0;

      i {
        font-size: 16px;
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
      gap: 8px;
      margin-bottom: 4px;
    }

    .notification-title {
      font-size: 14px;
      font-weight: 600;
      color: #333;
      line-height: 1.3;
    }

    .notification-time {
      font-size: 11px;
      color: #999;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .notification-message {
      margin: 0;
      font-size: 13px;
      color: #666;
      line-height: 1.4;

      &.truncated {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
    }

    .notification-item.expanded {
      background-color: #f5f9f9;

      .notification-message {
        display: block;
        overflow: visible;
      }
    }

    .notification-expanded-actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #e0e0e0;
    }

    .action-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border: 1px solid #ddd;
      border-radius: 16px;
      background: white;
      color: #666;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: #025359;
        color: #025359;
      }

      &.primary {
        background: #025359;
        border-color: #025359;
        color: white;

        &:hover {
          background: #013d40;
        }
      }

      i {
        font-size: 12px;
      }
    }

    .expand-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      color: #999;
      flex-shrink: 0;
      transition: color 0.2s;

      i {
        font-size: 14px;
      }
    }

    .notification-item:hover .expand-indicator {
      color: #025359;
    }

    .mark-read-btn {
      width: 28px;
      height: 28px;
      border: none;
      border-radius: 50%;
      background: #E8F5F5;
      color: #025359;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: all 0.2s;

      &:hover {
        background: #025359;
        color: white;
      }

      i {
        font-size: 12px;
      }
    }

    .load-more {
      padding: 16px;
      text-align: center;

      .load-more-btn {
        padding: 8px 24px;
        border: 1px solid #ddd;
        border-radius: 20px;
        background: white;
        color: #666;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 8px;

        &:hover:not(:disabled) {
          border-color: #025359;
          color: #025359;
        }

        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
  `]
})
export class NotificationsDialogComponent implements OnInit {
  private readonly notificationService = inject(NotificationService);
  private readonly dialogRef = inject(MatDialogRef<NotificationsDialogComponent>);

  readonly notifications = signal<NotificationListItem[]>([]);
  readonly loading = signal(true);
  readonly loadingMore = signal(false);
  readonly hasMore = signal(false);
  readonly unreadCount = this.notificationService.unreadCount;
  readonly expandedId = signal<number | null>(null);

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

        // Marquer automatiquement toutes les notifications comme lues a l'ouverture
        if (response.results.some(n => !n.read)) {
          this.notificationService.markAllAsRead().subscribe({
            next: () => {
              // Mettre a jour la liste locale pour refleter l'etat "lu"
              this.notifications.update(list =>
                list.map(n => ({ ...n, read: true }))
              );
            }
          });
        }
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

  onNotificationClick(notification: NotificationListItem, event: Event): void {
    // Si on clique sur le bouton d'action, ne pas toggle l'expansion
    if ((event.target as HTMLElement).closest('.action-btn')) {
      return;
    }

    // Toggle l'expansion
    if (this.expandedId() === notification.id) {
      this.expandedId.set(null);
    } else {
      this.expandedId.set(notification.id);
      // Marquer comme lu si non lu
      if (!notification.read) {
        this.markAsRead(notification);
      }
    }
  }

  goToAction(notification: NotificationListItem, event: Event): void {
    event.stopPropagation();
    if (notification.action_url) {
      this.dialogRef.close(notification.action_url);
    }
  }

  isExpanded(id: number): boolean {
    return this.expandedId() === id;
  }

  markAsRead(notification: NotificationListItem, event?: Event): void {
    event?.stopPropagation();

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

  close(): void {
    this.dialogRef.close();
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
      month: 'short'
    });
  }
}
