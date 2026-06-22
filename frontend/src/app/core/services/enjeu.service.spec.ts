import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { EnjeuService } from './enjeu.service';
import {
  Enjeu,
  PlanEnjeuxResponse,
  EnjeuStats,
  PaginatedEnjeuxResponse,
  FacteurInfluence,
  Pression,
  ObjectifLongTerme,
  ObjectifLongTermeCreatePayload,
  NiveauExigence
} from '../models/enjeu.model';

describe('EnjeuService', () => {
  let service: EnjeuService;
  let httpMock: HttpTestingController;

  const mockEnjeu: Enjeu = {
    id_enjeu: 1,
    id_pg: 10,
    id_categorie: 100,
    categorie_mnemonique: 'ENJEU',
    categorie_label: 'Enjeu de conservation',
    libelle: 'Protection zones humides',
    rang: 1,
    categorie_ecologique: true,
    habitat: true,
    espece: false,
    processus: false,
    patrimoine_geologique: false,
    geo_ex_situ: false,
    geo_in_situ: false,
    geo_documents: false,
    geo_autre: false,
    fonctionnalite_ecosysteme: false,
    autre_ecologique: false,
    valeur_paysagere: false,
    patrimoine_culturel: false,
    developpement_durable: false,
    usages: false,
    valeur_ajoutee: false,
    autre_socioeco: false,
    nb_facteurs_influence: 2,
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
  };

  const mockFcr: Enjeu = {
    id_enjeu: 2,
    id_pg: 10,
    id_categorie: 101,
    categorie_mnemonique: 'FCR',
    categorie_label: 'Facteur Clé de Réussite',
    libelle: 'Connaissance scientifique',
    habitat: false,
    espece: false,
    processus: false,
    patrimoine_geologique: false,
    geo_ex_situ: false,
    geo_in_situ: false,
    geo_documents: false,
    geo_autre: false,
    fonctionnalite_ecosysteme: false,
    autre_ecologique: false,
    valeur_paysagere: false,
    patrimoine_culturel: false,
    developpement_durable: false,
    usages: false,
    valeur_ajoutee: false,
    autre_socioeco: false,
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
  };

  const mockPlanEnjeuxResponse: PlanEnjeuxResponse = {
    plan_id: 10,
    plan_nom: 'Plan Test',
    enjeux: [mockEnjeu],
    fcr: [mockFcr],
    total_enjeux: 1,
    total_fcr: 1,
  };

  const mockPaginatedResponse: PaginatedEnjeuxResponse = {
    count: 2,
    next: null,
    previous: null,
    results: [mockEnjeu, mockFcr],
  };

  const mockStats: EnjeuStats = {
    total_enjeux: 5,
    total_fcr: 3,
    par_priorite: { priorite_1: 2, priorite_2: 2, priorite_3: 1 },
    par_type: { habitat: 3, espece: 1, processus: 1 },
  };

  const mockFacteur: FacteurInfluence = {
    id_facteur_influence: 1,
    id_enjeu: 1,
    libelle: 'Changement climatique',
    description: 'Impact du climat',
    nb_pressions: 2,
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
  };

  const mockPression: Pression = {
    id_pression: 1,
    id_facteur_influence: 1,
    libelle: 'Sécheresse',
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [EnjeuService],
    });
    service = TestBed.inject(EnjeuService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // =========================================================================
  // Initialization
  // =========================================================================

  describe('initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have loading=false initially', () => {
      expect(service.loading()).toBe(false);
    });

    it('should have error=null initially', () => {
      expect(service.error()).toBeNull();
    });
  });

  // =========================================================================
  // getPlanEnjeux
  // =========================================================================

  describe('getPlanEnjeux', () => {
    it('should call correct API endpoint', fakeAsync(() => {
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPlanEnjeuxResponse);
      tick();
    }));

    it('should store response in currentPlanEnjeux signal', fakeAsync(() => {
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();
      expect(service.currentPlanEnjeux()).toEqual(mockPlanEnjeuxResponse);
    }));

    it('should use cache for same plan_id', fakeAsync(() => {
      // First call
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();

      // Second call - should use cache
      service.getPlanEnjeux(10).subscribe(result => {
        expect(result).toEqual(mockPlanEnjeuxResponse);
      });
      httpMock.expectNone('/api/plans/enjeux/by-plan/10/');
      tick();
    }));

    it('should bypass cache with forceRefresh=true', fakeAsync(() => {
      // First call
      service.getPlanEnjeux(10).subscribe();
      const req1 = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req1.flush(mockPlanEnjeuxResponse);
      tick();

      // Second call with forceRefresh
      service.getPlanEnjeux(10, true).subscribe();
      const req2 = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req2.flush(mockPlanEnjeuxResponse);
      tick();
    }));

    it('should set loading=true during request', fakeAsync(() => {
      service.getPlanEnjeux(10).subscribe();
      expect(service.loading()).toBe(true);
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();
      expect(service.loading()).toBe(false);
    }));

    it('should set error on failure', fakeAsync(() => {
      service.getPlanEnjeux(10).subscribe({
        error: () => {},
      });
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.loading()).toBe(false);
      expect(service.error()).toBeTruthy();
    }));

    it('should compute hasEnjeux correctly', fakeAsync(() => {
      expect(service.hasEnjeux()).toBe(false);
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();
      expect(service.hasEnjeux()).toBe(true);
    }));

    it('should compute totalCount correctly', fakeAsync(() => {
      expect(service.totalCount()).toBe(0);
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();
      expect(service.totalCount()).toBe(2);
    }));
  });

  // =========================================================================
  // CRUD Enjeux
  // =========================================================================

  describe('getEnjeu', () => {
    it('should call GET /api/plans/enjeux/{id}/', fakeAsync(() => {
      service.getEnjeu(1).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      expect(req.request.method).toBe('GET');
      req.flush(mockEnjeu);
      tick();
    }));
  });

  describe('createEnjeu', () => {
    it('should call POST /api/plans/enjeux/', fakeAsync(() => {
      const payload = {
        id_pg: 10,
        id_categorie: 100,
        libelle: 'Nouvel Enjeu',
        rang: 1 as const,
        categorie_ecologique: true,
      };
      service.createEnjeu(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockEnjeu);
      tick();
    }));

    it('should set loading during request', fakeAsync(() => {
      service.createEnjeu({
        id_pg: 10, id_categorie: 100, libelle: 'Test', rang: 1, categorie_ecologique: true
      }).subscribe();
      expect(service.loading()).toBe(true);
      const req = httpMock.expectOne('/api/plans/enjeux/');
      req.flush(mockEnjeu);
      tick();
      expect(service.loading()).toBe(false);
    }));

    it('should set error on failure', fakeAsync(() => {
      service.createEnjeu({
        id_pg: 10, id_categorie: 100, libelle: 'Test', rang: 1, categorie_ecologique: true
      }).subscribe({ error: () => {} });
      const req = httpMock.expectOne('/api/plans/enjeux/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.error()).toBeTruthy();
    }));
  });

  describe('createFcr', () => {
    it('should call POST /api/plans/enjeux/', fakeAsync(() => {
      const payload = {
        id_pg: 10,
        id_categorie: 101,
        libelle: 'Nouveau FCR',
        id_categorie_fcr: 200,
      };
      service.createFcr(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/');
      expect(req.request.method).toBe('POST');
      req.flush(mockFcr);
      tick();
    }));

    it('should set loading during request', fakeAsync(() => {
      service.createFcr({
        id_pg: 10, id_categorie: 101, libelle: 'FCR', id_categorie_fcr: 200
      }).subscribe();
      expect(service.loading()).toBe(true);
      const req = httpMock.expectOne('/api/plans/enjeux/');
      req.flush(mockFcr);
      tick();
      expect(service.loading()).toBe(false);
    }));

    it('should set error on failure', fakeAsync(() => {
      service.createFcr({
        id_pg: 10, id_categorie: 101, libelle: 'FCR', id_categorie_fcr: 200
      }).subscribe({ error: () => {} });
      const req = httpMock.expectOne('/api/plans/enjeux/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.error()).toBeTruthy();
    }));
  });

  describe('updateEnjeu', () => {
    it('should call PATCH /api/plans/enjeux/{id}/', fakeAsync(() => {
      service.updateEnjeu(1, { libelle: 'Updated' }).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockEnjeu);
      tick();
    }));

    it('should set loading during request', fakeAsync(() => {
      service.updateEnjeu(1, { libelle: 'Updated' }).subscribe();
      expect(service.loading()).toBe(true);
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      req.flush(mockEnjeu);
      tick();
      expect(service.loading()).toBe(false);
    }));

    it('should set error on failure', fakeAsync(() => {
      service.updateEnjeu(1, { libelle: 'Updated' }).subscribe({ error: () => {} });
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.error()).toBeTruthy();
    }));
  });

  describe('deleteEnjeu', () => {
    it('should call DELETE /api/plans/enjeux/{id}/', fakeAsync(() => {
      service.deleteEnjeu(1).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));

    it('should set loading during request', fakeAsync(() => {
      service.deleteEnjeu(1).subscribe();
      expect(service.loading()).toBe(true);
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      req.flush(null);
      tick();
      expect(service.loading()).toBe(false);
    }));

    it('should set error on failure', fakeAsync(() => {
      service.deleteEnjeu(1).subscribe({ error: () => {} });
      const req = httpMock.expectOne('/api/plans/enjeux/1/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.error()).toBeTruthy();
    }));
  });

  describe('getEnjeuStats', () => {
    it('should call GET /api/plans/enjeux/stats/', fakeAsync(() => {
      service.getEnjeuStats().subscribe(result => {
        expect(result).toEqual(mockStats);
      });
      const req = httpMock.expectOne('/api/plans/enjeux/stats/');
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
      tick();
    }));
  });

  // =========================================================================
  // Taxon/Habitat operations
  // =========================================================================

  describe('addTaxon', () => {
    it('should call POST /api/plans/enjeux/{id}/add_taxon/', fakeAsync(() => {
      const taxon = { cd_nom: 12345, nom_complet: 'Taxon Test' };
      service.addTaxon(1, taxon).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/add_taxon/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(taxon);
      req.flush(taxon);
      tick();
    }));
  });

  describe('removeTaxon', () => {
    it('should call DELETE /api/plans/enjeux/{id}/remove_taxon/{cd_nom}/', fakeAsync(() => {
      service.removeTaxon(1, 12345).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/remove_taxon/12345/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });

  describe('addHabitat', () => {
    it('should call POST /api/plans/enjeux/{id}/add_habitat/', fakeAsync(() => {
      const habitat = { cd_hab: 'HAB_001', lb_hab_fr: 'Habitat Test' };
      service.addHabitat(1, habitat).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/add_habitat/');
      expect(req.request.method).toBe('POST');
      req.flush(habitat);
      tick();
    }));
  });

  describe('removeHabitat', () => {
    it('should call DELETE with URL-encoded cd_hab', fakeAsync(() => {
      service.removeHabitat(1, 'HAB/001').subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/remove_habitat/HAB%2F001/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));

    it('should call DELETE for simple cd_hab', fakeAsync(() => {
      service.removeHabitat(1, 'HAB_001').subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/1/remove_habitat/HAB_001/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });

  // =========================================================================
  // Facteur Influence CRUD
  // =========================================================================

  describe('createFacteurInfluence', () => {
    it('should call POST /api/plans/facteurs-influence/', fakeAsync(() => {
      const payload = { id_enjeu: 1, libelle: 'Nouveau Facteur' };
      service.createFacteurInfluence(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/facteurs-influence/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockFacteur);
      tick();
    }));
  });

  describe('updateFacteurInfluence', () => {
    it('should call PATCH /api/plans/facteurs-influence/{id}/', fakeAsync(() => {
      service.updateFacteurInfluence(1, { libelle: 'Updated' }).subscribe();
      const req = httpMock.expectOne('/api/plans/facteurs-influence/1/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockFacteur);
      tick();
    }));
  });

  describe('deleteFacteurInfluence', () => {
    it('should call DELETE /api/plans/facteurs-influence/{id}/', fakeAsync(() => {
      service.deleteFacteurInfluence(1).subscribe();
      const req = httpMock.expectOne('/api/plans/facteurs-influence/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });

  // =========================================================================
  // Pression CRUD
  // =========================================================================

  describe('createPression', () => {
    it('should call POST /api/plans/pressions/', fakeAsync(() => {
      const payload = { id_facteur_influence: 1, libelle: 'Nouvelle Pression' };
      service.createPression(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/pressions/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockPression);
      tick();
    }));
  });

  describe('updatePression', () => {
    it('should call PATCH /api/plans/pressions/{id}/', fakeAsync(() => {
      service.updatePression(1, { libelle: 'Updated' }).subscribe();
      const req = httpMock.expectOne('/api/plans/pressions/1/');
      expect(req.request.method).toBe('PATCH');
      req.flush(mockPression);
      tick();
    }));
  });

  describe('deletePression', () => {
    it('should call DELETE /api/plans/pressions/{id}/', fakeAsync(() => {
      service.deletePression(1).subscribe();
      const req = httpMock.expectOne('/api/plans/pressions/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });

  // =========================================================================
  // Utility methods
  // =========================================================================

  describe('clearCurrentPlanEnjeux', () => {
    it('should set signal to null', fakeAsync(() => {
      // First load data
      service.getPlanEnjeux(10).subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req.flush(mockPlanEnjeuxResponse);
      tick();
      expect(service.currentPlanEnjeux()).not.toBeNull();

      // Clear
      service.clearCurrentPlanEnjeux();
      expect(service.currentPlanEnjeux()).toBeNull();
    }));
  });

  describe('refreshCurrentPlanEnjeux', () => {
    it('should call getPlanEnjeux with forceRefresh if data exists', fakeAsync(() => {
      // First load data
      service.getPlanEnjeux(10).subscribe();
      const req1 = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req1.flush(mockPlanEnjeuxResponse);
      tick();

      // Refresh
      service.refreshCurrentPlanEnjeux();
      const req2 = httpMock.expectOne('/api/plans/enjeux/by-plan/10/');
      req2.flush(mockPlanEnjeuxResponse);
      tick();
    }));

    it('should do nothing if no current data', () => {
      service.refreshCurrentPlanEnjeux();
      httpMock.expectNone('/api/plans/enjeux/by-plan/');
    });
  });

  // =========================================================================
  // getEnjeux with filters
  // =========================================================================

  describe('getEnjeux', () => {
    it('should call GET /api/plans/enjeux/ without filters', fakeAsync(() => {
      service.getEnjeux().subscribe();
      const req = httpMock.expectOne('/api/plans/enjeux/');
      expect(req.request.method).toBe('GET');
      req.flush(mockPaginatedResponse);
      tick();
    }));

    it('should pass id_pg filter', fakeAsync(() => {
      service.getEnjeux({ id_pg: 1 }).subscribe();
      const req = httpMock.expectOne(r => r.url === '/api/plans/enjeux/' && r.params.get('id_pg') === '1');
      req.flush(mockPaginatedResponse);
      tick();
    }));

    it('should pass search filter', fakeAsync(() => {
      service.getEnjeux({ search: 'test' }).subscribe();
      const req = httpMock.expectOne(r => r.url === '/api/plans/enjeux/' && r.params.get('search') === 'test');
      req.flush(mockPaginatedResponse);
      tick();
    }));

    it('should build all filter params correctly', fakeAsync(() => {
      service.getEnjeux({
        id_pg: 5,
        is_enjeu: true,
        rang: 2,
        categorie_ecologique: true,
        habitat: true,
        search: 'bio',
      }).subscribe();
      const req = httpMock.expectOne(r => {
        return r.url === '/api/plans/enjeux/'
          && r.params.get('id_pg') === '5'
          && r.params.get('is_enjeu') === 'true'
          && r.params.get('rang') === '2'
          && r.params.get('categorie_ecologique') === 'true'
          && r.params.get('habitat') === 'true'
          && r.params.get('search') === 'bio';
      });
      req.flush(mockPaginatedResponse);
      tick();
    }));

    it('should set error on failure', fakeAsync(() => {
      service.getEnjeux().subscribe({ error: () => {} });
      const req = httpMock.expectOne('/api/plans/enjeux/');
      req.error(new ProgressEvent('error'));
      tick();
      expect(service.error()).toBeTruthy();
    }));
  });

  // =========================================================================
  // ObjectifLongTerme CRUD
  // =========================================================================

  const mockOlt: ObjectifLongTerme = {
    id_olt: 1,
    id_enjeu: 1,
    libelle: 'OLT test',
    description: 'Description OLT',
    niveaux_exigence: [],
    nb_niveaux_exigence: 0,
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
    createur_nom: 'Admin',
  };

  describe('createObjectifLongTerme', () => {
    it('should call POST /api/plans/objectifs-long-terme/', fakeAsync(() => {
      const payload: ObjectifLongTermeCreatePayload = { id_enjeu: 1, libelle: 'Nouvel OLT', description: 'Desc' };
      service.createObjectifLongTerme(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/objectifs-long-terme/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockOlt);
      tick();
    }));

    it('should return the created OLT', fakeAsync(() => {
      const payload: ObjectifLongTermeCreatePayload = { id_enjeu: 1, libelle: 'Nouvel OLT' };
      let result: ObjectifLongTerme | undefined;
      service.createObjectifLongTerme(payload).subscribe(r => result = r);
      const req = httpMock.expectOne('/api/plans/objectifs-long-terme/');
      req.flush(mockOlt);
      tick();
      expect(result).toEqual(mockOlt);
    }));
  });

  describe('updateObjectifLongTerme', () => {
    it('should call PATCH /api/plans/objectifs-long-terme/{id}/', fakeAsync(() => {
      service.updateObjectifLongTerme(1, { libelle: 'Updated OLT' }).subscribe();
      const req = httpMock.expectOne('/api/plans/objectifs-long-terme/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ libelle: 'Updated OLT' });
      req.flush(mockOlt);
      tick();
    }));

    it('should send only provided fields', fakeAsync(() => {
      service.updateObjectifLongTerme(1, { description: 'New desc' }).subscribe();
      const req = httpMock.expectOne('/api/plans/objectifs-long-terme/1/');
      expect(req.request.body).toEqual({ description: 'New desc' });
      req.flush(mockOlt);
      tick();
    }));
  });

  describe('deleteObjectifLongTerme', () => {
    it('should call DELETE /api/plans/objectifs-long-terme/{id}/', fakeAsync(() => {
      service.deleteObjectifLongTerme(1).subscribe();
      const req = httpMock.expectOne('/api/plans/objectifs-long-terme/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });

  // =========================================================================
  // NiveauExigence CRUD
  // =========================================================================

  const mockNe: NiveauExigence = {
    id_ne: 1,
    id_olt: 1,
    libelle: 'NE test',
    description: 'Description NE',
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
    createur_nom: 'Admin',
  };

  describe('createNiveauExigence', () => {
    it('should call POST /api/plans/niveaux-exigence/', fakeAsync(() => {
      const payload = { id_olt: 1, libelle: 'Nouveau NE', description: 'Desc' };
      service.createNiveauExigence(payload).subscribe();
      const req = httpMock.expectOne('/api/plans/niveaux-exigence/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockNe);
      tick();
    }));

    it('should return the created NE', fakeAsync(() => {
      const payload = { id_olt: 1, libelle: 'Nouveau NE' };
      let result: NiveauExigence | undefined;
      service.createNiveauExigence(payload).subscribe(r => result = r);
      const req = httpMock.expectOne('/api/plans/niveaux-exigence/');
      req.flush(mockNe);
      tick();
      expect(result).toEqual(mockNe);
    }));
  });

  describe('updateNiveauExigence', () => {
    it('should call PATCH /api/plans/niveaux-exigence/{id}/', fakeAsync(() => {
      service.updateNiveauExigence(1, { libelle: 'Updated NE' }).subscribe();
      const req = httpMock.expectOne('/api/plans/niveaux-exigence/1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ libelle: 'Updated NE' });
      req.flush(mockNe);
      tick();
    }));

    it('should send only provided fields', fakeAsync(() => {
      service.updateNiveauExigence(1, { description: 'New desc' }).subscribe();
      const req = httpMock.expectOne('/api/plans/niveaux-exigence/1/');
      expect(req.request.body).toEqual({ description: 'New desc' });
      req.flush(mockNe);
      tick();
    }));
  });

  describe('deleteNiveauExigence', () => {
    it('should call DELETE /api/plans/niveaux-exigence/{id}/', fakeAsync(() => {
      service.deleteNiveauExigence(1).subscribe();
      const req = httpMock.expectOne('/api/plans/niveaux-exigence/1/');
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();
    }));
  });
});
