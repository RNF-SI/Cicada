/**
 * Service pour la gestion des ressources humaines des plans de gestion (#560).
 *
 * Expose :
 * - le référentiel global des fonctions/postes (`/api/plans/fonctions/`),
 *   avec création à la volée d'une fonction manquante ;
 * - les personnes rattachées à un plan (`/api/plans/personnes/`).
 *
 * Les lignes de temps de travail (prévisionnel / réalisé) sont portées par les
 * opérations et leurs réalisations (voir enjeu.service / realisation.service).
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { Fonction, PersonnePlan, PersonnePlanPayload } from '../models/rh.model';

@Injectable({ providedIn: 'root' })
export class RhService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/plans';

  /** Cache du référentiel de fonctions (partagé, rechargé à la demande). */
  readonly fonctions = signal<Fonction[]>([]);

  // ---- Fonctions (référentiel global) ------------------------------------

  loadFonctions(actifOnly: boolean = true): Observable<Fonction[]> {
    const suffix = actifOnly ? '?actif=true' : '';
    return this.http
      .get<Fonction[]>(`${this.apiUrl}/fonctions/${suffix}`)
      .pipe(tap((list) => this.fonctions.set(list)));
  }

  /**
   * Crée une fonction à la volée. Le backend déduplique (insensible à la
   * casse) et renvoie la fonction existante le cas échéant.
   */
  createFonction(libelle: string, financeParDefaut: boolean = true): Observable<Fonction> {
    return this.http
      .post<Fonction>(`${this.apiUrl}/fonctions/`, {
        libelle,
        finance_par_defaut: financeParDefaut,
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

  // ---- Personnes du plan --------------------------------------------------

  getPersonnesByPlan(planId: number): Observable<PersonnePlan[]> {
    return this.http.get<PersonnePlan[]>(`${this.apiUrl}/personnes/by-plan/${planId}/`);
  }

  createPersonne(payload: PersonnePlanPayload): Observable<PersonnePlan> {
    return this.http.post<PersonnePlan>(`${this.apiUrl}/personnes/`, payload);
  }

  updatePersonne(id: number, payload: Partial<PersonnePlanPayload>): Observable<PersonnePlan> {
    return this.http.patch<PersonnePlan>(`${this.apiUrl}/personnes/${id}/`, payload);
  }

  deletePersonne(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/personnes/${id}/`);
  }
}
