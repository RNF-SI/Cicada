/**
 * Global Error Handler pour Angular.
 *
 * Ce handler capture toutes les erreurs non-catchees dans l'application
 * et les envoie au LoggingService.
 */

import { ErrorHandler, Injectable, inject, NgZone } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { LoggingService } from '../services/logging.service';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private loggingService = inject(LoggingService);
  private ngZone = inject(NgZone);

  /**
   * Gere les erreurs non-catchees.
   */
  handleError(error: Error | HttpErrorResponse): void {
    // Executer dans la zone Angular pour eviter les problemes de detection de changements
    this.ngZone.run(() => {
      this.processError(error);
    });
  }

  /**
   * Traite l'erreur selon son type.
   */
  private processError(error: Error | HttpErrorResponse): void {
    // Les erreurs HTTP sont deja gerees par l'interceptor
    if (error instanceof HttpErrorResponse) {
      // Ne pas re-logger, deja fait par l'interceptor
      return;
    }

    // Erreurs de chunk loading (lazy loading echoue)
    if (this.isChunkLoadError(error)) {
      this.loggingService.error('Chunk loading failed - application may need refresh', error, {
        type: 'chunk_load_error',
      });
      // Optionnel: recharger la page
      // window.location.reload();
      return;
    }

    // Erreurs de rejection de promesse non geree
    if (this.isUnhandledRejection(error)) {
      this.loggingService.error('Unhandled promise rejection', error, {
        type: 'unhandled_rejection',
      });
      return;
    }

    // Autres erreurs JavaScript
    this.loggingService.error('Unhandled error', error, {
      type: 'javascript_error',
      component: this.extractComponentName(error),
    });

    // En dev, re-throw pour voir l'erreur dans la console
    // En prod, l'erreur est loggee mais l'app continue
    if (typeof console !== 'undefined') {
      console.error('GlobalErrorHandler caught:', error);
    }
  }

  /**
   * Detecte les erreurs de chargement de chunk.
   */
  private isChunkLoadError(error: Error): boolean {
    return (
      error.name === 'ChunkLoadError' ||
      error.message?.includes('Loading chunk') ||
      error.message?.includes('Failed to fetch dynamically imported module')
    );
  }

  /**
   * Detecte les rejections de promesse non gerees.
   */
  private isUnhandledRejection(error: unknown): boolean {
    return error instanceof PromiseRejectionEvent;
  }

  /**
   * Extrait le nom du composant de la stack trace si possible.
   */
  private extractComponentName(error: Error): string | undefined {
    const stack = error.stack;
    if (!stack) return undefined;

    // Chercher un pattern comme "at MyComponent.ngOnInit"
    const match = stack.match(/at (\w+Component)\./);
    return match ? match[1] : undefined;
  }
}
