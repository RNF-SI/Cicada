/**
 * Configuration de l'environnement de production.
 *
 * Ce fichier remplace environment.ts lors du build de production.
 * En production, les modifications sont bloquées pendant l'impersonnation
 * pour des raisons de sécurité et de traçabilité.
 */
export const environment = {
  production: true,

  /**
   * Bloque les modifications (POST/PUT/DELETE) lors de l'impersonnation.
   * En production, seule la consultation est autorisée.
   *
   * Pour activer les modifications en production (urgence uniquement),
   * passez cette valeur à true via la variable d'environnement
   * ALLOW_IMPERSONATION_MODIFICATIONS=true au déploiement.
   * Voir la documentation dans docs/FONCTIONNALITES.md
   */
  allowImpersonationModifications: false
};
