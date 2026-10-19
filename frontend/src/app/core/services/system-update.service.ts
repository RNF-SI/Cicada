import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface SystemUpdateResult {
  success: boolean;
  version?: string;
  error?: string;
  timestamp: string;
}

export interface SystemVersionInfo {
  current_version: string;
  update_available: boolean;
  latest_version: string | null;
  last_check: string | null;
  /** Échec de la dernière interrogation de l'API de suivi, effacé par la suivante qui réussit */
  last_check_error?: string | null;
  /** Vérification demandée par le bouton, pas encore prise par le heartbeat de l'hôte */
  check_pending?: boolean;
  /** Déclencheur déposé par le bouton, pas encore consommé par l'updater de l'hôte */
  update_pending?: boolean;
  /** Dernière mise à jour faite par l'updater (réussie ou non) */
  last_update?: SystemUpdateResult | null;
}

export interface TriggerUpdateResponse {
  success: boolean;
  message?: string;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class SystemUpdateService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/system';

  /**
   * #719 — Échéance (ms) jusqu'à laquelle une mise à jour lancée depuis cet
   * onglet est réputée en cours. Pendant ce temps, l'application redémarre :
   * les appels qui échouent faute de serveur ne sont pas des erreurs à
   * signaler (cf. `updateInterceptor`). L'échéance borne le cas où le suivi
   * s'arrête sans conclure (page quittée, updater muet).
   */
  private updateUntil = 0;

  /** Durée maximale d'une mise à jour, au-delà de laquelle on cesse de masquer les erreurs. */
  static readonly UPDATE_MAX_MS = 15 * 60 * 1000;

  markUpdateInProgress(): void {
    this.updateUntil = Date.now() + SystemUpdateService.UPDATE_MAX_MS;
  }

  markUpdateFinished(): void {
    this.updateUntil = 0;
  }

  isUpdateInProgress(): boolean {
    return Date.now() < this.updateUntil;
  }

  getVersion(): Observable<SystemVersionInfo> {
    return this.http.get<SystemVersionInfo>(`${this.apiUrl}/version/`).pipe(
      catchError(() => of({
        current_version: '?',
        update_available: false,
        latest_version: null,
        last_check: null
      }))
    );
  }

  /**
   * Même appel, sans masquer l'erreur : pendant une mise à jour, « l'API ne
   * répond pas » est une information (l'application redémarre), pas une panne.
   */
  pollVersion(): Observable<SystemVersionInfo> {
    return this.http.get<SystemVersionInfo>(`${this.apiUrl}/version/`);
  }

  /**
   * #646 — Version applicative seule, affichée en pied de sidebar
   * d'administration. Endpoint distinct de `getVersion()`, réservé au super
   * admin : celui-ci est ouvert à tout compte authentifié.
   */
  getAppVersion(): Observable<string | null> {
    return this.http.get<{ version: string }>(`${this.apiUrl}/app-version/`).pipe(
      map(res => res.version),
      catchError(() => of(null))
    );
  }

  /** Demande à l'hôte d'interroger tout de suite l'API de suivi (heartbeat immédiat). */
  checkForUpdate(): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(`${this.apiUrl}/check-update/`, {});
  }

  triggerUpdate(version: string): Observable<TriggerUpdateResponse> {
    return this.http.post<TriggerUpdateResponse>(`${this.apiUrl}/trigger-update/`, { version });
  }
}
