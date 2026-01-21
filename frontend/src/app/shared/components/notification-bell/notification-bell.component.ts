/**
 * Composant cloche de notifications pour le header.
 * Affiche un badge avec le nombre de notifications non lues.
 */
import { Component, inject, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';

import { NotificationService } from '../../../core/services/notification.service';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationListItem } from '../../../core/models/notification.model';

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatMenuModule,
    MatButtonModule,
    MatBadgeModule,
    MatDividerModule
  ],
  templateUrl: './notification-bell.component.html',
  styleUrl: './notification-bell.component.scss'
})
export class NotificationBellComponent implements OnInit, OnDestroy {
  private readonly notificationService = inject(NotificationService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  // Signals depuis le service
  readonly notifications = this.notificationService.notifications;
  readonly unreadCount = this.notificationService.unreadCount;
  readonly pendingValidations = this.notificationService.pendingValidations;
  readonly totalBadgeCount = this.notificationService.totalBadgeCount;
  readonly hasUnread = this.notificationService.hasUnread;

  // Computed: peut acceder aux validations
  readonly canAccessValidations = computed(() => {
    return this.authService.canAccessAdmin();
  });

  // Badge display (max 99+)
  readonly badgeDisplay = computed(() => {
    const count = this.totalBadgeCount();
    if (count > 99) return '99+';
    return count.toString();
  });

  ngOnInit(): void {
    // Demarrer le polling si authentifie
    if (this.authService.isAuthenticated()) {
      this.notificationService.startPolling();
    }
  }

  ngOnDestroy(): void {
    this.notificationService.stopPolling();
  }

  /**
   * Navigue vers une notification.
   */
  onNotificationClick(notification: NotificationListItem): void {
    // Marquer comme lue
    if (!notification.read) {
      this.notificationService.markAsRead(notification.id).subscribe();
    }

    // Naviguer si URL d'action
    if (notification.action_url) {
      this.router.navigateByUrl(notification.action_url);
    }
  }

  /**
   * Marque toutes les notifications comme lues.
   */
  markAllAsRead(): void {
    this.notificationService.markAllAsRead().subscribe();
  }

  /**
   * Appele quand le menu des notifications s'ouvre.
   * Marque automatiquement toutes les notifications comme lues.
   */
  onMenuOpened(): void {
    if (this.notificationService.unreadCount() > 0) {
      this.notificationService.markAllAsRead().subscribe();
    }
  }

  /**
   * Navigue vers la page des validations.
   */
  goToValidations(): void {
    this.router.navigate(['/administration/validations']);
  }

  /**
   * Navigue vers la page d'activite unifiee.
   */
  goToActivity(): void {
    this.router.navigate(['/activite']);
  }

  /**
   * Obtient l'icone selon le type de notification.
   */
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

  /**
   * Obtient la classe CSS selon la priorite.
   */
  getPriorityClass(priority: string): string {
    const classes: Record<string, string> = {
      'low': 'priority-low',
      'medium': 'priority-medium',
      'high': 'priority-high',
      'critical': 'priority-critical',
    };
    return classes[priority] || 'priority-medium';
  }

  /**
   * Formate la date relative.
   */
  getRelativeTime(dateString: string): string {
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

    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
  }
}
