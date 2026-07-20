import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
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
  /**
   * Pour `indicateurs` : précise si parent est NE ou RA.
   * Pour `operations` (#544) : `indicateur` réordonne à la portée indicateur
   * (défaut backend : `metrique`).
   */
  parent_type?: 'ne' | 'ra' | 'indicateur';
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

/** #586 — Déplacement d'une action vers un autre indicateur (état ou réponse). */
export interface MoveOperationPayload {
  new_indicateur_id: number;
  position: number;
}

/** #486 — Valeurs de formulaire simulées pour l'aperçu du code d'action. */
export interface OperationCodePreviewParams {
  /** Édition : id de l'action déjà en base (absent en création). */
  operation_id?: number | null;
  type_action_id?: number | null;
  categorie_action_reserve_id?: number | null;
  numero_manuel?: number | null;
  /** Création : parent qui déterminera la position dans le parcours du plan. */
  metrique_id?: number | null;
  indicateur_id?: number | null;
}

export interface OperationCodePreview {
  /** Code complet (`CS3`), ou null si le plan ne permet pas de le situer. */
  code: string | null;
  /** Préfixe seul (`CS`), toujours renseigné. */
  prefix: string;
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
   * Déplace une action vers un autre indicateur, d'état ou de réponse — #586.
   * Endpoint dédié : l'opération rattache l'action au nouvel indicateur et coupe
   * ses liens vers les métriques de l'indicateur quitté, en plus de la position.
   */
  moveOperation(operationId: number, payload: MoveOperationPayload): Observable<unknown> {
    return this.http.post(`${this.base}/operations/${operationId}/move/`, payload);
  }

  /**
   * Récupère le dict `{id_operation: code_affichage}` pour un plan.
   * Utilisé pour rafraîchir uniquement les codes après un DnD, sans
   * recharger la totalité de l'arbre du plan (#228 — réduit la latence).
   */
  getOperationCodes(planId: number): Observable<Record<number, string>> {
    return this.http.get<Record<number, string>>(`${this.base}/plans/${planId}/operation-codes/`);
  }

  /**
   * #486 — Code d'affichage qu'aurait une action AVANT son enregistrement.
   *
   * Le rang du code dépend du parcours de tout l'arbre du plan et des numéros
   * réservés manuellement (#485) : il ne peut pas être déduit côté client. Le
   * backend rejoue donc le calcul en simulant les valeurs du formulaire, sans
   * rien persister.
   */
  getOperationCodePreview(
    planId: number,
    params: OperationCodePreviewParams,
  ): Observable<OperationCodePreview> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value != null) httpParams = httpParams.set(key, String(value));
    }
    return this.http.get<OperationCodePreview>(
      `${this.base}/plans/${planId}/operation-code-preview/`,
      { params: httpParams },
    );
  }
}
