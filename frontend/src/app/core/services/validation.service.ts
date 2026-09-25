/**
 * Service pour la gestion des validations.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import {
  ValidationRequest,
  ValidationRequestListItem,
  RequestValidatorsResponse,
  ValidationCountResponse,
  ValidationApproveData,
  ValidationRejectData,
  ValidationActionResponse,
  SiteAccessRequestData,
  PlanAccessRequestData,
  ModuleAccessRequestData,
  PublicRegistrationData,
  PublicRegistrationResponse,
  RegistrationStatusResponse
} from '../models/notification.model';
import { NotificationService } from './notification.service';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Forme imbriquee renvoyee par `UsersPagination`, la classe de pagination par
 * defaut du projet (`REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS`) : le total vit
 * dans `pagination.count` et non a la racine.
 */
interface NestedPaginatedResponse<T> {
  links?: { next: string | null; previous: string | null };
  pagination?: {
    count: number;
    current_page: number;
    total_pages: number;
    page_size: number;
    has_next: boolean;
    has_previous: boolean;
  };
  results: T[];
}

/**
 * Normalise les deux formes de reponse paginee (plate DRF ou imbriquee
 * `UsersPagination`) vers `PaginatedResponse`.
 *
 * Sans cela, `count` est `undefined` cote appelant : le paginateur recoit une
 * longueur nulle et le bouton « page suivante » reste desactive (#658).
 */
function normalizePagination<T>(
  response: PaginatedResponse<T> | NestedPaginatedResponse<T>
): PaginatedResponse<T> {
  const nested = response as NestedPaginatedResponse<T>;
  if (nested.pagination) {
    return {
      count: nested.pagination.count,
      next: nested.links?.next ?? null,
      previous: nested.links?.previous ?? null,
      results: nested.results ?? []
    };
  }
  const flat = response as PaginatedResponse<T>;
  return {
    count: flat.count ?? 0,
    next: flat.next ?? null,
    previous: flat.previous ?? null,
    results: flat.results ?? []
  };
}

export interface ValidationFilters {
  status?: string;
  request_type?: string;
  page?: number;
}

/**
 * Interface pour les options de type/statut retournées par l'API.
 */
export interface ValidationTypeOption {
  value: string;
  label: string;
}

/**
 * Réponse de l'endpoint /api/validations/types/
 */
export interface ValidationTypesResponse {
  request_types: ValidationTypeOption[];
  statuses: ValidationTypeOption[];
}

@Injectable({
  providedIn: 'root'
})
export class ValidationService {
  private readonly http = inject(HttpClient);
  private readonly notificationService = inject(NotificationService);
  private readonly apiUrl = '/api/validations';
  private readonly authUrl = '/api/auth';

  /**
   * Recupere la liste paginee des demandes de validation.
   */
  getValidationRequests(filters?: ValidationFilters): Observable<PaginatedResponse<ValidationRequestListItem>> {
    let params = new HttpParams();

    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    if (filters?.request_type) {
      params = params.set('request_type', filters.request_type);
    }
    if (filters?.page) {
      params = params.set('page', filters.page.toString());
    }

    return this.http
      .get<PaginatedResponse<ValidationRequestListItem> | NestedPaginatedResponse<ValidationRequestListItem>>(
        this.apiUrl + '/',
        { params }
      )
      .pipe(map(response => normalizePagination(response)));
  }

