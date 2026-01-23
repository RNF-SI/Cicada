import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, tap, of } from 'rxjs';

export interface SiteConfiguration {
  homepage_image: string | null;
  homepage_image_url: string | null;
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
