import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  AjustementDuPlan, ApercuReport, ContenuAnnuel, ConversionReglages, DetailAnnuel, ReglagesAnnee,
  ReportDemande, TableauAnnuel,
} from '../models/planification-annuelle.model';

/**
 * #794 — Planification annuelle ajustée : tableau d'une année, ajustement
 * d'une action, report. Les règles (prévu effectif, décalage, reste à faire)
 * sont côté serveur (`apps/plans/planification_annuelle.py`).
 */
@Injectable({ providedIn: 'root' })
export class PlanificationAnnuelleService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/plans/planification-annuelle';

  /** Tableau de l'année ; sans `annee`, l'année en cours bornée au plan. */
  tableau(planId: number, annee?: number | null): Observable<TableauAnnuel> {
    let params = new HttpParams();
    if (annee) {
      params = params.set('annee', String(annee));
    }
    return this.http.get<TableauAnnuel>(`${this.apiUrl}/plan/${planId}/`, { params });
  }

  /** Toutes les années ajustées des actions du plan (suivi, #794). */
  ajustements(planId: number): Observable<{ ajustements: AjustementDuPlan[] }> {
    return this.http.get<{ ajustements: AjustementDuPlan[] }>(`${this.apiUrl}/plan/${planId}/ajustements/`);
  }

  detail(operationId: number, annee: number): Observable<DetailAnnuel> {
    return this.http.get<DetailAnnuel>(`${this.apiUrl}/operation/${operationId}/${annee}/`);
  }

  /** Remplace l'ajustement de l'année et marque l'action revue. */
  enregistrer(operationId: number, annee: number, contenu: ContenuAnnuel): Observable<DetailAnnuel> {
    return this.http.put<DetailAnnuel>(`${this.apiUrl}/operation/${operationId}/${annee}/`, contenu);
  }

  /** Revient à la programmation du plan de gestion pour l'année. */
  revenirAuPlan(operationId: number, annee: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/operation/${operationId}/${annee}/`);
  }

  /**
   * Saisie en cours réécrite selon un autre réglage de l'année (déclinaisons,
   * coût salarial), total conservé. Rien n'est enregistré.
   */
  convertir(
    operationId: number, annee: number, contenu: ContenuAnnuel, reglages: ReglagesAnnee,
  ): Observable<ConversionReglages> {
    return this.http.post<ConversionReglages>(
      `${this.apiUrl}/operation/${operationId}/${annee}/reglages/`, { contenu, reglages });
  }

  reporter(operationId: number, annee: number, demande: ReportDemande): Observable<ApercuReport> {
    return this.http.post<ApercuReport>(
      `${this.apiUrl}/operation/${operationId}/${annee}/report/`, demande);
  }
}
