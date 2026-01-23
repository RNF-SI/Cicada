import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ActivityService } from './activity.service';
import {
  ActivityLogListItem,
  ActivityLogDetail,
  ActivityStats,
  ActivityTabsCounts,
  PaginatedActivityResponse,
  ActivityTab
} from '../models/activity.model';

describe('ActivityService', () => {
  let service: ActivityService;
  let httpMock: HttpTestingController;

  const mockActivityItem: ActivityLogListItem = {
    id: 1,
    entity_type: 'site',
    entity_type_display: 'Site',
    entity_id: 1,
    entity_name: 'Reserve de Camargue',
    actor_name: 'Jean Dupont',
    action: 'create',
    action_display: 'Creation',
    description: 'Creation du site Reserve de Camargue',
    visibility: 'public',
    created_at: '2024-01-15T10:00:00Z'
  };

  const mockActivityDetail: ActivityLogDetail = {
    ...mockActivityItem,
    actor: 1,
    actor_email: 'jean.dupont@test.fr',
    changes: {
      nom_site: { old: null, new: 'Reserve de Camargue' }
    },
    metadata: {},
    visibility_display: 'Public'
  };

  const mockPaginatedResponse: PaginatedActivityResponse = {
    count: 1,
    next: null,
    previous: null,
    results: [mockActivityItem]
  };

  const mockStats: ActivityStats = {
    total: 100,
    by_type: { site: 50, plan: 30, user: 10, organisme: 5, validation: 5 },
    by_action: {
      create: 40,
      update: 30,
      delete: 10,
      add_member: 5,
      remove_member: 5,
      add_referent: 3,
      remove_referent: 2,
      status_change: 2,
      activate: 1,
      deactivate: 1,
      rgpd_request: 0,
      rgpd_cancelled: 0,
      rgpd_anonymized: 0,
      access_granted: 1,
      access_revoked: 0,
      validation_approved: 0,
      validation_rejected: 0,
      file_upload: 0,
      file_delete: 0
    },
    by_day: [
      { date: '2024-01-15', count: 10 },
      { date: '2024-01-14', count: 8 }
    ]
  };

  const mockTabsCounts: ActivityTabsCounts = {
    all: 100,
    my_sites: 25,
    my_plans: 15,
    my_rights: 10,
    validations: 5,
    system: 3,
    rgpd: 2
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ActivityService]
    });

    service = TestBed.inject(ActivityService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have initial values', () => {
      expect(service.tabsCounts()).toBeNull();
      expect(service.currentTab()).toBe('all');
      expect(service.loading()).toBe(false);
      expect(service.totalCount()).toBe(0);
    });

    it('should set current tab', () => {
      service.setCurrentTab('my_sites');
      expect(service.currentTab()).toBe('my_sites');
    });
  });

  // ==================== GET ACTIVITIES ====================

  describe('Get Activities', () => {
    it('should get activities without filters', () => {
      service.getActivities().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results.length).toBe(1);
        expect(response.results[0].entity_name).toBe('Reserve de Camargue');
      });

      const req = httpMock.expectOne('/api/activity/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with entity_type filter', () => {
      service.getActivities({ entity_type: 'site' }).subscribe();

      const req = httpMock.expectOne('/api/activity/?entity_type=site');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with action filter', () => {
      service.getActivities({ action: 'create' }).subscribe();

      const req = httpMock.expectOne('/api/activity/?action=create');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with visibility filter', () => {
      service.getActivities({ visibility: 'admin' }).subscribe();

      const req = httpMock.expectOne('/api/activity/?visibility=admin');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with site_id filter', () => {
      service.getActivities({ site_id: 1 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?site_id=1');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with date filters', () => {
      service.getActivities({
        date_from: '2024-01-01',
        date_to: '2024-01-31'
      }).subscribe();

      const req = httpMock.expectOne(r =>
        r.url === '/api/activity/' &&
        r.params.get('date_from') === '2024-01-01' &&
        r.params.get('date_to') === '2024-01-31'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with search filter', () => {
      service.getActivities({ search: 'Camargue' }).subscribe();

      const req = httpMock.expectOne('/api/activity/?search=Camargue');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with page filter', () => {
      service.getActivities({ page: 2 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?page=2');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities with multiple filters', () => {
      service.getActivities({
        entity_type: 'site',
        action: 'create',
        page: 1
      }).subscribe();

      const req = httpMock.expectOne(r =>
        r.url === '/api/activity/' &&
        r.params.get('entity_type') === 'site' &&
        r.params.get('action') === 'create' &&
        r.params.get('page') === '1'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should set loading state during request', fakeAsync(() => {
      expect(service.loading()).toBe(false);

      service.getActivities().subscribe();

      expect(service.loading()).toBe(true);

      const req = httpMock.expectOne('/api/activity/');
      req.flush(mockPaginatedResponse);

      tick();
      expect(service.loading()).toBe(false);
    }));
  });

  // ==================== GET SINGLE ACTIVITY ====================

  describe('Get Activity Detail', () => {
    it('should get activity detail by id', () => {
      service.getActivity(1).subscribe(activity => {
        expect(activity.id).toBe(1);
        expect(activity.entity_name).toBe('Reserve de Camargue');
        expect(activity.changes).toBeDefined();
      });

      const req = httpMock.expectOne('/api/activity/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockActivityDetail);
    });
  });

  // ==================== SPECIALIZED ENDPOINTS ====================

  describe('Specialized Endpoints', () => {
    it('should get my sites activities', () => {
      service.getMySitesActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/my_sites/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get my sites activities with filters', () => {
      service.getMySitesActivities({ action: 'create' }).subscribe();

      const req = httpMock.expectOne('/api/activity/my_sites/?action=create');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get my plans activities', () => {
      service.getMyPlansActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/my_plans/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get my rights activities', () => {
      service.getMyRightsActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/my_rights/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get validations activities', () => {
      service.getValidationsActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/validations/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get system activities', () => {
      service.getSystemActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/system/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get rgpd activities', () => {
      service.getRgpdActivities().subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/activity/rgpd/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });
  });

  // ==================== STATS AND COUNTS ====================

  describe('Stats and Counts', () => {
    it('should get activity stats', () => {
      service.getStats().subscribe(stats => {
        expect(stats.total).toBe(100);
        expect(stats.by_type.site).toBe(50);
        expect(stats.by_day.length).toBe(2);
      });

      const req = httpMock.expectOne('/api/activity/stats/');
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });

    it('should get tabs counts and update signal', () => {
      service.getTabsCounts().subscribe(counts => {
        expect(counts.all).toBe(100);
        expect(counts.my_sites).toBe(25);
      });

      const req = httpMock.expectOne('/api/activity/tabs_counts/');
      expect(req.request.method).toBe('GET');
      req.flush(mockTabsCounts);

      expect(service.tabsCounts()).toEqual(mockTabsCounts);
      expect(service.totalCount()).toBe(100);
    });

    it('should refresh tabs counts', fakeAsync(() => {
      service.refreshTabsCounts();

      const req = httpMock.expectOne('/api/activity/tabs_counts/');
      req.flush(mockTabsCounts);

      tick();

      expect(service.tabsCounts()).toEqual(mockTabsCounts);
    }));
  });

  // ==================== GET ACTIVITIES BY TAB ====================

  describe('Get Activities By Tab', () => {
    it('should get activities for "all" tab', () => {
      service.getActivitiesByTab('all').subscribe();

      const req = httpMock.expectOne('/api/activity/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "my_sites" tab', () => {
      service.getActivitiesByTab('my_sites').subscribe();

      const req = httpMock.expectOne('/api/activity/my_sites/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "my_plans" tab', () => {
      service.getActivitiesByTab('my_plans').subscribe();

      const req = httpMock.expectOne('/api/activity/my_plans/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "my_rights" tab', () => {
      service.getActivitiesByTab('my_rights').subscribe();

      const req = httpMock.expectOne('/api/activity/my_rights/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "validations" tab', () => {
      service.getActivitiesByTab('validations').subscribe();

      const req = httpMock.expectOne('/api/activity/validations/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "system" tab', () => {
      service.getActivitiesByTab('system').subscribe();

      const req = httpMock.expectOne('/api/activity/system/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities for "rgpd" tab', () => {
      service.getActivitiesByTab('rgpd').subscribe();

      const req = httpMock.expectOne('/api/activity/rgpd/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should get activities by tab with filters', () => {
      service.getActivitiesByTab('my_sites', { action: 'create', page: 2 }).subscribe();

      const req = httpMock.expectOne(r =>
        r.url === '/api/activity/my_sites/' &&
        r.params.get('action') === 'create' &&
        r.params.get('page') === '2'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should default to "all" for unknown tab', () => {
      // Cast to any to test default behavior
      service.getActivitiesByTab('unknown' as ActivityTab).subscribe();

      const req = httpMock.expectOne('/api/activity/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });
  });

  // ==================== FILTER PARAMS BUILDING ====================

  describe('Filter Params Building', () => {
    it('should build params with plan_id', () => {
      service.getActivities({ plan_id: 123 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?plan_id=123');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should build params with organisme_id', () => {
      service.getActivities({ organisme_id: 456 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?organisme_id=456');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should build params with user_id', () => {
      service.getActivities({ user_id: 789 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?user_id=789');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should build params with actor_id', () => {
      service.getActivities({ actor_id: 111 }).subscribe();

      const req = httpMock.expectOne('/api/activity/?actor_id=111');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
    });

    it('should not include undefined filters', () => {
      service.getActivities({
        entity_type: 'site',
        action: undefined,
        page: undefined
      }).subscribe();

      const req = httpMock.expectOne('/api/activity/?entity_type=site');
      expect(req.request.method).toBe('GET');
      expect(req.request.params.has('action')).toBe(false);
      expect(req.request.params.has('page')).toBe(false);
      req.flush(mockPaginatedResponse);
    });
  });

  // ==================== COMPUTED SIGNALS ====================

  describe('Computed Signals', () => {
    it('should compute totalCount from tabsCounts', () => {
      expect(service.totalCount()).toBe(0);

      service.getTabsCounts().subscribe();
      const req = httpMock.expectOne('/api/activity/tabs_counts/');
      req.flush(mockTabsCounts);

      expect(service.totalCount()).toBe(100);
    });

    it('should return 0 for totalCount when tabsCounts is null', () => {
      expect(service.tabsCounts()).toBeNull();
      expect(service.totalCount()).toBe(0);
    });
  });
});
