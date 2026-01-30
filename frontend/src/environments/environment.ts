/**
 * Configuration de l'environnement de développement.
 *
 * Ce fichier est utilisé par défaut lors du développement local.
 * En mode développement, certaines restrictions sont assouplies
 * pour faciliter les tests (ex: impersonnation avec modifications).
 */
export const environment = {
  production: false,

  /**
   * Permet les modifications (POST/PUT/DELETE) lors de l'impersonnation.
   * En mode développement, c'est activé pour permettre les tests.
   * En mode production, c'est désactivé par défaut pour la sécurité.
   */
  allowImpersonationModifications: true
};
