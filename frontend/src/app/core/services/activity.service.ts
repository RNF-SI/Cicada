/**
 * Service pour la gestion de l'historique d'activite.
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import {
  ActivityLogListItem,
  ActivityLogDetail,
  ActivityStats,
  ActivityTabsCounts,
  ActivityFilters,
  PaginatedActivityResponse,
  ActivityTab
} from '../models/activity.model';

@Injectable({
  providedIn: 'root'
})
export class ActivityService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/activity';

  // Signals pour l'etat reactif
  private tabsCountsSignal = signal<ActivityTabsCounts | null>(null);
  private currentTabSignal = signal<ActivityTab>('all');
  private loadingSignal = signal<boolean>(false);

  // Signals publics en lecture seule
  readonly tabsCounts = this.tabsCountsSignal.asReadonly();
  readonly currentTab = this.currentTabSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  // Computed signals
  readonly totalCount = computed(() => this.tabsCountsSignal()?.all ?? 0);

  /**
   * Change l'onglet actif.
   */
  setCurrentTab(tab: ActivityTab): void {
    this.currentTabSignal.set(tab);
  }

  /**
   * Construit les HttpParams a partir des filtres.
   */
  private buildParams(filters?: ActivityFilters): HttpParams {
    let params = new HttpParams();

    if (filters) {
      if (filters.entity_type) params = params.set('entity_type', filters.entity_type);
      if (filters.action) params = params.set('action', filters.action);
      if (filters.visibility) params = params.set('visibility', filters.visibility);
      if (filters.site_id) params = params.set('site_id', filters.site_id.toString());
      if (filters.plan_id) params = params.set('plan_id', filters.plan_id.toString());
      if (filters.organisme_id) params = params.set('organisme_id', filters.organisme_id.toString());
      if (filters.user_id) params = params.set('user_id', filters.user_id.toString());
      if (filters.actor_id) params = params.set('actor_id', filters.actor_id.toString());
      if (filters.date_from) params = params.set('date_from', filters.date_from);
      if (filters.date_to) params = params.set('date_to', filters.date_to);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
    }

    return params;
  }

  /**
   * Recupere la liste paginee des activites.
   */
  getActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere le detail d'une activite.
   */
  getActivity(id: number): Observable<ActivityLogDetail> {
    return this.http.get<ActivityLogDetail>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Recupere les activites sur mes sites.
   */
  getMySitesActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/my_sites/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les activites sur mes plans.
   */
  getMyPlansActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/my_plans/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les activites concernant mes droits.
   */
  getMyRightsActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/my_rights/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les activites de validation (admin_og+).
   */
  getValidationsActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/validations/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les activites systeme (super_admin only).
   */
  getSystemActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/system/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les activites RGPD (super_admin only).
   */
  getRgpdActivities(filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    this.loadingSignal.set(true);
    const params = this.buildParams(filters);

    return this.http.get<PaginatedActivityResponse>(`${this.apiUrl}/rgpd/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false))
    );
  }

  /**
   * Recupere les statistiques d'activite.
   */
  getStats(): Observable<ActivityStats> {
    return this.http.get<ActivityStats>(`${this.apiUrl}/stats/`);
  }

  /**
   * Recupere les compteurs pour les onglets.
   */
  getTabsCounts(): Observable<ActivityTabsCounts> {
    return this.http.get<ActivityTabsCounts>(`${this.apiUrl}/tabs_counts/`).pipe(
      tap(counts => this.tabsCountsSignal.set(counts))
    );
  }

  /**
   * Recupere les activites selon l'onglet actif.
   */
  getActivitiesByTab(tab: ActivityTab, filters?: ActivityFilters): Observable<PaginatedActivityResponse> {
    switch (tab) {
      case 'my_sites':
        return this.getMySitesActivities(filters);
      case 'my_plans':
        return this.getMyPlansActivities(filters);
      case 'my_rights':
        return this.getMyRightsActivities(filters);
      case 'validations':
        return this.getValidationsActivities(filters);
      case 'system':
        return this.getSystemActivities(filters);
      case 'rgpd':
        return this.getRgpdActivities(filters);
      case 'all':
      default:
        return this.getActivities(filters);
    }
  }

  /**
   * Rafraichit les compteurs d'onglets.
   */
  refreshTabsCounts(): void {
    this.getTabsCounts().subscribe();
  }
}
