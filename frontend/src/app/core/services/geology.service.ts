import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

export interface InpgAutocomplete {
  id_inpg: number;
  id_metier: string | null;
  lb_site: string | null;
  region: string | null;
  departements: string | null;
  communes: string | null;
  interet_geol_principal: string | null;
}

export interface InpgBulkFoundItem {
  input: string;
  id_inpg: number;
  id_metier: string | null;
  lb_site: string | null;
  region: string | null;
  interet_geol_principal: string | null;
}

export interface InpgBulkNotFoundItem {
  input: string;
  candidates: { id_inpg: number; lb_site: string | null; id_metier: string | null }[];
}

export interface InpgBulkValidationResult {
  found: InpgBulkFoundItem[];
  not_found: InpgBulkNotFoundItem[];
}

@Injectable({
  providedIn: 'root'
})
export class GeologyService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/inpg';

  private autocompleteCache = new Map<string, InpgAutocomplete[]>();
  private readonly maxCacheSize = 100;

  /**
   * Autocomplete sur les sites INPG (trigrammes + unaccent).
   */
  autocomplete(search: string, options?: {
    limit?: number;
  }): Observable<InpgAutocomplete[]> {
    if (search.length < 2) {
      return of([]);
    }

    const cacheKey = search;
    const cached = this.autocompleteCache.get(cacheKey);
    if (cached) {
      return of(cached);
    }

    let params = new HttpParams().set('search', search);
    if (options?.limit) params = params.set('limit', options.limit.toString());

    return this.http.get<InpgAutocomplete[]>(
      `${this.apiUrl}/autocomplete/`, { params }
    ).pipe(
      tap(results => {
        if (this.autocompleteCache.size >= this.maxCacheSize) {
          const firstKey = this.autocompleteCache.keys().next().value;
          if (firstKey !== undefined) {
            this.autocompleteCache.delete(firstKey);
          }
        }
        this.autocompleteCache.set(cacheKey, results);
      })
    );
  }

  /**
   * Valide une liste d'entrées (id_inpg, id_metier, ou noms de sites)
   * contre le référentiel INPG.
   */
  validateBulk(items: string[]): Observable<InpgBulkValidationResult> {
    return this.http.post<InpgBulkValidationResult>(
      `${this.apiUrl}/validate-bulk/`, { items }
    );
  }
}
