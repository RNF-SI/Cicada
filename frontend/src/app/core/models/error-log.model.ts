/**
 * Modeles pour les logs d'erreur.
 */

export type ErrorLogLevel = 'WARNING' | 'ERROR' | 'CRITICAL';

/**
 * Log d'erreur (version liste).
 */
export interface ErrorLog {
  id: number;
  level: ErrorLogLevel;
  level_display: string;
  message: string;
  logger_name: string | null;
  correlation_id: string | null;
  user: number | null;
  user_name: string | null;
  path: string | null;
  method: string | null;
  exception_type: string | null;
  acknowledged: boolean;
  acknowledged_by: number | null;
  acknowledged_by_name: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

/**
 * Log d'erreur (version detail avec stack trace).
 */
export interface ErrorLogDetail extends ErrorLog {
  user_email: string | null;
  stack_trace: string | null;
  context: Record<string, unknown>;
}

/**
 * Statistiques des logs d'erreur.
 */
export interface ErrorLogStats {
  total: number;
  unacknowledged: number;
  by_level: Record<string, number>;
  by_day: Array<{ date: string; count: number }>;
}

/**
 * Reponse paginee de logs d'erreur.
 */
export interface ErrorLogPaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ErrorLog[];
}

/**
 * Filtres pour la recherche de logs.
 */
export interface ErrorLogFilters {
  level?: ErrorLogLevel;
  acknowledged?: boolean;
  date_from?: string;
  date_to?: string;
  exception_type?: string;
  search?: string;
  page?: number;
  ordering?: string;
}

/**
 * Reponse d'acquittement.
 */
export interface AcknowledgeResponse {
  id?: number;
  acknowledged: boolean;
  acknowledged_by: number;
  acknowledged_at: string;
  acknowledged_count?: number;
}
