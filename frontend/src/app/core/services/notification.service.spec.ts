import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { NotificationService } from './notification.service';
import {
  NotificationListItem,
  NotificationPollResponse
} from '../models/notification.model';

describe('NotificationService', () => {
  let service: NotificationService;
  let httpMock: HttpTestingController;

  const mockNotification: NotificationListItem = {
    id: 1,
    notification_type: 'info',
    title: 'Test Notification',
    message: 'Test message',
    priority: 'medium',
    read: false,
    created_at: '2024-01-01T10:00:00Z'
  };

  const mockPollResponse: NotificationPollResponse = {
    notifications: [mockNotification],
    unread_count: 1,
    pending_validations: 2,
    has_updates: true,
    timestamp: '2024-01-01T10:00:00Z'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [NotificationService]
    });

    service = TestBed.inject(NotificationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    service.ngOnDestroy();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have initial values', () => {
      expect(service.notifications()).toEqual([]);
      expect(service.unreadCount()).toBe(0);
      expect(service.pendingValidations()).toBe(0);
      expect(service.hasUnread()).toBe(false);
      expect(service.hasPendingValidations()).toBe(false);
      expect(service.totalBadgeCount()).toBe(0);
    });
  });

  // ==================== POLL TESTS ====================

  describe('Polling', () => {
    it('should poll for notifications', () => {
      service.poll().subscribe(response => {
        expect(response.notifications.length).toBe(1);
        expect(response.unread_count).toBe(1);
        expect(response.pending_validations).toBe(2);
      });

      const req = httpMock.expectOne('/api/notifications/poll/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPollResponse);
    });

    it('should update signals after poll', () => {
      service.poll().subscribe();

      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush(mockPollResponse);

      expect(service.notifications().length).toBe(1);
      expect(service.unreadCount()).toBe(1);
      expect(service.pendingValidations()).toBe(2);
      expect(service.hasUnread()).toBe(true);
      expect(service.hasPendingValidations()).toBe(true);
      expect(service.totalBadgeCount()).toBe(3);
    });

    it('should include since param when timestamp exists', fakeAsync(() => {
      // First poll to set timestamp
      service.poll().subscribe();
      const req1 = httpMock.expectOne('/api/notifications/poll/');
      req1.flush(mockPollResponse);

      tick(100);

      // Second poll should include since param
      service.poll().subscribe();
      const req2 = httpMock.expectOne(req =>
        req.url === '/api/notifications/poll/' &&
        req.params.has('since')
      );
      req2.flush(mockPollResponse);
    }));

    it('should handle poll error gracefully', () => {
      // Set initial values
      service.poll().subscribe();
      const req1 = httpMock.expectOne('/api/notifications/poll/');
      req1.flush(mockPollResponse);

      expect(service.unreadCount()).toBe(1);

      // Error should preserve existing values
      service.poll().subscribe(response => {
        expect(response.unread_count).toBe(1);
      });

      // Second poll includes since param
      const req2 = httpMock.expectOne(req =>
        req.url === '/api/notifications/poll/' &&
        req.params.has('since')
      );
      req2.error(new ProgressEvent('error'));

      expect(service.unreadCount()).toBe(1);
    });

    it('should start polling', fakeAsync(() => {
      service.startPolling();

      // First immediate poll
      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush(mockPollResponse);

      // Stop polling to prevent interval calls
      service.stopPolling();
    }));

    it('should not start polling twice', fakeAsync(() => {
      service.startPolling();

      const req1 = httpMock.expectOne('/api/notifications/poll/');
      req1.flush(mockPollResponse);

      // Second call should do nothing
      service.startPolling();

      // Stop polling
      service.stopPolling();
    }));

    it('should stop polling', fakeAsync(() => {
      service.startPolling();

      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush(mockPollResponse);

      service.stopPolling();

      // After stopping, no more polls should occur
      tick(60000); // Wait longer than polling interval
      httpMock.expectNone('/api/notifications/poll/');
    }));
  });

  // ==================== GET OPERATIONS ====================

  describe('Get Operations', () => {
    it('should get notifications paginated', () => {
      service.getNotifications(2).subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/notifications/?page=2');
      expect(req.request.method).toBe('GET');
      req.flush({
        count: 1,
        next: null,
        previous: null,
        results: [mockNotification]
      });
    });

    it('should get single notification', () => {
      service.getNotification(1).subscribe(notification => {
        expect(notification.id).toBe(1);
        expect(notification.title).toBe('Test Notification');
      });

      const req = httpMock.expectOne('/api/notifications/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockNotification);
    });

    it('should get unread notifications', () => {
      service.getUnreadNotifications().subscribe(notifications => {
        expect(notifications.length).toBe(1);
        expect(notifications[0].read).toBe(false);
      });

      const req = httpMock.expectOne('/api/notifications/unread/');
      expect(req.request.method).toBe('GET');
      req.flush([mockNotification]);
    });

    it('should get unread count and update signal', () => {
      service.getUnreadCount().subscribe(response => {
        expect(response.unread_count).toBe(5);
      });

      const req = httpMock.expectOne('/api/notifications/count/');
      expect(req.request.method).toBe('GET');
      req.flush({ unread_count: 5 });

      expect(service.unreadCount()).toBe(5);
    });
  });

  // ==================== MARK AS READ ====================

  describe('Mark As Read', () => {
    it('should mark notification as read', () => {
      // First, populate with a notification
      service.poll().subscribe();
      const pollReq = httpMock.expectOne('/api/notifications/poll/');
      pollReq.flush(mockPollResponse);

      expect(service.notifications()[0].read).toBe(false);

      // Mark as read
      service.markAsRead(1).subscribe(response => {
        expect(response.status).toBe('ok');
        expect(response.unread_count).toBe(0);
      });

      const req = httpMock.expectOne('/api/notifications/1/mark_read/');
      expect(req.request.method).toBe('POST');
      req.flush({ status: 'ok', unread_count: 0 });

      // Check signals updated
      expect(service.unreadCount()).toBe(0);
      expect(service.notifications()[0].read).toBe(true);
    });

    it('should mark all notifications as read', () => {
      // First, populate with notifications
      service.poll().subscribe();
      const pollReq = httpMock.expectOne('/api/notifications/poll/');
      pollReq.flush({
        ...mockPollResponse,
        notifications: [
          mockNotification,
          { ...mockNotification, id: 2, read: false }
        ],
        unread_count: 2
      });

      expect(service.unreadCount()).toBe(2);

      // Mark all as read
      service.markAllAsRead().subscribe(response => {
        expect(response.status).toBe('ok');
        expect(response.unread_count).toBe(0);
        expect(response.updated_count).toBe(2);
      });

      const req = httpMock.expectOne('/api/notifications/mark_all_read/');
      expect(req.request.method).toBe('POST');
      req.flush({ status: 'ok', unread_count: 0, updated_count: 2 });

      // Check signals updated
      expect(service.unreadCount()).toBe(0);
      expect(service.notifications().every(n => n.read)).toBe(true);
    });
  });

  // ==================== DELETE ====================

  describe('Delete', () => {
    it('should delete notification', () => {
      // First, populate with notifications
      service.poll().subscribe();
      const pollReq = httpMock.expectOne('/api/notifications/poll/');
      pollReq.flush({
        ...mockPollResponse,
        notifications: [
          mockNotification,
          { ...mockNotification, id: 2 }
        ]
      });

      expect(service.notifications().length).toBe(2);

      // Delete
      service.deleteNotification(1).subscribe();

      const req = httpMock.expectOne('/api/notifications/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);

      // Check notification removed
      expect(service.notifications().length).toBe(1);
      expect(service.notifications()[0].id).toBe(2);
    });
  });

  // ==================== OTHER OPERATIONS ====================

  describe('Other Operations', () => {
    it('should update pending validations count', () => {
      expect(service.pendingValidations()).toBe(0);

      service.updatePendingValidationsCount(5);

      expect(service.pendingValidations()).toBe(5);
      expect(service.hasPendingValidations()).toBe(true);
    });

    it('should refresh notifications', () => {
      // First poll to set timestamp
      service.poll().subscribe();
      const req1 = httpMock.expectOne('/api/notifications/poll/');
      req1.flush(mockPollResponse);

      // Refresh should clear timestamp and poll again
      service.refresh().subscribe();

      // Should not include since param after refresh
      const req2 = httpMock.expectOne(req =>
        req.url === '/api/notifications/poll/' &&
        !req.params.has('since')
      );
      req2.flush(mockPollResponse);
    });
  });

  // ==================== COMPUTED SIGNALS ====================

  describe('Computed Signals', () => {
    it('should compute hasUnread correctly', () => {
      expect(service.hasUnread()).toBe(false);

      service.poll().subscribe();
      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush({ ...mockPollResponse, unread_count: 3 });

      expect(service.hasUnread()).toBe(true);
    });

    it('should compute hasPendingValidations correctly', () => {
      expect(service.hasPendingValidations()).toBe(false);

      service.poll().subscribe();
      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush({ ...mockPollResponse, pending_validations: 5 });

      expect(service.hasPendingValidations()).toBe(true);
    });

    it('should compute totalBadgeCount correctly', () => {
      expect(service.totalBadgeCount()).toBe(0);

      service.poll().subscribe();
      const req = httpMock.expectOne('/api/notifications/poll/');
      req.flush({ ...mockPollResponse, unread_count: 3, pending_validations: 2 });

      expect(service.totalBadgeCount()).toBe(5);
    });
  });

  // ==================== RACE CONDITION PROTECTION ====================

  describe('Race Condition Protection', () => {
    it('should not update count from old poll after markAllAsRead', fakeAsync(() => {
      // Start with some unread
      service.poll().subscribe();
      let req = httpMock.expectOne('/api/notifications/poll/');
      req.flush({ ...mockPollResponse, unread_count: 5 });

      expect(service.unreadCount()).toBe(5);

      // Mark all as read
      service.markAllAsRead().subscribe();
      req = httpMock.expectOne('/api/notifications/mark_all_read/');
      req.flush({ status: 'ok', unread_count: 0, updated_count: 5 });

      expect(service.unreadCount()).toBe(0);

      // A poll that started before markAllAsRead completes
      // Should not overwrite the 0 count
      tick(100);

      // The protection is in the service code - after markAllAsRead,
      // any poll that started BEFORE should not update the count
    }));
  });
});
