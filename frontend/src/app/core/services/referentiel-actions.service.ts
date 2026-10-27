import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * #751 — actions dont le type est à actualiser après un passage du référentiel
 * des types d'action (codification Eden 62 → Gestref V1, puis versions
 * suivantes). Backend : `apps/plans/views_referentiel.py`.
 */

export interface ActionAActualiser {
  id_operation: number;
  libelle: string;
  code_affichage: string | null;
  enjeu_slug: string | null;
  statut: 'applique' | 'a_actualiser' | 'actualise';
  confiance: 'sure' | 'probable' | 'a_arbitrer';
  ancien_code: string;
  ancien_libelle: string;
  suggestion_code: string;
  suggestion_libelle: string;
  suggestion_id: number | null;
  note: string;
  type_actuel_id: number | null;
  type_actuel_code: string | null;
  type_actuel_libelle: string | null;
  actualise_par: string | null;
  actualise_le: string | null;
}

export interface PlanAActualiser {
  id_pg: number | null;
  nom: string;
  slug: string | null;
  statut: string | null;
  a_actualiser: ActionAActualiser[];
  actualisees: ActionAActualiser[];
  automatiques: ActionAActualiser[];
}

export interface ActionsAActualiserReponse {
  passage: { id: number; depuis: string; vers: string; date: string } | null;
  total_a_actualiser: number;
  plans: PlanAActualiser[];
}

/** Ce que la fiche d'une action expose tant que son type est à choisir. */
export interface TypeActionAActualiser {
  passage: number;
  version: string;
  ancien_code: string;
  ancien_libelle: string;
  suggestion_id: number | null;
  suggestion_code: string;
  suggestion_libelle: string;
  note: string;
}

/** Réponse 409 : un autre référent a choisi le type entre-temps. */
export interface TypeDejaModifie {
  code: 'type_deja_modifie';
  detail: string;
  id_type_action: number | null;
  type_action_label: string;
  actualise_par: string;
}

@Injectable({ providedIn: 'root' })
export class ReferentielActionsService {
  private readonly http = inject(HttpClient);

  aActualiser(planId?: number | null): Observable<ActionsAActualiserReponse> {
    const params: Record<string, string> = planId ? { plan: String(planId) } : {};
    return this.http.get<ActionsAActualiserReponse>(
      '/api/plans/referentiel-actions/a-actualiser/', { params });
  }

  /**
   * Pose le type choisi, y compris dans un plan validé. `typeAttendu` = le
   * type affiché quand l'utilisateur a choisi (409 s'il a changé depuis).
   */
  actualiserType(operationId: number, typeId: number, typeAttendu: number | null): Observable<unknown> {
    return this.http.post(`/api/plans/operations/${operationId}/actualiser-type/`, {
      id_type_action: typeId,
      type_attendu: typeAttendu,
    });
  }
}
