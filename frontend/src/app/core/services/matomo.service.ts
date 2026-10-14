import { DOCUMENT, Injectable, effect, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { SettingsService, SiteConfiguration } from './settings.service';

type MatomoCommand = unknown[];

declare global {
  interface Window {
    _paq?: MatomoCommand[];
  }
}

/**
 * #670 — Mesure d'audience Matomo.
 *
 * Le serveur et l'identifiant de site sont des paramètres d'instance, réglés
 * par un super admin dans /administration/parametres. Tant qu'ils ne sont pas
 * renseignés et activés, aucun script n'est chargé et rien n'est envoyé.
 *
 * - **Sans cookie** (`disableCookies`) : exemption de consentement CNIL, pas
 *   de bandeau à afficher.
 * - **Aucun identifiant utilisateur** : `setUserId` n'est jamais appelé.
 * - **SPA** : un chargement de page ne suffit pas, chaque fin de navigation
 *   Angular envoie une page vue.
 */
@Injectable({ providedIn: 'root' })
export class MatomoService {
  private readonly settings = inject(SettingsService);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);

  /** Serveur + site pour lesquels le traceur est configuré (null = inactif). */
  private configuredFor: string | null = null;
  private scriptLoaded = false;
  private previousUrl: string | null = null;

  constructor() {
    effect(() => this.configure(this.settings.config()));
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(event => this.trackPageView(event.urlAfterRedirects));
  }

  /** La mesure est-elle activée et complète sur cette instance ? */
  isActive(): boolean {
    const config = this.settings.config();
    return !!(config?.matomo_enabled && config.matomo_url && config.matomo_site_id);
  }

  /** Événement métier (export, validation, création de plan…). */
  trackEvent(category: string, action: string, name?: string): void {
    if (!this.isReady()) return;
    this.push(name ? ['trackEvent', category, action, name] : ['trackEvent', category, action]);
  }

  /** Recherche interne (exploration des données). */
  trackSiteSearch(keyword: string, category: string, count?: number): void {
    if (!this.isReady()) return;
    this.push(['trackSiteSearch', keyword, category, count ?? false]);
  }

  private isReady(): boolean {
    return this.isActive() && this.configuredFor !== null;
  }

  private configure(config: SiteConfiguration | null): void {
    if (!this.isActive() || !config) return;
    const url = config.matomo_url.replace(/\/+$/, '');
    const key = `${url}|${config.matomo_site_id}`;
    if (this.configuredFor === key) return;

    // Avant toute page vue : sans cette commande, matomo.js pose ses cookies.
    this.push(['disableCookies']);
    this.push(['setTrackerUrl', `${url}/matomo.php`]);
    this.push(['setSiteId', config.matomo_site_id]);
    this.configuredFor = key;

    if (!this.scriptLoaded) {
      const script = this.document.createElement('script');
      script.async = true;
      script.src = `${url}/matomo.js`;
      this.document.head.appendChild(script);
      this.scriptLoaded = true;
    }

    // La navigation initiale a pu se terminer avant le chargement des réglages.
    if (this.router.navigated) {
      this.trackPageView(this.router.url);
    }
  }

  private trackPageView(url: string): void {
    if (!this.isReady() || url === this.previousUrl) return;
    const origin = this.document.location?.origin ?? '';
    if (this.previousUrl) {
      this.push(['setReferrerUrl', origin + this.previousUrl]);
    }
    this.push(['setCustomUrl', origin + url]);
    this.push(['setDocumentTitle', this.document.title]);
    this.push(['trackPageView']);
    this.previousUrl = url;
  }

  private push(command: MatomoCommand): void {
    const win = this.document.defaultView;
    if (!win) return;
    win._paq = win._paq || [];
    win._paq.push(command);
  }
}
