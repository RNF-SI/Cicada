/**
 * Service pour la gestion des Suivis/Inventaires (standalone).
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap, catchError, throwError } from 'rxjs';

import {
  SuiviInventaireList,
  SuiviInventaireDetail,
  SuiviInventaireCreatePayload,
  InventaireFilters,
  PaginatedInventairesResponse,
} from '../models/inventaire.model';

@Injectable({
  providedIn: 'root'
})
export class InventaireService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/inventaires';

  // Signals for reactive state
  private loadingSignal = signal<boolean>(false);
  private errorSignal = signal<string | null>(null);

  // Public readonly signals
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();

  /**
   * Build HttpParams from filters.
   */
  private buildParams(filters?: InventaireFilters): HttpParams {
    let params = new HttpParams();

    if (filters) {
      if (filters.actif !== undefined) params = params.set('actif', filters.actif.toString());
      if (filters.id_statut) params = params.set('id_statut', filters.id_statut.toString());
      if (filters.id_pg) params = params.set('id_pg', filters.id_pg.toString());
      if (filters.annee_min) params = params.set('annee_min', filters.annee_min.toString());
      if (filters.annee_max) params = params.set('annee_max', filters.annee_max.toString());
      if (filters.site) params = params.set('site', filters.site.toString());
      if (filters.type_action_prefix) params = params.set('type_action_prefix', filters.type_action_prefix);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return params;
  }

  /**
   * Get paginated list of suivis/inventaires.
   */
  getInventaires(filters?: InventaireFilters): Observable<PaginatedInventairesResponse> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedInventairesResponse>(`${this.apiUrl}/suivis/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error loading inventaires');
        return throwError(() => err);
      })
    );
  }

  /**
   * Get a single suivi/inventaire by ID.
   */
  getInventaire(id: number): Observable<SuiviInventaireDetail> {
    return this.http.get<SuiviInventaireDetail>(`${this.apiUrl}/suivis/${id}/`);
  }

  /**
   * Create a new suivi/inventaire.
   */
  createInventaire(payload: SuiviInventaireCreatePayload): Observable<SuiviInventaireDetail> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.post<SuiviInventaireDetail>(`${this.apiUrl}/suivis/`, payload).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error creating inventaire');
        return throwError(() => err);
      })
    );
  }

  /**
   * Update an existing suivi/inventaire.
   */
  updateInventaire(id: number, payload: Partial<SuiviInventaireCreatePayload>): Observable<SuiviInventaireDetail> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.patch<SuiviInventaireDetail>(`${this.apiUrl}/suivis/${id}/`, payload).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error updating inventaire');
        return throwError(() => err);
      })
    );
  }

  /**
   * Delete a suivi/inventaire.
   */
  deleteInventaire(id: number): Observable<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.delete<void>(`${this.apiUrl}/suivis/${id}/`).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error deleting inventaire');
        return throwError(() => err);
      })
    );
  }
}
