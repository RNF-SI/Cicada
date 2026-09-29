import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { MatomoService } from './matomo.service';
import { SettingsService, SiteConfiguration } from './settings.service';

@Component({ template: '' })
class DummyComponent {}

describe('MatomoService (#670)', () => {
  const config = signal<SiteConfiguration | null>(null);
  let service: MatomoService;
  let router: Router;

  const activeConfig = (overrides: Partial<SiteConfiguration> = {}) => ({
    matomo_enabled: true,
    matomo_url: 'https://matomo.example.org/',
    matomo_site_id: '12',
    ...overrides,
  }) as SiteConfiguration;

  const commands = () => window._paq ?? [];
  const matomoScripts = () =>
    Array.from(document.head.querySelectorAll('script')).filter(s => s.src.includes('matomo.js'));

  beforeEach(() => {
    delete window._paq;
    matomoScripts().forEach(s => s.remove());
    config.set(null);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'a', component: DummyComponent },
          { path: 'b', component: DummyComponent },
        ]),
        { provide: SettingsService, useValue: { config } },
      ],
    });
    service = TestBed.inject(MatomoService);
    router = TestBed.inject(Router);
  });

  it('ne charge rien et n\'envoie rien tant que Matomo n\'est pas activé', async () => {
    config.set(activeConfig({ matomo_enabled: false }));
    TestBed.tick();
    await router.navigateByUrl('/a');
    service.trackEvent('Exports', 'export-plan-docx');

    expect(commands()).toEqual([]);
    expect(matomoScripts()).toHaveLength(0);
  });

  it('ne s\'active pas sans identifiant de site', () => {
    config.set(activeConfig({ matomo_site_id: '' }));
    TestBed.tick();

    expect(service.isActive()).toBe(false);
    expect(matomoScripts()).toHaveLength(0);
  });

  it('charge le traceur sans cookie, sur le serveur de l\'instance', () => {
    config.set(activeConfig());
    TestBed.tick();

    expect(commands()[0]).toEqual(['disableCookies']);
    expect(commands()).toContainEqual(['setTrackerUrl', 'https://matomo.example.org/matomo.php']);
    expect(commands()).toContainEqual(['setSiteId', '12']);
    expect(matomoScripts().map(s => s.src)).toEqual(['https://matomo.example.org/matomo.js']);
    expect(commands().some(c => c[0] === 'setUserId')).toBe(false);
  });

  it('envoie une page vue à chaque navigation', async () => {
    config.set(activeConfig());
    TestBed.tick();
    await router.navigateByUrl('/a');
    await router.navigateByUrl('/b');

    const pageViews = commands().filter(c => c[0] === 'trackPageView');
    const urls = commands().filter(c => c[0] === 'setCustomUrl').map(c => c[1]);
    expect(pageViews).toHaveLength(2);
    expect(urls).toEqual([`${location.origin}/a`, `${location.origin}/b`]);
    expect(commands()).toContainEqual(['setReferrerUrl', `${location.origin}/a`]);
  });

  it('compte la page courante quand les réglages arrivent après la navigation', async () => {
    await router.navigateByUrl('/a');
    config.set(activeConfig());
    TestBed.tick();

    expect(commands().filter(c => c[0] === 'trackPageView')).toHaveLength(1);
  });

  it('ne reconfigure pas le traceur quand les réglages sont rechargés à l\'identique', () => {
    config.set(activeConfig());
    TestBed.tick();
    config.set(activeConfig());
    TestBed.tick();

    expect(commands().filter(c => c[0] === 'setSiteId')).toHaveLength(1);
    expect(matomoScripts()).toHaveLength(1);
  });

  it('envoie les événements métier une fois actif', () => {
    config.set(activeConfig());
    TestBed.tick();
    service.trackEvent('Plans', 'Changement de statut', 'valide');
    service.trackSiteSearch('loutre', 'Contenus', 3);

    expect(commands()).toContainEqual(['trackEvent', 'Plans', 'Changement de statut', 'valide']);
    expect(commands()).toContainEqual(['trackSiteSearch', 'loutre', 'Contenus', 3]);
  });
});
