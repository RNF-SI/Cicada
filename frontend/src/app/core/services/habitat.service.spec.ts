import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import {
  HabitatService,
  HabitatAutocomplete,
  HabitatDetail,
  Typologie,
  CorrespondanceHabitat,
  HabitatCorrespondanceResponse,
} from './habitat.service';

describe('HabitatService', () => {
  let service: HabitatService;
  let httpMock: HttpTestingController;

  const mockAutocomplete: HabitatAutocomplete[] = [
    {
      cd_hab: 1000,
      cd_typo: 7,
      lb_code: 'G1.1',
      search_name: 'G1.1 Forêts riveraines',
      lb_hab_fr: 'Forêts riveraines',
      lb_hab_fr_complet: 'Forêts riveraines et forêts galeries',
      lb_typo: 'EUNIS',
      niveau: 3,
    },
  ];

  const mockDetail: HabitatDetail = {
    cd_hab: 1000,
    fg_validite: 'oui',
    cd_typo: 7,
    lb_code: 'G1.1',
    lb_hab_fr: 'Forêts riveraines',
    lb_hab_fr_complet: 'Forêts riveraines et forêts galeries',
    lb_hab_en: 'Riparian forests',
    lb_auteur: '',
    niveau: 3,
    lb_description: 'Description des forêts riveraines.',
    cd_hab_sup: 500,
    path_cd_hab: '500.1000',
    cd_corresp_encours: '',
    date_creation: '2020-01-01',
    date_maj: '2024-06-15',
  };

  const mockTypologies: Typologie[] = [
    {
      cd_typo: 7,
      cd_table: 'EUNIS',
      lb_typo: 'EUNIS',
      nom_jeu_donnees: 'EUNIS Habitats',
      date_creation: '2019',
      date_mise_jour: '2024',
      auteur_jeu_donnees: 'EEA',
      territoire: 'Europe',
    },
  ];

  const mockCorrespondances: CorrespondanceHabitat[] = [
    {
      id: 1,
      cd_hab: 1000,
      cd_hab_entre: 3000,
      cd_typo_entre: 8,
      lb_code_entre: '31.2',
      lb_hab_entre: 'Landes sèches',
      niveau_entre: 2,
      type_rel: 'est_equivalent',
    },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [HabitatService],
    });

    service = TestBed.inject(HabitatService);
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

  describe('getDetail', () => {
    it('should fetch habitat detail', fakeAsync(() => {
      let result: HabitatDetail | undefined;
      service.getDetail(1000).subscribe(h => { result = h; });

      const req = httpMock.expectOne('/api/habref/1000/');
      expect(req.request.method).toBe('GET');
      req.flush(mockDetail);
      tick();

      expect(result!.cd_hab).toBe(1000);
      expect(result!.lb_hab_fr).toBe('Forêts riveraines');
    }));
  });

  describe('autocomplete', () => {
    it('should return empty for search < 2 chars', fakeAsync(() => {
      let result: HabitatAutocomplete[] | undefined;
      service.autocomplete('a').subscribe(r => { result = r; });
      tick();

      httpMock.expectNone('/api/habref/autocomplete/');
      expect(result).toEqual([]);
    }));

    it('should search with 2+ characters', fakeAsync(() => {
      let result: HabitatAutocomplete[] | undefined;
      service.autocomplete('For').subscribe(r => { result = r; });

      const req = httpMock.expectOne(
        (r) => r.url === '/api/habref/autocomplete/' && r.params.get('search') === 'For'
      );
      req.flush(mockAutocomplete);
      tick();

      expect(result!.length).toBe(1);
      expect(result![0].lb_hab_fr).toBe('Forêts riveraines');
    }));

    it('should pass cd_typo filter', fakeAsync(() => {
      service.autocomplete('For', { cdTypo: 7 }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.params.get('cd_typo') === '7'
      );
      req.flush(mockAutocomplete);
    }));

    it('should pass multiple cd_typo as comma-separated list (#469)', fakeAsync(() => {
      service.autocomplete('For', { cdTypos: [7, 8] }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.params.get('cd_typo') === '7,8'
      );
      req.flush(mockAutocomplete);
    }));

    it('should omit cd_typo when typo list is empty (#469)', fakeAsync(() => {
      service.autocomplete('For', { cdTypos: [] }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === '/api/habref/autocomplete/' && !r.params.has('cd_typo')
      );
      req.flush(mockAutocomplete);
    }));

    it('should cache results', fakeAsync(() => {
      // First call
      service.autocomplete('Forêt').subscribe();
      httpMock.expectOne(
        (r) => r.params.get('search') === 'Forêt'
      ).flush(mockAutocomplete);
      tick();

      // Second call — cached
      let cached: HabitatAutocomplete[] | undefined;
      service.autocomplete('Forêt').subscribe(r => { cached = r; });
      tick();

      httpMock.expectNone('/api/habref/autocomplete/');
      expect(cached).toEqual(mockAutocomplete);
    }));
  });

  describe('getTypologies', () => {
    it('should fetch typologies list', fakeAsync(() => {
      let result: Typologie[] | undefined;
      service.getTypologies().subscribe(t => { result = t; });

      const req = httpMock.expectOne('/api/habref/typo/');
      req.flush(mockTypologies);
      tick();

      expect(result!.length).toBe(1);
      expect(result![0].lb_typo).toBe('EUNIS');
    }));

    it('should request with_habitats when asked (#469)', fakeAsync(() => {
      service.getTypologies(true).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === '/api/habref/typo/' && r.params.get('with_habitats') === '1'
      );
      req.flush(mockTypologies);
      tick();
    }));
  });

  describe('getCorrespondances', () => {
    it('should fetch correspondances for a habitat', fakeAsync(() => {
      let result: HabitatCorrespondanceResponse | undefined;
      service.getCorrespondances(1000).subscribe(c => { result = c; });

      const req = httpMock.expectOne('/api/habref/correspondance/1000/');
      req.flush({ habitat: null, related: mockCorrespondances });
      tick();

      expect(result!.related.length).toBe(1);
      expect(result!.related[0].cd_hab_entre).toBe(3000);
    }));
  });
});
