/**
 * #703 — La liste des structures explorées était mise en cache pour toute la
 * session : après une bascule hub ↔ local faite dans les paramètres (#695),
 * sans recharger la page, l'exploration gardait celle de l'ancien mode.
 */
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ExplorationService } from './exploration.service';
import { FederationRaccordementService } from './federation-raccordement.service';

describe('ExplorationService — liste des structures (#703)', () => {
  let service: ExplorationService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ExplorationService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const repondre = (ids: string[]) =>
    http.expectOne('/api/exploration/instances/').flush({
      instances: ids.map((id) => ({ instance_id: id, libelle: id })),
    });

  it('garde la liste en cache tant que rien ne change', () => {
    service.instances().subscribe();
    repondre(['rnf', 'cen']);
    service.instances().subscribe();
    http.expectNone('/api/exploration/instances/');
  });

  it('la relit après une bascule du raccordement', () => {
    let derniere: string[] = [];
    service.instances().subscribe();
    repondre(['rnf', 'cen']);

    TestBed.inject(FederationRaccordementService)
      .configurer({ exploration_source: 'local' } as any)
      .subscribe();
    http.expectOne((r) => r.url.endsWith('configuration/')).flush({});

    service.instances().subscribe((liste) => (derniere = liste.map((i) => i.instance_id)));
    repondre(['rnf']);
    expect(derniere).toEqual(['rnf']);
  });
});
