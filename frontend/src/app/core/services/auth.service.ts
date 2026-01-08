import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, BehaviorSubject, throwError, of } from 'rxjs';
import { tap, catchError, map, switchMap } from 'rxjs/operators';
import {
  User,
  AuthTokens,
  LoginRequest,
  LoginResponse,
  RefreshResponse,
  UserRole,
  ImpersonationInfo,
  ImpersonationResponse,
  StopImpersonationResponse
} from '../models/user.model';

const TOKEN_KEY = 'auth_tokens';
const USER_KEY = 'current_user';
const TOKEN_TIMESTAMP_KEY = 'auth_token_timestamp';
const IMPERSONATION_KEY = 'impersonation_info';
const ORIGINAL_TOKENS_KEY = 'original_auth_tokens';
const ORIGINAL_USER_KEY = 'original_user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly apiUrl = '/api/auth';

  // State management with signals
  private currentUserSignal = signal<User | null>(null);
  private isLoadingSignal = signal<boolean>(false);
  private isInitializedSignal = signal<boolean>(false);
  private impersonationInfoSignal = signal<ImpersonationInfo | null>(null);

  // Public readonly signals
  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();
  readonly isInitialized = this.isInitializedSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUserSignal() !== null);
  readonly impersonationInfo = this.impersonationInfoSignal.asReadonly();
  readonly isImpersonating = computed(() => this.impersonationInfoSignal()?.isImpersonating === true);

  // Computed properties for role checks
  readonly isSuperAdmin = computed(() => this.currentUser()?.niveau_role === 'super_admin');
  readonly isAdminOrganisme = computed(() => {
    const role = this.currentUser()?.niveau_role;
    return role === 'admin_og' || role === 'super_admin';
  });
  readonly isReferent = computed(() => {
    const role = this.currentUser()?.niveau_role;
    return role === 'referent' || role === 'admin_og' || role === 'super_admin';
  });
  readonly canAccessAdmin = computed(() => {
    const role = this.currentUser()?.niveau_role;
    // Referents can access admin for managing plans/validations
    return role === 'referent' || role === 'admin_og' || role === 'super_admin';
  });

  // Original user info (when impersonating)
  readonly originalUser = computed(() => {
    const info = this.impersonationInfoSignal();
    return info?.impersonator ?? null;
  });

  constructor() {
    // Initialize from localStorage on service creation
    this.initializeFromStorage();
  }

  /**
   * Initialize auth state from localStorage
   * Uses cached user data immediately, only verifies token if stale (>30 min)
   */
  private initializeFromStorage(): void {
    const tokens = this.getStoredTokens();
    const user = this.getStoredUser();
    const impersonationInfo = this.getStoredImpersonationInfo();

    if (tokens && user) {
      // Set user immediately from cache (synchronous - no race condition)
      this.currentUserSignal.set(user);
      this.isInitializedSignal.set(true);

      // Restore impersonation state if any
      if (impersonationInfo) {
        this.impersonationInfoSignal.set(impersonationInfo);
      }

      // Only verify token if it's been more than 30 minutes since last verification
      // This avoids unnecessary API calls on every page load/new window
      const lastVerified = localStorage.getItem(TOKEN_TIMESTAMP_KEY);
      const thirtyMinutesAgo = Date.now() - (30 * 60 * 1000);

      if (!lastVerified || parseInt(lastVerified, 10) < thirtyMinutesAgo) {
        this.verifyToken().subscribe();
      }
    } else {
      this.isInitializedSignal.set(true);
    }
  }

  /**
   * Verify current token by calling the /me endpoint
   */
  verifyToken(): Observable<User | null> {
    const tokens = this.getStoredTokens();
    if (!tokens) {
      return of(null);
    }

    return this.http.get<User>(`${this.apiUrl}/me/`).pipe(
      tap(user => {
        this.currentUserSignal.set(user);
        this.storeUser(user);
        this.updateVerificationTimestamp();
      }),
      catchError(() => {
        // Token invalid, try refresh or logout
        return this.refreshToken().pipe(
          switchMap(() => this.http.get<User>(`${this.apiUrl}/me/`)),
          tap(user => {
            this.currentUserSignal.set(user);
            this.storeUser(user);
            this.updateVerificationTimestamp();
          }),
          catchError(() => {
            this.clearAuthData();
            return of(null);
          })
        );
      })
    );
  }

  /**
   * Update the last verification timestamp
   */
  private updateVerificationTimestamp(): void {
    localStorage.setItem(TOKEN_TIMESTAMP_KEY, Date.now().toString());
  }

  /**
   * Login with email and password
   */
  login(credentials: LoginRequest): Observable<User> {
    this.isLoadingSignal.set(true);

    return this.http.post<LoginResponse>(`${this.apiUrl}/login/`, credentials).pipe(
      tap(response => {
        this.storeTokens({ access: response.access, refresh: response.refresh });
        this.storeUser(response.user);
        this.updateVerificationTimestamp();
        this.currentUserSignal.set(response.user);
        this.isInitializedSignal.set(true);
        this.isLoadingSignal.set(false);
      }),
      map(response => response.user),
      catchError(error => {
        this.isLoadingSignal.set(false);
        return this.handleError(error);
      })
    );
  }

  /**
   * Logout - blacklist refresh token and clear local data
   */
  logout(): Observable<void> {
    const tokens = this.getStoredTokens();

    if (tokens?.refresh) {
      return this.http.post<void>(`${this.apiUrl}/logout/`, { refresh: tokens.refresh }).pipe(
        tap(() => this.clearAuthData()),
        catchError(() => {
          // Even if API call fails, clear local data
          this.clearAuthData();
          return of(undefined);
        })
      );
    }

    this.clearAuthData();
    return of(undefined);
  }

  /**
   * Refresh access token
   */
  refreshToken(): Observable<string> {
    const tokens = this.getStoredTokens();

    if (!tokens?.refresh) {
      return throwError(() => new Error('No refresh token available'));
    }

    return this.http.post<RefreshResponse>(`${this.apiUrl}/refresh/`, {
      refresh: tokens.refresh
    }).pipe(
      tap(response => {
        const newTokens: AuthTokens = {
          access: response.access,
          refresh: tokens.refresh
        };
        this.storeTokens(newTokens);
      }),
      map(response => response.access),
      catchError(error => {
        this.clearAuthData();
        return throwError(() => error);
      })
    );
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    const tokens = this.getStoredTokens();
    return tokens?.access ?? null;
  }

  /**
   * Check if user has minimum required role
   */
  hasRole(requiredRole: UserRole): boolean {
    const user = this.currentUser();
    if (!user) return false;

    const roleHierarchy: UserRole[] = ['utilisateur', 'referent', 'admin_og', 'super_admin'];
    const userRoleIndex = roleHierarchy.indexOf(user.niveau_role);
    const requiredRoleIndex = roleHierarchy.indexOf(requiredRole);

    return userRoleIndex >= requiredRoleIndex;
  }

  /**
   * Get user display name
   */
  getUserDisplayName(): string {
    const user = this.currentUser();
    if (!user) return '';

    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.identifiant || user.email;
  }

  // Private storage methods
  private storeTokens(tokens: AuthTokens): void {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  }

  private getStoredTokens(): AuthTokens | null {
    const tokens = localStorage.getItem(TOKEN_KEY);
    return tokens ? JSON.parse(tokens) : null;
  }

  private storeUser(user: User): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  private getStoredUser(): User | null {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  }

  private clearAuthData(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_TIMESTAMP_KEY);
    this.currentUserSignal.set(null);
    this.router.navigate(['/accueil']);
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'Une erreur est survenue';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = error.error.message;
    } else {
      // Server-side error
      if (error.status === 401) {
        errorMessage = 'Email ou mot de passe incorrect';
      } else if (error.status === 400) {
        if (error.error?.detail) {
          errorMessage = error.error.detail;
        } else if (error.error?.non_field_errors) {
          errorMessage = error.error.non_field_errors[0];
        }
      } else if (error.status === 0) {
        errorMessage = 'Impossible de se connecter au serveur';
      }
    }

    return throwError(() => new Error(errorMessage));
  }

  // ==================== IMPERSONATION METHODS ====================

  /**
   * Start impersonating another user (super_admin only)
   * Stores original tokens to allow returning to admin account
   */
  startImpersonation(userId: number, reason?: string): Observable<ImpersonationResponse> {
    // Store original tokens before impersonation
    const currentTokens = this.getStoredTokens();
    const currentUser = this.getStoredUser();

    if (currentTokens && currentUser) {
      localStorage.setItem(ORIGINAL_TOKENS_KEY, JSON.stringify(currentTokens));
      localStorage.setItem(ORIGINAL_USER_KEY, JSON.stringify(currentUser));
    }

    const body = reason ? { reason } : {};

    return this.http.post<ImpersonationResponse>(`${this.apiUrl}/impersonate/${userId}/`, body).pipe(
      tap(response => {
        // Store new tokens for impersonated user
        this.storeTokens({ access: response.access, refresh: response.refresh });
        this.storeUser(response.user);
        this.updateVerificationTimestamp();

        // Store impersonation info
        this.storeImpersonationInfo(response.impersonation);
        this.impersonationInfoSignal.set(response.impersonation);

        // Update current user signal
        this.currentUserSignal.set(response.user);
      }),
      catchError(error => {
        // Restore original tokens on error
        const originalTokens = localStorage.getItem(ORIGINAL_TOKENS_KEY);
        const originalUser = localStorage.getItem(ORIGINAL_USER_KEY);

        if (originalTokens && originalUser) {
          this.storeTokens(JSON.parse(originalTokens));
          this.storeUser(JSON.parse(originalUser));
        }

        localStorage.removeItem(ORIGINAL_TOKENS_KEY);
        localStorage.removeItem(ORIGINAL_USER_KEY);

        return this.handleError(error);
      })
    );
  }

  /**
   * Stop impersonation and return to original admin account
   */
  stopImpersonation(): Observable<StopImpersonationResponse> {
    return this.http.post<StopImpersonationResponse>(`${this.apiUrl}/stop-impersonation/`, {}).pipe(
      tap(response => {
        // Clear impersonation data
        this.clearImpersonationData();

        // Restore admin tokens
        this.storeTokens({ access: response.access, refresh: response.refresh });
        this.storeUser(response.user);
        this.updateVerificationTimestamp();

        // Update signals
        this.impersonationInfoSignal.set(null);
        this.currentUserSignal.set(response.user);
      }),
      catchError(error => {
        // If API fails, try to restore from stored original tokens
        const originalTokens = localStorage.getItem(ORIGINAL_TOKENS_KEY);
        const originalUser = localStorage.getItem(ORIGINAL_USER_KEY);

        if (originalTokens && originalUser) {
          const tokens = JSON.parse(originalTokens);
          const user = JSON.parse(originalUser);

          this.storeTokens(tokens);
          this.storeUser(user);
          this.currentUserSignal.set(user);
        }

        this.clearImpersonationData();
        this.impersonationInfoSignal.set(null);

        return throwError(() => error);
      })
    );
  }

  /**
   * Get display name of original admin (when impersonating)
   */
  getOriginalUserDisplayName(): string {
    const info = this.impersonationInfoSignal();
    if (!info?.impersonator) return '';

    const impersonator = info.impersonator;
    if (impersonator.prenom_role && impersonator.nom_role) {
      return `${impersonator.prenom_role} ${impersonator.nom_role}`;
    }
    return impersonator.email;
  }

  // Private impersonation storage methods
  private storeImpersonationInfo(info: ImpersonationInfo): void {
    localStorage.setItem(IMPERSONATION_KEY, JSON.stringify(info));
  }

  private getStoredImpersonationInfo(): ImpersonationInfo | null {
    const info = localStorage.getItem(IMPERSONATION_KEY);
    return info ? JSON.parse(info) : null;
  }

  private clearImpersonationData(): void {
    localStorage.removeItem(IMPERSONATION_KEY);
    localStorage.removeItem(ORIGINAL_TOKENS_KEY);
    localStorage.removeItem(ORIGINAL_USER_KEY);
  }
}
