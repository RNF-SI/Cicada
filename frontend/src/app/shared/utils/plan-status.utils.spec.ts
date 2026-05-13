import { getPlanStatusKey } from './plan-status.utils';

describe('getPlanStatusKey (#281)', () => {
  it('renvoie la clé brute pour les statuts non `etendu`', () => {
    expect(getPlanStatusKey('draft', 'RNN')).toBe('plans.status.draft');
    expect(getPlanStatusKey('valide', 'PNR')).toBe('plans.status.valide');
    expect(getPlanStatusKey('archive', null)).toBe('plans.status.archive');
  });

  it('contextualise `etendu` pour les réserves naturelles (RNN/RNR)', () => {
    expect(getPlanStatusKey('etendu', 'RNN')).toBe('plans.status.etendu_rnn');
    expect(getPlanStatusKey('etendu', 'RNR')).toBe('plans.status.etendu_rnn');
  });

  it('contextualise `etendu` pour les PNR', () => {
    expect(getPlanStatusKey('etendu', 'PNR')).toBe('plans.status.etendu_pnr');
  });

  it('contextualise `etendu` pour les ENS / ENSD', () => {
    expect(getPlanStatusKey('etendu', 'ENS')).toBe('plans.status.etendu_ens');
    expect(getPlanStatusKey('etendu', 'ENSD')).toBe('plans.status.etendu_ens');
  });

  it('insensible à la casse', () => {
    expect(getPlanStatusKey('etendu', 'rnn')).toBe('plans.status.etendu_rnn');
    expect(getPlanStatusKey('etendu', 'pnr')).toBe('plans.status.etendu_pnr');
  });

  it('retombe sur le libellé générique `etendu` quand le type est inconnu ou absent', () => {
    expect(getPlanStatusKey('etendu', null)).toBe('plans.status.etendu');
    expect(getPlanStatusKey('etendu', undefined)).toBe('plans.status.etendu');
    expect(getPlanStatusKey('etendu', 'AUTRE')).toBe('plans.status.etendu');
    expect(getPlanStatusKey('etendu', '')).toBe('plans.status.etendu');
  });
});
