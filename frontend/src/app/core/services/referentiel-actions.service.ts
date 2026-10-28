import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

/**
 * #751 — actions dont le type est à actualiser après un passage du référentiel
 * des types d'action (codification Eden 62 → Gestref V1, puis versions
 * suivantes). Backend : `apps/plans/views_referentiel.py`.
 */

/** Équivalent proposé par la table de correspondance (#776). */
export interface OptionType {
  id: number;
  code: string;
  libelle: string;
}

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
  /** #776 — équivalents possibles, le premier étant la proposition. */
  options: OptionType[];
  a_un_suivi: boolean;
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
  options: OptionType[];
  note: string;
}

/** Suivi d'une action qui devient CS (#776) : existant, ou nouveau. */
export interface SuiviActualisation {
  id_suivi?: number;
  intitule?: string;
  objectif_principal?: string;
  cibles_principales?: string;
  protocoles?: Record<string, unknown>[];
}

/** Bilan de « Accepter toutes les propositions » (#776). */
export interface BilanPropositions {
  acceptees: number;
  plusieurs_options: number;
  suivi_requis: number;
}

/** Réponse 409 : un autre référent a choisi le type entre-temps. */
export interface TypeDejaModifie {
  code: 'type_deja_modifie';
  detail: string;
  id_type_action: number | null;
  type_action_label: string;
  actualise_par: string;
}

/** Bandeau affiché sur toutes les pages tant qu'il reste des actions à actualiser. */
export interface CompteAActualiser {
  total: number;
  /** Changements automatiques, rappelés plus discrètement (#776). */
  automatiques: number;
  vers: string | null;
}

@Injectable({ providedIn: 'root' })
export class ReferentielActionsService {
  private readonly http = inject(HttpClient);

  /** Actions des plans de l'utilisateur dont le type est à choisir (bandeau de l'en-tête). */
  readonly compte = signal<CompteAActualiser | null>(null);

  rafraichirCompte(): void {
    this.http.get<CompteAActualiser>('/api/plans/referentiel-actions/a-actualiser/compte/').subscribe({
      next: c => this.compte.set(c),
      error: () => this.compte.set(null),
    });
  }

  oublierCompte(): void {
    this.compte.set(null);
  }

  aActualiser(planId?: number | null): Observable<ActionsAActualiserReponse> {
    const params: Record<string, string> = planId ? { plan: String(planId) } : {};
    return this.http.get<ActionsAActualiserReponse>(
      '/api/plans/referentiel-actions/a-actualiser/', { params });
  }

  /**
   * Pose le type choisi, y compris dans un plan validé. `typeAttendu` = le
   * type affiché quand l'utilisateur a choisi (409 s'il a changé depuis).
   */
  actualiserType(
    operationId: number, typeId: number, typeAttendu: number | null, suivi?: SuiviActualisation,
  ): Observable<unknown> {
    return this.http.post(`/api/plans/operations/${operationId}/actualiser-type/`, {
      id_type_action: typeId,
      type_attendu: typeAttendu,
      ...(suivi ? { suivi } : {}),
    }).pipe(tap(() => this.rafraichirCompte()));
  }

  /** Pose l'équivalent unique des actions à actualiser qui n'en ont qu'un. */
  accepterPropositions(planId?: number | null): Observable<BilanPropositions> {
    return this.http.post<BilanPropositions>('/api/plans/referentiel-actions/accepter-propositions/',
      planId ? { plan: planId } : {}).pipe(tap(() => this.rafraichirCompte()));
  }
}
