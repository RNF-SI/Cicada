import { derniereActivite } from './admin-users.component';

/** #771 — colonne « Dernière activité » de la liste des utilisateurs. */
describe('derniereActivite (#771)', () => {
  it('prend la dernière activité, plus récente que la dernière connexion', () => {
    expect(derniereActivite({ derniere_activite: '2026-10-28T09:00:00Z', last_login: '2026-10-01T08:00:00Z' }))
      .toBe('2026-10-28T09:00:00Z');
  });

  it('retombe sur la dernière connexion pour un compte pas revu depuis la mise à jour', () => {
    expect(derniereActivite({ derniere_activite: null, last_login: '2026-10-01T08:00:00Z' }))
      .toBe('2026-10-01T08:00:00Z');
  });

  it('rien du tout : jamais', () => {
    expect(derniereActivite({})).toBeNull();
  });
});
