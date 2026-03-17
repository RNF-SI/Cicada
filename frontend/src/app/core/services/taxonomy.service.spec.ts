import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { TaxonomyService, TaxrefAutocomplete, TaxrefDetail, TaxrefVersion } from './taxonomy.service';

describe('TaxonomyService', () => {
  let service: TaxonomyService;
  let httpMock: HttpTestingController;

  const mockAutocompleteResults: TaxrefAutocomplete[] = [
    {
      cd_nom: 60577,
      cd_ref: 60577,
      search_name: 'Canis lupus Loup gris',
      nom_valide: 'Canis lupus Linnaeus, 1758',
      nom_vern: 'Loup gris',
      lb_nom: 'Canis lupus',
      regne: 'Animalia',
      group2_inpn: 'Mammiferes',
      id_rang: 'ES',
    },
  ];

  const mockDetail: TaxrefDetail = {
    cd_nom: 60577,
    cd_ref: 60577,
    id_statut: 'P',
    id_habitat: 3,
    id_rang: 'ES',
    regne: 'Animalia',
    phylum: 'Chordata',
    classe: 'Mammalia',
    ordre: 'Carnivora',
    famille: 'Canidae',
    sous_famille: '',
    tribu: '',
    cd_taxsup: 0,
    cd_sup: 0,
    lb_nom: 'Canis lupus',
    lb_auteur: 'Linnaeus, 1758',
    nom_complet: 'Canis lupus Linnaeus, 1758',
    nom_complet_html: '<i>Canis lupus</i> Linnaeus, 1758',
    nom_valide: 'Canis lupus Linnaeus, 1758',
    nom_vern: 'Loup gris',
    nom_vern_eng: 'Grey Wolf',
    group1_inpn: 'Mammifères',
    group2_inpn: 'Mammiferes',
    group3_inpn: '',
    url: 'https://inpn.mnhn.fr/espece/cd_nom/60577',
  };

  const mockVersion: TaxrefVersion = {
    referential_name: 'taxref',
    version: '18',
    update_date: '2025-01-15T10:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [TaxonomyService],
    });

    service = TestBed.inject(TaxonomyService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });
  });

  describe('getVersion', () => {
    it('should fetch the current TaxRef version', fakeAsync(() => {
      let result: TaxrefVersion | undefined;
      service.getVersion().subscribe(v => { result = v; });

      const req = httpMock.expectOne('/api/taxref/version/');
      expect(req.request.method).toBe('GET');
      req.flush(mockVersion);
      tick();

      expect(result).toEqual(mockVersion);
      expect(result!.version).toBe('18');
    }));
  });

  describe('getDetail', () => {
    it('should fetch taxon detail by cd_nom', fakeAsync(() => {
      let result: TaxrefDetail | undefined;
      service.getDetail(60577).subscribe(t => { result = t; });

      const req = httpMock.expectOne('/api/taxref/60577/');
      expect(req.request.method).toBe('GET');
      req.flush(mockDetail);
      tick();

      expect(result).toEqual(mockDetail);
      expect(result!.lb_nom).toBe('Canis lupus');
    }));
  });

  describe('autocomplete', () => {
    it('should return empty array for search < 2 chars', fakeAsync(() => {
      let result: TaxrefAutocomplete[] | undefined;
      service.autocomplete('a').subscribe(r => { result = r; });
      tick();

      // No HTTP request should be made
      httpMock.expectNone('/api/taxref/autocomplete/');
      expect(result).toEqual([]);
    }));

    it('should search with 2+ characters', fakeAsync(() => {
      let result: TaxrefAutocomplete[] | undefined;
      service.autocomplete('Can').subscribe(r => { result = r; });

      const req = httpMock.expectOne(
        (r) => r.url === '/api/taxref/autocomplete/' && r.params.get('search') === 'Can'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockAutocompleteResults);
      tick();

      expect(result).toEqual(mockAutocompleteResults);
      expect(result!.length).toBe(1);
    }));

    it('should pass optional filters', fakeAsync(() => {
      service.autocomplete('Can', { regne: 'Animalia', limit: 10 }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === '/api/taxref/autocomplete/'
          && r.params.get('search') === 'Can'
          && r.params.get('regne') === 'Animalia'
          && r.params.get('limit') === '10'
      );
      req.flush(mockAutocompleteResults);
    }));

    it('should cache results', fakeAsync(() => {
      // First call
      service.autocomplete('Canis').subscribe();
      const req1 = httpMock.expectOne(
        (r) => r.url === '/api/taxref/autocomplete/' && r.params.get('search') === 'Canis'
      );
      req1.flush(mockAutocompleteResults);
      tick();

      // Second call with same search — should use cache
      let cachedResult: TaxrefAutocomplete[] | undefined;
      service.autocomplete('Canis').subscribe(r => { cachedResult = r; });
      tick();

      // No new HTTP request
      httpMock.expectNone('/api/taxref/autocomplete/');
      expect(cachedResult).toEqual(mockAutocompleteResults);
    }));

    it('should not cache results for different filters', fakeAsync(() => {
      service.autocomplete('Can', { regne: 'Animalia' }).subscribe();
      httpMock.expectOne(
        (r) => r.params.get('regne') === 'Animalia'
      ).flush(mockAutocompleteResults);
      tick();

      service.autocomplete('Can', { regne: 'Plantae' }).subscribe();
      const req2 = httpMock.expectOne(
        (r) => r.params.get('regne') === 'Plantae'
      );
      req2.flush([]);
    }));
  });

  describe('list', () => {
    it('should fetch paginated list', fakeAsync(() => {
      const mockResponse = { count: 1, results: [mockAutocompleteResults[0]] };

      let result: any;
      service.list({ page: 1, regne: 'Animalia' }).subscribe(r => { result = r; });

      const req = httpMock.expectOne(
        (r) => r.url === '/api/taxref/'
          && r.params.get('page') === '1'
          && r.params.get('regne') === 'Animalia'
      );
      req.flush(mockResponse);
      tick();

      expect(result.count).toBe(1);
    }));
  });

  describe('searchField', () => {
    it('should search by field name', fakeAsync(() => {
      service.searchField('nom_vern', 'Loup').subscribe();

      const req = httpMock.expectOne(
        (r) => r.url.includes('/api/taxref/search/nom_vern/Loup/')
      );
      expect(req.request.method).toBe('GET');
      req.flush([mockAutocompleteResults[0]]);
    }));
  });
});
