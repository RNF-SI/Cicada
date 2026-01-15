/**
 * Service pour la gestion des modules applicatifs.
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';

import { Module, ModuleCreateUpdate, ModuleAccessStatus } from '../models/module.model';

@Injectable({
  providedIn: 'root'
})
export class ModuleService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/modules';

  // Cache des modules accessibles
  private readonly _accessibleModules = signal<Module[]>([]);
  private readonly _allModules = signal<Module[]>([]);
  private readonly _modulesRequiringAccess = signal<Module[]>([]);
  private readonly _isLoading = signal(false);

  // Signaux publics en lecture seule
  readonly accessibleModules = this._accessibleModules.asReadonly();
  readonly allModules = this._allModules.asReadonly();
  readonly modulesRequiringAccess = this._modulesRequiringAccess.asReadonly();
  readonly isLoading = this._isLoading.asReadonly();

  /**
   * Recupere tous les modules actifs.
   */
  getModules(): Observable<Module[]> {
    return this.http.get<Module[]>(`${this.apiUrl}/`);
  }

  /**
   * Recupere un module par son ID.
   */
  getModule(id: number): Observable<Module> {
    return this.http.get<Module>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Recupere un module par son code.
   */
  getModuleByCode(code: string): Observable<Module | undefined> {
    return this.http.get<Module[]>(`${this.apiUrl}/`).pipe(
      tap(modules => {
        const module = modules.find(m => m.code === code);
        return module;
      }),
      catchError(() => of(undefined))
    ) as Observable<Module | undefined>;
  }

  /**
   * Cree un nouveau module (super_admin).
   */
  createModule(data: ModuleCreateUpdate): Observable<Module> {
    return this.http.post<Module>(`${this.apiUrl}/`, data);
  }

  /**
   * Met a jour un module (super_admin).
   */
  updateModule(id: number, data: Partial<ModuleCreateUpdate>): Observable<Module> {
    return this.http.patch<Module>(`${this.apiUrl}/${id}/`, data);
  }

  /**
   * Supprime un module (super_admin).
   */
  deleteModule(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Recupere tous les modules y compris inactifs (super_admin).
   */
  getAllModules(): Observable<Module[]> {
    return this.http.get<Module[]>(`${this.apiUrl}/all/`).pipe(
      tap(modules => this._allModules.set(modules))
    );
  }

  /**
   * Recupere les modules necessitant un acces.
   */
  getModulesRequiringAccess(): Observable<Module[]> {
    return this.http.get<Module[]>(`${this.apiUrl}/requiring_access/`).pipe(
      tap(modules => this._modulesRequiringAccess.set(modules))
    );
  }

  /**
   * Recupere les modules accessibles par l'utilisateur connecte.
   * C'est l'endpoint principal pour la page d'accueil.
   */
  getMyAccessibleModules(): Observable<Module[]> {
    this._isLoading.set(true);
    return this.http.get<Module[]>(`${this.apiUrl}/my_accessible/`).pipe(
      tap(modules => {
        this._accessibleModules.set(modules);
        this._isLoading.set(false);
      }),
      catchError(error => {
        console.error('Erreur chargement modules accessibles:', error);
        this._isLoading.set(false);
        return of([]);
      })
    );
  }

  /**
   * Recupere le statut d'acces pour un module specifique.
   */
  getModuleAccessStatus(moduleId: number): Observable<ModuleAccessStatus> {
    return this.http.get<ModuleAccessStatus>(`${this.apiUrl}/${moduleId}/access_status/`);
  }

  /**
   * Rafraichit le cache des modules accessibles.
   */
  refreshAccessibleModules(): void {
    this.getMyAccessibleModules().subscribe();
  }

  /**
   * Vide le cache (a appeler lors de la deconnexion).
   */
  clearCache(): void {
    this._accessibleModules.set([]);
    this._allModules.set([]);
    this._modulesRequiringAccess.set([]);
  }
}