  /**
   * Recupere une demande de validation par ID.
   */
  getValidationRequest(id: number): Observable<ValidationRequest> {
    return this.http.get<ValidationRequest>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Recupere le compteur de demandes en attente.
   */
  getPendingCount(): Observable<ValidationCountResponse> {
    return this.http.get<ValidationCountResponse>(`${this.apiUrl}/pending_count/`).pipe(
      tap(response => {
        this.notificationService.updatePendingValidationsCount(response.pending_count);
      })
    );
  }

  /**
   * Recupere les types de demandes et statuts disponibles.
   * Permet de synchroniser dynamiquement les filtres avec le backend.
   */
  getTypes(): Observable<ValidationTypesResponse> {
    return this.http.get<ValidationTypesResponse>(`${this.apiUrl}/types/`);
  }

  /**
   * Recupere les demandes faites par l'utilisateur courant.
   */
  getMyRequests(): Observable<ValidationRequestListItem[]> {
    return this.http.get<ValidationRequestListItem[]>(`${this.apiUrl}/my_requests/`);
  }

  /**
   * Récupère les validateurs (nom + rôle) pouvant traiter une demande.
   */
  getRequestValidators(id: number): Observable<RequestValidatorsResponse> {
    return this.http.get<RequestValidatorsResponse>(`${this.apiUrl}/${id}/validators/`);
  }

  /**
   * Approuve une demande de validation.
   */
  approveRequest(id: number, data?: ValidationApproveData): Observable<ValidationActionResponse> {
    return this.http.post<ValidationActionResponse>(`${this.apiUrl}/${id}/approve/`, data || {}).pipe(
      tap(() => {
        // Rafraichir les compteurs
        this.notificationService.refresh().subscribe();
      })
    );
  }

  /**
   * Rejette une demande de validation.
   */
  rejectRequest(id: number, data: ValidationRejectData): Observable<ValidationActionResponse> {
    return this.http.post<ValidationActionResponse>(`${this.apiUrl}/${id}/reject/`, data).pipe(
      tap(() => {
        // Rafraichir les compteurs
        this.notificationService.refresh().subscribe();
      })
    );
  }

  /**
   * Annule une demande (par le demandeur).
   */
  cancelRequest(id: number): Observable<ValidationActionResponse> {
    return this.http.post<ValidationActionResponse>(`${this.apiUrl}/${id}/cancel/`, {});
  }

  /**
   * Demande l'acces a un site.
   */
  requestSiteAccess(siteSlug: string, data?: SiteAccessRequestData): Observable<ValidationRequest> {
    return this.http.post<ValidationRequest>(`/api/users/sites/${siteSlug}/request_access/`, data || {});
  }

  /**
   * Demande de lier un site a son organisme.
   */
  requestSiteOrgLink(siteSlug: string, data?: { justification?: string }): Observable<ValidationRequest> {
    return this.http.post<ValidationRequest>(`/api/users/sites/${siteSlug}/request_org_link/`, data || {});
  }

  /**
   * Demande a devenir referent d'un site.
   */
  requestReferent(siteSlug: string, data?: { justification?: string }): Observable<ValidationRequest> {
    return this.http.post<ValidationRequest>(`/api/users/sites/${siteSlug}/request_referent/`, data || {});
  }

  /**
   * Invite un organisme a rejoindre un site (referent uniquement).
   */
  inviteOrganismeToSite(siteSlug: string, data: { organisme_id: number; justification?: string }): Observable<{ id: number; message: string }> {
    return this.http.post<{ id: number; message: string }>(`/api/users/sites/${siteSlug}/invite_organisme/`, data);
  }

  /**
   * Invite un utilisateur a rejoindre un site (referent uniquement).
   */
  inviteUserToSite(siteSlug: string, data: { user_id: number; justification?: string }): Observable<{ id: number; message: string }> {
    return this.http.post<{ id: number; message: string }>(`/api/users/sites/${siteSlug}/invite_user/`, data);
  }

  /**
   * Demande l'acces a un plan de gestion.
   */
  requestPlanAccess(planId: number, data?: PlanAccessRequestData): Observable<ValidationRequest> {
    return this.http.post<ValidationRequest>(`${this.apiUrl}/request_plan_access/`, {
      plan_id: planId,
      ...data
    });
  }

  /**
   * Demande a lier un site a un plan de gestion.
   */
  requestPlanSiteLink(planId: number, siteId: number, data?: { justification?: string }): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/request_plan_site_link/`, {
      plan_id: planId,
      site_id: siteId,
      ...data
    });
  }

  /**
   * Demande l'acces a un module.
   */
  requestModuleAccess(data: ModuleAccessRequestData): Observable<ValidationRequest> {
    return this.http.post<ValidationRequest>(`${this.apiUrl}/request_module_access/`, data);
  }

  /**
   * Octroie l'acces a un module directement (admin).
   */
  grantModuleAccess(data: { user_id: number; module_code: string }): Observable<ValidationActionResponse> {
    return this.http.post<ValidationActionResponse>(`${this.apiUrl}/grant_module_access/`, data);
  }

  /**
   * Revoque l'acces a un module (admin).
   */
  revokeModuleAccess(data: { user_id: number; module_code: string }): Observable<ValidationActionResponse> {
    return this.http.post<ValidationActionResponse>(`${this.apiUrl}/revoke_module_access/`, data);
  }

  /**
   * Recupere la liste des modules auxquels l'utilisateur a acces.
   */
  getMyModuleAccess(): Observable<{ modules: string[] }> {
    return this.http.get<{ modules: string[] }>(`${this.apiUrl}/my_module_access/`);
  }

  // ==================== Inscription publique ====================

  /**
   * Soumet une inscription publique.
   */
  register(data: PublicRegistrationData): Observable<PublicRegistrationResponse> {
    return this.http.post<PublicRegistrationResponse>(`${this.authUrl}/register/`, data);
  }

  /**
   * Verifie le statut d'une inscription.
   */
  checkRegistrationStatus(email: string): Observable<RegistrationStatusResponse> {
    const params = new HttpParams().set('email', email);
    return this.http.get<RegistrationStatusResponse>(`${this.authUrl}/registration-status/`, { params });
  }

  // ==================== Gestion des roles admin ====================

  /**
   * Demande la promotion d'un utilisateur en admin_og.
   */
  requestAdminPromotion(targetUserId: number, justification: string): Observable<{ id: number; message: string }> {
    return this.http.post<{ id: number; message: string }>(`${this.apiUrl}/request_admin_promotion/`, {
      target_user_id: targetUserId,
      justification
    });
  }

  /**
   * Demande la retrogradation d'un admin_og en utilisateur simple.
   */
  requestAdminDemotion(targetUserId: number, justification: string): Observable<{ id: number; message: string }> {
    return this.http.post<{ id: number; message: string }>(`${this.apiUrl}/request_admin_demotion/`, {
      target_user_id: targetUserId,
      justification
    });
  }
}
