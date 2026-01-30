import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { signal, WritableSignal } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';
import { of, throwError } from 'rxjs';

import { NotificationsDialogComponent } from './notifications-dialog.component';
import { NotificationService } from '../../../core/services/notification.service';
import { NotificationListItem } from '../../../core/models/notification.model';

describe('NotificationsDialogComponent', () => {
  let component: NotificationsDialogComponent;
  let fixture: ComponentFixture<NotificationsDialogComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<NotificationsDialogComponent>>;

  // Writable signals for mocking
  let unreadCountSignal: WritableSignal<number>;

  // Mock functions
  let getNotificationsMock: jest.Mock;
  let markAsReadMock: jest.Mock;
  let markAllAsReadMock: jest.Mock;

  const mockNotification: NotificationListItem = {
    id: 1,
    notification_type: 'info',
    title: 'Test Notification',
    message: 'This is a test notification message',
    priority: 'medium',
    read: false,
    created_at: new Date().toISOString()
  };

  const mockNotificationRead: NotificationListItem = {
    id: 2,
    notification_type: 'validation_approved',
    title: 'Validation Approved',
    message: 'Your request has been approved',
    priority: 'high',
    read: true,
    created_at: new Date().toISOString(),
    action_url: '/sites/123'
  };

  const mockPaginatedResponse = {
    count: 2,
    next: null,
    previous: null,
    results: [mockNotification, mockNotificationRead]
  };

  const setupTestBed = async () => {
    unreadCountSignal = signal(1);

    getNotificationsMock = jest.fn().mockReturnValue(of(mockPaginatedResponse));
    markAsReadMock = jest.fn().mockReturnValue(of({ status: 'ok', unread_count: 0 }));
    markAllAsReadMock = jest.fn().mockReturnValue(of({ status: 'ok', unread_count: 0, updated_count: 1 }));

    const notificationServiceMock = {
      unreadCount: unreadCountSignal.asReadonly(),
      getNotifications: getNotificationsMock,
      markAsRead: markAsReadMock,
      markAllAsRead: markAllAsReadMock
    };

    dialogRef = {
      close: jest.fn()
    } as any;

    await TestBed.configureTestingModule({
      imports: [
        NotificationsDialogComponent,
        NoopAnimationsModule
      ],
      providers: [
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(NotificationsDialogComponent);
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

    it('should load notifications on init', () => {
      fixture.detectChanges();

      expect(getNotificationsMock).toHaveBeenCalledWith(1);
      expect(component.notifications()).toHaveLength(2);
      expect(component.loading()).toBe(false);
    });

    it('should expose unreadCount from service', () => {
      fixture.detectChanges();
      expect(component.unreadCount()).toBe(1);
    });
  });

  // ==================== LOADING STATE ====================

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      // Before detectChanges, loading should be true
      expect(component.loading()).toBe(true);
    });

    it('should hide loading state after data loads', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));

    it('should hide loading state even on error', fakeAsync(() => {
      getNotificationsMock.mockReturnValue(throwError(() => new Error('Network error')));

      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
    }));
  });

  // ==================== EMPTY STATE ====================

  describe('Empty State', () => {
    it('should show empty state when no notifications', fakeAsync(() => {
      getNotificationsMock.mockReturnValue(of({
        count: 0,
        next: null,
        previous: null,
        results: []
      }));

      fixture.detectChanges();
      tick();

      expect(component.notifications()).toHaveLength(0);
    }));
  });

  // ==================== NOTIFICATIONS LIST ====================

  describe('Notifications List', () => {
    it('should display notifications from response', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.notifications()).toHaveLength(2);
      expect(component.notifications()[0].title).toBe('Test Notification');
      expect(component.notifications()[1].title).toBe('Validation Approved');
    }));

    it('should mark all as read automatically if unread notifications exist', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(markAllAsReadMock).toHaveBeenCalled();
    }));

    it('should not mark all as read if all notifications are already read', fakeAsync(() => {
      const allReadResponse = {
        count: 1,
        next: null,
        previous: null,
        results: [mockNotificationRead]
      };
      getNotificationsMock.mockReturnValue(of(allReadResponse));

      fixture.detectChanges();
      tick();

      expect(markAllAsReadMock).not.toHaveBeenCalled();
    }));
  });

  // ==================== EXPAND/COLLAPSE ====================

  describe('Expand/Collapse', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should not have any expanded notification initially', () => {
      expect(component.expandedId()).toBeNull();
    });

    it('should expand notification on click', () => {
      const mockEvent = { target: { closest: jest.fn().mockReturnValue(null) } } as any;

      component.onNotificationClick(mockNotification, mockEvent);

      expect(component.expandedId()).toBe(1);
      expect(component.isExpanded(1)).toBe(true);
    });

    it('should collapse notification when clicked again', () => {
      const mockEvent = { target: { closest: jest.fn().mockReturnValue(null) } } as any;

      // First click - expand
      component.onNotificationClick(mockNotification, mockEvent);
      expect(component.isExpanded(1)).toBe(true);

      // Second click - collapse
      component.onNotificationClick(mockNotification, mockEvent);
      expect(component.isExpanded(1)).toBe(false);
    });

    it('should not toggle expansion when clicking action button', () => {
      const mockEvent = {
        target: { closest: jest.fn().mockReturnValue(document.createElement('button')) }
      } as any;

      component.onNotificationClick(mockNotification, mockEvent);

      expect(component.expandedId()).toBeNull();
    });

    it('should mark notification as read when expanding unread notification', () => {
      const mockEvent = { target: { closest: jest.fn().mockReturnValue(null) } } as any;
      const unreadNotif = { ...mockNotification, read: false };

      component.onNotificationClick(unreadNotif, mockEvent);

      expect(markAsReadMock).toHaveBeenCalledWith(1);
    });

    it('should not mark as read when expanding already read notification', () => {
      const mockEvent = { target: { closest: jest.fn().mockReturnValue(null) } } as any;

      component.onNotificationClick(mockNotificationRead, mockEvent);

      // markAsRead should not be called for read notifications
      expect(markAsReadMock).not.toHaveBeenCalled();
    });
  });

  // ==================== MARK AS READ ====================

  describe('Mark As Read', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should mark single notification as read', fakeAsync(() => {
      component.markAsRead(mockNotification);
      tick();

      expect(markAsReadMock).toHaveBeenCalledWith(1);
    }));

    it('should stop event propagation when event provided', () => {
      const mockEvent = { stopPropagation: jest.fn() } as any;

      component.markAsRead(mockNotification, mockEvent);

      expect(mockEvent.stopPropagation).toHaveBeenCalled();
    });

    it('should update notification in list after marking as read', fakeAsync(() => {
      component.markAsRead(mockNotification);
      tick();

      const updatedNotification = component.notifications().find(n => n.id === 1);
      expect(updatedNotification?.read).toBe(true);
    }));
  });

  // ==================== MARK ALL AS READ ====================

  describe('Mark All As Read', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      markAllAsReadMock.mockClear();
    }));

    it('should call service to mark all as read', fakeAsync(() => {
      component.markAllAsRead();
      tick();

      expect(markAllAsReadMock).toHaveBeenCalled();
    }));

    it('should update all notifications in list', fakeAsync(() => {
      component.markAllAsRead();
      tick();

      const allRead = component.notifications().every(n => n.read);
      expect(allRead).toBe(true);
    }));
  });

  // ==================== PAGINATION ====================

  describe('Pagination', () => {
    it('should show load more button when hasMore is true', fakeAsync(() => {
      const responseWithMore = {
        ...mockPaginatedResponse,
        next: '/api/notifications/?page=2'
      };
      getNotificationsMock.mockReturnValue(of(responseWithMore));

      fixture.detectChanges();
      tick();

      expect(component.hasMore()).toBe(true);
    }));

    it('should not show load more button when hasMore is false', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.hasMore()).toBe(false);
    }));

    it('should load more notifications', fakeAsync(() => {
      // First load
      const responseWithMore = {
        ...mockPaginatedResponse,
        next: '/api/notifications/?page=2'
      };
      getNotificationsMock.mockReturnValue(of(responseWithMore));

      fixture.detectChanges();
      tick();

      // Setup for second page
      const moreNotifications: NotificationListItem = {
        id: 3,
        notification_type: 'info',
        title: 'Welcome',
        message: 'Welcome to the app',
        priority: 'low',
        read: true,
        created_at: new Date().toISOString()
      };
      const page2Response = {
        count: 3,
        next: null,
        previous: '/api/notifications/?page=1',
        results: [moreNotifications]
      };
      getNotificationsMock.mockReturnValue(of(page2Response));

      component.loadMore();
      tick();

      expect(getNotificationsMock).toHaveBeenCalledWith(2);
      expect(component.notifications()).toHaveLength(3);
      expect(component.hasMore()).toBe(false);
    }));

    it('should set loadingMore to false after load more completes', fakeAsync(() => {
      const responseWithMore = {
        ...mockPaginatedResponse,
        next: '/api/notifications/?page=2'
      };
      getNotificationsMock.mockReturnValue(of(responseWithMore));

      fixture.detectChanges();
      tick();

      expect(component.loadingMore()).toBe(false);

      // Start and complete load more
      getNotificationsMock.mockReturnValue(of(mockPaginatedResponse));
      component.loadMore();
      tick();

      // After loading completes
      expect(component.loadingMore()).toBe(false);
    }));
  });

  // ==================== NAVIGATION ====================

  describe('Navigation', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should close dialog with action URL when goToAction is called', () => {
      const mockEvent = { stopPropagation: jest.fn() } as any;

      component.goToAction(mockNotificationRead, mockEvent);

      expect(mockEvent.stopPropagation).toHaveBeenCalled();
      expect(dialogRef.close).toHaveBeenCalledWith('/sites/123');
    });

    it('should not close with URL when notification has no action_url', () => {
      const mockEvent = { stopPropagation: jest.fn() } as any;

      component.goToAction(mockNotification, mockEvent);

      expect(dialogRef.close).not.toHaveBeenCalled();
    });

    it('should close dialog when close is called', () => {
      component.close();

      expect(dialogRef.close).toHaveBeenCalledWith();
    });
  });

  // ==================== NOTIFICATION ICONS ====================

  describe('Notification Icons', () => {
    it('should return correct icon for welcome type', () => {
      expect(component.getNotificationIcon('welcome')).toBe('fi-rr-hand-wave');
    });

    it('should return correct icon for validation_request type', () => {
      expect(component.getNotificationIcon('validation_request')).toBe('fi-rr-check-circle');
    });

    it('should return correct icon for validation_approved type', () => {
      expect(component.getNotificationIcon('validation_approved')).toBe('fi-rr-check');
    });

    it('should return correct icon for validation_rejected type', () => {
      expect(component.getNotificationIcon('validation_rejected')).toBe('fi-rr-cross');
    });

    it('should return correct icon for user_associated_site type', () => {
      expect(component.getNotificationIcon('user_associated_site')).toBe('fi-rr-marker');
    });

    it('should return correct icon for user_associated_plan type', () => {
      expect(component.getNotificationIcon('user_associated_plan')).toBe('fi-rr-document');
    });

    it('should return correct icon for user_removed_site type', () => {
      expect(component.getNotificationIcon('user_removed_site')).toBe('fi-rr-marker');
    });

    it('should return correct icon for user_removed_plan type', () => {
      expect(component.getNotificationIcon('user_removed_plan')).toBe('fi-rr-document');
    });

    it('should return correct icon for account_deactivated type', () => {
      expect(component.getNotificationIcon('account_deactivated')).toBe('fi-rr-user-slash');
    });

    it('should return correct icon for account_activated type', () => {
      expect(component.getNotificationIcon('account_activated')).toBe('fi-rr-user-check');
    });

    it('should return correct icon for site_orphaned type', () => {
      expect(component.getNotificationIcon('site_orphaned')).toBe('fi-rr-exclamation');
    });

    it('should return correct icon for organisme_no_admin type', () => {
      expect(component.getNotificationIcon('organisme_no_admin')).toBe('fi-rr-exclamation');
    });

    it('should return correct icon for system_alert type', () => {
      expect(component.getNotificationIcon('system_alert')).toBe('fi-rr-bell');
    });

    it('should return correct icon for info type', () => {
      expect(component.getNotificationIcon('info')).toBe('fi-rr-info');
    });

    it('should return default icon for unknown type', () => {
      expect(component.getNotificationIcon('unknown_type')).toBe('fi-rr-bell');
    });
  });

  // ==================== DATE FORMATTING ====================

  describe('Date Formatting', () => {
    beforeEach(() => {
      jest.useFakeTimers();
      jest.setSystemTime(new Date('2024-01-15T12:00:00Z'));
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should return "A l\'instant" for times less than a minute ago', () => {
      const now = new Date().toISOString();
      expect(component.formatDate(now)).toBe('A l\'instant');
    });

    it('should return minutes ago for times less than an hour', () => {
      const tenMinsAgo = new Date('2024-01-15T11:50:00Z').toISOString();
      expect(component.formatDate(tenMinsAgo)).toBe('Il y a 10 min');
    });

    it('should return hours ago for times less than 24 hours', () => {
      const threeHoursAgo = new Date('2024-01-15T09:00:00Z').toISOString();
      expect(component.formatDate(threeHoursAgo)).toBe('Il y a 3h');
    });

    it('should return days ago for times less than a week', () => {
      const twoDaysAgo = new Date('2024-01-13T12:00:00Z').toISOString();
      expect(component.formatDate(twoDaysAgo)).toBe('Il y a 2j');
    });

    it('should return formatted date for times more than a week', () => {
      const twoWeeksAgo = new Date('2024-01-01T12:00:00Z').toISOString();
      const result = component.formatDate(twoWeeksAgo);
      // Should contain day and month
      expect(result).toContain('1');
      expect(result).toContain('janv');
    });
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    it('should handle error on initial load', fakeAsync(() => {
      getNotificationsMock.mockReturnValue(throwError(() => new Error('Network error')));

      fixture.detectChanges();
      tick();

      expect(component.loading()).toBe(false);
      expect(component.notifications()).toHaveLength(0);
    }));

    it('should handle error on load more', fakeAsync(() => {
      // First load successful
      const responseWithMore = {
        ...mockPaginatedResponse,
        next: '/api/notifications/?page=2'
      };
      getNotificationsMock.mockReturnValue(of(responseWithMore));

      fixture.detectChanges();
      tick();

      // Load more fails
      getNotificationsMock.mockReturnValue(throwError(() => new Error('Network error')));

      component.loadMore();
      tick();

      expect(component.loadingMore()).toBe(false);
      // Original notifications should still be there
      expect(component.notifications()).toHaveLength(2);
    }));
  });
});
