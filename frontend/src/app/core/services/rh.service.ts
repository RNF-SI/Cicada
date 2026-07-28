/**
 * Service pour la gestion des ressources humaines des plans de gestion (#560).
 *
 * Expose :
 * - le référentiel global des fonctions (`/api/plans/fonctions/`), avec
 *   création à la volée d'une fonction manquante ;
 * - les postes d'un plan (`/api/plans/postes/`). Aucun nominatif (RGPD).
 *
 * Les lignes de temps de travail (prévisionnel / réalisé) sont portées par les
 * opérations et leurs réalisations (voir enjeu.service / realisation.service).
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { Fonction, Poste, PostePayload, TypePoste } from '../models/rh.model';

@Injectable({ providedIn: 'root' })
export class RhService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/plans';

  /** Cache des fonctions du dernier plan chargé (rechargé à la demande). */
  readonly fonctions = signal<Fonction[]>([]);

  // ---- Fonctions (socle partagé + fonctions du plan, #631) ----------------

  /**
   * Fonctions proposées pour un plan : le socle partagé **et** les fonctions
   * propres à ce plan (#631). Sans `planId`, seul le socle est renvoyé.
   */
  loadFonctions(planId?: number | null, actifOnly: boolean = true): Observable<Fonction[]> {
    const params: string[] = [];
    if (actifOnly) params.push('actif=true');
    if (planId != null) params.push(`id_pg=${planId}`);
    const suffix = params.length ? `?${params.join('&')}` : '';
    return this.http
      .get<Fonction[]>(`${this.apiUrl}/fonctions/${suffix}`)
      .pipe(tap((list) => this.fonctions.set(list)));
  }

  /**
   * Crée une fonction à la volée, **rattachée au plan** (#631) : elle n'est
   * proposée que là, jamais ajoutée au socle partagé. Le backend déduplique
   * (insensible à la casse) sur ce périmètre et renvoie la fonction existante
   * le cas échéant.
   */
  createFonction(
    libelle: string,
    financeParDefaut: boolean = true,
    typePoste: TypePoste = 'salarie',
    planId?: number | null,
  ): Observable<Fonction> {
    return this.http
      .post<Fonction>(`${this.apiUrl}/fonctions/`, {
        libelle,
        finance_par_defaut: financeParDefaut,
        type_poste: typePoste,
        id_pg: planId ?? null,
      })
      .pipe(
        tap((f) => {
          if (!this.fonctions().some((x) => x.id_fonction === f.id_fonction)) {
            this.fonctions.set(
              [...this.fonctions(), f].sort((a, b) => a.libelle.localeCompare(b.libelle)),
            );
          }
        }),
      );
  }

  updateFonction(id: number, changes: Partial<Fonction>): Observable<Fonction> {
    return this.http.patch<Fonction>(`${this.apiUrl}/fonctions/${id}/`, changes);
  }

  deleteFonction(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/fonctions/${id}/`);
  }

  // ---- Postes du plan -----------------------------------------------------

  getPostesByPlan(planId: number): Observable<Poste[]> {
    return this.http.get<Poste[]>(`${this.apiUrl}/postes/by-plan/${planId}/`);
  }

  createPoste(payload: PostePayload): Observable<Poste> {
    return this.http.post<Poste>(`${this.apiUrl}/postes/`, payload);
  }

  updatePoste(id: number, payload: Partial<PostePayload>): Observable<Poste> {
    return this.http.patch<Poste>(`${this.apiUrl}/postes/${id}/`, payload);
  }

  deletePoste(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/postes/${id}/`);
  }
}
