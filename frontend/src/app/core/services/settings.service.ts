import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, tap, of } from 'rxjs';

export type ImagePosition = 'top' | 'center' | 'bottom';

export interface SiteConfiguration {
  homepage_image: string | null;
  homepage_image_url: string | null;
  homepage_image_position: ImagePosition;
  /** #448 — Couleur de fond du bandeau (header), hexadécimal #RRGGBB. */
  header_color: string;
  /** #601 — Couleur des bandeaux et titres des exports Excel/Word, #RRGGBB. */
  export_color: string;
  /** #448 — Logo de la structure (chemin relatif). */
  structure_logo: string | null;
  /** #448 — URL relative du logo de la structure. */
  structure_logo_url: string | null;
  /**
   * #458 — Paramètre d'instance : affiche le champ ID Doc'Gestion FCEN dans les
   * formulaires de plan. Désactivé par défaut (n'a de sens que sur l'instance FCEN).
   */
  enable_docgestion_fcen: boolean;
  updated_at: string;
  updated_by: number | null;
  updated_by_name: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/settings/';

  // Default homepage image path (used when no custom image is set)
  readonly defaultHomepageImage = 'assets/images/homepage-default.jpg';

  // State management with signals
  private configSignal = signal<SiteConfiguration | null>(null);
  private isLoadingSignal = signal<boolean>(false);
  private errorSignal = signal<string | null>(null);

  // Public readonly signals
  readonly config = this.configSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();

  /**
   * Get the homepage image URL, falling back to default if not set.
   */
  getHomepageImageUrl(): string {
    const config = this.configSignal();
    if (config?.homepage_image_url) {
      return config.homepage_image_url;
    }
    return this.defaultHomepageImage;
  }

  /** #448 — Bandeau blanc par défaut (comportement historique avant la
   *  personnalisation). L'admin peut choisir une autre couleur. */
  readonly defaultHeaderColor = '#FFFFFF';

  /** #448 — Couleur du bandeau configurée (repli sur la couleur par défaut). */
  getHeaderColor(): string {
    return this.configSignal()?.header_color || this.defaultHeaderColor;
  }

  /** #601 — Couleur CICADA par défaut pour les exports. */
  readonly defaultExportColor = '#025359';

  /** #601 — Couleur des exports de l'instance (repli sur celle de CICADA). */
  getExportColor(): string {
    return this.configSignal()?.export_color || this.defaultExportColor;
  }

  /**
   * #458 — Le champ ID Doc'Gestion FCEN est-il activé sur cette instance ?
   * Faux tant que la configuration n'est pas chargée (le champ reste masqué).
   */
  isDocGestionFcenEnabled(): boolean {
    return this.configSignal()?.enable_docgestion_fcen === true;
  }

  /** #448 — URL du logo de la structure (null si non défini). */
  getStructureLogoUrl(): string | null {
    return this.configSignal()?.structure_logo_url || null;
  }

  /** Réinitialise le logo de la structure (#448, super_admin). */
  resetStructureLogo(): Observable<SiteConfiguration> {
    const formData = new FormData();
    formData.append('reset_logo', 'true');
    return this.updateSettings(formData);
  }

  /**
   * Load site configuration from API.
   * This endpoint is public (no authentication required).
   */
  loadSettings(): Observable<SiteConfiguration> {
    this.isLoadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.get<SiteConfiguration>(this.apiUrl).pipe(
      tap(config => {
        this.configSignal.set(config);
        this.isLoadingSignal.set(false);
      }),
      catchError(error => {
        console.error('Error loading site configuration:', error);
        this.errorSignal.set('Unable to load site configuration');
        this.isLoadingSignal.set(false);
        // Return empty config so the app can still function
        return of({
          homepage_image: null,
          homepage_image_url: null,
          homepage_image_position: 'top' as ImagePosition,
          header_color: this.defaultHeaderColor,
          export_color: this.defaultExportColor,
          structure_logo: null,
          structure_logo_url: null,
          enable_docgestion_fcen: false,
          updated_at: '',
          updated_by: null,
          updated_by_name: null
        });
      })
    );
  }

  /**
   * Update site configuration (super_admin only).
   * @param formData FormData containing the image file
   */
  updateSettings(formData: FormData): Observable<SiteConfiguration> {
    this.isLoadingSignal.set(true);
    this.errorSignal.set(null);

    return this.http.patch<SiteConfiguration>(this.apiUrl, formData).pipe(
      tap(config => {
        this.configSignal.set(config);
        this.isLoadingSignal.set(false);
      }),
      catchError(error => {
        console.error('Error updating site configuration:', error);
        this.errorSignal.set('Unable to update site configuration');
        this.isLoadingSignal.set(false);
        throw error;
      })
    );
  }

  /**
   * Reset homepage image to default (super_admin only).
   */
  resetHomepageImage(): Observable<SiteConfiguration> {
    const formData = new FormData();
    formData.append('reset_image', 'true');
    return this.updateSettings(formData);
  }
}
