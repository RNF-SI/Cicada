import { campanuleProtocoleLabel } from './campanule.model';

describe('campanuleProtocoleLabel (#564)', () => {
  it('uses lb_protocole_court when present', () => {
    expect(
      campanuleProtocoleLabel({ lb_protocole_court: 'EPOC (2018)', lb_protocole_complet: 'EPOC complet' }),
    ).toBe('EPOC (2018)');
  });

  it('falls back to lb_protocole_complet when court is null', () => {
    expect(
      campanuleProtocoleLabel({
        lb_protocole_court: null as unknown as string,
        lb_protocole_complet: 'Oiseaux des jardins',
      }),
    ).toBe('Oiseaux des jardins');
  });

  it('falls back to lb_protocole_complet when court is empty/whitespace', () => {
    expect(
      campanuleProtocoleLabel({ lb_protocole_court: '   ', lb_protocole_complet: 'Milan royal' }),
    ).toBe('Milan royal');
  });

  it('returns empty string when nothing is set', () => {
    expect(campanuleProtocoleLabel(null)).toBe('');
    expect(campanuleProtocoleLabel(undefined)).toBe('');
    expect(campanuleProtocoleLabel({ lb_protocole_court: '', lb_protocole_complet: '' })).toBe('');
  });
});
