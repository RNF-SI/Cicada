import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ReorderService } from './reorder.service';

describe('ReorderService', () => {
  let service: ReorderService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), ReorderService],
    });
    service = TestBed.inject(ReorderService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('POSTs to /api/plans/<entity>/reorder/ with the payload', () => {
    service
      .reorder('enjeux', { parent_id: 7, ordered_ids: [3, 1, 2] })
      .subscribe(res => expect(res.updated).toBe(3));

    const req = httpMock.expectOne('/api/plans/enjeux/reorder/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ parent_id: 7, ordered_ids: [3, 1, 2] });
    req.flush({ updated: 3 });
  });

  it('propage parent_type pour les indicateurs', () => {
    service
      .reorder('indicateurs', { parent_id: 12, ordered_ids: [4, 5], parent_type: 'ne' })
      .subscribe();

    const req = httpMock.expectOne('/api/plans/indicateurs/reorder/');
    expect(req.request.body).toEqual({ parent_id: 12, ordered_ids: [4, 5], parent_type: 'ne' });
    req.flush({ updated: 2 });
  });

  // ---------------------------------------------------------------------------
  // #486 — aperçu du code d'action avant enregistrement
  // ---------------------------------------------------------------------------
  describe('getOperationCodePreview (#486)', () => {
    it('GET sur operation-code-preview avec les valeurs du formulaire', () => {
      service
        .getOperationCodePreview(42, {
          categorie_action_reserve_id: 8,
          metrique_id: 15,
          numero_manuel: 3,
        })
        .subscribe(res => {
          expect(res.code).toBe('CS3');
          expect(res.prefix).toBe('CS');
        });

      const req = httpMock.expectOne(
        r => r.url === '/api/plans/plans/42/operation-code-preview/',
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('categorie_action_reserve_id')).toBe('8');
      expect(req.request.params.get('metrique_id')).toBe('15');
      expect(req.request.params.get('numero_manuel')).toBe('3');
      req.flush({ code: 'CS3', prefix: 'CS' });
    });

    it('omet les paramètres null/undefined (pas de "null" en query string)', () => {
      service
        .getOperationCodePreview(7, {
          operation_id: 99,
          type_action_id: null,
          categorie_action_reserve_id: undefined,
          numero_manuel: null,
          metrique_id: null,
        })
        .subscribe();

      const req = httpMock.expectOne(
        r => r.url === '/api/plans/plans/7/operation-code-preview/',
      );
      expect(req.request.params.get('operation_id')).toBe('99');
      expect(req.request.params.has('type_action_id')).toBe(false);
      expect(req.request.params.has('categorie_action_reserve_id')).toBe(false);
      expect(req.request.params.has('numero_manuel')).toBe(false);
      expect(req.request.params.has('metrique_id')).toBe(false);
      req.flush({ code: 'AC1', prefix: 'AC' });
    });

    it('conserve numero_manuel = 0 (valeur significative, normalisée serveur)', () => {
      service.getOperationCodePreview(7, { numero_manuel: 0 }).subscribe();

      const req = httpMock.expectOne(
        r => r.url === '/api/plans/plans/7/operation-code-preview/',
      );
      expect(req.request.params.get('numero_manuel')).toBe('0');
      req.flush({ code: 'AC1', prefix: 'AC' });
    });
  });
});
