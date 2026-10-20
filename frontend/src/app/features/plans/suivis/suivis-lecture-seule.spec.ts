/**
 * #740 — Un utilisateur lié au plan (membre déclaré, rattaché à un site du
 * plan) consulte tout le volet Suivis en lecture seule. Les exports restent
 * réservés aux référents et gestionnaires (`peut_exporter`, calculé par l'API).
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const read = (f: string) => readFileSync(join(__dirname, f), 'utf8');

describe('Volet Suivis — lecture seule (#740)', () => {
  const pages = {
    'tableau de bord': ['plan-tableau-de-bord.component.html', 'plan-tableau-de-bord.component.ts'],
    'suivi des actions': ['plan-suivi-actions.component.html', 'plan-suivi-actions.component.ts'],
    'bilan': ['plan-bilan.component.html', 'plan-bilan.component.ts'],
  };

  for (const [nom, [html, ts]] of Object.entries(pages)) {
    it(`${nom} : exports masqués sans droit d'export`, () => {
      const tpl = read(html);
      // chaque déclencheur d'export est sous `@if (peutExporter())`
      const exports = [...tpl.matchAll(/exportTable\(\)|data-testid="bilan-export"|matMenuTriggerFor\]="genMenu"/g)];
      expect(exports.length).toBeGreaterThan(0);
      for (const m of exports) {
        const avant = tpl.slice(0, m.index);
        expect(avant).toContain('@if (peutExporter())');
      }
      expect(read(ts)).toContain('this.peutExporter.set(plan.peut_exporter === true)');
    });
  }

  it('tableau de bord et suivi des actions annoncent la consultation seule', () => {
    for (const html of ['plan-tableau-de-bord.component.html', 'plan-suivi-actions.component.html']) {
      expect(read(html)).toContain('plans.suivis.readOnlyBanner.title');
    }
  });
});
