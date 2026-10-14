import { HttpParams, HttpRequest } from '@angular/common/http';
import { matomoTrackingFor } from './matomo.interceptor';

describe('matomoTrackingFor (#670)', () => {
  const get = (url: string, params?: Record<string, string>) =>
    new HttpRequest('GET', url, { params: new HttpParams({ fromObject: params ?? {} }) });
  const post = (url: string, body: unknown = {}) => new HttpRequest('POST', url, body);

  it('suit les exports du plan et de la fiche action', () => {
    expect(matomoTrackingFor(get('/api/plans/plans/12/export-plan-docx/'), null))
      .toEqual({ kind: 'event', category: 'Exports', action: 'export-plan-docx' });
    expect(matomoTrackingFor(post('/api/plans/plans/12/export-tableau-de-bord-xlsx/'), null))
      .toEqual({ kind: 'event', category: 'Exports', action: 'export-tableau-de-bord-xlsx' });
    expect(matomoTrackingFor(get('/api/plans/operations/7/export-fiche-xlsx/'), null))
      .toEqual({ kind: 'event', category: 'Exports', action: 'export-fiche-xlsx' });
  });

  it('suit la création et le changement de statut d\'un plan', () => {
    expect(matomoTrackingFor(post('/api/plans/plans/'), null))
      .toEqual({ kind: 'event', category: 'Plans', action: 'Création' });
    expect(matomoTrackingFor(post('/api/plans/plans/3/change-status/', { new_status: 'valide' }), null))
      .toEqual({ kind: 'event', category: 'Plans', action: 'Changement de statut', name: 'valide' });
  });

  it('suit la création d\'une nouvelle version', () => {
    expect(matomoTrackingFor(post('/api/plans/plans/3/create-evaluation/'), null))
      .toEqual({ kind: 'event', category: 'Plans', action: 'Évaluation mi-parcours' });
    expect(matomoTrackingFor(post('/api/plans/plans/3/duplicate/'), null))
      .toEqual({ kind: 'event', category: 'Plans', action: 'Nouvelle version' });
  });

  it('suit les validations', () => {
    expect(matomoTrackingFor(post('/api/validations/4/approve/'), null))
      .toEqual({ kind: 'event', category: 'Validations', action: 'Approbation' });
    expect(matomoTrackingFor(post('/api/validations/4/reject/'), null))
      .toEqual({ kind: 'event', category: 'Validations', action: 'Rejet' });
  });

  it('suit une recherche d\'exploration avec son nombre de résultats', () => {
    const body = { pagination: { count: 42 } };
    expect(matomoTrackingFor(get('/api/exploration/contenus/', { q: 'loutre' }), body))
      .toEqual({ kind: 'search', keyword: 'loutre', category: 'Contenus', count: 42 });
  });

  it('ne compte pas une page suivante ni une recherche vide comme une recherche', () => {
    expect(matomoTrackingFor(get('/api/exploration/plans/', { q: 'loutre', page: '2' }), null)).toBeNull();
    expect(matomoTrackingFor(get('/api/exploration/plans/'), null)).toBeNull();
  });

  it('ignore les lectures et écritures ordinaires', () => {
    expect(matomoTrackingFor(get('/api/plans/plans/'), null)).toBeNull();
    expect(matomoTrackingFor(get('/api/plans/plans/3/'), null)).toBeNull();
    expect(matomoTrackingFor(post('/api/plans/enjeux/'), null)).toBeNull();
    expect(matomoTrackingFor(post('/api/plans/plans/3/assign-referent/'), null)).toBeNull();
  });
});
