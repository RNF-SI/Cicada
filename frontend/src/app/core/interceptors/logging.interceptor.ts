/**
 * HTTP Interceptor pour le logging des requetes.
 *
 * Ce interceptor:
 * - Capture le X-Correlation-ID des reponses HTTP
 * - Log les erreurs HTTP (4xx, 5xx) avec le correlation ID
 * - Mesure les temps de reponse API
 */

import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
  HttpResponse,
  HttpErrorResponse,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { tap, catchError, throwError } from 'rxjs';
import { LoggingService } from '../services/logging.service';

/**
 * Interceptor fonctionnel pour le logging HTTP.
 */
export const loggingInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const loggingService = inject(LoggingService);
  const startTime = Date.now();

  // Ne pas logger les requetes de logging elles-memes (eviter boucles)
  if (req.headers.has('X-No-Logging')) {
    return next(req);
  }

  return next(req).pipe(
    tap((event) => {
      if (event instanceof HttpResponse) {
        // Capturer le correlation ID de la reponse
        const correlationId = event.headers.get('X-Correlation-ID');
        if (correlationId) {
          loggingService.setCorrelationId(correlationId);
        }

        // Log les requetes lentes (> 1s)
        const duration = Date.now() - startTime;
        if (duration > 1000) {
          loggingService.warn(`Slow request: ${req.method} ${req.url}`, {
            duration_ms: duration,
            status: event.status,
          });
        }
      }
    }),
    catchError((error: HttpErrorResponse) => {
      // Capturer le correlation ID meme en cas d'erreur
      const correlationId = error.headers?.get('X-Correlation-ID');
      if (correlationId) {
        loggingService.setCorrelationId(correlationId);
      }

      // Log l'erreur HTTP
      const duration = Date.now() - startTime;
      loggingService.logHttpError(error, {
        method: req.method,
        duration_ms: duration,
      });

      return throwError(() => error);
    })
  );
};
