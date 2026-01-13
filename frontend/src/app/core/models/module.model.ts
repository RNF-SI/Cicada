/**
 * Modeles pour les modules applicatifs.
 */

/**
 * Couleurs disponibles pour les tuiles de modules.
 */
export type TileColor = 'primary' | 'salmon' | 'terra-cotta' | 'yellow' | 'pale-green';

/**
 * Interface pour un module applicatif.
 */
export interface Module {
  id: number;
  code: string;
  name: string;
  description?: string;
  icon: string;
  color: TileColor;
  route: string;
  requires_access: boolean;
  is_active?: boolean;
  display_order: number;
  created_at?: string;
  updated_at?: string;
}

/**
 * Interface pour la creation/mise a jour d'un module.
 */
export interface ModuleCreateUpdate {
  code: string;
  name: string;
  description?: string;
  icon: string;
  color: TileColor;
  route: string;
  requires_access: boolean;
  is_active?: boolean;
  display_order?: number;
}

/**
 * Interface pour le statut d'acces a un module.
 */
export interface ModuleAccessStatus {
  module_code: string;
  requires_access: boolean;
  has_access: boolean;
  status: 'granted' | 'none' | 'pending' | 'approved' | 'rejected' | 'cancelled' | 'expired';
  request_id?: number;
  message: string;
  created_at?: string;
  validated_at?: string;
}
