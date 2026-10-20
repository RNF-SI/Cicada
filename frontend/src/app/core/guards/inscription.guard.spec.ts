import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, firstValueFrom, isObservable, of } from 'rxjs';
import { signal } from '@angular/core';
import { SettingsService, SiteConfiguration } from '../services/settings.service';
import { REDIRECTION_EXTERNE, inscriptionLocaleGuard } from './inscription.guard';

/**
 * #724 — Inscription confiée à une plateforme externe : l'adresse
 * /auth/register y renvoie, plutôt que d'ouvrir le formulaire local.
 */
describe('inscriptionLocaleGuard (#724)', () => {
  const URL = 'https://inscription.example.org/cicada';
  let redirection: jest.Mock;

  async function lancer(config: Partial<SiteConfiguration> | null, charge: Partial<SiteConfiguration> = {}) {
    redirection = jest.fn();
    TestBed.configureTestingModule({
      providers: [
        { provide: REDIRECTION_EXTERNE, useValue: redirection },
        {
          provide: SettingsService,
          useValue: {
            config: signal(config),
            loadSettings: () => of(charge as SiteConfiguration),
          },
        },
      ],
    });
    const resultat = TestBed.runInInjectionContext(() =>
      inscriptionLocaleGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot));
    return isObservable(resultat) ? firstValueFrom(resultat as Observable<boolean>) : resultat;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('laisse ouvrir le formulaire local sans URL externe', async () => {
    expect(await lancer({ inscription_url_externe: '' })).toBe(true);
    expect(redirection).not.toHaveBeenCalled();
  });

  it('renvoie vers la plateforme externe quand elle est réglée', async () => {
    expect(await lancer({ inscription_url_externe: URL })).toBe(false);
    expect(redirection).toHaveBeenCalledWith(URL);
  });

  it('charge les paramètres s\'ils ne le sont pas encore (accès direct à l\'adresse)', async () => {
    expect(await lancer(null, { inscription_url_externe: URL })).toBe(false);
    expect(redirection).toHaveBeenCalledWith(URL);
  });
});
