/**
 * Service pour les sites et plans orphelins.
 *
 * Remplace l'ancien audit hebdomadaire par email : l'etat orphelin est un etat
 * persistant que les admins consultent a la demande (page Administration > Orphelins).
 * Expose aussi un compteur rafraichi periodiquement pour le badge de navigation.
 */
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface OrphanSite {
  id_site: number;
  nom_site: string;
  slug: string;
  organismes: string[];
}

export interface OrphanPlan {
  id_pg: number;
  nom: string;
  slug: string;
}

export interface OrphansResponse {
  sites: OrphanSite[];
  plans: OrphanPlan[];
  sites_count: number;
  plans_count: number;
}

export interface OrphansCounts {
  sites_count: number;
  plans_count: number;
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class OrphansService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/admin/orphans';

  // Compteur total (sites + plans) pour le badge de navigation
  readonly count = signal<number>(0);
  readonly isLoading = signal<boolean>(false);

  private refreshInterval: ReturnType<typeof setInterval> | null = null;

  /**
   * Demarre le rafraichissement automatique du compteur (appele depuis le layout admin).
   */
  startAutoRefresh(intervalMs: number = 300000): void {
    this.stopAutoRefresh();
    this.refreshCount();
    this.refreshInterval = setInterval(() => this.refreshCount(), intervalMs);
  }

  stopAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Rafraichit le compteur du badge (silencieux en cas d'erreur).
   */
  refreshCount(): void {
    this.getCounts().subscribe({
      next: (counts) => this.count.set(counts.total),
      error: () => {}
    });
  }

  /**
   * Recupere la liste complete des sites et plans orphelins.
   */
  getOrphans(): Observable<OrphansResponse> {
    this.isLoading.set(true);
    return this.http.get<OrphansResponse>(`${this.baseUrl}/`).pipe(
      tap((data) => {
        this.count.set(data.sites_count + data.plans_count);
        this.isLoading.set(false);
      })
    );
  }

  /**
   * Recupere uniquement les compteurs (leger, pour le badge).
   */
  getCounts(): Observable<OrphansCounts> {
    return this.http.get<OrphansCounts>(`${this.baseUrl}/counts/`);
  }
}
