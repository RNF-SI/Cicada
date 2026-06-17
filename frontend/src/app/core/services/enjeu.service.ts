/**
 * Service pour la gestion des Enjeux, FCR et Responsabilites.
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, tap, catchError, throwError, map } from 'rxjs';

import {
  Enjeu,
  EnjeuCreatePayload,
  FcrCreatePayload,
  EnjeuUpdatePayload,
  PlanEnjeuxResponse,
  EnjeuStats,
  EnjeuFilters,
  PaginatedEnjeuxResponse,
  FacteurInfluence,
  FacteurInfluenceCreatePayload,
  Pression,
  PressionCreatePayload,
  ObjectifLongTerme,
  ObjectifLongTermeCreatePayload,
  NiveauExigence,
  NiveauExigenceCreatePayload,
  ObjectifOperationnel,
  ObjectifOperationnelCreatePayload,
  ResultatAttendu,
  ResultatAttenduCreatePayload,
  Indicateur,
  IndicateurCreatePayload,
  Metrique,
  MetriqueCreatePayload,
  Mesure,
  MesureCreatePayload,
  Operation,
  OperationCreatePayload,
  Responsabilite,
  ResponsabiliteCreatePayload,
  SiteResponsabilitesResponse,
  ResponsabiliteStats,
  TaxonRef,
  HabitatRef
} from '../models/enjeu.model';
import { MindmapNode } from '../models/mindmap.model';

/** #355 — Réponse de l'endpoint de surcharge du niveau de réalisation global. */
export interface GlobalRealisationResponse {
  id_operation: number;
  niveau_realisation_global_mnemonique: string | null;
  niveau_realisation_global_label: string | null;
  niveau_realisation_global_manuel: boolean;
}

/** #355 — Évaluation globale d'un indicateur (tableau de bord). */
export interface IndicateurMetriqueGlobal {
  id_metrique: number;
  nom_metrique: string;
  etat_reference: string | null;
  sens_variation: string | null;
  series: { annee: number; valeur: string | null; score: number | null }[];
  etat_courant: { annee: number; score: number } | null;
  moyenne: number | null;
  tendance: 'hausse' | 'baisse' | 'stable';
}

export interface IndicateurGlobalResponse {
  id_indicateur: number;
  nom_indicateur: string;
  type_indicateur: string | null;
  type_indicateur_label: string | null;
  metriques: IndicateurMetriqueGlobal[];
  serie: { annee: number; score: number }[];
  etat_courant_score: number | null;
  moyenne_score: number | null;
  tendance: 'hausse' | 'baisse' | 'stable';
}

