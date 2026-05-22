import { getPlanStatusKey, getExtensionBadgeKey } from './plan-status.utils';

describe('getPlanStatusKey', () => {
  it('renvoie la clé brute pour chaque statut', () => {
    expect(getPlanStatusKey('draft')).toBe('plans.status.draft');
    expect(getPlanStatusKey('valide')).toBe('plans.status.valide');
    expect(getPlanStatusKey('modifie')).toBe('plans.status.modifie');
    expect(getPlanStatusKey('mi_parcours')).toBe('plans.status.mi_parcours');
    expect(getPlanStatusKey('archive')).toBe('plans.status.archive');
  });
});

describe('getExtensionBadgeKey (#281)', () => {
  it('contextualise le badge pour les réserves naturelles (RNN/RNR)', () => {
    expect(getExtensionBadgeKey('RNN')).toBe('plans.extension.badge_rnn');
    expect(getExtensionBadgeKey('RNR')).toBe('plans.extension.badge_rnn');
  });

  it('contextualise le badge pour les PNR', () => {
    expect(getExtensionBadgeKey('PNR')).toBe('plans.extension.badge_pnr');
  });

  it('contextualise le badge pour les ENS / ENSD', () => {
    expect(getExtensionBadgeKey('ENS')).toBe('plans.extension.badge_ens');
    expect(getExtensionBadgeKey('ENSD')).toBe('plans.extension.badge_ens');
  });

  it('insensible à la casse', () => {
    expect(getExtensionBadgeKey('rnn')).toBe('plans.extension.badge_rnn');
    expect(getExtensionBadgeKey('pnr')).toBe('plans.extension.badge_pnr');
  });

  it('retombe sur le libellé générique quand le type est inconnu ou absent', () => {
    expect(getExtensionBadgeKey(null)).toBe('plans.extension.badge');
    expect(getExtensionBadgeKey(undefined)).toBe('plans.extension.badge');
    expect(getExtensionBadgeKey('AUTRE')).toBe('plans.extension.badge');
    expect(getExtensionBadgeKey('')).toBe('plans.extension.badge');
  });
});
