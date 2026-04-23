import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
  AdminOrganisme,
  AdminSite,
  AdminUser,
  AdminPlan,
  PlanFichier,
  OrganismeCreatePayload,
  SiteCreatePayload,
  PlanCreatePayload,
  PlanStatut,
  EvaluationType,
  RedacteurType,
  PaginatedResponse,
  PaginatedResponseNested,
  OrganismeSite,
  SiteOrganisme,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
  DuplicateCheckResult,
  RgpdRequest,
  BulkImportFieldMapping,
  BulkImportValidationResult,
  BulkImportResult,
  BulkImportJobStatus,
  PlanDuplicateOptions
} from '../models/admin.model';

export interface DashboardStats {
  totalPlans: number;
  plansActifs: number;
  totalUtilisateurs: number;
  totalSites: number;
  totalOrganismes: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/users';

  // ==================== ORGANISMES ====================

  /**
   * Get list of organismes
   * @param params.for_invite Si true, permet aux référents de voir tous les organismes (pour invitation)
   */
  getOrganismes(params?: { search?: string; page?: number; page_size?: number; for_invite?: boolean }): Observable<PaginatedResponse<AdminOrganisme>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    if (params?.for_invite) {
      httpParams = httpParams.set('for_invite', 'true');
    }

    return this.http.get<PaginatedResponse<AdminOrganisme>>(`${this.apiUrl}/organismes/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get single organisme by ID
   */
  getOrganisme(id: number): Observable<AdminOrganisme> {
    return this.http.get<AdminOrganisme>(`${this.apiUrl}/organismes/${id}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new organisme
   */
  createOrganisme(payload: OrganismeCreatePayload): Observable<AdminOrganisme> {
    return this.http.post<AdminOrganisme>(`${this.apiUrl}/organismes/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update an organisme
   */
  updateOrganisme(id: number, payload: Partial<OrganismeCreatePayload>): Observable<AdminOrganisme> {
    return this.http.patch<AdminOrganisme>(`${this.apiUrl}/organismes/${id}/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Link a site to an organisme
   */
  assignSiteToOrganisme(organismeId: number, siteId: number, principal: boolean = false): Observable<any> {
    return this.http.post(`${this.apiUrl}/organismes/${organismeId}/assign_site/`, {
      site_id: siteId,
      principal
    }).pipe(catchError(this.handleError));
  }

  /**
   * Unlink a site from an organisme
   */
  removeSiteFromOrganisme(organismeId: number, siteId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/organismes/${organismeId}/sites/${siteId}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get sites linked to an organisme
   */
  getOrganismeSites(organismeId: number): Observable<OrganismeSite[]> {
    return this.http.get<OrganismeSite[]>(`${this.apiUrl}/organismes/${organismeId}/sites/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get users belonging to an organisme
   */
  getOrganismeUsers(organismeId: number): Observable<AdminUser[]> {
    return this.http.get<PaginatedResponse<AdminUser>>(`${this.apiUrl}/users/?organisme=${organismeId}`)
      .pipe(
        map(res => res.results),
        catchError(this.handleError)
      );
  }

  // ==================== SITES ====================

  /**
   * Get all sites available for assignment (no organisme filtering)
   * Used for adding sites to an organisme
   */
  getSitesAvailableForAssignment(search?: string): Observable<PaginatedResponse<AdminSite>> {
    let httpParams = new HttpParams();
    if (search) {
      httpParams = httpParams.set('search', search);
    }

    return this.http.get<PaginatedResponse<AdminSite>>(`${this.apiUrl}/sites/available_for_assignment/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get list of sites
   */
  getSites(params?: { search?: string; page?: number; page_size?: number; type?: string; organisme?: number }): Observable<PaginatedResponse<AdminSite>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    if (params?.type) {
      httpParams = httpParams.set('type_site_label', params.type);
    }
    if (params?.organisme) {
      httpParams = httpParams.set('organisme', params.organisme.toString());
    }

    return this.http.get<PaginatedResponse<AdminSite>>(`${this.apiUrl}/sites/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get single site by slug
   */
  getSite(slug: string): Observable<AdminSite> {
    return this.http.get<AdminSite>(`${this.apiUrl}/sites/${slug}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Search all sites (including sites from other organisations).
   * Used for site-org link requests.
   * GET /api/users/sites/search_all/
   */
  searchAllSites(params?: { search?: string; page_size?: number }): Observable<PaginatedResponse<AdminSite>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    return this.http.get<PaginatedResponse<AdminSite>>(`${this.apiUrl}/sites/search_all/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign a user to a site with referent role
   */
  assignUserToSite(siteSlug: string, userId: number, referent: boolean = true): Observable<any> {
    return this.http.post(`${this.apiUrl}/sites/${siteSlug}/assign_user/`, {
      user_id: userId,
      referent
    }).pipe(catchError(this.handleError));
  }

  /**
   * Remove user from site
   */
  removeUserFromSite(siteSlug: string, userId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/sites/${siteSlug}/users/${userId}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get users assigned to a site
   */
  getSiteUsers(siteSlug: string): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(`${this.apiUrl}/sites/${siteSlug}/users/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get organismes managing a site
   */
  getSiteOrganismes(siteSlug: string): Observable<SiteOrganisme[]> {
    return this.http.get<SiteOrganisme[]>(`${this.apiUrl}/sites/${siteSlug}/organismes/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new site
   */
  createSite(payload: SiteCreatePayload): Observable<AdminSite> {
    return this.http.post<AdminSite>(`${this.apiUrl}/sites/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update a site
   */
  updateSite(slug: string, payload: Partial<SiteCreatePayload>): Observable<AdminSite> {
    return this.http.patch<AdminSite>(`${this.apiUrl}/sites/${slug}/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a site
   */
  deleteSite(slug: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/sites/${slug}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Check for duplicate sites by INPN code or name
   * GET /api/users/sites/check_duplicates/
   * @param params - nom_site: search by similar names, id_inpn: exact INPN match, exclude_id: site to exclude (edit mode)
   */
  checkDuplicates(params: { nom_site?: string; id_inpn?: string; exclude_id?: number }): Observable<DuplicateCheckResult> {
    let httpParams = new HttpParams();
    if (params.nom_site) {
      httpParams = httpParams.set('nom_site', params.nom_site);
    }
    if (params.id_inpn) {
      httpParams = httpParams.set('id_inpn', params.id_inpn);
    }
    if (params.exclude_id) {
      httpParams = httpParams.set('exclude_id', params.exclude_id.toString());
    }
    return this.http.get<DuplicateCheckResult>(`${this.apiUrl}/sites/check_duplicates/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get site types (nomenclatures)
   */
  getSiteTypes(): Observable<{ id_nomenclature: number; cd_nomenclature: string | null; mnemonique: string; label: string }[]> {
    return this.http.get<any>('/api/nomenclatures/?type=TYPE_SITE')
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
  }

  // ==================== SITES GEOJSON ====================

  /**
   * Get a single site as GeoJSON Feature
   * @param slug Site slug
   */
  getSiteGeoJSON(slug: string): Observable<GeoJSONFeature> {
    return this.http.get<GeoJSONFeature>(`${this.apiUrl}/sites/${slug}/geojson/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get all accessible sites as GeoJSON FeatureCollection
   * Limited to 100 sites for performance
   */
  getSitesGeoJSON(): Observable<GeoJSONFeatureCollection> {
    return this.http.get<GeoJSONFeatureCollection>(`${this.apiUrl}/sites/geojson_list/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get sites filtered by user access as GeoJSON
   * @param userSitesOnly If true, only returns sites the user has access to
   */
  getSitesGeoJSONFiltered(params?: { userSitesOnly?: boolean }): Observable<GeoJSONFeatureCollection> {
    let httpParams = new HttpParams();
    if (params?.userSitesOnly) {
      httpParams = httpParams.set('user_sites_only', 'true');
    }
    return this.http.get<GeoJSONFeatureCollection>(`${this.apiUrl}/sites/geojson_list/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  // ==================== USERS ====================

  /**
   * Get list of users
   */
  getUsers(params?: { search?: string; page?: number; page_size?: number; role?: string; organisme?: number; active?: boolean }): Observable<PaginatedResponse<AdminUser>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    if (params?.role) {
      httpParams = httpParams.set('role_level', params.role);
    }
    if (params?.organisme) {
      httpParams = httpParams.set('organisme', params.organisme.toString());
    }
    if (params?.active !== undefined) {
      httpParams = httpParams.set('active', params.active.toString());
    }

    return this.http.get<PaginatedResponse<AdminUser>>(`${this.apiUrl}/users/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get single user by ID
   */
  getUser(id: number): Observable<AdminUser> {
    return this.http.get<AdminUser>(`${this.apiUrl}/users/${id}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update user (including organisme assignment)
   */
  updateUser(id: number, payload: Partial<AdminUser>): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.apiUrl}/users/${id}/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign organisme to user
   */
  assignOrganismeToUser(userId: number, uuidOrganisme: string | null): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.apiUrl}/users/${userId}/`, {
      uuid_organisme: uuidOrganisme
    }).pipe(catchError(this.handleError));
  }

  /**
   * Promote user to Rédacteur Principal
   */
  setRedacteurPrincipal(userId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/${userId}/set-redacteur-principal/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Remove Rédacteur Principal role from user
   */
  removeRedacteurPrincipal(userId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/${userId}/remove-redacteur-principal/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Toggle user active status
   */
  toggleUserStatus(userId: number, active: boolean): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.apiUrl}/users/${userId}/`, {
      active: active
    }).pipe(catchError(this.handleError));
  }

  /**
   * Assign site to user
   */
  assignSiteToUser(userId: number, siteId: number, referent: boolean = true): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/${userId}/sites/`, {
      site_id: siteId,
      referent
    }).pipe(catchError(this.handleError));
  }

  /**
   * Remove site from user
   */
  removeSiteFromUser(userId: number, siteId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/users/${userId}/sites/${siteId}/`)
      .pipe(catchError(this.handleError));
  }

  // ==================== PLANS DE GESTION ====================

  private readonly plansApiUrl = '/api/plans';

  /**
   * Get list of plans de gestion
   */
  getPlans(params?: {
    search?: string;
    page?: number;
    page_size?: number;
    statut?: PlanStatut;
    organisme?: number;
    site?: number;
    scope?: 'mine';
  }): Observable<PaginatedResponse<AdminPlan>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    if (params?.statut) {
      httpParams = httpParams.set('statut', params.statut);
    }
    if (params?.organisme) {
      httpParams = httpParams.set('organisme', params.organisme.toString());
    }
    if (params?.site) {
      httpParams = httpParams.set('site_id', params.site.toString());
    }
    if (params?.scope) {
      httpParams = httpParams.set('scope', params.scope);
    }

    return this.http.get<PaginatedResponse<AdminPlan>>(`${this.plansApiUrl}/plans/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get single plan by ID
   */
  getPlan(id: number): Observable<AdminPlan> {
    return this.http.get<AdminPlan>(`${this.plansApiUrl}/plans/${id}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get a plan de gestion by slug
   */
  getPlanBySlug(slug: string): Observable<AdminPlan> {
    return this.http.get<AdminPlan>(`${this.plansApiUrl}/plans/by-slug/${slug}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new plan de gestion
   */
  createPlan(payload: PlanCreatePayload): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update a plan de gestion
   */
  updatePlan(id: number, payload: Partial<PlanCreatePayload>): Observable<AdminPlan> {
    return this.http.patch<AdminPlan>(`${this.plansApiUrl}/plans/${id}/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a plan de gestion
   */
  deletePlan(id: number): Observable<void> {
    return this.http.delete<void>(`${this.plansApiUrl}/plans/${id}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update plan status (valider, archiver, etc.)
   */
  updatePlanStatus(id: number, statut: PlanStatut): Observable<AdminPlan> {
    return this.http.patch<AdminPlan>(`${this.plansApiUrl}/plans/${id}/`, { statut })
      .pipe(catchError(this.handleError));
  }

  /**
   * Change plan status via dedicated endpoint with transition validation
   * POST /api/plans/plans/{id}/change-status/
   */
  changePlanStatus(planId: number, newStatus: PlanStatut): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/change-status/`, { new_status: newStatus })
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a mid-term evaluation from a validated plan
   * POST /api/plans/plans/{id}/create-evaluation/
   */
  createEvaluation(planId: number): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/create-evaluation/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Duplicate a plan with configurable options
   * POST /api/plans/plans/{id}/duplicate/
   */
  duplicatePlan(planId: number, options: PlanDuplicateOptions): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/duplicate/`, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign a single site to a plan
   * POST /api/plans/plans/{id}/assign_site/
   */
  assignSiteToPlan(planId: number, siteId: number, rang?: number, commentaire?: string): Observable<AdminPlan> {
    const payload: { site_id: number; rang?: number; commentaire?: string } = { site_id: siteId };
    if (rang !== undefined) payload.rang = rang;
    if (commentaire) payload.commentaire = commentaire;
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/assign_site/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign multiple sites to a plan (calls API for each site)
   */
  assignSitesToPlan(planId: number, siteIds: number[]): Observable<AdminPlan[]> {
    if (siteIds.length === 0) {
      return of([]);
    }
    const requests = siteIds.map(siteId => this.assignSiteToPlan(planId, siteId));
    return forkJoin(requests).pipe(catchError(this.handleError));
  }

  /**
   * Remove a site from a plan
   * DELETE /api/plans/plans/{id}/remove_site/?site_id=X
   */
  removeSiteFromPlan(planId: number, siteId: number): Observable<any> {
    return this.http.delete(`${this.plansApiUrl}/plans/${planId}/remove_site/`, {
      params: { site_id: siteId.toString() }
    }).pipe(catchError(this.handleError));
  }

  /**
   * Assign a single referent to a plan
   * POST /api/plans/plans/{id}/assign_referent/
   */
  assignReferentToPlan(planId: number, referentId: number): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/assign_referent/`, {
      referent_id: referentId
    }).pipe(catchError(this.handleError));
  }

  /**
   * Assign multiple referents to a plan (calls API for each referent)
   */
  assignReferentsToPlan(planId: number, referentIds: number[]): Observable<AdminPlan[]> {
    if (referentIds.length === 0) {
      return of([]);
    }
    const requests = referentIds.map(referentId => this.assignReferentToPlan(planId, referentId));
    return forkJoin(requests).pipe(catchError(this.handleError));
  }

  /**
   * Remove a referent from a plan
   * DELETE /api/plans/plans/{id}/remove_referent/?referent_id=X
   */
  removeReferentFromPlan(planId: number, referentId: number): Observable<any> {
    return this.http.delete(`${this.plansApiUrl}/plans/${planId}/remove_referent/`, {
      params: { referent_id: referentId.toString() }
    }).pipe(catchError(this.handleError));
  }

  /**
   * Assign a member (non-referent) to a plan
   * POST /api/plans/plans/{id}/assign_member/
   */
  assignMemberToPlan(planId: number, userId: number): Observable<any> {
    return this.http.post(`${this.plansApiUrl}/plans/${planId}/assign_member/`, {
      user_id: userId
    }).pipe(catchError(this.handleError));
  }

  /**
   * Remove a member from a plan
   * DELETE /api/plans/plans/{id}/remove_member/?user_id=X
   */
  removeMemberFromPlan(planId: number, userId: number): Observable<any> {
    return this.http.delete(`${this.plansApiUrl}/plans/${planId}/remove_member/`, {
      params: { user_id: userId.toString() }
    }).pipe(catchError(this.handleError));
  }

  /**
   * Get evaluation types (nomenclatures)
   */
  getEvaluationTypes(): Observable<EvaluationType[]> {
    return this.http.get<any>('/api/nomenclatures/?type=TYPE_EVALUATION')
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
  }

  /**
   * Get redacteur types (nomenclatures)
   */
  getRedacteurTypes(): Observable<RedacteurType[]> {
    return this.http.get<any>('/api/nomenclatures/?type=TYPE_REDACTEUR')
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
  }

  /**
   * Get nomenclatures by type
   */
  getNomenclaturesByType(typeMnemonique: string): Observable<{ id_nomenclature: number; mnemonique: string; label: string; definition?: string; hierarchy?: string }[]> {
    return this.http.get<any>(`/api/nomenclatures/?type=${typeMnemonique}`)
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
  }

  /**
   * Get nomenclatures by type filtered by code prefix
   */
  getNomenclaturesByTypeAndPrefix(typeMnemonique: string, prefix: string): Observable<{ id_nomenclature: number; mnemonique: string; cd_nomenclature?: string; label: string; definition?: string; hierarchy?: string; group_label?: string }[]> {
    return this.http.get<any>(`/api/nomenclatures/?type=${typeMnemonique}&prefix=${prefix}`)
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
  }

  /**
   * Get a specific nomenclature by type and mnemonique
   */
  getNomenclatureByMnemonique(typeMnemonique: string, mnemonique: string): Observable<{ id_nomenclature: number; mnemonique: string; label: string }> {
    return this.http.get<any>(`/api/nomenclatures/?type=${typeMnemonique}&mnemonique=${mnemonique}`)
      .pipe(
        map(res => {
          const results = res.results || res;
          if (Array.isArray(results) && results.length > 0) {
            return results[0];
          }
          throw new Error(`Nomenclature ${mnemonique} not found for type ${typeMnemonique}`);
        }),
        catchError(this.handleError)
      );
  }

  // ==================== DASHBOARD ====================

  /**
   * Get dashboard statistics
   * Each request handles its own error to prevent one failure from breaking all stats
   * Note: /api/users/* endpoints use nested pagination format { pagination: { count } }
   *       /api/plans/* endpoints use standard format { count }
   */
  getDashboardStats(): Observable<DashboardStats> {
    return forkJoin({
      users: this.http.get<PaginatedResponseNested<AdminUser>>(`${this.apiUrl}/users/`).pipe(
        map(res => res.pagination?.count ?? 0),
        catchError(() => of(0))
      ),
      sites: this.http.get<PaginatedResponseNested<AdminSite>>(`${this.apiUrl}/sites/`).pipe(
        map(res => res.pagination?.count ?? 0),
        catchError(() => of(0))
      ),
      organismes: this.http.get<PaginatedResponseNested<AdminOrganisme>>(`${this.apiUrl}/organismes/`).pipe(
        map(res => res.pagination?.count ?? 0),
        catchError(() => of(0))
      ),
      plans: this.http.get<PaginatedResponseNested<any>>('/api/plans/plans/').pipe(
        map(res => res.pagination?.count ?? 0),
        catchError(() => of(0))
      ),
      plansActifs: this.http.get<PaginatedResponseNested<any>>('/api/plans/plans/?actif=true').pipe(
        map(res => res.pagination?.count ?? 0),
        catchError(() => of(0))
      )
    }).pipe(
      map(results => ({
        totalUtilisateurs: results.users,
        totalSites: results.sites,
        totalOrganismes: results.organismes,
        totalPlans: results.plans,
        plansActifs: results.plansActifs
      }))
    );
  }

  // ==================== RGPD (Super Admin Only) ====================

  /**
   * Get list of RGPD deletion requests
   * GET /api/users/users/rgpd_requests/
   */
  getRgpdRequests(params?: { page?: number }): Observable<PaginatedResponse<RgpdRequest>> {
    let httpParams = new HttpParams();
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    return this.http.get<PaginatedResponse<RgpdRequest>>(`${this.apiUrl}/users/rgpd_requests/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Deactivate a user account via RGPD request
   * POST /api/users/users/{id}/deactivate_rgpd/
   */
  deactivateUserRgpd(userId: number): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.apiUrl}/users/${userId}/deactivate_rgpd/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Anonymize a user account via RGPD request
   * POST /api/users/users/{id}/anonymize_rgpd/
   */
  anonymizeUserRgpd(userId: number): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.apiUrl}/users/${userId}/anonymize_rgpd/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Reject a RGPD deletion request
   * POST /api/users/users/{id}/reject_rgpd/
   */
  rejectRgpdRequest(userId: number): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.apiUrl}/users/${userId}/reject_rgpd/`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Get the configured authentication provider
   * GET /api/users/users/auth_provider/
   */
  getAuthProvider(): Observable<{ provider: string }> {
    return this.http.get<{ provider: string }>(`${this.apiUrl}/users/auth_provider/`)
      .pipe(catchError(this.handleError));
  }

  // ==================== BULK IMPORT ====================

  /**
   * Validate a bulk import file (GeoJSON or CSV)
   * POST multipart /api/users/sites/bulk_import_validate/
   */
  bulkImportValidate(file: File, fieldMapping?: BulkImportFieldMapping): Observable<BulkImportValidationResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (fieldMapping) {
      formData.append('field_mapping', JSON.stringify(fieldMapping));
    }
    return this.http.post<BulkImportValidationResult>(
      `${this.apiUrl}/sites/bulk_import_validate/`,
      formData
    ).pipe(catchError(this.handleError));
  }

  /**
   * Execute bulk import of selected sites
   * POST JSON /api/users/sites/bulk_import_execute/
   */
  bulkImportExecute(sites: any[], selectedIndices: number[]): Observable<BulkImportResult> {
    return this.http.post<BulkImportResult>(
      `${this.apiUrl}/sites/bulk_import_execute/`,
      { sites, selected_indices: selectedIndices }
    ).pipe(catchError(this.handleError));
  }

  /**
   * Get status of an async bulk import job
   * GET /api/users/sites/bulk_import_status/?job_id=X
   */
  bulkImportStatus(jobId: number): Observable<BulkImportJobStatus> {
    return this.http.get<BulkImportJobStatus>(
      `${this.apiUrl}/sites/bulk_import_status/`,
      { params: { job_id: jobId.toString() } }
    ).pipe(catchError(this.handleError));
  }

  // ==================== FICHIERS PLANS ====================

  /**
   * Get fichiers for a plan
   */
  getPlanFichiers(planId: number): Observable<PaginatedResponse<PlanFichier>> {
    return this.http.get<PaginatedResponse<PlanFichier>>(`${this.plansApiUrl}/fichiers/`, {
      params: { plan_id: planId.toString() }
    }).pipe(catchError(this.handleError));
  }

  /**
   * Upload a fichier for a plan
   */
  uploadFichier(planId: number, file: File, metadata: {
    type_fichier?: string;
    titre?: string;
    description?: string;
    auteur?: string;
    date_document?: string;
    public?: boolean;
  }): Observable<PlanFichier> {
    const formData = new FormData();
    formData.append('fichier', file);
    formData.append('plan_de_gestion', planId.toString());
    formData.append('nom_fichier', file.name);
    if (metadata.type_fichier) formData.append('type_fichier', metadata.type_fichier);
    if (metadata.titre) formData.append('titre', metadata.titre);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.auteur) formData.append('auteur', metadata.auteur);
    if (metadata.date_document) formData.append('date_document', metadata.date_document);
    if (metadata.public !== undefined) formData.append('public', metadata.public.toString());

    return this.http.post<PlanFichier>(`${this.plansApiUrl}/fichiers/`, formData)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a fichier
   */
  deleteFichier(fichierId: number): Observable<void> {
    return this.http.delete<void>(`${this.plansApiUrl}/fichiers/${fichierId}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Download a fichier as blob (needed because JWT auth can't be sent via window.open)
   */
  downloadFichierBlob(fichierId: number): Observable<Blob> {
    return this.http.get(`${this.plansApiUrl}/fichiers/${fichierId}/download/`, {
      responseType: 'blob'
    }).pipe(catchError(this.handleError));
  }

  // ==================== ERROR HANDLING ====================

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'Une erreur est survenue';

    // Log the full error for debugging
    console.error('API Error:', error);

    if (error.error instanceof ErrorEvent) {
      errorMessage = error.error.message;
    } else {
      if (error.status === 400) {
        if (error.error?.detail) {
          errorMessage = error.error.detail;
        } else if (typeof error.error === 'object') {
          // Collect all validation errors
          const errors: string[] = [];
          Object.keys(error.error).forEach(key => {
            const fieldErrors = error.error[key];
            if (Array.isArray(fieldErrors)) {
              errors.push(`${key}: ${fieldErrors.join(', ')}`);
            } else {
              errors.push(`${key}: ${fieldErrors}`);
            }
          });
          errorMessage = errors.join('\n');
        }
      } else if (error.status === 403) {
        errorMessage = error.error?.detail || 'Vous n\'avez pas les droits pour effectuer cette action';
      } else if (error.status === 404) {
        errorMessage = 'Ressource non trouvée';
      } else if (error.status === 500) {
        errorMessage = error.error?.detail || error.error?.error || 'Erreur serveur. Veuillez réessayer.';
        console.error('Server error details:', error.error);
      } else if (error.status === 0) {
        errorMessage = 'Impossible de se connecter au serveur';
      }
    }

    return throwError(() => new Error(errorMessage));
  }
}
