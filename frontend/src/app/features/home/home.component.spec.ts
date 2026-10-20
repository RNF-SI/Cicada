import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA, signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { firstValueFrom, of } from 'rxjs';

import { HomeComponent } from './home.component';
import { AuthService } from '../../core/services/auth.service';
import { PublicStatsService } from '../../core/services/public-stats.service';
import { ModuleService } from '../../core/services/module.service';
import { SettingsService, SiteConfiguration } from '../../core/services/settings.service';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { EuFundingNoticeComponent } from '../../shared/components/eu-funding-notice/eu-funding-notice.component';
import { PartnersBandComponent } from '../../shared/components/partners-band/partners-band.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation() {
    return of({
      'home.guest.title': 'Titre CICADA par défaut',
      'home.guest.subtitle': 'Sous-titre CICADA par défaut',
    });
  }
}

/** #710 — Accueil visiteur : textes et logo de la structure personnalisables. */
describe('HomeComponent — accueil visiteur (#710)', () => {
  let fixture: ComponentFixture<HomeComponent>;
  const config = signal<Partial<SiteConfiguration> | null>(null);

  const setup = async (partial: Partial<SiteConfiguration>) => {
    config.set(partial);
    await TestBed.configureTestingModule({
      imports: [
        HomeComponent,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr',
        }),
      ],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            isAuthenticated: signal(false),
            currentUser: signal(null),
            getLoginMode: () => of({ mode: 'local' }),
          },
        },
        {
          provide: PublicStatsService,
          useValue: { stats: signal(null), isLoading: signal(false), loadStats: () => of(null) },
        },
        {
          provide: ModuleService,
          useValue: {
            accessibleModules: signal([]),
            isLoading: signal(false),
            loadError: signal(null),
            getMyAccessibleModules: () => of([]),
          },
        },
        {
          provide: SettingsService,
          useValue: {
            config,
            loadSettings: () => of(config()),
            getHomepageImageUrl: () => 'assets/images/homepage-default.jpg',
            getStructureLogoUrl: () => config()?.structure_logo_url || null,
            inscriptionUrlExterne: () => config()?.inscription_url_externe || null,
          },
        },
      ],
    })
      .overrideComponent(HomeComponent, {
        remove: { imports: [HeaderComponent, EuFundingNoticeComponent, PartnersBandComponent] },
        add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] },
      })
      .compileComponents();

    await firstValueFrom(TestBed.inject(TranslateService).use('fr'));
    fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
  };

  const text = (testId: string) =>
    (fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null)?.textContent?.trim();

  afterEach(() => TestBed.resetTestingModule());

  // #724 — « Créer un compte » mène à la plateforme externe quand elle est réglée.
  it('« Créer un compte » mène au formulaire local par défaut', async () => {
    await setup({ inscription_url_externe: '' });
    const lien = fixture.nativeElement.querySelector('[data-testid="home-create-account"]') as HTMLAnchorElement;
    expect(lien.getAttribute('href')).toBe('/auth/register');
  });

  it('« Créer un compte » ouvre la plateforme externe dans un nouvel onglet', async () => {
    await setup({ inscription_url_externe: 'https://inscription.example.org/cicada' });
    const lien = fixture.nativeElement.querySelector('[data-testid="home-create-account"]') as HTMLAnchorElement;
    expect(lien.getAttribute('href')).toBe('https://inscription.example.org/cicada');
    expect(lien.getAttribute('target')).toBe('_blank');
    expect(lien.getAttribute('rel')).toContain('noopener');
  });

  it('affiche les textes par défaut quand l\'instance ne les a pas personnalisés', async () => {
    await setup({ accueil_titre: '', accueil_sous_titre: '' });

    expect(text('home-guest-title')).toBe('Titre CICADA par défaut');
    expect(text('home-guest-subtitle')).toBe('Sous-titre CICADA par défaut');
  });

  it('affiche les textes personnalisés de l\'instance', async () => {
    await setup({ accueil_titre: 'Portail des réserves', accueil_sous_titre: 'Bienvenue sur notre instance' });

    expect(text('home-guest-title')).toBe('Portail des réserves');
    expect(text('home-guest-subtitle')).toBe('Bienvenue sur notre instance');
  });

  it('place le logo de la structure avant le titre', async () => {
    await setup({ structure_logo_url: '/api/settings/structure-logo/?v=logo.png' });

    const logo = fixture.nativeElement.querySelector('[data-testid="home-structure-logo"]') as HTMLImageElement;
    const title = fixture.nativeElement.querySelector('[data-testid="home-guest-title"]') as HTMLElement;
    expect(logo.getAttribute('src')).toBe('/api/settings/structure-logo/?v=logo.png');
    expect(logo.parentElement).toBe(title.parentElement);
    expect(logo.nextElementSibling).toBe(title);
  });

  it('n\'affiche pas de logo de structure quand il n\'y en a pas', async () => {
    await setup({ structure_logo_url: null });

    expect(fixture.nativeElement.querySelector('[data-testid="home-structure-logo"]')).toBeNull();
  });
});
