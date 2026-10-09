import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { Component } from '@angular/core';

import { ExplorationRetourService } from './exploration-retour.service';

@Component({ template: '', standalone: true })
class VideComponent {}

describe('ExplorationRetourService', () => {
  let service: ExplorationRetourService;
  let router: Router;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideRouter([
        { path: 'exploration', component: VideComponent },
        { path: 'exploration/contenus', component: VideComponent },
        { path: 'plans/:slug', component: VideComponent },
      ])],
    });
    service = TestBed.inject(ExplorationRetourService);
    router = TestBed.inject(Router);
  });

  it('sans recherche visitée, renvoie à l’accueil de l’exploration', () => {
    expect(router.serializeUrl(service.lienRetour())).toBe('/exploration');
  });

  it('sans recherche visitée mais avec un mot cherché, relance la recherche', () => {
    expect(router.serializeUrl(service.lienRetour('humide'))).toBe('/exploration/contenus?q=humide');
  });

  it('retient la dernière recherche, filtres compris, et ignore les autres écrans', async () => {
    await router.navigateByUrl('/exploration/contenus?q=humide&onglet=actions&page=2');
    await router.navigateByUrl('/plans/cen-test:camargue');
    expect(router.serializeUrl(service.lienRetour('autre')))
      .toBe('/exploration/contenus?q=humide&onglet=actions&page=2');
  });

  it('survit à un rechargement grâce au sessionStorage', async () => {
    await router.navigateByUrl('/exploration/contenus?q=roseliere');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const neuf = TestBed.inject(ExplorationRetourService);
    expect(TestBed.inject(Router).serializeUrl(neuf.lienRetour()))
      .toBe('/exploration/contenus?q=roseliere');
  });
});
