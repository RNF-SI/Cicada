import { planEndYear } from './plan-periode';

describe('planEndYear (#672)', () => {
  it('utilise l\'échéance effective renvoyée par l\'API', () => {
    expect(planEndYear({ annee_fin: 2025, annee_fin_effective: 2027, annees_extension: 2 })).toBe(2027);
  });
  it('la recalcule si l\'API ne la fournit pas', () => {
    expect(planEndYear({ annee_fin: 2025, annees_extension: 1 })).toBe(2026);
  });
  it('plan non prolongé : annee_fin', () => {
    expect(planEndYear({ annee_fin: 2025, annees_extension: 0 })).toBe(2025);
    expect(planEndYear({ annee_fin: 2025 })).toBe(2025);
  });
  it('sans année de fin : null', () => {
    expect(planEndYear({ annee_fin: null })).toBeNull();
    expect(planEndYear({})).toBeNull();
  });
});