@Injectable({
  providedIn: 'root'
})
export class EnjeuService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/plans';

  // Signals for reactive state
  private loadingSignal = signal<boolean>(false);
  private errorSignal = signal<string | null>(null);
  private currentPlanEnjeuxSignal = signal<PlanEnjeuxResponse | null>(null);

  // Public readonly signals
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();
  readonly currentPlanEnjeux = this.currentPlanEnjeuxSignal.asReadonly();

  // Computed signals
  readonly hasEnjeux = computed(() => {
    const data = this.currentPlanEnjeuxSignal();
    return data ? (data.total_enjeux + data.total_fcr) > 0 : false;
  });

  readonly totalCount = computed(() => {
    const data = this.currentPlanEnjeuxSignal();
    return data ? data.total_enjeux + data.total_fcr : 0;
  });

  // ==========================================================================
  // Enjeux CRUD
  // ==========================================================================

  /**
   * Build HttpParams from filters.
   */
  private buildEnjeuParams(filters?: EnjeuFilters): HttpParams {
    let params = new HttpParams();

    if (filters) {
      if (filters.id_pg) params = params.set('id_pg', filters.id_pg.toString());
      if (filters.categorie) params = params.set('categorie', filters.categorie);
      if (filters.is_enjeu !== undefined) params = params.set('is_enjeu', filters.is_enjeu.toString());
      if (filters.is_fcr !== undefined) params = params.set('is_fcr', filters.is_fcr.toString());
      if (filters.rang) params = params.set('rang', filters.rang.toString());
      if (filters.rang_min) params = params.set('rang_min', filters.rang_min.toString());
      if (filters.rang_max) params = params.set('rang_max', filters.rang_max.toString());
      if (filters.categorie_ecologique !== undefined) {
        params = params.set('categorie_ecologique', filters.categorie_ecologique.toString());
      }
      if (filters.habitat !== undefined) params = params.set('habitat', filters.habitat.toString());
      if (filters.espece !== undefined) params = params.set('espece', filters.espece.toString());
      if (filters.processus !== undefined) params = params.set('processus', filters.processus.toString());
      if (filters.categorie_fcr) params = params.set('categorie_fcr', filters.categorie_fcr);
      if (filters.has_taxons !== undefined) params = params.set('has_taxons', filters.has_taxons.toString());
      if (filters.has_habitats !== undefined) params = params.set('has_habitats', filters.has_habitats.toString());
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
    }

    return params;
  }

  /**
   * Get paginated list of enjeux.
   */
  getEnjeux(filters?: EnjeuFilters): Observable<PaginatedEnjeuxResponse> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    const params = this.buildEnjeuParams(filters);

    return this.http.get<PaginatedEnjeuxResponse>(`${this.apiUrl}/enjeux/`, { params }).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error loading enjeux');
        return throwError(() => err);
      })
    );
  }

  /**
   * Get enjeux and FCR for a specific plan.
   * Uses cached data if already loaded for the same plan.
   */
  getPlanEnjeux(planId: number, forceRefresh = false): Observable<PlanEnjeuxResponse> {
    const cached = this.currentPlanEnjeuxSignal();
    if (!forceRefresh && cached && cached.plan_id === planId) {
      return of(cached);
    }

    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.get<PlanEnjeuxResponse>(`${this.apiUrl}/enjeux/by-plan/${planId}/`).pipe(
      tap(response => {
        this.currentPlanEnjeuxSignal.set(response);
        this.loadingSignal.set(false);
      }),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error loading plan enjeux');
        return throwError(() => err);
      })
    );
  }

  /**
   * #355 — Surcharge manuelle du niveau de réalisation GLOBAL d'une action.
   * `mnemonique = null` retire la surcharge (retour au calcul automatique).
   */
  setGlobalRealisation(
    operationId: number,
    niveauId: number | null,
    commentaire?: string
  ): Observable<GlobalRealisationResponse> {
    const url = `${this.apiUrl}/realisations/global-realisation/${operationId}/`;
    if (niveauId === null) {
      return this.http.delete<GlobalRealisationResponse>(url);
    }
    return this.http.post<GlobalRealisationResponse>(url, {
      id_niveau_realisation: niveauId,
      commentaire_override: commentaire ?? '',
    });
  }

  /**
   * #355 — Évaluation globale d'un indicateur (série annuelle, état courant,
   * moyenne, tendance) pour la page globale du tableau de bord.
   */
  getIndicateurGlobal(indicateurId: number): Observable<IndicateurGlobalResponse> {
    return this.http.get<IndicateurGlobalResponse>(
      `${this.apiUrl}/indicateurs/${indicateurId}/global/`
    );
  }

  /**
   * Get a single enjeu by ID.
   */
  getEnjeu(id: number): Observable<Enjeu> {
    return this.http.get<Enjeu>(`${this.apiUrl}/enjeux/${id}/`);
  }

  /**
   * Create a new enjeu.
   */
  createEnjeu(payload: EnjeuCreatePayload): Observable<Enjeu> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.post<Enjeu>(`${this.apiUrl}/enjeux/`, payload).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error creating enjeu');
        return throwError(() => err);
      })
    );
  }

  /**
   * Create a new FCR.
   */
  createFcr(payload: FcrCreatePayload): Observable<Enjeu> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.post<Enjeu>(`${this.apiUrl}/enjeux/`, payload).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error creating FCR');
        return throwError(() => err);
      })
    );
  }

  /**
   * Update an existing enjeu or FCR.
   */
  updateEnjeu(id: number, payload: EnjeuUpdatePayload): Observable<Enjeu> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.patch<Enjeu>(`${this.apiUrl}/enjeux/${id}/`, payload).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error updating enjeu');
        return throwError(() => err);
      })
    );
  }

  /**
   * Delete an enjeu or FCR.
   */
  deleteEnjeu(id: number): Observable<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.delete<void>(`${this.apiUrl}/enjeux/${id}/`).pipe(
      tap(() => this.loadingSignal.set(false)),
      catchError(err => {
        this.loadingSignal.set(false);
        this.errorSignal.set(err.message || 'Error deleting enjeu');
        return throwError(() => err);
      })
    );
  }

  /**
   * Get enjeu statistics.
   */
  getEnjeuStats(): Observable<EnjeuStats> {
    return this.http.get<EnjeuStats>(`${this.apiUrl}/enjeux/stats/`);
  }

  // ==========================================================================
  // Taxon operations
  // ==========================================================================

  /**
   * Add a taxon to an enjeu.
   */
  addTaxon(enjeuId: number, taxon: TaxonRef): Observable<TaxonRef> {
    return this.http.post<TaxonRef>(
      `${this.apiUrl}/enjeux/${enjeuId}/add_taxon/`,
      taxon
    );
  }

  /**
   * Remove a taxon from an enjeu.
   */
  removeTaxon(enjeuId: number, cdNom: number): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/enjeux/${enjeuId}/remove_taxon/${cdNom}/`
    );
  }

  // ==========================================================================
  // Habitat operations
  // ==========================================================================

  /**
   * Add a habitat to an enjeu.
   */
  addHabitat(enjeuId: number, habitat: HabitatRef): Observable<HabitatRef> {
    return this.http.post<HabitatRef>(
      `${this.apiUrl}/enjeux/${enjeuId}/add_habitat/`,
      habitat
    );
  }

  /**
   * Remove a habitat from an enjeu.
   */
  removeHabitat(enjeuId: number, cdHab: string): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/enjeux/${enjeuId}/remove_habitat/${encodeURIComponent(cdHab)}/`
    );
  }

  // ==========================================================================
  // Facteurs d'Influence CRUD
  // ==========================================================================

  /**
   * Create a new facteur d'influence.
   */
  createFacteurInfluence(payload: FacteurInfluenceCreatePayload): Observable<FacteurInfluence> {
    return this.http.post<FacteurInfluence>(`${this.apiUrl}/facteurs-influence/`, payload);
  }

  /**
   * Update a facteur d'influence.
   */
  updateFacteurInfluence(id: number, payload: Partial<FacteurInfluenceCreatePayload>): Observable<FacteurInfluence> {
    return this.http.patch<FacteurInfluence>(`${this.apiUrl}/facteurs-influence/${id}/`, payload);
  }

  /**
   * Delete a facteur d'influence.
   */
  deleteFacteurInfluence(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/facteurs-influence/${id}/`);
  }

  // ==========================================================================
  // Pressions CRUD
  // ==========================================================================

  /**
   * Create a new pression.
   */
  createPression(payload: PressionCreatePayload): Observable<Pression> {
    return this.http.post<Pression>(`${this.apiUrl}/pressions/`, payload);
  }

  /**
   * Update a pression.
   */
  updatePression(id: number, payload: Partial<PressionCreatePayload>): Observable<Pression> {
    return this.http.patch<Pression>(`${this.apiUrl}/pressions/${id}/`, payload);
  }

  /**
   * Delete a pression.
   */
  deletePression(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/pressions/${id}/`);
  }

  // ==========================================================================
  // Objectifs à Long Terme CRUD
  // ==========================================================================

  createObjectifLongTerme(payload: ObjectifLongTermeCreatePayload): Observable<ObjectifLongTerme> {
    return this.http.post<ObjectifLongTerme>(`${this.apiUrl}/objectifs-long-terme/`, payload);
  }

  updateObjectifLongTerme(id: number, payload: Partial<ObjectifLongTermeCreatePayload>): Observable<ObjectifLongTerme> {
    return this.http.patch<ObjectifLongTerme>(`${this.apiUrl}/objectifs-long-terme/${id}/`, payload);
  }

  deleteObjectifLongTerme(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/objectifs-long-terme/${id}/`);
  }

  // ==========================================================================
  // Niveaux d'Exigence CRUD
  // ==========================================================================

  createNiveauExigence(payload: NiveauExigenceCreatePayload): Observable<NiveauExigence> {
    return this.http.post<NiveauExigence>(`${this.apiUrl}/niveaux-exigence/`, payload);
  }

  updateNiveauExigence(id: number, payload: Partial<NiveauExigenceCreatePayload>): Observable<NiveauExigence> {
    return this.http.patch<NiveauExigence>(`${this.apiUrl}/niveaux-exigence/${id}/`, payload);
  }

  deleteNiveauExigence(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/niveaux-exigence/${id}/`);
  }

  // ==========================================================================
  // Objectifs Opérationnels CRUD
  // ==========================================================================

  createObjectifOperationnel(payload: ObjectifOperationnelCreatePayload): Observable<ObjectifOperationnel> {
    return this.http.post<ObjectifOperationnel>(`${this.apiUrl}/objectifs-operationnels/`, payload);
  }

  updateObjectifOperationnel(id: number, payload: Partial<ObjectifOperationnelCreatePayload>): Observable<ObjectifOperationnel> {
    return this.http.patch<ObjectifOperationnel>(`${this.apiUrl}/objectifs-operationnels/${id}/`, payload);
  }

  deleteObjectifOperationnel(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/objectifs-operationnels/${id}/`);
  }

  // ==========================================================================
  // Résultats Attendus CRUD
  // ==========================================================================

  createResultatAttendu(payload: ResultatAttenduCreatePayload): Observable<ResultatAttendu> {
    return this.http.post<ResultatAttendu>(`${this.apiUrl}/resultats-attendus/`, payload);
  }

  updateResultatAttendu(id: number, payload: Partial<ResultatAttenduCreatePayload>): Observable<ResultatAttendu> {
    return this.http.patch<ResultatAttendu>(`${this.apiUrl}/resultats-attendus/${id}/`, payload);
  }

  deleteResultatAttendu(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/resultats-attendus/${id}/`);
  }

  // ==========================================================================
  // Indicateurs CRUD
  // ==========================================================================

  /** Détail d'un indicateur (inclut ses métriques avec seuils, mesures, etc.). */
  getIndicateur(id: number): Observable<Indicateur> {
    return this.http.get<Indicateur>(`${this.apiUrl}/indicateurs/${id}/`);
  }

  createIndicateur(payload: IndicateurCreatePayload): Observable<Indicateur> {
    return this.http.post<Indicateur>(`${this.apiUrl}/indicateurs/`, payload);
  }

  updateIndicateur(id: number, payload: Partial<IndicateurCreatePayload>): Observable<Indicateur> {
    return this.http.patch<Indicateur>(`${this.apiUrl}/indicateurs/${id}/`, payload);
  }

  deleteIndicateur(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/indicateurs/${id}/`);
  }

  /**
   * Duplique un indicateur (avec ses métriques et liens taxonomiques) sur
   * un ou plusieurs niveaux d'exigence et/ou résultats attendus cibles
   * (#262). Les mesures (données dans le temps) ne sont pas copiées.
   */
  duplicateIndicateur(id: number, payload: { ne_ids: number[]; ra_ids: number[] }):
    Observable<{ created_ids: number[]; count: number }> {
    return this.http.post<{ created_ids: number[]; count: number }>(
      `${this.apiUrl}/indicateurs/${id}/duplicate/`,
      payload,
    );
  }

  // ==========================================================================
  // Metriques CRUD
  // ==========================================================================

  createMetrique(payload: MetriqueCreatePayload): Observable<Metrique> {
    return this.http.post<Metrique>(`${this.apiUrl}/metriques/`, payload);
  }

  updateMetrique(id: number, payload: Partial<MetriqueCreatePayload>): Observable<Metrique> {
    return this.http.patch<Metrique>(`${this.apiUrl}/metriques/${id}/`, payload);
  }

  deleteMetrique(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/metriques/${id}/`);
  }

  // ==========================================================================
  // Mesures CRUD
  // ==========================================================================

  /** Liste les mesures d'une métrique (toutes années). */
  getMesuresByMetrique(metriqueId: number): Observable<Mesure[]> {
    return this.http.get<any>(`${this.apiUrl}/mesures/`, {
      params: { id_metrique: String(metriqueId), page_size: '100' },
    }).pipe(
      map(res => (res?.results ?? res ?? []) as Mesure[]),
    );
  }

  createMesure(payload: MesureCreatePayload): Observable<Mesure> {
    return this.http.post<Mesure>(`${this.apiUrl}/mesures/`, payload);
  }

  // ==========================================================================
  // IndicateurMesure — saisie annuelle au niveau indicateur
  // ==========================================================================

  /** Score auto calculé pour un (indicateur, année). */
  getIndicatorAutoScore(idIndicateur: number, annee: number): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/indicateur-mesures/auto-score/`,
      { params: { id_indicateur: String(idIndicateur), annee: String(annee) } },
    );
  }

  /** Score effectif (override si présent, sinon auto). */
  getIndicatorResolved(idIndicateur: number, annee: number): Observable<any> {
    return this.http.get<any>(
      `${this.apiUrl}/indicateur-mesures/resolved/`,
      { params: { id_indicateur: String(idIndicateur), annee: String(annee) } },
    );
  }

  /** Upsert d'une saisie d'indicateur (override + commentaire). */
  upsertIndicateurMesure(payload: {
    id_indicateur: number; annee: number;
    score_override?: number | null; commentaire_override?: string | null;
  }): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/indicateur-mesures/upsert/`,
      payload,
    );
  }

  /** Supprime un override (passage en mode auto). */
  deleteIndicateurMesure(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/indicateur-mesures/${id}/`);
  }

  /** Crée un nouvel indicateur de réponse + métrique liés à l'opération. */
  createOperationResponseIndicator(
    operationId: number,
    payload: {
      nom_indicateur: string;
      nom_metrique?: string;
      type_metrique_id?: number | null;
      valeur_cible?: string;
    },
  ): Observable<{
    id_metrique: number; id_indicateur: number;
    nom_indicateur: string; nom_metrique: string;
    etat_reference: string; type_metrique: number | null;
  }> {
    return this.http.post<any>(
      `${this.apiUrl}/operations/${operationId}/create-indicator/`,
      payload,
    );
  }

  /** Retire le lien entre l'opération et une métrique (n'efface pas l'indicateur). */
  unlinkOperationMetrique(operationId: number, metriqueId: number): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/operations/${operationId}/remove-metrique/`,
      { metrique_id: metriqueId },
    );
  }


  updateMesure(id: number, payload: Partial<MesureCreatePayload>): Observable<Mesure> {
    return this.http.patch<Mesure>(`${this.apiUrl}/mesures/${id}/`, payload);
  }

  deleteMesure(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/mesures/${id}/`);
  }

  // ==========================================================================
  // Operations CRUD
  // ==========================================================================

  getOperation(id: number): Observable<Operation> {
    return this.http.get<Operation>(`${this.apiUrl}/operations/${id}/`);
  }

  createOperation(payload: OperationCreatePayload): Observable<Operation> {
    return this.http.post<Operation>(`${this.apiUrl}/operations/`, payload);
  }

  updateOperation(id: number, payload: Partial<OperationCreatePayload>): Observable<Operation> {
    return this.http.patch<Operation>(`${this.apiUrl}/operations/${id}/`, payload);
  }

  deleteOperation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/operations/${id}/`);
  }

  getOperationsByIndicateur(indicateurId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/operations/by-indicateur/${indicateurId}/`);
  }

  getOperationsByPlan(planId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/operations/by-plan/${planId}/`);
  }

  addMetriqueToOperation(operationId: number, metriqueId: number): Observable<Operation> {
    return this.http.post<Operation>(
      `${this.apiUrl}/operations/${operationId}/add-metrique/`,
      { metrique_id: metriqueId }
    );
  }

  removeMetriqueFromOperation(operationId: number, metriqueId: number): Observable<Operation> {
    return this.http.post<Operation>(
      `${this.apiUrl}/operations/${operationId}/remove-metrique/`,
      { metrique_id: metriqueId }
    );
  }

  getMetriquesByIndicateur(indicateurId: number): Observable<Metrique[]> {
    return this.http.get<any>(`${this.apiUrl}/indicateurs/${indicateurId}/`).pipe(
      tap(() => {}),
      catchError(err => throwError(() => err))
    );
  }

  // ==========================================================================
  // Responsabilites CRUD
  // ==========================================================================

  /**
   * Get paginated list of responsabilites.
   */
  getResponsabilites(filters?: {
    id_site?: number;
    type_responsabilite?: string;
    niveau_responsabilite?: string;
    search?: string;
    page?: number;
  }): Observable<{ count: number; results: Responsabilite[] }> {
    let params = new HttpParams();

    if (filters) {
      if (filters.id_site) params = params.set('id_site', filters.id_site.toString());
      if (filters.type_responsabilite) params = params.set('type_responsabilite', filters.type_responsabilite);
      if (filters.niveau_responsabilite) params = params.set('niveau_responsabilite', filters.niveau_responsabilite);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
    }

    return this.http.get<{ count: number; results: Responsabilite[] }>(
      `${this.apiUrl}/responsabilites/`,
      { params }
    );
  }

  /**
   * Get responsabilites for a specific site.
   */
  getSiteResponsabilites(siteId: number): Observable<SiteResponsabilitesResponse> {
    return this.http.get<SiteResponsabilitesResponse>(
      `${this.apiUrl}/responsabilites/by-site/${siteId}/`
    );
  }

  /**
   * Get a single responsabilite by ID.
   */
  getResponsabilite(id: number): Observable<Responsabilite> {
    return this.http.get<Responsabilite>(`${this.apiUrl}/responsabilites/${id}/`);
  }

  /**
   * Create a new responsabilite.
   */
  createResponsabilite(payload: ResponsabiliteCreatePayload): Observable<Responsabilite> {
    return this.http.post<Responsabilite>(`${this.apiUrl}/responsabilites/`, payload);
  }

  /**
   * Update an existing responsabilite.
   */
  updateResponsabilite(
    id: number,
    payload: Partial<ResponsabiliteCreatePayload>
  ): Observable<Responsabilite> {
    return this.http.patch<Responsabilite>(`${this.apiUrl}/responsabilites/${id}/`, payload);
  }

  /**
   * Delete a responsabilite.
   */
  deleteResponsabilite(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/responsabilites/${id}/`);
  }

  /**
   * Get responsabilite statistics.
   */
  getResponsabiliteStats(): Observable<ResponsabiliteStats> {
    return this.http.get<ResponsabiliteStats>(`${this.apiUrl}/responsabilites/stats/`);
  }

  // ==========================================================================
  // Utility methods
  // ==========================================================================

  /**
   * Clear the current plan enjeux cache.
   */
  clearCurrentPlanEnjeux(): void {
    this.currentPlanEnjeuxSignal.set(null);
  }

  updatePlanEnjeuxCache(data: PlanEnjeuxResponse): void {
    this.currentPlanEnjeuxSignal.set(data);
  }

  /**
   * Refresh the current plan enjeux data.
   */
  refreshCurrentPlanEnjeux(): void {
    const current = this.currentPlanEnjeuxSignal();
    if (current) {
      this.getPlanEnjeux(current.plan_id, true).subscribe();
    }
  }

  /**
   * Get the mindmap tree data for a plan.
   */
  getMindmapData(planId: number): Observable<MindmapNode> {
    return this.http.get<MindmapNode>(`${this.apiUrl}/plans/${planId}/mindmap/`);
  }

  /**
   * Get the inverse mindmap tree data for a plan (Actions → Enjeux).
   */
  getMindmapInverseData(planId: number): Observable<MindmapNode> {
    return this.http.get<MindmapNode>(`${this.apiUrl}/plans/${planId}/mindmap-inverse/`);
  }
}
