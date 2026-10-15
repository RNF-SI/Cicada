import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { updateInterceptor } from './update.interceptor';
import { SystemUpdateService } from '../services/system-update.service';

describe('updateInterceptor (#719)', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let systemUpdate: SystemUpdateService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([updateInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    systemUpdate = TestBed.inject(SystemUpdateService);
  });

  afterEach(() => backend.verify());

  /** Lance un GET, y répond par `status`, et rend ce que l'appelant a reçu. */
  function call(url: string, status: number) {
    const received = { error: undefined as unknown, completed: false };
    http.get(url).subscribe({
      error: (e) => (received.error = e),
      complete: () => (received.completed = true),
    });
    backend.expectOne(url).flush(null, { status, statusText: 'Erreur' });
    return received;
  }

  it('ignore un 502 pendant une mise à jour', () => {
    systemUpdate.markUpdateInProgress();
    const r = call('/api/notifications/', 502);
    expect(r.error).toBeUndefined();
    expect(r.completed).toBe(true);
  });

  it.each([0, 503, 504])('ignore aussi le statut %i pendant une mise à jour', (status) => {
    systemUpdate.markUpdateInProgress();
    expect(call('/api/plans/plans/', status).error).toBeUndefined();
  });

  it('laisse passer un 502 hors mise à jour', () => {
    expect(call('/api/notifications/', 502).error).toBeDefined();
  });

  it('laisse passer les vraies erreurs pendant une mise à jour', () => {
    systemUpdate.markUpdateInProgress();
    expect(call('/api/plans/plans/', 400).error).toBeDefined();
    expect(call('/api/plans/plans/', 500).error).toBeDefined();
  });

  it('laisse passer les erreurs du suivi de la mise à jour, qui en a besoin', () => {
    systemUpdate.markUpdateInProgress();
    expect(call('/api/system/version/', 502).error).toBeDefined();
  });

  it('cesse de masquer une fois la mise à jour terminée', () => {
    systemUpdate.markUpdateInProgress();
    systemUpdate.markUpdateFinished();
    expect(call('/api/notifications/', 502).error).toBeDefined();
  });
});
