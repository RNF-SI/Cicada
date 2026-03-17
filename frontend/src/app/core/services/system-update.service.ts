import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';

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

  triggerUpdate(version: string): Observable<TriggerUpdateResponse> {
    return this.http.post<TriggerUpdateResponse>(`${this.apiUrl}/trigger-update/`, { version });
  }
}
