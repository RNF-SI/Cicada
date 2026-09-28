import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ValidationService, ValidationFilters, ValidationTypesResponse } from './validation.service';
import { NotificationService } from './notification.service';
import {
  ValidationRequest,
  ValidationRequestListItem,
  ValidationCountResponse,
  PublicRegistrationResponse,
  RegistrationStatusResponse
} from '../models/notification.model';
import { of } from 'rxjs';

describe('ValidationService', () => {
  let service: ValidationService;
  let httpMock: HttpTestingController;
  let notificationServiceMock: {
    updatePendingValidationsCount: jest.Mock;
    refresh: jest.Mock;
  };

  const mockValidationRequest: ValidationRequestListItem = {
    id: 1,
    request_type: 'site_access',
    request_type_display: 'Demande accès site',
    status: 'pending',
    status_display: 'En attente',
    created_at: '2024-01-01T10:00:00Z',
    requester_id: 1,
    requester_name: 'Jean Dupont',
    target_name: 'Site Test'
  };

  const mockFullRequest: ValidationRequest = {
    id: 1,
    request_type: 'site_access',
    request_type_display: 'Demande accès site',
    status: 'pending',
    status_display: 'En attente',
    created_at: '2024-01-01T10:00:00Z',
    requester: {
      id: 1,
      email: 'jean@test.com',
      nom_complet: 'Jean Dupont'
    },
    target_site: {
      id: 1,
      nom_site: 'Site Test'
    }
  };

  beforeEach(() => {
    notificationServiceMock = {
      updatePendingValidationsCount: jest.fn(),
      refresh: jest.fn().mockReturnValue(of({
        notifications: [],
        unread_count: 0,
        pending_validations: 0,
        has_updates: false,
        timestamp: ''
      }))
    };

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        ValidationService,
        { provide: NotificationService, useValue: notificationServiceMock }
      ]
    });

    service = TestBed.inject(ValidationService);
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
  });

  // ==================== GET VALIDATION REQUESTS ====================

  describe('Get Validation Requests', () => {
    it('should get validation requests without filters', () => {
      service.getValidationRequests().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/validations/');
      expect(req.request.method).toBe('GET');
      req.flush({ count: 1, next: null, previous: null, results: [mockValidationRequest] });
    });

    it('should get validation requests with status filter', () => {
      service.getValidationRequests({ status: 'pending' }).subscribe();

      const req = httpMock.expectOne('/api/validations/?status=pending');
      expect(req.request.method).toBe('GET');
      req.flush({ count: 1, next: null, previous: null, results: [mockValidationRequest] });
    });

    it('should get validation requests with request_type filter', () => {
      service.getValidationRequests({ request_type: 'site_access' }).subscribe();

      const req = httpMock.expectOne('/api/validations/?request_type=site_access');
      expect(req.request.method).toBe('GET');
      req.flush({ count: 1, next: null, previous: null, results: [mockValidationRequest] });
    });

    it('should get validation requests with page filter', () => {
      service.getValidationRequests({ page: 2 }).subscribe();

      const req = httpMock.expectOne('/api/validations/?page=2');
      expect(req.request.method).toBe('GET');
      req.flush({ count: 1, next: null, previous: null, results: [mockValidationRequest] });
    });

    it('should get validation requests with multiple filters', () => {
      service.getValidationRequests({ status: 'pending', request_type: 'site_access', page: 1 }).subscribe();

      const req = httpMock.expectOne(r =>
        r.url === '/api/validations/' &&
        r.params.get('status') === 'pending' &&
        r.params.get('request_type') === 'site_access' &&
        r.params.get('page') === '1'
      );
      expect(req.request.method).toBe('GET');
      req.flush({ count: 1, next: null, previous: null, results: [mockValidationRequest] });
    });

    // #658 - l'API renvoie la forme imbriquee de `UsersPagination` : sans
    // normalisation, `count` est undefined et le paginateur reste bloque.
    it('should normalize the nested pagination shape (UsersPagination)', () => {
      service.getValidationRequests({ page: 2 }).subscribe(response => {
        expect(response.count).toBe(34);
        expect(response.next).toBe('/api/validations/?page=3');
        expect(response.previous).toBe('/api/validations/?page=1');
        expect(response.results.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/validations/?page=2');
      req.flush({
        links: { next: '/api/validations/?page=3', previous: '/api/validations/?page=1' },
        pagination: {
          count: 34,
          current_page: 2,
          total_pages: 2,
          page_size: 20,
          has_next: false,
          has_previous: true
        },
        results: [mockValidationRequest]
      });
    });

    it('should keep the flat DRF pagination shape working', () => {
      service.getValidationRequests().subscribe(response => {
        expect(response.count).toBe(42);
        expect(response.results.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/validations/');
      req.flush({ count: 42, next: null, previous: null, results: [mockValidationRequest] });
    });
  });

  // ==================== GET SINGLE REQUEST ====================

  describe('Get Single Request', () => {
    it('should get validation request by id', () => {
      service.getValidationRequest(1).subscribe(request => {
        expect(request.id).toBe(1);
        expect(request.request_type).toBe('site_access');
      });

      const req = httpMock.expectOne('/api/validations/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockFullRequest);
    });
  });

  // ==================== PENDING COUNT ====================

  describe('Pending Count', () => {
    it('should get pending count and update notification service', () => {
      const countResponse: ValidationCountResponse = { pending_count: 5 };

      service.getPendingCount().subscribe(response => {
        expect(response.pending_count).toBe(5);
      });

      const req = httpMock.expectOne('/api/validations/pending_count/');
      expect(req.request.method).toBe('GET');
      req.flush(countResponse);

      expect(notificationServiceMock.updatePendingValidationsCount).toHaveBeenCalledWith(5);
    });
  });

  // ==================== GET TYPES ====================

  describe('Get Types', () => {
    it('should get validation types', () => {
      const typesResponse: ValidationTypesResponse = {
        request_types: [
          { value: 'site_access', label: 'Demande accès site' },
          { value: 'plan_access', label: 'Demande accès plan' }
        ],
        statuses: [
          { value: 'pending', label: 'En attente' },
          { value: 'approved', label: 'Approuvé' }
        ]
      };

      service.getTypes().subscribe(response => {
        expect(response.request_types.length).toBe(2);
        expect(response.statuses.length).toBe(2);
      });

      const req = httpMock.expectOne('/api/validations/types/');
      expect(req.request.method).toBe('GET');
      req.flush(typesResponse);
    });
  });

  // ==================== MY REQUESTS ====================

  describe('My Requests', () => {
    it('should get my requests', () => {
      service.getMyRequests().subscribe(requests => {
        expect(requests.length).toBe(1);
        expect(requests[0].id).toBe(1);
      });

      const req = httpMock.expectOne('/api/validations/my_requests/');
      expect(req.request.method).toBe('GET');
      req.flush([mockValidationRequest]);
    });
  });

  // ==================== APPROVE/REJECT ====================

  describe('Approve and Reject', () => {
    it('should approve request', () => {
      service.approveRequest(1).subscribe(response => {
        expect(response.status).toBe('approved');
      });

      const req = httpMock.expectOne('/api/validations/1/approve/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ status: 'approved', message: 'Demande approuvée' });

      expect(notificationServiceMock.refresh).toHaveBeenCalled();
    });

    it('should approve request with comment', () => {
      service.approveRequest(1, { comment: 'Approved!' }).subscribe();

      const req = httpMock.expectOne('/api/validations/1/approve/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ comment: 'Approved!' });
      req.flush({ status: 'approved', message: 'Demande approuvée' });
    });

    it('should reject request with comment', () => {
      service.rejectRequest(1, { comment: 'Not eligible' }).subscribe(response => {
        expect(response.status).toBe('rejected');
      });

      const req = httpMock.expectOne('/api/validations/1/reject/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ comment: 'Not eligible' });
      req.flush({ status: 'rejected', message: 'Demande rejetée' });

      expect(notificationServiceMock.refresh).toHaveBeenCalled();
    });
  });

  // ==================== CANCEL ====================

  describe('Cancel Request', () => {
    it('should cancel request', () => {
      service.cancelRequest(1).subscribe(response => {
        expect(response.status).toBe('cancelled');
      });

      const req = httpMock.expectOne('/api/validations/1/cancel/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ status: 'cancelled', message: 'Demande annulée' });
    });
  });

  // ==================== SITE ACCESS REQUESTS ====================

  describe('Site Access Requests', () => {
    it('should request site access', () => {
      service.requestSiteAccess('test-site').subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/request_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(mockFullRequest);
    });

    it('should request site access with justification', () => {
      service.requestSiteAccess('test-site', { justification: 'Need access for work' }).subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/request_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ justification: 'Need access for work' });
      req.flush(mockFullRequest);
    });

    it('should request site org link', () => {
      service.requestSiteOrgLink('test-site', { justification: 'Our organisme manages this site' }).subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/request_org_link/');
      expect(req.request.method).toBe('POST');
      req.flush(mockFullRequest);
    });

    it('should request referent status', () => {
      service.requestReferent('test-site', { justification: 'I am the site manager' }).subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/request_referent/');
      expect(req.request.method).toBe('POST');
      req.flush(mockFullRequest);
    });
  });

  // ==================== INVITE TO SITE ====================

  describe('Invite to Site', () => {
    it('should invite organisme to site', () => {
      service.inviteOrganismeToSite('test-site', { organisme_id: 1, justification: 'Partner org' }).subscribe(response => {
        expect(response.id).toBeDefined();
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/invite_organisme/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ organisme_id: 1, justification: 'Partner org' });
      req.flush({ id: 1, message: 'Invitation envoyée' });
    });

    it('should invite user to site', () => {
      service.inviteUserToSite('test-site', { user_id: 1, justification: 'New team member' }).subscribe(response => {
        expect(response.id).toBeDefined();
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/invite_user/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ user_id: 1, justification: 'New team member' });
      req.flush({ id: 1, message: 'Invitation envoyée' });
    });
  });

  // ==================== PLAN ACCESS ====================

  describe('Plan Access', () => {
    it('should request plan access', () => {
      service.requestPlanAccess(1).subscribe();

      const req = httpMock.expectOne('/api/validations/request_plan_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ plan_id: 1 });
      req.flush(mockFullRequest);
    });

    it('should request plan access with justification', () => {
      service.requestPlanAccess(1, { justification: 'Need to review the plan' }).subscribe();

      const req = httpMock.expectOne('/api/validations/request_plan_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ plan_id: 1, justification: 'Need to review the plan' });
      req.flush(mockFullRequest);
    });
  });

  // ==================== MODULE ACCESS ====================

  describe('Module Access', () => {
    it('should request module access', () => {
      service.requestModuleAccess({ module_code: 'zonages', justification: 'Need zonage access' }).subscribe();

      const req = httpMock.expectOne('/api/validations/request_module_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ module_code: 'zonages', justification: 'Need zonage access' });
      req.flush(mockFullRequest);
    });

    it('should grant module access', () => {
      service.grantModuleAccess({ user_id: 1, module_code: 'zonages' }).subscribe();

      const req = httpMock.expectOne('/api/validations/grant_module_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ user_id: 1, module_code: 'zonages' });
      req.flush({ status: 'granted', message: 'Accès accordé' });
    });

    it('should revoke module access', () => {
      service.revokeModuleAccess({ user_id: 1, module_code: 'zonages' }).subscribe();

      const req = httpMock.expectOne('/api/validations/revoke_module_access/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ user_id: 1, module_code: 'zonages' });
      req.flush({ status: 'revoked', message: 'Accès révoqué' });
    });

    it('should get my module access', () => {
      service.getMyModuleAccess().subscribe(response => {
        expect(response.modules).toContain('plans');
      });

      const req = httpMock.expectOne('/api/validations/my_module_access/');
      expect(req.request.method).toBe('GET');
      req.flush({ modules: ['plans', 'sites'] });
    });
  });

  // ==================== REGISTRATION ====================

  describe('Registration', () => {
    it('should register new user', () => {
      const registrationData = {
        email: 'newuser@test.com',
        password: 'Test123!',
        password_confirm: 'Test123!',
        nom_role: 'Dupont',
        prenom_role: 'Jean',
        organisme_id: 1
      };

      const response: PublicRegistrationResponse = {
        message: 'Inscription enregistrée',
        validation_request_id: 1
      };

      service.register(registrationData).subscribe(res => {
        expect(res.validation_request_id).toBe(1);
      });

      const req = httpMock.expectOne('/api/auth/register/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(registrationData);
      req.flush(response);
    });

    it('should check registration status - pending', () => {
      service.checkRegistrationStatus('pending@test.com').subscribe(response => {
        expect(response.status).toBe('pending');
      });

      const req = httpMock.expectOne('/api/auth/registration-status/?email=pending@test.com');
      expect(req.request.method).toBe('GET');
      req.flush({ status: 'pending', message: 'En attente de validation' });
    });

    it('should check registration status - registered', () => {
      service.checkRegistrationStatus('registered@test.com').subscribe(response => {
        expect(response.status).toBe('registered');
      });

      const req = httpMock.expectOne('/api/auth/registration-status/?email=registered@test.com');
      expect(req.request.method).toBe('GET');
      req.flush({ status: 'registered', message: 'Utilisateur enregistré' });
    });

    it('should check registration status - not found', () => {
      service.checkRegistrationStatus('unknown@test.com').subscribe(response => {
        expect(response.status).toBe('not_found');
      });

      const req = httpMock.expectOne('/api/auth/registration-status/?email=unknown@test.com');
      expect(req.request.method).toBe('GET');
      req.flush({ status: 'not_found', message: 'Email non trouvé' });
    });
  });

  // ==================== ADMIN ROLE MANAGEMENT ====================

  describe('Admin Role Management', () => {
    it('should request admin promotion', () => {
      service.requestAdminPromotion(1, 'Good candidate for admin').subscribe(response => {
        expect(response.id).toBeDefined();
      });

      const req = httpMock.expectOne('/api/validations/request_admin_promotion/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        target_user_id: 1,
        justification: 'Good candidate for admin'
      });
      req.flush({ id: 1, message: 'Demande de promotion envoyée' });
    });

    it('should request admin demotion', () => {
      service.requestAdminDemotion(1, 'No longer needs admin rights').subscribe(response => {
        expect(response.id).toBeDefined();
      });

      const req = httpMock.expectOne('/api/validations/request_admin_demotion/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        target_user_id: 1,
        justification: 'No longer needs admin rights'
      });
      req.flush({ id: 1, message: 'Demande de rétrogradation envoyée' });
    });
  });
});
