import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface SystemVersionInfo {
  current_version: string;
  update_available: boolean;
  latest_version: string | null;
  last_check: string | null;
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

  triggerUpdate(version: string): Observable<TriggerUpdateResponse> {
    return this.http.post<TriggerUpdateResponse>(`${this.apiUrl}/trigger-update/`, { version });
  }
}
