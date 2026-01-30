/**
 * Composant pour la page "Mon profil".
 * Affiche les informations de l'utilisateur et les options RGPD.
 */
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { DeleteAccountModalComponent, DeleteAccountModalData, DeleteAccountModalResult } from '../../shared/components/modals';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    TranslateModule
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent {
  private readonly authService = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  // Utilisateur courant
  readonly currentUser = this.authService.currentUser;

  // State for RGPD actions
  readonly isDeleting = signal(false);
  readonly isCancelling = signal(false);

  /**
   * Retourne le nom complet de l'utilisateur.
   */
  getFullName(): string {
    const user = this.currentUser();
    if (!user) return '';
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  /**
   * Retourne le libelle du niveau de role.
   */
  getRoleLevelLabel(): string {
    const user = this.currentUser();
    if (!user) return '';

    const labels: Record<string, string> = {
      'super_admin': 'Super Administrateur',
      'admin_og': 'Administrateur Organisme',
      'utilisateur': 'Utilisateur'
    };

    // If user is a referent (via is_referent), show that
    if (user.is_referent && user.niveau_role === 'utilisateur') {
      return 'Referent';
    }

    return labels[user.niveau_role] || user.niveau_role;
  }

  /**
   * Formate une date.
   */
  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  /**
   * Formate une date avec l'heure.
   */
  formatDateTime(dateString: string | null | undefined): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // ==================== RGPD METHODS ====================

  /**
   * Verifie si l'utilisateur a une demande de suppression en cours.
   */
  hasPendingDeletion(): boolean {
    const user = this.currentUser();
    return user?.deletion_requested_at != null;
  }

  /**
   * Retourne la date de demande de suppression formatee.
   */
  getDeletionRequestDate(): string {
    const user = this.currentUser();
    if (!user?.deletion_requested_at) return '';
    return this.formatDate(user.deletion_requested_at);
  }

  /**
   * Calcule le nombre de jours restants avant anonymisation.
   */
  getDaysUntilDeletion(): number {
    const user = this.currentUser();
    if (!user?.deletion_requested_at) return 0;

    const requestDate = new Date(user.deletion_requested_at);
    const deletionDate = new Date(requestDate);
    deletionDate.setDate(deletionDate.getDate() + 30);

    const now = new Date();
    const diffTime = deletionDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    return Math.max(0, diffDays);
  }

  /**
   * Ouvre le dialogue de confirmation de suppression de compte.
   */
  openDeleteAccountDialog(): void {
    const user = this.currentUser();
    if (!user) return;

    const dialogRef = this.dialog.open(DeleteAccountModalComponent, {
      width: '550px',
      maxWidth: '95vw',
      data: {
        userEmail: user.email
      } as DeleteAccountModalData
    });

    dialogRef.afterClosed().subscribe((result: DeleteAccountModalResult | undefined) => {
      if (result?.confirmed) {
        this.requestAccountDeletion();
      }
    });
  }

  /**
   * Demande la suppression du compte.
   */
  private requestAccountDeletion(): void {
    this.isDeleting.set(true);

    this.authService.requestAccountDeletion().subscribe({
      next: () => {
        this.isDeleting.set(false);
        this.snackBar.open(
          this.translate.instant('profile.rgpd.messages.deletionRequested'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        // Logout the user since account is deactivated
        this.authService.logout().subscribe();
      },
      error: (err) => {
        this.isDeleting.set(false);
        this.snackBar.open(
          err.message || this.translate.instant('profile.rgpd.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /**
   * Annule la demande de suppression du compte.
   */
  cancelAccountDeletion(): void {
    this.isCancelling.set(true);

    this.authService.cancelAccountDeletion().subscribe({
      next: () => {
        this.isCancelling.set(false);
        this.snackBar.open(
          this.translate.instant('profile.rgpd.messages.deletionCancelled'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
      error: (err) => {
        this.isCancelling.set(false);
        this.snackBar.open(
          err.message || this.translate.instant('profile.rgpd.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }
}
