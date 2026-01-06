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
 */
export type UserRole = 'utilisateur' | 'referent' | 'admin_og' | 'super_admin';

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
