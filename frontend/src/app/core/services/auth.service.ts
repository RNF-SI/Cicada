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
  UserRole
} from '../models/user.model';

const TOKEN_KEY = 'auth_tokens';
const USER_KEY = 'current_user';

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

  // Public readonly signals
  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUserSignal() !== null);

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
    return role === 'admin_og' || role === 'super_admin';
  });

  constructor() {
    // Initialize from localStorage on service creation
    this.initializeFromStorage();
  }

  /**
   * Initialize auth state from localStorage
   */
  private initializeFromStorage(): void {
    const tokens = this.getStoredTokens();
    const user = this.getStoredUser();

    if (tokens && user) {
      this.currentUserSignal.set(user);
      // Optionally verify token validity by calling /me endpoint
      this.verifyToken().subscribe();
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
      }),
      catchError(() => {
        // Token invalid, try refresh or logout
        return this.refreshToken().pipe(
          switchMap(() => this.http.get<User>(`${this.apiUrl}/me/`)),
          tap(user => {
            this.currentUserSignal.set(user);
            this.storeUser(user);
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
   * Login with email and password
   */
  login(credentials: LoginRequest): Observable<User> {
    this.isLoadingSignal.set(true);

    return this.http.post<LoginResponse>(`${this.apiUrl}/login/`, credentials).pipe(
      tap(response => {
        this.storeTokens({ access: response.access, refresh: response.refresh });
        this.storeUser(response.user);
        this.currentUserSignal.set(response.user);
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
}
