/**
 * #719 — Pendant une mise à jour lancée par le bouton, l'application
 * redémarre : pendant quelques secondes, le serveur renvoie 502/503/504 (ou
 * ne répond pas du tout). Un écran ouvert à ce moment affichait alors un
 * message d'erreur, qui faisait croire à l'échec d'une mise à jour réussie.
 *
 * Tant que la mise à jour est en cours, ces erreurs « serveur indisponible »
 * sont ignorées : l'appel se termine sans valeur, comme s'il n'avait pas eu
 * lieu. Les appels de `/api/system/` passent tels quels — le suivi de la
 * mise à jour s'appuie justement sur leur échec pour détecter le redémarrage.
 */

import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { EMPTY, catchError, throwError } from 'rxjs';
import { SystemUpdateService } from '../services/system-update.service';

const SERVEUR_INDISPONIBLE = new Set([0, 502, 503, 504]);

export const updateInterceptor: HttpInterceptorFn = (req, next) => {
  const systemUpdate = inject(SystemUpdateService);

  if (req.url.includes('/api/system/')) {
    return next(req);
  }

  return next(req).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        SERVEUR_INDISPONIBLE.has(error.status) &&
        systemUpdate.isUpdateInProgress()
      ) {
        return EMPTY;
      }
      return throwError(() => error);
    })
  );
};
