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
});
