import { Injectable, inject, computed } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

/**
 * Service pour gérer les restrictions d'impersonnation.
 *
 * En mode production (allowImpersonationModifications = false),
 * les modifications sont bloquées pendant l'impersonnation.
 * Ce service permet de :
 * - Vérifier si les modifications sont autorisées
 * - Désactiver visuellement les boutons d'action
 * - Afficher un message explicatif à l'utilisateur
 */
@Injectable({
  providedIn: 'root'
})
export class ImpersonationGuardService {
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  /**
   * Indique si les modifications sont bloquées.
   * True si : impersonnation active ET modifications non autorisées
   */
  readonly isReadOnly = computed(() => {
    return this.authService.isImpersonating() && !environment.allowImpersonationModifications;
  });

  /**
   * Indique si les modifications sont autorisées.
   * Inverse de isReadOnly pour plus de lisibilité dans les templates.
   */
  readonly canModify = computed(() => !this.isReadOnly());

  /**
   * Vérifie si une action peut être exécutée.
   * Si non, affiche un message d'erreur et retourne false.
   *
   * Usage dans un composant :
   * ```
   * onSave() {
   *   if (!this.impersonationGuard.checkCanModify()) return;
   *   // ... continuer avec la sauvegarde
   * }
   * ```
   */
  checkCanModify(): boolean {
    if (this.isReadOnly()) {
      this.showReadOnlyMessage();
      return false;
    }
    return true;
  }

  /**
   * Affiche le message d'erreur en mode lecture seule.
   */
  showReadOnlyMessage(): void {
    this.snackBar.open(
      this.translate.instant('header.impersonation.readOnlyError'),
      this.translate.instant('common.actions.close'),
      {
        duration: 5000,
        panelClass: ['snackbar-warning']
      }
    );
  }
}
