/**
 * Service de logging centralise pour l'application Angular.
 *
 * Ce service fournit:
 * - Logging structure avec niveaux (debug, info, warn, error)
 * - Capture du correlation_id des reponses HTTP
 * - Formatage coherent des logs
 * - Option pour envoyer les erreurs critiques au backend
 */

import { Injectable, isDevMode, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  correlation_id?: string;
  context?: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

@Injectable({
  providedIn: 'root',
})
export class LoggingService {
  private http = inject(HttpClient);

  /**
   * Correlation ID courant (recupere de la derniere reponse HTTP).
   */
  private currentCorrelationId: string | null = null;

  /**
   * Niveau de log minimum (debug en dev, info en prod).
   */
  private minLevel: LogLevel = isDevMode() ? 'debug' : 'info';

  /**
   * Ordre des niveaux pour comparaison.
   */
  private readonly levelOrder: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
  };

  /**
   * Definit le correlation ID courant.
   * Appele par l'interceptor HTTP.
   */
  setCorrelationId(id: string | null): void {
    this.currentCorrelationId = id;
  }

  /**
   * Recupere le correlation ID courant.
   */
  getCorrelationId(): string | null {
    return this.currentCorrelationId;
  }

  /**
   * Log un message de niveau debug.
   */
  debug(message: string, context?: Record<string, unknown>): void {
    this.log('debug', message, context);
  }

  /**
   * Log un message de niveau info.
   */
  info(message: string, context?: Record<string, unknown>): void {
    this.log('info', message, context);
  }

  /**
   * Log un message de niveau warn.
   */
  warn(message: string, context?: Record<string, unknown>): void {
    this.log('warn', message, context);
  }

  /**
   * Log un message de niveau error.
   */
  error(message: string, error?: Error | HttpErrorResponse, context?: Record<string, unknown>): void {
    const errorDetails = error
      ? {
          name: error.name,
          message: error.message,
          stack: error instanceof Error ? error.stack : undefined,
        }
      : undefined;

    this.log('error', message, context, errorDetails);

    // En production, envoyer les erreurs critiques au backend
    if (!isDevMode() && error) {
      this.sendErrorToBackend(message, errorDetails, context);
    }
  }

  /**
   * Log une erreur HTTP.
   */
  logHttpError(error: HttpErrorResponse, context?: Record<string, unknown>): void {
    const message = `HTTP Error ${error.status}: ${error.message}`;
    const httpContext = {
      ...context,
      url: error.url,
      status: error.status,
      statusText: error.statusText,
    };

    this.error(message, error, httpContext);
  }

  /**
   * Methode principale de logging.
   */
  private log(
    level: LogLevel,
    message: string,
    context?: Record<string, unknown>,
    errorDetails?: LogEntry['error']
  ): void {
    // Verifier le niveau minimum
    if (this.levelOrder[level] < this.levelOrder[this.minLevel]) {
      return;
    }

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      correlation_id: this.currentCorrelationId || undefined,
      context,
      error: errorDetails,
    };

    // Log en console avec formatage
    this.logToConsole(entry);
  }

  /**
   * Log en console avec formatage adapte au niveau.
   */
  private logToConsole(entry: LogEntry): void {
    const prefix = entry.correlation_id ? `[${entry.correlation_id.slice(0, 8)}]` : '[-]';
    const formattedMessage = `${prefix} ${entry.message}`;

    // En dev, afficher un format lisible
    if (isDevMode()) {
      switch (entry.level) {
        case 'debug':
          console.debug(formattedMessage, entry.context || '');
          break;
        case 'info':
          console.info(formattedMessage, entry.context || '');
          break;
        case 'warn':
          console.warn(formattedMessage, entry.context || '');
          break;
        case 'error':
          console.error(formattedMessage, entry.error || '', entry.context || '');
          break;
      }
    } else {
      // En prod, log JSON structure
      console.log(JSON.stringify(entry));
    }
  }

  /**
   * Envoie les erreurs critiques au backend (optionnel).
   * Desactive par defaut pour eviter les boucles d'erreurs.
   */
  private sendErrorToBackend(
    message: string,
    error?: LogEntry['error'],
    context?: Record<string, unknown>
  ): void {
    // Endpoint optionnel pour recevoir les erreurs client
    const endpoint = '/api/logs/client/';

    // Eviter les erreurs en cascade
    try {
      this.http
        .post(
          endpoint,
          {
            timestamp: new Date().toISOString(),
            level: 'error',
            message,
            correlation_id: this.currentCorrelationId,
            error,
            context,
            user_agent: navigator.userAgent,
            url: window.location.href,
          },
          { headers: { 'X-No-Logging': 'true' } }
        )
        .subscribe({
          error: () => {
            // Ignorer les erreurs d'envoi silencieusement
          },
        });
    } catch {
      // Ignorer silencieusement
    }
  }
}
