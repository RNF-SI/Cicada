import { InjectionToken, inject } from '@angular/core';
import { CanActivateFn } from '@angular/router';
import { map, of } from 'rxjs';
import { SettingsService } from '../services/settings.service';

/** Sortie de l'application vers une adresse externe (remplaçable en test). */
export const REDIRECTION_EXTERNE = new InjectionToken<(url: string) => void>('REDIRECTION_EXTERNE', {
  providedIn: 'root',
  factory: () => (url: string) => window.location.assign(url),
});

/**
 * #724 — Quand l'inscription est confiée à une plateforme externe, l'adresse
 * /auth/register y renvoie : une seule porte d'entrée. Les paramètres sont
 * chargés s'ils ne le sont pas encore (lien ouvert directement).
 */
export const inscriptionLocaleGuard: CanActivateFn = () => {
  const settings = inject(SettingsService);
  const rediriger = inject(REDIRECTION_EXTERNE);
  const config$ = settings.config() ? of(settings.config()) : settings.loadSettings();
  return config$.pipe(
    map(config => {
      const url = config?.inscription_url_externe;
      if (!url) return true;
      rediriger(url);
      return false;
    }),
  );
};
