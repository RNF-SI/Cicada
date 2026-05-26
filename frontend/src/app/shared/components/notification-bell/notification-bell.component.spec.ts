import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Component, signal, WritableSignal } from '@angular/core';
import { of } from 'rxjs';
import { NotificationBellComponent } from './notification-bell.component';
import { NotificationService } from '../../../core/services/notification.service';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationListItem } from '../../../core/models/notification.model';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

describe('NotificationBellComponent', () => {
  let component: NotificationBellComponent;
  let fixture: ComponentFixture<NotificationBellComponent>;
  let router: Router;

  // Writable signals for mocking
  let notificationsSignal: WritableSignal<NotificationListItem[]>;
  let unreadCountSignal: WritableSignal<number>;
  let pendingValidationsSignal: WritableSignal<number>;
  let totalBadgeCountSignal: WritableSignal<number>;
  let hasUnreadSignal: WritableSignal<boolean>;
  let isAuthenticatedSignal: WritableSignal<boolean>;
  let canAccessAdminSignal: WritableSignal<boolean>;

  // Mock functions
  let startPollingMock: jest.Mock;
  let stopPollingMock: jest.Mock;
  let markAsReadMock: jest.Mock;
  let markAllAsReadMock: jest.Mock;

  const mockNotification: NotificationListItem = {
    id: 1,
    notification_type: 'info',
    title: 'Test Notification',
    message: 'Test message',
    priority: 'medium',
    read: false,
    created_at: new Date().toISOString()
  };

  const setupTestBed = async () => {
    // Create writable signals
    notificationsSignal = signal<NotificationListItem[]>([mockNotification]);
    unreadCountSignal = signal(1);
    pendingValidationsSignal = signal(2);
    totalBadgeCountSignal = signal(3);
    hasUnreadSignal = signal(true);
    isAuthenticatedSignal = signal(true);
    canAccessAdminSignal = signal(true);

    // Create mock functions
    startPollingMock = jest.fn();
    stopPollingMock = jest.fn();
    markAsReadMock = jest.fn().mockReturnValue(of({ status: 'ok' }));
    markAllAsReadMock = jest.fn().mockReturnValue(of({ status: 'ok', unread_count: 0, updated_count: 1 }));

    const notificationServiceMock = {
      notifications: notificationsSignal.asReadonly(),
      unreadCount: unreadCountSignal.asReadonly(),
      pendingValidations: pendingValidationsSignal.asReadonly(),
      totalBadgeCount: totalBadgeCountSignal.asReadonly(),
      hasUnread: hasUnreadSignal.asReadonly(),
      startPolling: startPollingMock,
      stopPolling: stopPollingMock,
      markAsRead: markAsReadMock,
      markAllAsRead: markAllAsReadMock
    };

    const authServiceMock = {
      isAuthenticated: isAuthenticatedSignal.asReadonly(),
      canAccessAdmin: canAccessAdminSignal.asReadonly()
    };

    await TestBed.configureTestingModule({
      imports: [
        NotificationBellComponent,
        NoopAnimationsModule
      ],
      providers: [
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'activite', component: DummyComponent },
          { path: 'administration/validations', component: DummyComponent }
        ]),
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(NotificationBellComponent);
    component = fixture.componentInstance;
  };

  beforeEach(async () => {
    await setupTestBed();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should expose notification signals from service', () => {
      fixture.detectChanges();
      expect(component.notifications()).toEqual([mockNotification]);
      expect(component.unreadCount()).toBe(1);
      expect(component.pendingValidations()).toBe(2);
      expect(component.totalBadgeCount()).toBe(3);
      expect(component.hasUnread()).toBe(true);
    });
  });

  // ==================== BADGE DISPLAY ====================

  describe('Badge Display', () => {
    it('should display badge count normally', () => {
      totalBadgeCountSignal.set(5);
      fixture.detectChanges();

      expect(component.badgeDisplay()).toBe('5');
    });

    it('should display 99+ when count exceeds 99', () => {
      totalBadgeCountSignal.set(100);
      fixture.detectChanges();

      expect(component.badgeDisplay()).toBe('99+');
    });

    it('should display 99+ when count is 150', () => {
      totalBadgeCountSignal.set(150);
      fixture.detectChanges();

      expect(component.badgeDisplay()).toBe('99+');
    });

    it('should display 0 when no notifications', () => {
      totalBadgeCountSignal.set(0);
      fixture.detectChanges();

      expect(component.badgeDisplay()).toBe('0');
    });
  });

  // ==================== ADMIN ACCESS ====================

  describe('Admin Access', () => {
    it('should allow validations access when admin', () => {
      canAccessAdminSignal.set(true);
      fixture.detectChanges();

      expect(component.canAccessValidations()).toBe(true);
    });

    it('should not allow validations access when not admin', () => {
      canAccessAdminSignal.set(false);
      fixture.detectChanges();

      expect(component.canAccessValidations()).toBe(false);
    });
  });

  // ==================== LIFECYCLE ====================

  describe('Lifecycle', () => {
    it('should start polling on init when authenticated', () => {
      isAuthenticatedSignal.set(true);
      fixture.detectChanges();
      component.ngOnInit();

      expect(startPollingMock).toHaveBeenCalled();
    });

    it('should not start polling on init when not authenticated', () => {
      isAuthenticatedSignal.set(false);
      fixture.detectChanges();
      component.ngOnInit();

      // Called once during setupTestBed, should not be called again
      expect(startPollingMock).not.toHaveBeenCalled();
    });

    it('should stop polling on destroy', () => {
      fixture.detectChanges();
      component.ngOnDestroy();

      expect(stopPollingMock).toHaveBeenCalled();
    });
  });

  // ==================== NOTIFICATION CLICK ====================

  describe('Notification Click', () => {
    it('should mark notification as read when clicking unread notification', () => {
      fixture.detectChanges();
      const unreadNotification: NotificationListItem = {
        ...mockNotification,
        read: false
      };

      component.onNotificationClick(unreadNotification);

      expect(markAsReadMock).toHaveBeenCalledWith(1);
    });

    it('should not mark notification as read when already read', () => {
      fixture.detectChanges();
      const readNotification: NotificationListItem = {
        ...mockNotification,
        read: true
      };

      component.onNotificationClick(readNotification);

      expect(markAsReadMock).not.toHaveBeenCalled();
    });

    it('should navigate to action URL when provided', fakeAsync(() => {
      fixture.detectChanges();
      const navigateSpy = jest.spyOn(router, 'navigateByUrl');
      const notificationWithUrl: NotificationListItem = {
        ...mockNotification,
        read: true,
        action_url: '/activite'
      };

      component.onNotificationClick(notificationWithUrl);
      tick();

      expect(navigateSpy).toHaveBeenCalledWith('/activite');
    }));

    it('should not navigate when no action URL', () => {
      fixture.detectChanges();
      const navigateSpy = jest.spyOn(router, 'navigateByUrl');
      const notificationWithoutUrl: NotificationListItem = {
        ...mockNotification,
        read: true
        // No action_url
      };

      component.onNotificationClick(notificationWithoutUrl);

      expect(navigateSpy).not.toHaveBeenCalled();
    });
  });

  // ==================== MARK ALL AS READ ====================

  describe('Mark All As Read', () => {
    it('should call service to mark all as read', () => {
      fixture.detectChanges();

      component.markAllAsRead();

      expect(markAllAsReadMock).toHaveBeenCalled();
    });
  });

  // ==================== MENU OPENED ====================

  describe('Menu Opened', () => {
    it('should mark all as read when menu opens with unread notifications', () => {
      unreadCountSignal.set(5);
      fixture.detectChanges();

      component.onMenuOpened();

      expect(markAllAsReadMock).toHaveBeenCalled();
    });

    it('should not mark all as read when menu opens with no unread', () => {
      unreadCountSignal.set(0);
      fixture.detectChanges();

      component.onMenuOpened();

      expect(markAllAsReadMock).not.toHaveBeenCalled();
    });
  });

  // ==================== NAVIGATION ====================

  describe('Navigation', () => {
    it('should navigate to validations page', fakeAsync(() => {
      fixture.detectChanges();
      const navigateSpy = jest.spyOn(router, 'navigate');

      component.goToValidations();
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/administration/validations']);
    }));

    it('should navigate to activity page', fakeAsync(() => {
      fixture.detectChanges();
      const navigateSpy = jest.spyOn(router, 'navigate');

      component.goToActivity();
      tick();

      expect(navigateSpy).toHaveBeenCalledWith(['/activite']);
    }));
  });

  // ==================== NOTIFICATION ICONS ====================

  describe('Notification Icons', () => {
    // Revue design Amandine — icône unique générique partout (harmonisation panel/page)
    it('should return fi-rr-bell for any type', () => {
      expect(component.getNotificationIcon('welcome')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('validation_request')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('validation_approved')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('validation_rejected')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('user_associated_site')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('user_associated_plan')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('account_deactivated')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('account_activated')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('system_alert')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('info')).toBe('fi-rr-bell');
      expect(component.getNotificationIcon('unknown_type')).toBe('fi-rr-bell');
    });
  });

  // ==================== PRIORITY CLASSES ====================

  describe('Priority Classes', () => {
    it('should return correct class for low priority', () => {
      expect(component.getPriorityClass('low')).toBe('priority-low');
    });

    it('should return correct class for medium priority', () => {
      expect(component.getPriorityClass('medium')).toBe('priority-medium');
    });

    it('should return correct class for high priority', () => {
      expect(component.getPriorityClass('high')).toBe('priority-high');
    });

    it('should return correct class for critical priority', () => {
      expect(component.getPriorityClass('critical')).toBe('priority-critical');
    });

    it('should return default class for unknown priority', () => {
      expect(component.getPriorityClass('unknown')).toBe('priority-medium');
    });
  });

  // ==================== RELATIVE TIME ====================

  describe('Relative Time', () => {
    beforeEach(() => {
      jest.useFakeTimers();
      jest.setSystemTime(new Date('2024-01-15T12:00:00Z'));
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should return "A l\'instant" for recent times', () => {
      const now = new Date();
      expect(component.getRelativeTime(now.toISOString())).toBe('A l\'instant');
    });

    it('should return minutes ago for times less than an hour', () => {
      const tenMinsAgo = new Date('2024-01-15T11:50:00Z');
      expect(component.getRelativeTime(tenMinsAgo.toISOString())).toBe('Il y a 10 min');
    });

    it('should return hours ago for times less than a day', () => {
      const threeHoursAgo = new Date('2024-01-15T09:00:00Z');
      expect(component.getRelativeTime(threeHoursAgo.toISOString())).toBe('Il y a 3h');
    });

    it('should return days ago for times less than a week', () => {
      const twoDaysAgo = new Date('2024-01-13T12:00:00Z');
      expect(component.getRelativeTime(twoDaysAgo.toISOString())).toBe('Il y a 2j');
    });

    it('should return formatted date for times more than a week', () => {
      const twoWeeksAgo = new Date('2024-01-01T12:00:00Z');
      const result = component.getRelativeTime(twoWeeksAgo.toISOString());
      // Should contain day and month
      expect(result).toContain('1');
      expect(result).toContain('janv');
    });
  });
});
