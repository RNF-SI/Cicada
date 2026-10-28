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

/** #777 — un référentiel vu de la page super-admin. */
export interface VersionDisponible {
  nom: string;
  code: string;
  libelle: string;
  depuis: string;
  applicable: boolean;
  en_service: boolean;
}

export interface EtatReferentiel {
  code: string;
  libelle: string;
  en_service: { code: string; libelle: string };
  versions: VersionDisponible[];
  passage: {
    id: number; depuis: string; vers: string; vers_code: string; date: string;
    a_actualiser: number; automatiques: number; actualises: number;
  } | null;
}

/** Rapport de simulation (types d'action : `actions` ; autres : `objets`). */
export interface RapportPassage {
  depuis: string;
  vers: string;
  actions?: Record<string, number>;
  objets?: Record<string, number>;
  suivis?: Record<string, number>;
  devient_cs?: { total: number; sans_suivi: number };
  a_arbitrer_par_code: [string, number][];
  plans: { plan: string | null; statut: string | null; sure?: number; probable?: number; a_arbitrer?: number }[];
  plans_sans_destinataire: string[];
}

/** Bandeau affiché sur toutes les pages tant qu'il reste des actions à actualiser. */
/** #779 — PressRef, TaxRef, HabRef : élément touché par un passage. */
export interface ElementAActualiser {
  id: number;
  cible: string;
  cible_libelle: string;
  contexte: string;
  statut: 'applique' | 'a_actualiser' | 'actualise';
  confiance: 'sure' | 'probable' | 'a_arbitrer';
  ancien_code: string;
  ancien_libelle: string;
  code_actuel: string;
  libelle_actuel: string;
  options: { code: string; libelle: string }[];
  note: string;
  actualise_par: string | null;
  actualise_le: string | null;
}

export interface PlanElements {
  id_pg: number | null;
  nom: string;
  slug: string | null;
  statut: string | null;
  a_actualiser: ElementAActualiser[];
  actualisees: ElementAActualiser[];
  automatiques: ElementAActualiser[];
}

export interface ReferentielElements {
  code: 'PRESSREF' | 'TAXREF' | 'HABREF';
  libelle: string;
  passage: { depuis: string; vers: string; date: string };
  total_a_actualiser: number;
  plans: PlanElements[];
}

export interface CompteAActualiser {
  total: number;
  /** Changements automatiques, rappelés plus discrètement (#776). */
  automatiques: number;
  vers: string | null;
  /** #779 — détail par référentiel (types d'action, PressRef, TaxRef, HabRef). */
  referentiels: { code: string; libelle: string; total: number; automatiques: number }[];
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

  /** #779 — éléments à actualiser de PressRef, TaxRef, HabRef. */
  referentielsAActualiser(planId?: number | null): Observable<{ referentiels: ReferentielElements[] }> {
    const params: Record<string, string> = planId ? { plan: String(planId) } : {};
    return this.http.get<{ referentiels: ReferentielElements[] }>(
      '/api/plans/referentiels/a-actualiser/', { params });
  }

  actualiserElement(id: number, code: string, attendu: string): Observable<ElementAActualiser> {
    return this.http.post<ElementAActualiser>(`/api/plans/referentiels/objets/${id}/actualiser/`,
      { code, attendu }).pipe(tap(() => this.rafraichirCompte()));
  }

  accepterPropositionsReferentiel(referentiel: string, planId?: number | null): Observable<BilanPropositions> {
    return this.http.post<BilanPropositions>('/api/plans/referentiels/accepter-propositions/',
      { referentiel, ...(planId ? { plan: planId } : {}) }).pipe(tap(() => this.rafraichirCompte()));
  }

  // ── #777 — page super-admin « Référentiels » ─────────────────────────
  etatAdmin(): Observable<{ referentiels: EtatReferentiel[] }> {
    return this.http.get<{ referentiels: EtatReferentiel[] }>('/api/plans/referentiels/admin/');
  }

  simulerAdmin(code: string, version: string): Observable<{ rapport: RapportPassage }> {
    return this.http.post<{ rapport: RapportPassage }>(
      `/api/plans/referentiels/admin/${code}/simuler/`, { version });
  }

  passageAdmin(code: string, action: 'appliquer' | 'annuler', version: string, sansEmail = false):
      Observable<{ referentiels: EtatReferentiel[] }> {
    return this.http.post<{ referentiels: EtatReferentiel[] }>(
      `/api/plans/referentiels/admin/${code}/${action}/`, { version, sans_email: sansEmail })
      .pipe(tap(() => this.rafraichirCompte()));
  }

  /** Pose l'équivalent unique des actions à actualiser qui n'en ont qu'un. */
  accepterPropositions(planId?: number | null): Observable<BilanPropositions> {
    return this.http.post<BilanPropositions>('/api/plans/referentiel-actions/accepter-propositions/',
      planId ? { plan: planId } : {}).pipe(tap(() => this.rafraichirCompte()));
  }
}
