import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
  AdminOrganisme,
  AdminSite,
  AdminUser,
  AdminPlan,
  OrganismeCreatePayload,
  SiteCreatePayload,
  PlanCreatePayload,
  PlanStatut,
  EvaluationType,
  RedacteurType,
  PaginatedResponse,
  PaginatedResponseNested,
  OrganismeSite,
  SiteOrganisme
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
   */
  getOrganismes(params?: { search?: string; page?: number }): Observable<PaginatedResponse<AdminOrganisme>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
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
  getSites(params?: { search?: string; page?: number; page_size?: number; type?: string }): Observable<PaginatedResponse<AdminSite>> {
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
      httpParams = httpParams.set('id_type_site', params.type);
    }

    return this.http.get<PaginatedResponse<AdminSite>>(`${this.apiUrl}/sites/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get single site by ID
   */
  getSite(id: number): Observable<AdminSite> {
    return this.http.get<AdminSite>(`${this.apiUrl}/sites/${id}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign a user to a site with roles (referent and/or conservateur)
   */
  assignUserToSite(siteId: number, userId: number, referent: boolean = true, conservateur: boolean = false): Observable<any> {
    return this.http.post(`${this.apiUrl}/sites/${siteId}/assign_user/`, {
      user_id: userId,
      referent,
      conservateur
    }).pipe(catchError(this.handleError));
  }

  /**
   * Remove user from site
   */
  removeUserFromSite(siteId: number, userId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/sites/${siteId}/users/${userId}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get users assigned to a site
   */
  getSiteUsers(siteId: number): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(`${this.apiUrl}/sites/${siteId}/users/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get organismes managing a site
   */
  getSiteOrganismes(siteId: number): Observable<SiteOrganisme[]> {
    return this.http.get<SiteOrganisme[]>(`${this.apiUrl}/sites/${siteId}/organismes/`)
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
  updateSite(id: number, payload: Partial<SiteCreatePayload>): Observable<AdminSite> {
    return this.http.patch<AdminSite>(`${this.apiUrl}/sites/${id}/`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get site types (nomenclatures)
   */
  getSiteTypes(): Observable<{ id_nomenclature: number; cd_nomenclature: string; label: string }[]> {
    return this.http.get<any>('/api/nomenclatures/?type=TYPE_SITE')
      .pipe(
        map(res => res.results || res),
        catchError(this.handleError)
      );
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
    statut?: PlanStatut;
    organisme?: number;
    site?: number;
  }): Observable<PaginatedResponse<AdminPlan>> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.statut) {
      httpParams = httpParams.set('statut', params.statut);
    }
    if (params?.organisme) {
      httpParams = httpParams.set('organisme', params.organisme.toString());
    }
    if (params?.site) {
      httpParams = httpParams.set('site', params.site.toString());
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
   * Assign sites to a plan
   */
  assignSitesToPlan(planId: number, siteIds: number[]): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/assign_sites/`, {
      site_ids: siteIds
    }).pipe(catchError(this.handleError));
  }

  /**
   * Remove a site from a plan
   */
  removeSiteFromPlan(planId: number, siteId: number): Observable<any> {
    return this.http.delete(`${this.plansApiUrl}/plans/${planId}/sites/${siteId}/`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Assign referents to a plan
   */
  assignReferentsToPlan(planId: number, referentIds: number[]): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/assign_referents/`, {
      referent_ids: referentIds
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
