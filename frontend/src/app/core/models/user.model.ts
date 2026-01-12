/**
 * User model matching the backend API response
 */
export interface User {
  id: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  identifiant?: string;
  organisme?: Organisme;
  niveau_role: UserRole;
  is_staff: boolean;
  is_active: boolean;
  is_referent?: boolean;  // Computed: true if user is site or plan referent
  date_joined?: string;
  last_login?: string;
}

export interface Organisme {
  id: number;
  nom_organisme: string;
  adresse_organisme?: string;
  cp_organisme?: string;
  ville_organisme?: string;
  tel_organisme?: string;
  email_organisme?: string;
}

/**
 * User role levels - matches backend permission system
 * Note: Le role 'referent' a ete supprime. Un utilisateur est considere comme
 * "referent" s'il est referent d'au moins un site ou plan de gestion.
 * Ceci est verifie cote backend via is_referent().
 */
export type UserRole = 'utilisateur' | 'admin_og' | 'super_admin';

/**
 * Authentication tokens from JWT
 */
export interface AuthTokens {
  access: string;
  refresh: string;
}

/**
 * Login request payload
 * Accepts either email or username (identifiant)
 */
export interface LoginRequest {
  username: string;  // Can be email or identifiant
  password: string;
}

/**
 * Login response from backend
 */
export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

/**
 * Token refresh response
 */
export interface RefreshResponse {
  access: string;
}

/**
 * Impersonation info stored in localStorage
 */
export interface ImpersonationInfo {
  isImpersonating: boolean;
  impersonator: {
    id: number;
    email: string;
    nom_role?: string;
    prenom_role?: string;
  };
  logId: number;
  startedAt: string;
}

/**
 * Response from impersonation start endpoint
 */
export interface ImpersonationResponse {
  access: string;
  refresh: string;
  user: User;
  impersonation: ImpersonationInfo;
}

/**
 * Response from stop impersonation endpoint
 */
export interface StopImpersonationResponse {
  access: string;
  refresh: string;
  user: User;
  message: string;
}
