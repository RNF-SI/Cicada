/**
 * Service pour le suivi de réalisation des opérations (Phase 1 - Suivis).
 *
 * Endpoints exposés par /api/plans/realisations/ et /api/plans/realisations-organismes/.
 * Source de vérité côté backend : RealisationOperationAnnee (1-1 OperationAnnee) et
 * RealisationOperationAnneeOrganisme (1-1 OperationAnneeOrganisme).
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  RealisationOperationAnnee,
  RealisationOperationAnneeOrganisme,
  RealisationUpsertPayload,
  RealisationOrganismeUpsertPayload,
} from '../models/enjeu.model';


export interface RealisationsByOperationResponse {
  operation_id: number;
  realisations: RealisationOperationAnnee[];
  total: number;
}

export interface RealisationsByPlanResponse {
  plan_id: number;
  plan_nom: string;
  realisations: RealisationOperationAnnee[];
  total: number;
}

export interface BilanCounts {
  non_demarre: number;
  en_cours: number;
  partiel: number;
  termine: number;
  abandonne: number;
  reporte: number;
  inconnu: number;
  total: number;
}

export interface BilanCategorie extends BilanCounts {
  code: string;
  label: string;
}

export interface BilanEnjeu extends BilanCounts {
  enjeu_id: number;
  libelle: string;
}

export interface BilanBudgetPair {
  previsionnel: number;
  realise: number;
}

export interface BilanResponse {
  plan_id: number;
  plan_nom: string;
  annee_min: number | null;
  annee_max: number | null;
  taux_realisation: BilanCounts;
  by_categorie_action: BilanCategorie[];
  by_enjeu: BilanEnjeu[];
  budget: {
    fonctionnement: BilanBudgetPair;
    investissement: BilanBudgetPair;
    total: BilanBudgetPair;
  };
  rh: BilanBudgetPair;
}

export interface BilanFilters {
  enjeu_id?: number;
  organisme_id?: number;
}

export interface BilanIndicateursScoreEntry {
  score: number;        // 0..5 (0 = sans donnée)
  label: string;
  count: number;
}

export interface BilanIndicateursEnjeuEntry {
  enjeu_id: number;
  libelle: string;
  moyenne: number;      // 0..5
  count: number;        // nombre d'indicateurs agrégés
}

export interface BilanIndicateursResponse {
  plan_id: number;
  plan_nom: string;
  total_indicateurs: number;
  indicateurs_evalues: number;
  taux_evaluation_pct: number;
  score_distribution: BilanIndicateursScoreEntry[];
  by_enjeu: BilanIndicateursEnjeuEntry[];
}


@Injectable({ providedIn: 'root' })
export class RealisationService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/plans';

  // -------------------------------------------------------------------------
  // RealisationOperationAnnee (réalisation annuelle)
  // -------------------------------------------------------------------------

  /** Crée ou met à jour la réalisation pour une OperationAnnee donnée. */
  upsert(payload: RealisationUpsertPayload): Observable<RealisationOperationAnnee> {
    return this.http.post<RealisationOperationAnnee>(
      `${this.apiUrl}/realisations/upsert/`,
      payload,
    );
  }

  /** Liste les réalisations d'une opération (toutes années). */
  byOperation(operationId: number): Observable<RealisationsByOperationResponse> {
    return this.http.get<RealisationsByOperationResponse>(
      `${this.apiUrl}/realisations/by-operation/${operationId}/`,
    );
  }

  /** Liste les réalisations d'un plan (toutes opérations × années). */
  byPlan(planId: number): Observable<RealisationsByPlanResponse> {
    return this.http.get<RealisationsByPlanResponse>(
      `${this.apiUrl}/realisations/by-plan/${planId}/`,
    );
  }

  /** Agrégations pour l'onglet Indicateurs du Bilan (Phase 4 - Figma #4043). */
  bilanIndicateurs(planId: number): Observable<BilanIndicateursResponse> {
    return this.http.get<BilanIndicateursResponse>(
      `${this.apiUrl}/realisations/bilan-indicateurs/${planId}/`,
    );
  }

  /** Agrégations pour la page Bilan (taux, catégories, enjeux, budgets, RH). */
  bilan(planId: number, filters?: BilanFilters): Observable<BilanResponse> {
    let params = new HttpParams();
    if (filters?.enjeu_id) params = params.set('enjeu_id', String(filters.enjeu_id));
    if (filters?.organisme_id) params = params.set('organisme_id', String(filters.organisme_id));
    return this.http.get<BilanResponse>(
      `${this.apiUrl}/realisations/bilan/${planId}/`,
      { params },
    );
  }

  /** Récupère une réalisation par id. */
  get(id: number): Observable<RealisationOperationAnnee> {
    return this.http.get<RealisationOperationAnnee>(
      `${this.apiUrl}/realisations/${id}/`,
    );
  }

  /** Édite une réalisation existante. */
  patch(id: number, payload: Partial<RealisationUpsertPayload>): Observable<RealisationOperationAnnee> {
    return this.http.patch<RealisationOperationAnnee>(
      `${this.apiUrl}/realisations/${id}/`,
      payload,
    );
  }

  /** Supprime une réalisation. */
  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/realisations/${id}/`);
  }

  // -------------------------------------------------------------------------
  // RealisationOperationAnneeOrganisme (ventilation)
  // -------------------------------------------------------------------------

  /** Upsert d'une ligne de ventilation par organisme. */
  upsertOrganisme(
    payload: RealisationOrganismeUpsertPayload,
  ): Observable<RealisationOperationAnneeOrganisme> {
    return this.http.post<RealisationOperationAnneeOrganisme>(
      `${this.apiUrl}/realisations-organismes/upsert/`,
      payload,
    );
  }

  /** Édite une ventilation existante. */
  patchOrganisme(
    id: number,
    payload: Partial<RealisationOrganismeUpsertPayload>,
  ): Observable<RealisationOperationAnneeOrganisme> {
    return this.http.patch<RealisationOperationAnneeOrganisme>(
      `${this.apiUrl}/realisations-organismes/${id}/`,
      payload,
    );
  }
}
