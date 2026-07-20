/**
 * Service pour l'API CAMPanule (référentiel de protocoles).
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CampanuleAutocomplete, CampanuleProtocoleDetail } from '../models/campanule.model';

@Injectable({ providedIn: 'root' })
export class CampanuleService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/campanule';

  /**
   * Autocomplete sur les protocoles CAMPanule.
   * @param search Terme de recherche — vide = liste alphabétique (#584)
   * @param limit Nombre max de résultats (défaut 20)
   * @param cible Filtre optionnel par cible (ex: "Oiseaux")
   */
  autocomplete(search: string, limit = 20, cible?: string): Observable<CampanuleAutocomplete[]> {
    let params = new HttpParams()
      .set('search', search)
      .set('limit', limit.toString());

    if (cible) {
      params = params.set('cible', cible);
    }

    return this.http.get<CampanuleAutocomplete[]>(`${this.baseUrl}/autocomplete/`, { params });
  }

  /**
   * Récupère le détail complet d'un protocole CAMPanule.
   */
  getProtocole(cdProtocole: number): Observable<CampanuleProtocoleDetail> {
    return this.http.get<CampanuleProtocoleDetail>(`${this.baseUrl}/${cdProtocole}/`);
  }
}
