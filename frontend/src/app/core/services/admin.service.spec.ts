import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AdminService, DashboardStats } from './admin.service';
import {
  AdminOrganisme,
  AdminSite,
  AdminUser,
  AdminPlan,
  PaginatedResponse,
  DuplicateCheckResult
} from '../models/admin.model';

describe('AdminService', () => {
  let service: AdminService;
  let httpMock: HttpTestingController;

  const mockOrganisme: AdminOrganisme = {
    id_organisme: 1,
    uuid_organisme: 'uuid-123',
    nom_organisme: 'Test Organisme',
    users_count: 5,
    sites_count: 3
  };

  const mockSite: AdminSite = {
    id_site: 1,
    slug: 'test-site',
    nom_site: 'Test Site',
    id_inpn: 'FR1234567'
  };

  const mockUser: AdminUser = {
    id_role: 1,
    email: 'test@example.com',
    nom_role: 'Dupont',
    prenom_role: 'Jean',
    role_level: 'utilisateur',
    active: true
  };

  const mockPlan: AdminPlan = {
    id_pg: 1,
    nom: 'Test Plan',
    statut: 'valide',
    gestion_partagee: false,
    ct88: false,
    risque_incendie: false,
    sites: [],
    referents: []
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AdminService]
    });

    service = TestBed.inject(AdminService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // ==================== ORGANISMES TESTS ====================

  describe('Organismes', () => {
    it('should get organismes', () => {
      const mockResponse: PaginatedResponse<AdminOrganisme> = {
        count: 1,
        results: [mockOrganisme]
      };

      service.getOrganismes().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results.length).toBe(1);
        expect(response.results[0].nom_organisme).toBe('Test Organisme');
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get organismes with search param', () => {
      const mockResponse: PaginatedResponse<AdminOrganisme> = {
        count: 1,
        results: [mockOrganisme]
      };

      service.getOrganismes({ search: 'test' }).subscribe();

      const req = httpMock.expectOne('/api/users/organismes/?search=test');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get organismes with page param', () => {
      const mockResponse: PaginatedResponse<AdminOrganisme> = {
        count: 1,
        results: [mockOrganisme]
      };

      service.getOrganismes({ page: 2 }).subscribe();

      const req = httpMock.expectOne('/api/users/organismes/?page=2');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get single organisme', () => {
      service.getOrganisme(1).subscribe(org => {
        expect(org.id_organisme).toBe(1);
        expect(org.nom_organisme).toBe('Test Organisme');
      });

      const req = httpMock.expectOne('/api/users/organismes/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockOrganisme);
    });

    it('should create organisme', () => {
      const payload = { nom_organisme: 'New Organisme' };

      service.createOrganisme(payload).subscribe(org => {
        expect(org.nom_organisme).toBe('Test Organisme');
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockOrganisme);
    });

    it('should update organisme', () => {
      const payload = { nom_organisme: 'Updated Organisme' };

      service.updateOrganisme(1, payload).subscribe(org => {
        expect(org.id_organisme).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/organismes/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(payload);
      req.flush(mockOrganisme);
    });

    it('should assign site to organisme', () => {
      service.assignSiteToOrganisme(1, 2, true).subscribe();

      const req = httpMock.expectOne('/api/users/organismes/1/assign_site/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ site_id: 2, principal: true });
      req.flush({});
    });

    it('should remove site from organisme', () => {
      service.removeSiteFromOrganisme(1, 2).subscribe();

      const req = httpMock.expectOne('/api/users/organismes/1/sites/2/');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
    });

    it('should get organisme sites', () => {
      service.getOrganismeSites(1).subscribe(sites => {
        expect(sites.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/organismes/1/sites/');
      expect(req.request.method).toBe('GET');
      req.flush([{ id_site: 1, nom_site: 'Test Site' }]);
    });

    it('should get organisme users', () => {
      const mockResponse: PaginatedResponse<AdminUser> = {
        count: 1,
        results: [mockUser]
      };

      service.getOrganismeUsers(1).subscribe(users => {
        expect(users.length).toBe(1);
        expect(users[0].email).toBe('test@example.com');
      });

      const req = httpMock.expectOne('/api/users/users/?organisme=1');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  // ==================== SITES TESTS ====================

  describe('Sites', () => {
    it('should get sites', () => {
      const mockResponse: PaginatedResponse<AdminSite> = {
        count: 1,
        results: [mockSite]
      };

      service.getSites().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results[0].nom_site).toBe('Test Site');
      });

      const req = httpMock.expectOne('/api/users/sites/');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get sites with filters', () => {
      const mockResponse: PaginatedResponse<AdminSite> = {
        count: 1,
        results: [mockSite]
      };

      service.getSites({ search: 'test', page: 2, page_size: 20, type: 'RNN' }).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === '/api/users/sites/' &&
        req.params.get('search') === 'test' &&
        req.params.get('page') === '2' &&
        req.params.get('page_size') === '20' &&
        req.params.get('id_type_site') === 'RNN'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get single site by slug', () => {
      service.getSite('test-site').subscribe(site => {
        expect(site.slug).toBe('test-site');
        expect(site.nom_site).toBe('Test Site');
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/');
      expect(req.request.method).toBe('GET');
      req.flush(mockSite);
    });

    it('should create site', () => {
      const payload = { nom_site: 'New Site' };

      service.createSite(payload).subscribe(site => {
        expect(site.nom_site).toBe('Test Site');
      });

      const req = httpMock.expectOne('/api/users/sites/');
      expect(req.request.method).toBe('POST');
      req.flush(mockSite);
    });

    it('should update site', () => {
      const payload = { nom_site: 'Updated Site' };

      service.updateSite('test-site', payload).subscribe(site => {
        expect(site.slug).toBe('test-site');
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockSite);
    });

    it('should check duplicates', () => {
      const mockResult: DuplicateCheckResult = {
        exact_inpn_match: null,
        similar_names: []
      };

      service.checkDuplicates({ nom_site: 'Test', id_inpn: 'FR123' }).subscribe(result => {
        expect(result.exact_inpn_match).toBeNull();
      });

      const req = httpMock.expectOne(req =>
        req.url === '/api/users/sites/check_duplicates/' &&
        req.params.get('nom_site') === 'Test' &&
        req.params.get('id_inpn') === 'FR123'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResult);
    });

    it('should search all sites', () => {
      const mockResponse: PaginatedResponse<AdminSite> = {
        count: 1,
        results: [mockSite]
      };

      service.searchAllSites({ search: 'test' }).subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/sites/search_all/?search=test');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get sites available for assignment', () => {
      const mockResponse: PaginatedResponse<AdminSite> = {
        count: 1,
        results: [mockSite]
      };

      service.getSitesAvailableForAssignment('test').subscribe(response => {
        expect(response.count).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/sites/available_for_assignment/?search=test');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should assign user to site', () => {
      service.assignUserToSite('test-site', 1, true).subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/assign_user/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ user_id: 1, referent: true });
      req.flush({});
    });

    it('should remove user from site', () => {
      service.removeUserFromSite('test-site', 1).subscribe();

      const req = httpMock.expectOne('/api/users/sites/test-site/users/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
    });

    it('should get site users', () => {
      service.getSiteUsers('test-site').subscribe(users => {
        expect(users.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/users/');
      expect(req.request.method).toBe('GET');
      req.flush([mockUser]);
    });

    it('should get site organismes', () => {
      service.getSiteOrganismes('test-site').subscribe(organismes => {
        expect(organismes.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/organismes/');
      expect(req.request.method).toBe('GET');
      req.flush([{ id_organisme: 1, nom_organisme: 'Test Org' }]);
    });

    it('should get site types', () => {
      service.getSiteTypes().subscribe(types => {
        expect(types.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/nomenclatures/?type=TYPE_SITE');
      expect(req.request.method).toBe('GET');
      req.flush({ results: [{ id_nomenclature: 1, cd_nomenclature: 'RNN', label: 'Reserve' }] });
    });
  });

  // ==================== SITES GEOJSON TESTS ====================

  describe('Sites GeoJSON', () => {
    it('should get site GeoJSON', () => {
      const mockGeoJSON = {
        type: 'Feature' as const,
        properties: { id_site: 1, nom_site: 'Test Site' },
        geometry: { type: 'Point' as const, coordinates: [2.0, 46.0] }
      };

      service.getSiteGeoJSON('test-site').subscribe(geojson => {
        expect(geojson.type).toBe('Feature');
      });

      const req = httpMock.expectOne('/api/users/sites/test-site/geojson/');
      expect(req.request.method).toBe('GET');
      req.flush(mockGeoJSON);
    });

    it('should get sites GeoJSON list', () => {
      const mockCollection = {
        type: 'FeatureCollection' as const,
        features: []
      };

      service.getSitesGeoJSON().subscribe(geojson => {
        expect(geojson.type).toBe('FeatureCollection');
      });

      const req = httpMock.expectOne('/api/users/sites/geojson_list/');
      expect(req.request.method).toBe('GET');
      req.flush(mockCollection);
    });

    it('should get sites GeoJSON filtered', () => {
      const mockCollection = {
        type: 'FeatureCollection' as const,
        features: []
      };

      service.getSitesGeoJSONFiltered({ userSitesOnly: true }).subscribe(geojson => {
        expect(geojson.type).toBe('FeatureCollection');
      });

      const req = httpMock.expectOne('/api/users/sites/geojson_list/?user_sites_only=true');
      expect(req.request.method).toBe('GET');
      req.flush(mockCollection);
    });
  });

  // ==================== USERS TESTS ====================

  describe('Users', () => {
    it('should get users', () => {
      const mockResponse: PaginatedResponse<AdminUser> = {
        count: 1,
        results: [mockUser]
      };

      service.getUsers().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results[0].email).toBe('test@example.com');
      });

      const req = httpMock.expectOne('/api/users/users/');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get users with filters', () => {
      const mockResponse: PaginatedResponse<AdminUser> = {
        count: 1,
        results: [mockUser]
      };

      service.getUsers({
        search: 'test',
        page: 2,
        page_size: 20,
        role: 'admin_og',
        organisme: 1,
        active: true
      }).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === '/api/users/users/' &&
        req.params.get('search') === 'test' &&
        req.params.get('page') === '2' &&
        req.params.get('page_size') === '20' &&
        req.params.get('role_level') === 'admin_og' &&
        req.params.get('organisme') === '1' &&
        req.params.get('active') === 'true'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get single user', () => {
      service.getUser(1).subscribe(user => {
        expect(user.id_role).toBe(1);
        expect(user.email).toBe('test@example.com');
      });

      const req = httpMock.expectOne('/api/users/users/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockUser);
    });

    it('should update user', () => {
      const payload = { nom_role: 'Updated' };

      service.updateUser(1, payload).subscribe(user => {
        expect(user.id_role).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/users/1/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockUser);
    });

    it('should toggle user status', () => {
      service.toggleUserStatus(1, false).subscribe(user => {
        expect(user.id_role).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/users/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ active: false });
      req.flush(mockUser);
    });

    it('should assign organisme to user', () => {
      service.assignOrganismeToUser(1, 'uuid-123').subscribe(user => {
        expect(user.id_role).toBe(1);
      });

      const req = httpMock.expectOne('/api/users/users/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ uuid_organisme: 'uuid-123' });
      req.flush(mockUser);
    });

    it('should assign site to user', () => {
      service.assignSiteToUser(1, 2, true).subscribe();

      const req = httpMock.expectOne('/api/users/users/1/sites/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ site_id: 2, referent: true });
      req.flush({});
    });

    it('should remove site from user', () => {
      service.removeSiteFromUser(1, 2).subscribe();

      const req = httpMock.expectOne('/api/users/users/1/sites/2/');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
    });
  });

  // ==================== PLANS TESTS ====================

  describe('Plans', () => {
    it('should get plans', () => {
      const mockResponse: PaginatedResponse<AdminPlan> = {
        count: 1,
        results: [mockPlan]
      };

      service.getPlans().subscribe(response => {
        expect(response.count).toBe(1);
        expect(response.results[0].nom).toBe('Test Plan');
      });

      const req = httpMock.expectOne('/api/plans/plans/');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get plans with filters', () => {
      const mockResponse: PaginatedResponse<AdminPlan> = {
        count: 1,
        results: [mockPlan]
      };

      service.getPlans({
        search: 'test',
        page: 2,
        page_size: 20,
        statut: 'valide',
        organisme: 1,
        site: 2
      }).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === '/api/plans/plans/' &&
        req.params.get('search') === 'test' &&
        req.params.get('page') === '2' &&
        req.params.get('page_size') === '20' &&
        req.params.get('statut') === 'valide' &&
        req.params.get('organisme') === '1' &&
        req.params.get('site_id') === '2'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get single plan', () => {
      service.getPlan(1).subscribe(plan => {
        expect(plan.id_pg).toBe(1);
        expect(plan.nom).toBe('Test Plan');
      });

      const req = httpMock.expectOne('/api/plans/plans/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPlan);
    });

    it('should create plan', () => {
      const payload = {
        nom: 'New Plan',
        statut: 'draft' as const,
        sites_ids: [1],
        rang: 1,
        ct88: false,
        annee_debut: 2024,
        annee_fin: 2034
      };

      service.createPlan(payload).subscribe(plan => {
        expect(plan.nom).toBe('Test Plan');
      });

      const req = httpMock.expectOne('/api/plans/plans/');
      expect(req.request.method).toBe('POST');
      req.flush(mockPlan);
    });

    it('should update plan', () => {
      const payload = { nom: 'Updated Plan' };

      service.updatePlan(1, payload).subscribe(plan => {
        expect(plan.id_pg).toBe(1);
      });

      const req = httpMock.expectOne('/api/plans/plans/1/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockPlan);
    });

    it('should delete plan', () => {
      service.deletePlan(1).subscribe();

      const req = httpMock.expectOne('/api/plans/plans/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });

    it('should update plan status', () => {
      service.updatePlanStatus(1, 'archive').subscribe(plan => {
        expect(plan.id_pg).toBe(1);
      });

      const req = httpMock.expectOne('/api/plans/plans/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ statut: 'archive' });
      req.flush(mockPlan);
    });

    it('should assign site to plan', () => {
      service.assignSiteToPlan(1, 2, 1, 'Test comment').subscribe();

      const req = httpMock.expectOne('/api/plans/plans/1/assign_site/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ site_id: 2, rang: 1, commentaire: 'Test comment' });
      req.flush(mockPlan);
    });

    it('should assign multiple sites to plan', (done) => {
      service.assignSitesToPlan(1, [2, 3]).subscribe(results => {
        expect(results.length).toBe(2);
        done();
      });

      const requests = httpMock.match('/api/plans/plans/1/assign_site/');
      expect(requests.length).toBe(2);
      requests.forEach(req => {
        expect(req.request.method).toBe('POST');
        req.flush(mockPlan);
      });
    });

    it('should return empty array when assigning zero sites', (done) => {
      service.assignSitesToPlan(1, []).subscribe(results => {
        expect(results).toEqual([]);
        done();
      });
    });

    it('should remove site from plan', () => {
      service.removeSiteFromPlan(1, 2).subscribe();

      const req = httpMock.expectOne('/api/plans/plans/1/remove_site/?site_id=2');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
    });

    it('should assign referent to plan', () => {
      service.assignReferentToPlan(1, 2).subscribe();

      const req = httpMock.expectOne('/api/plans/plans/1/assign_referent/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ referent_id: 2 });
      req.flush(mockPlan);
    });

    it('should assign multiple referents to plan', (done) => {
      service.assignReferentsToPlan(1, [2, 3]).subscribe(results => {
        expect(results.length).toBe(2);
        done();
      });

      const requests = httpMock.match('/api/plans/plans/1/assign_referent/');
      expect(requests.length).toBe(2);
      requests.forEach(req => {
        expect(req.request.method).toBe('POST');
        req.flush(mockPlan);
      });
    });

    it('should return empty array when assigning zero referents', (done) => {
      service.assignReferentsToPlan(1, []).subscribe(results => {
        expect(results).toEqual([]);
        done();
      });
    });

    it('should remove referent from plan', () => {
      service.removeReferentFromPlan(1, 2).subscribe();

      const req = httpMock.expectOne('/api/plans/plans/1/remove_referent/?referent_id=2');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
    });

    it('should get evaluation types', () => {
      service.getEvaluationTypes().subscribe(types => {
        expect(types.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/nomenclatures/?type=TYPE_EVALUATION');
      expect(req.request.method).toBe('GET');
      req.flush({ results: [{ id_nomenclature: 1, cd_nomenclature: 'EVAL', label: 'Evaluation' }] });
    });

    it('should get redacteur types', () => {
      service.getRedacteurTypes().subscribe(types => {
        expect(types.length).toBe(1);
      });

      const req = httpMock.expectOne('/api/nomenclatures/?type=TYPE_REDACTEUR');
      expect(req.request.method).toBe('GET');
      req.flush({ results: [{ id_nomenclature: 1, cd_nomenclature: 'RED', label: 'Redacteur' }] });
    });
  });

  // ==================== DASHBOARD TESTS ====================

  describe('Dashboard', () => {
    it('should get dashboard stats', (done) => {
      service.getDashboardStats().subscribe(stats => {
        expect(stats.totalUtilisateurs).toBe(10);
        expect(stats.totalSites).toBe(20);
        expect(stats.totalOrganismes).toBe(5);
        expect(stats.totalPlans).toBe(15);
        expect(stats.plansActifs).toBe(8);
        done();
      });

      // Respond to all requests
      const usersReq = httpMock.expectOne('/api/users/users/');
      usersReq.flush({ pagination: { count: 10 } });

      const sitesReq = httpMock.expectOne('/api/users/sites/');
      sitesReq.flush({ pagination: { count: 20 } });

      const orgsReq = httpMock.expectOne('/api/users/organismes/');
      orgsReq.flush({ pagination: { count: 5 } });

      const plansReq = httpMock.expectOne('/api/plans/plans/');
      plansReq.flush({ pagination: { count: 15 } });

      const plansActifsReq = httpMock.expectOne('/api/plans/plans/?actif=true');
      plansActifsReq.flush({ pagination: { count: 8 } });
    });

    it('should handle dashboard stats errors gracefully', (done) => {
      service.getDashboardStats().subscribe(stats => {
        // Should return 0 for failed requests
        expect(stats.totalUtilisateurs).toBe(0);
        expect(stats.totalSites).toBe(20);
        done();
      });

      // Simulate error for users request
      const usersReq = httpMock.expectOne('/api/users/users/');
      usersReq.error(new ErrorEvent('Network error'));

      // Other requests succeed
      const sitesReq = httpMock.expectOne('/api/users/sites/');
      sitesReq.flush({ pagination: { count: 20 } });

      const orgsReq = httpMock.expectOne('/api/users/organismes/');
      orgsReq.flush({ pagination: { count: 0 } });

      const plansReq = httpMock.expectOne('/api/plans/plans/');
      plansReq.flush({ pagination: { count: 0 } });

      const plansActifsReq = httpMock.expectOne('/api/plans/plans/?actif=true');
      plansActifsReq.flush({ pagination: { count: 0 } });
    });
  });

  // ==================== ERROR HANDLING TESTS ====================

  describe('Error Handling', () => {
    it('should handle 400 error with detail', (done) => {
      service.getOrganismes().subscribe({
        error: (error) => {
          expect(error.message).toBe('Validation error');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      req.flush({ detail: 'Validation error' }, { status: 400, statusText: 'Bad Request' });
    });

    it('should handle 400 error with field errors', (done) => {
      service.getOrganismes().subscribe({
        error: (error) => {
          expect(error.message).toContain('nom_organisme');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      req.flush({ nom_organisme: ['Ce champ est requis'] }, { status: 400, statusText: 'Bad Request' });
    });

    it('should handle 403 error', (done) => {
      service.getOrganismes().subscribe({
        error: (error) => {
          expect(error.message).toContain('droits');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      req.flush({}, { status: 403, statusText: 'Forbidden' });
    });

    it('should handle 404 error', (done) => {
      service.getOrganisme(999).subscribe({
        error: (error) => {
          expect(error.message).toBe('Ressource non trouvée');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/999/');
      req.flush({}, { status: 404, statusText: 'Not Found' });
    });

    it('should handle 500 error', (done) => {
      service.getOrganismes().subscribe({
        error: (error) => {
          expect(error.message).toContain('serveur');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      req.flush({}, { status: 500, statusText: 'Internal Server Error' });
    });

    it('should handle network error', (done) => {
      service.getOrganismes().subscribe({
        error: (error) => {
          expect(error.message).toContain('connecter');
          done();
        }
      });

      const req = httpMock.expectOne('/api/users/organismes/');
      req.error(new ProgressEvent('error'), { status: 0 });
    });
  });
});
