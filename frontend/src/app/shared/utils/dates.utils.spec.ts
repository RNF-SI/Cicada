/**
 * #862 — dates sans heure (avis CSRPN, comité, arrêté, document, mesure).
 *
 * Le sélecteur de date rend minuit HEURE LOCALE ; `toISOString()` convertit en
 * UTC : en métropole, le 15/03 partait « 2026-03-14 ». À l'inverse,
 * `new Date('2026-03-14')` est minuit UTC : affiché le 13/03 en Guyane.
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join } from 'path';

import { anneeDe, dateDepuisISO, dateLocaleISO } from './dates.utils';

const FUSEAUX = ['Europe/Paris', 'America/Cayenne', 'Pacific/Noumea', 'UTC'];

describe('dates sans heure (#862)', () => {
  const tzAvant = process.env['TZ'];
  afterEach(() => { process.env['TZ'] = tzAvant; });

  it.each(FUSEAUX)('la date choisie est la date envoyée (%s)', (tz) => {
    process.env['TZ'] = tz;
    const choisie = new Date(2026, 2, 15);          // ce que rend le sélecteur
    expect(dateLocaleISO(choisie)).toBe('2026-03-15');
    expect(dateLocaleISO(new Date(2026, 0, 1))).toBe('2026-01-01');
  });

  it.each(FUSEAUX)('la date relue est la date affichée (%s)', (tz) => {
    process.env['TZ'] = tz;
    const relue = dateDepuisISO('2026-03-14')!;
    expect([relue.getFullYear(), relue.getMonth() + 1, relue.getDate()]).toEqual([2026, 3, 14]);
    expect(dateLocaleISO(relue)).toBe('2026-03-14');
  });

  it.each(FUSEAUX)("une mesure du 1er janvier compte pour son année (%s)", (tz) => {
    process.env['TZ'] = tz;
    expect(anneeDe('2026-01-01')).toBe(2026);
    expect(anneeDe('2026-01-01T00:00:00Z')).toBe(2026);
  });

  it('valeurs vides ou illisibles', () => {
    expect(dateLocaleISO(null)).toBeNull();
    expect(dateLocaleISO(undefined)).toBeNull();
    expect(dateLocaleISO('2026-03-14')).toBe('2026-03-14');
    expect(dateDepuisISO(null)).toBeNull();
    expect(dateDepuisISO('')).toBeNull();
    expect(dateDepuisISO('pas une date')).toBeNull();
    expect(anneeDe(null)).toBeNull();
  });
});

describe('aucune date sans heure produite par toISOString() (#862)', () => {
  function fichiers(dossier: string): string[] {
    return readdirSync(dossier).flatMap((nom) => {
      const chemin = join(dossier, nom);
      if (statSync(chemin).isDirectory()) return fichiers(chemin);
      return /\.ts$/.test(nom) && !/\.spec\.ts$/.test(nom) ? [chemin] : [];
    });
  }

  it("ni toISOString() tronqué ni new Date() d'une date du serveur", () => {
    const racine = join(__dirname, '../..');
    const fautifs: string[] = [];
    for (const f of fichiers(racine)) {
      const lignes = readFileSync(f, 'utf8').split('\n');
      lignes.forEach((ligne, i) => {
        if (/toISOString\(\)\s*\.(slice\(0,\s*10\)|split\(['"]T['"]\))/.test(ligne)
          || /new Date\([\w?.]*\.(date_mesure|date_lancement_suivi|date_avis_csrpn|date_document|date_validation_comite|date_arrete_pref)\)/.test(ligne)) {
          fautifs.push(`${f.replace(racine, '')}:${i + 1}`);
        }
      });
    }
    expect(fautifs).toEqual([]);
  });
});
