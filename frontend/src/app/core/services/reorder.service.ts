import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type ReorderEntity =
  | 'enjeux'
  | 'facteurs-influence'
  | 'pressions'
  | 'objectifs-long-terme'
  | 'niveaux-exigence'
  | 'objectifs-operationnels'
  | 'resultats-attendus'
  | 'indicateurs'
  | 'metriques'
  | 'operations';

export interface ReorderPayload {
  parent_id: number;
  ordered_ids: number[];
  /** Pour `indicateurs` : précise si parent est NE ou RA. */
  parent_type?: 'ne' | 'ra';
}

export interface ReorderResponse {
  updated: number;
}

export interface MoveIndicateurPayload {
  new_parent_type: 'ne' | 'ra';
  new_parent_id: number;
  position: number;
}

export interface MovePressionPayload {
  new_facteur_id: number;
  position: number;
}

@Injectable({ providedIn: 'root' })
export class ReorderService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/plans';

  reorder(entity: ReorderEntity, payload: ReorderPayload): Observable<ReorderResponse> {
    return this.http.post<ReorderResponse>(`${this.base}/${entity}/reorder/`, payload);
  }

  /**
   * Déplace un indicateur entre niveaux d'exigence (NE) ou résultats attendus
   * (RA). Endpoint dédié car l'opération change le parent (changement de FK)
   * en plus de la position — #261.
   */
  moveIndicateur(indicateurId: number, payload: MoveIndicateurPayload): Observable<unknown> {
    return this.http.post(`${this.base}/indicateurs/${indicateurId}/move/`, payload);
  }

  /**
   * Déplace une pression vers un autre facteur d'influence — #472.
   * Endpoint dédié car l'opération change le parent (FK `id_facteur_influence`)
   * en plus de la position.
   */
  movePression(pressionId: number, payload: MovePressionPayload): Observable<unknown> {
    return this.http.post(`${this.base}/pressions/${pressionId}/move/`, payload);
  }

  /**
   * Récupère le dict `{id_operation: code_affichage}` pour un plan.
   * Utilisé pour rafraîchir uniquement les codes après un DnD, sans
   * recharger la totalité de l'arbre du plan (#228 — réduit la latence).
   */
  getOperationCodes(planId: number): Observable<Record<number, string>> {
    return this.http.get<Record<number, string>>(`${this.base}/plans/${planId}/operation-codes/`);
  }
}
