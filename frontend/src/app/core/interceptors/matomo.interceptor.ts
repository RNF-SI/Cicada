import { HttpInterceptorFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs';
import { MatomoService } from '../services/matomo.service';

/** #670 — Ce qu'une réponse réussie envoie à Matomo. */
export type MatomoTracking =
  | { kind: 'event'; category: string; action: string; name?: string }
  | { kind: 'search'; keyword: string; category: string; count?: number };

/** Opérations sur un plan qui créent une nouvelle version (libellés Matomo). */
const PLAN_VERSION_ACTIONS: Record<string, string> = {
  'duplicate': 'Nouvelle version',
  'create-evaluation': 'Évaluation mi-parcours',
  'create-next-rang': 'Nouveau rang',
  'extend-duration': 'Prolongation',
  'start-revision': 'Révision',
};

/**
 * #670 — Traduit une requête réussie en événement Matomo (ou null).
 *
 * Centraliser ici plutôt que dans chaque composant : une même action est
 * souvent déclenchée depuis plusieurs écrans (création de plan depuis la page
 * dédiée ou la modale, exports depuis la page Exports ou la fiche action).
 */
export function matomoTrackingFor(
  req: HttpRequest<unknown>,
  responseBody: unknown,
): MatomoTracking | null {
  const path = req.url.replace(/^https?:\/\/[^/]+/, '').split('?')[0];
  const method = req.method.toUpperCase();

  let match = path.match(/^\/api\/plans\/(?:plans|operations)\/\d+\/(export-[a-z0-9-]+)\/$/);
  if (match) {
    return { kind: 'event', category: 'Exports', action: match[1] };
  }

  if (method === 'POST') {
    if (/^\/api\/plans\/plans\/$/.test(path)) {
      return { kind: 'event', category: 'Plans', action: 'Création' };
    }
    if (/^\/api\/plans\/plans\/\d+\/change-status\/$/.test(path)) {
      const status = (req.body as { new_status?: string } | null)?.new_status;
      return { kind: 'event', category: 'Plans', action: 'Changement de statut', name: status };
    }
    match = path.match(/^\/api\/plans\/plans\/\d+\/([a-z-]+)\/$/);
    if (match && PLAN_VERSION_ACTIONS[match[1]]) {
      return { kind: 'event', category: 'Plans', action: PLAN_VERSION_ACTIONS[match[1]] };
    }
    match = path.match(/^\/api\/validations\/\d+\/(approve|reject)\/$/);
    if (match) {
      return {
        kind: 'event',
        category: 'Validations',
        action: match[1] === 'approve' ? 'Approbation' : 'Rejet',
      };
    }
  }

  if (method === 'GET') {
    match = path.match(/^\/api\/exploration\/(contenus|plans)\/$/);
    const keyword = req.params.get('q')?.trim();
    // Une page suivante n'est pas une nouvelle recherche.
    if (match && keyword && !req.params.has('page')) {
      const count = (responseBody as { pagination?: { count?: number } } | null)?.pagination?.count;
      return {
        kind: 'search',
        keyword,
        category: match[1] === 'plans' ? 'Plans' : 'Contenus',
        count: typeof count === 'number' ? count : undefined,
      };
    }
  }

  return null;
}

/** #670 — Envoie à Matomo les actions métier réussies (inerte si Matomo est inactif). */
export const matomoInterceptor: HttpInterceptorFn = (req, next) => {
  const matomo = inject(MatomoService);
  return next(req).pipe(
    tap(event => {
      if (!(event instanceof HttpResponse) || !event.ok || !matomo.isActive()) return;
      const tracking = matomoTrackingFor(req, event.body);
      if (tracking?.kind === 'event') {
        matomo.trackEvent(tracking.category, tracking.action, tracking.name);
      } else if (tracking?.kind === 'search') {
        matomo.trackSiteSearch(tracking.keyword, tracking.category, tracking.count);
      }
    }),
  );
};
