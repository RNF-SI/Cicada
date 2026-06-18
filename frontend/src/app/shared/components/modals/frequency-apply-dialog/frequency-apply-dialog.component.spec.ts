/**
 * Tests unitaires de la logique de calcul des occurrences (#374) de la modale
 * « Appliquer aux années ». On instancie le composant à la main pour tester
 * recompute() / yearStep / occurrencesParAn sans monter le dialog Material.
 */
import { FrequencyApplyDialogComponent, FrequencyApplyDialogData } from './frequency-apply-dialog.component';

function make(data: Partial<FrequencyApplyDialogData>): FrequencyApplyDialogComponent {
  const c = Object.create(FrequencyApplyDialogComponent.prototype) as FrequencyApplyDialogComponent;
  (c as any).data = {
    years: data.years ?? [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034],
    monthLabels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'],
    frequenceNombre: data.frequenceNombre ?? 1,
    frequenceUnite: data.frequenceUnite ?? 'an',
    defaultStartYearIndex: data.defaultStartYearIndex ?? 0,
    defaultStartMonth: data.defaultStartMonth ?? 1,
  };
  return c;
}

const markedYears = (c: FrequencyApplyDialogComponent) =>
  c.data.years.filter((_, i) => c.yearFlags[i]);
const markedMonths = (c: FrequencyApplyDialogComponent) =>
  c.monthFlags.map((v, i) => (v ? i + 1 : 0)).filter(Boolean);

describe('FrequencyApplyDialogComponent — calcul des occurrences (#374)', () => {
  it('5 ans depuis 2026 → 2026 et 2031', () => {
    const c = make({ frequenceUnite: '5_ans', frequenceNombre: 1 });
    c.startYearIndex = 1; // 2026
    c.startMonth = 1;
    c.recompute();
    expect(markedYears(c)).toEqual([2026, 2031]);
  });

  it('annuel (tous les ans) depuis 2027 → 2027..2034', () => {
    const c = make({ frequenceUnite: 'an', frequenceNombre: 1 });
    c.startYearIndex = 2; // 2027
    c.startMonth = 1;
    c.recompute();
    expect(markedYears(c)).toEqual([2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]);
  });

  it('2 fois par an depuis janvier → 2 mois espacés de 6 (Jan, Juil)', () => {
    const c = make({ frequenceUnite: 'an', frequenceNombre: 2 });
    c.startYearIndex = 0;
    c.startMonth = 1;
    c.recompute();
    expect(markedMonths(c)).toEqual([1, 7]);
  });

  it('trimestriel depuis mars → Mar, Juin, Sep, Déc', () => {
    const c = make({ frequenceUnite: 'trimestre', frequenceNombre: 1 });
    c.startYearIndex = 0;
    c.startMonth = 3;
    c.recompute();
    expect(markedMonths(c)).toEqual([3, 6, 9, 12]);
  });

  it('fréquence pluriannuelle → un seul mois récurrent (le mois de départ)', () => {
    const c = make({ frequenceUnite: '5_ans', frequenceNombre: 1 });
    c.startYearIndex = 0;
    c.startMonth = 4;
    c.recompute();
    expect(markedMonths(c)).toEqual([4]);
  });

  it('confirm() renvoie monthFlags indexé 1..12', () => {
    const c = make({ frequenceUnite: 'an', frequenceNombre: 1 });
    c.startYearIndex = 0;
    c.startMonth = 5;
    c.recompute();
    let captured: any = null;
    (c as any).dialogRef = { close: (r: any) => (captured = r) };
    c.confirm();
    expect(captured.monthFlags['5']).toBe(true);
    expect(captured.monthFlags['1']).toBe(false);
    expect(captured.yearFlags.length).toBe(10);
  });
});
