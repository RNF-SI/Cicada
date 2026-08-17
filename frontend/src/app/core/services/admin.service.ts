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
  SitePlansResponse,
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
  PlanDuplicateOptions,
  PlanVersionChainItem,
  ArborescenceImportReport,
  ArborescenceImportResult,
  ImportSheet,
  ImportMode,
  ParsedData,
  ForeignSheet
} from '../models/admin.model';
import { SiteCreationValidatorsResponse } from '../models/notification.model';

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

  /**
   * Libellés lisibles des champs pour les messages d'erreur de validation (#439).
   * Une valeur vide ('') affiche le message sans préfixe (le message backend est
   * déjà explicite, ex. erreurs de géométrie).
   */
  private static readonly FIELD_LABELS: Record<string, string> = {
    nom_site: 'Nom du site',
    id_inpn: 'Code INPN',
    id_local: 'Identifiant local',
    surf_off: 'Surface officielle',
    geom_geojson: '',
    geom_pt_geojson: '',
    id_type_site: 'Type de site',
    type_site_precision: 'Précision du type',
    non_field_errors: '',
  };

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
   * Aperçu (avant création) des validateurs d'une future création de site.
   * Retourne auto_validated=true si l'utilisateur courant valide lui-même.
   */
  getSiteCreationValidators(): Observable<SiteCreationValidatorsResponse> {
    return this.http.get<SiteCreationValidatorsResponse>(`${this.apiUrl}/sites/creation-validators/`)
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
   * Statistiques agrégées des plans, respectant les mêmes filtres que `getPlans`
   * (#184). Réponse : `{ total, par_statut: { draft, valide, archive, ... } }`.
   */
  getPlanStats(params?: {
    search?: string;
    statut?: PlanStatut;
    organisme?: number;
    site?: number;
    scope?: 'mine';
  }): Observable<{ total: number; par_statut: Record<string, number> }> {
    let httpParams = new HttpParams();
    if (params?.search) httpParams = httpParams.set('search', params.search);
    if (params?.statut) httpParams = httpParams.set('statut', params.statut);
    if (params?.organisme) httpParams = httpParams.set('organisme', params.organisme.toString());
    if (params?.site) httpParams = httpParams.set('site_id', params.site.toString());
    if (params?.scope) httpParams = httpParams.set('scope', params.scope);

    return this.http.get<{ total: number; par_statut: Record<string, number> }>(
      `${this.plansApiUrl}/plans/stats/`,
      { params: httpParams },
    ).pipe(catchError(this.handleError));
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
   * Récupère les plans validés/archivés associés à un ou plusieurs sites,
   * groupés par site. Utilisé à la création d'un plan pour alerter sur un
   * doublon de rang et proposer le rattachement au plan du rang précédent.
   */
  getPlansForSites(siteIds: number[]): Observable<SitePlansResponse> {
    const params = new HttpParams().set('site_ids', siteIds.join(','));
    return this.http.get<SitePlansResponse>(`${this.plansApiUrl}/plans/for-sites/`, { params })
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
   * Change plan status via dedicated endpoint with transition validation.
   * Depuis #277 refactor : ne gère plus que {draft, valide, modifie, archive}.
   * Pour piloter le workflow CSRPN, utiliser {@link changeCsrpnStep}.
   *
   * POST /api/plans/plans/{id}/change-status/
   */
  changePlanStatus(
    planId: number,
    newStatus: PlanStatut,
    options: {
      isMiParcours?: boolean;
    } = {},
  ): Observable<AdminPlan> {
    const body: Record<string, unknown> = { new_status: newStatus };
    if (options.isMiParcours) body['is_mi_parcours'] = true;
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/change-status/`, body)
      .pipe(catchError(this.handleError));
  }

  /**
   * #277 — Gérer le workflow CSRPN (étape orthogonale au statut).
   *
   * POST /api/plans/plans/{id}/csrpn-step/
   * @param planId — Plan en `draft`.
   * @param step — `avis_csrpn` | `comite_consultatif` | `arrete_pref` | `null` (annulation).
   * @param options — Dates et numéro d'arrêté optionnels.
   */
  changeCsrpnStep(
    planId: number,
    step: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref' | null,
    options: {
      dateAvisCsrpn?: string;
      dateValidationComite?: string;
      dateArretePref?: string;
      numeroArretePref?: string;
    } = {},
  ): Observable<AdminPlan> {
    const body: Record<string, unknown> = { step };
    if (options.dateAvisCsrpn) body['date_avis_csrpn'] = options.dateAvisCsrpn;
    if (options.dateValidationComite) body['date_validation_comite'] = options.dateValidationComite;
    if (options.dateArretePref) body['date_arrete_pref'] = options.dateArretePref;
    if (options.numeroArretePref) body['numero_arrete_pref'] = options.numeroArretePref;
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/csrpn-step/`, body)
      .pipe(catchError(this.handleError));
  }

  /**
   * #347 — Enregistrer/éditer/effacer une validation administrative indépendante.
   *
   * POST /api/plans/plans/{id}/admin-validation/
   * @param planId — Plan concerné (n'importe quel statut).
   * @param key — `avis_csrpn` | `comite_consultatif` | `arrete_pref`.
   * @param date — Date de validation (`null` pour effacer).
   * @param numeroArrete — N° d'arrêté (uniquement pour `arrete_pref`).
   */
  recordAdminValidation(
    planId: number,
    key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref',
    date: string | null,
    numeroArrete?: string | null,
  ): Observable<AdminPlan> {
    const body: Record<string, unknown> = { key, date };
    if (key === 'arrete_pref') body['numero_arrete_pref'] = numeroArrete ?? null;
    return this.http.post<AdminPlan>(`${this.plansApiUrl}/plans/${planId}/admin-validation/`, body)
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
   * #250 — Extend the duration of a validated plan by 1 or 2 years
   * POST /api/plans/plans/{id}/extend-duration/
   */
  extendPlanDuration(planId: number, years: 1 | 2): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(
      `${this.plansApiUrl}/plans/${planId}/extend-duration/`,
      { years }
    ).pipe(catchError(this.handleError));
  }

  /**
   * #250 — Remove the extension of a plan (annees_extension → 0)
   * POST /api/plans/plans/{id}/remove-extension/
   */
  removePlanExtension(planId: number): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(
      `${this.plansApiUrl}/plans/${planId}/remove-extension/`,
      {}
    ).pipe(catchError(this.handleError));
  }

  /**
   * #278 — Mark a validated plan as "en cours de révision" with an optional
   * link to the next rang plan.
   * POST /api/plans/plans/{id}/start-revision/
   */
  startPlanRevision(planId: number, nextRangPlanId?: number | null): Observable<AdminPlan> {
    const payload: { next_rang_plan_id?: number } = {};
    if (nextRangPlanId != null) {
      payload.next_rang_plan_id = nextRangPlanId;
    }
    return this.http.post<AdminPlan>(
      `${this.plansApiUrl}/plans/${planId}/start-revision/`,
      payload
    ).pipe(catchError(this.handleError));
  }

  /**
   * #278 — Create the draft of the next rang from a validated plan.
   * POST /api/plans/plans/{id}/create-next-rang/
   */
  createNextRangPlan(
    planId: number,
    options?: { nom?: string; annee_debut?: number; annee_fin?: number }
  ): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(
      `${this.plansApiUrl}/plans/${planId}/create-next-rang/`,
      options ?? {}
    ).pipe(catchError(this.handleError));
  }

  /**
   * #278 — Stop the revision of a plan (en_revision → false).
   * POST /api/plans/plans/{id}/end-revision/
   */
  endPlanRevision(planId: number): Observable<AdminPlan> {
    return this.http.post<AdminPlan>(
      `${this.plansApiUrl}/plans/${planId}/end-revision/`,
      {}
    ).pipe(catchError(this.handleError));
  }

  /**
   * #348 — Supprime définitivement une version (plan) de la chaîne de versions.
   * Cascade les liens, re-rattache les enfants au parent, renumérote les
   * versions restantes. Renvoie la chaîne restante.
   * POST /api/plans/plans/{id}/delete-version/
   */
  deletePlanVersion(planId: number): Observable<{ deleted_id: number; version_chain: PlanVersionChainItem[] }> {
    return this.http.post<{ deleted_id: number; version_chain: PlanVersionChainItem[] }>(
      `${this.plansApiUrl}/plans/${planId}/delete-version/`,
      {}
    ).pipe(catchError(this.handleError));
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
   * Télécharge le classeur Excel d'import d'arborescence.
   * GET /api/plans/plans/{id}/export-arborescence-xlsx/
   * @param empty true = modèle vierge ; false = pré-rempli avec le plan.
   */
  downloadArborescenceTemplate(planId: number, empty: boolean): Observable<Blob> {
    const suffix = empty ? '?empty=1' : '';
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-arborescence-xlsx/${suffix}`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge l'arborescence au format « présentation » (modèle CICADA :
   * un onglet par enjeu/FCR + grille de lecture des métriques).
   * GET /api/plans/plans/{id}/export-arborescence-presentation-xlsx/
   */
  downloadArborescencePresentation(planId: number): Observable<Blob> {
    return this.http
      .get(
        `${this.plansApiUrl}/plans/${planId}/export-arborescence-presentation-xlsx/`,
        { responseType: 'blob' },
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge le tableau de bord des indicateurs mis en forme (#638).
   * POST /api/plans/plans/{id}/export-tableau-de-bord-xlsx/
   *
   * En POST : le tableau est filtré et ses scores calculés côté client, qui
   * envoie donc les lignes telles qu'il les affiche ; le serveur ne fait que
   * la mise en forme (en-têtes et cases colorées).
   */
  downloadTableauDeBordXlsx(planId: number, payload: unknown): Observable<Blob> {
    return this.http
      .post(`${this.plansApiUrl}/plans/${planId}/export-tableau-de-bord-xlsx/`, payload, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge le tableau de suivi des actions mis en forme (#637).
   * POST /api/plans/plans/{id}/export-suivi-actions-xlsx/
   *
   * Même contrat que `downloadTableauDeBordXlsx` : le client envoie l'onglet
   * qu'il affiche, le serveur ne fait que la mise en forme.
   */
  downloadSuiviActionsXlsx(planId: number, payload: unknown): Observable<Blob> {
    return this.http
      .post(`${this.plansApiUrl}/plans/${planId}/export-suivi-actions-xlsx/`, payload, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge les fiches action du plan (Excel, un onglet par action).
   * GET /api/plans/plans/{id}/export-fiches-actions-xlsx/
   */
  downloadFichesActions(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-fiches-actions-xlsx/`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge la fiche « plan de gestion » (Word : enjeux + FCR).
   * GET /api/plans/plans/{id}/export-plan-docx/
   */
  downloadPlanDocx(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-plan-docx/`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /** Télécharge les RH prévisionnelles (Excel). */
  downloadRhPrevisionnel(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-rh-previsionnel-xlsx/`, { responseType: 'blob' })
      .pipe(catchError(this.handleError));
  }

  /** Télécharge le suivi RH (Excel, prévu/réalisé). */
  downloadRhSuivi(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-rh-suivi-xlsx/`, { responseType: 'blob' })
      .pipe(catchError(this.handleError));
  }

  /** Télécharge le budget prévisionnel (Excel). */
  downloadBudgetPrevisionnel(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-budget-previsionnel-xlsx/`, { responseType: 'blob' })
      .pipe(catchError(this.handleError));
  }

  /** Télécharge le suivi budgétaire (Excel, prévu/réalisé). */
  downloadBudgetSuivi(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-budget-suivi-xlsx/`, { responseType: 'blob' })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge l'exemple d'arborescence complet (indépendant d'un plan).
   * GET /api/plans/plans/example-arborescence-xlsx/
   */
  downloadArborescenceExample(): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/example-arborescence-xlsx/`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Valide (sans écrire) un fichier d'import d'arborescence.
   * POST /api/plans/plans/{id}/import-arborescence/validate/
   */
  validateArborescenceImport(
    planId: number,
    file: File,
    mode: ImportMode = 'create',
  ): Observable<ArborescenceImportReport> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    return this.http
      .post<ArborescenceImportReport>(
        `${this.plansApiUrl}/plans/${planId}/import-arborescence/validate/`,
        formData,
      )
      .pipe(catchError(this.handleError));
  }

  /** Résumé du contenu existant (pour la confirmation de remplacement). */
  getArborescenceExistingSummary(planId: number): Observable<Record<string, number>> {
    return this.http
      .get<Record<string, number>>(
        `${this.plansApiUrl}/plans/${planId}/import-arborescence/existing-summary/`,
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Importe l'arborescence dans le plan (création seule, transaction).
   * POST /api/plans/plans/{id}/import-arborescence/
   *
   * Ne passe PAS par `handleError` : en cas d'échec de validation (400), le
   * corps de la réponse porte le rapport (`ArborescenceImportReport`), que le
   * composant lit via `err.error`.
   */
  importArborescence(
    planId: number,
    file: File,
    mode: ImportMode = 'create',
  ): Observable<ArborescenceImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    return this.http.post<ArborescenceImportResult>(
      `${this.plansApiUrl}/plans/${planId}/import-arborescence/`,
      formData,
    );
  }

  /**
   * Schéma du format d'arborescence (onglets + colonnes).
   * GET /api/plans/plans/import-arborescence-schema/
   */
  getImportSchema(): Observable<{ sheets: ImportSheet[] }> {
    return this.http
      .get<{ sheets: ImportSheet[] }>(
        `${this.plansApiUrl}/plans/import-arborescence-schema/`,
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Valide des données d'arborescence éditées (JSON), sans fichier (#9).
   * POST /api/plans/plans/{id}/import-arborescence/validate-data/
   */
  validateArborescenceData(
    planId: number,
    data: ParsedData,
    mode: ImportMode = 'create',
  ): Observable<ArborescenceImportReport> {
    return this.http
      .post<ArborescenceImportReport>(
        `${this.plansApiUrl}/plans/${planId}/import-arborescence/validate-data/`,
        { data, mode },
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Importe des données d'arborescence éditées (JSON), sans fichier (#9/#10).
   * Ne pipe PAS handleError : le rapport d'échec (400) est lu via err.error.
   */
  importArborescenceData(
    planId: number,
    data: ParsedData,
    mode: ImportMode = 'create',
  ): Observable<ArborescenceImportResult> {
    return this.http.post<ArborescenceImportResult>(
      `${this.plansApiUrl}/plans/${planId}/import-arborescence/import-data/`,
      { data, mode },
    );
  }

  /**
   * Lit un classeur Excel quelconque (mapping #10).
   * POST /api/plans/plans/read-xlsx/
   */
  readForeignXlsx(file: File): Observable<{ sheets: ForeignSheet[] }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<{ sheets: ForeignSheet[] }>(`${this.plansApiUrl}/plans/read-xlsx/`, formData)
      .pipe(catchError(this.handleError));
  }

  // --- Module 2 : import des actions -------------------------------------

  /**
   * Télécharge le classeur d'import des actions (onglet de référence des
   * indicateurs pré-rempli + onglet Actions).
   * GET /api/plans/plans/{id}/export-actions-xlsx/
   */
  downloadActionsTemplate(planId: number): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/${planId}/export-actions-xlsx/`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Télécharge l'exemple d'actions complet (indépendant d'un plan).
   * GET /api/plans/plans/example-actions-xlsx/
   */
  downloadActionsExample(): Observable<Blob> {
    return this.http
      .get(`${this.plansApiUrl}/plans/example-actions-xlsx/`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Valide (sans écrire) un fichier d'import d'actions.
   * POST /api/plans/plans/{id}/import-actions/validate/
   */
  validateActionsImport(planId: number, file: File): Observable<ArborescenceImportReport> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<ArborescenceImportReport>(
        `${this.plansApiUrl}/plans/${planId}/import-actions/validate/`,
        formData,
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Importe les actions dans le plan (création seule, transaction).
   * POST /api/plans/plans/{id}/import-actions/
   * Ne passe PAS par `handleError` : le rapport 400 est lu via `err.error`.
   */
  importActions(planId: number, file: File): Observable<ArborescenceImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ArborescenceImportResult>(
      `${this.plansApiUrl}/plans/${planId}/import-actions/`,
      formData,
    );
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
        } else if (typeof error.error === 'string') {
          errorMessage = error.error;
        } else if (typeof error.error === 'object' && error.error !== null) {
          // Collect all validation errors with human-readable field labels (#439)
          const errors: string[] = [];
          Object.keys(error.error).forEach(key => {
            const fieldErrors = error.error[key];
            const message = Array.isArray(fieldErrors) ? fieldErrors.join(', ') : `${fieldErrors}`;
            const label = AdminService.FIELD_LABELS[key];
            // Pas de préfixe pour les erreurs non-champ ou les champs « géométrie »
            // dont le message est déjà explicite (ex. « La géométrie fournie est invalide… »).
            // `error` / `detail` sont des messages métier déjà rédigés côté backend
            // (ex. « Un brouillon est déjà en cours sur ce plan… ») → pas de préfixe.
            if (label === '' || key === 'non_field_errors' || key === 'error' || key === 'detail') {
              errors.push(message);
            } else {
              errors.push(`${label ?? key} : ${message}`);
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
      } else {
        // Statut non géré : remonter le détail/code plutôt qu'un message opaque (#439)
        errorMessage = error.error?.detail || error.error?.error
          || `Une erreur est survenue (code ${error.status}).`;
      }
    }

    return throwError(() => new Error(errorMessage));
  }
}
