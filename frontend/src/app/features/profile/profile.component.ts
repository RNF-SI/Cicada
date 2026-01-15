/**
 * Composant pour la page "Mon profil".
 * Affiche les informations de l'utilisateur et ses demandes en cours.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { ValidationService } from '../../core/services/validation.service';
import { User } from '../../core/models/user.model';
import {
  ValidationRequestListItem,
  ValidationStatus,
  ValidationRequestType
} from '../../core/models/notification.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatTabsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslateModule
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly validationService = inject(ValidationService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  // Utilisateur courant
  readonly currentUser = this.authService.currentUser;

  // Demandes de l'utilisateur
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly loadingRequests = signal(false);

  // Colonnes du tableau des demandes
  readonly requestColumns = ['type', 'target', 'date', 'validated_at', 'status', 'validator'];

  ngOnInit(): void {
    this.loadMyRequests();
  }

  /**
   * Charge les demandes de l'utilisateur.
   */
  loadMyRequests(): void {
    this.loadingRequests.set(true);

    this.validationService.getMyRequests().subscribe({
      next: (requests) => {
        this.myRequests.set(requests);
        this.loadingRequests.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement mes demandes:', error);
        this.snackBar.open(
          this.translate.instant('profile.requests.loadError'),
          this.translate.instant('common.actions.close'), {
          duration: 3000
        });
        this.loadingRequests.set(false);
      }
    });
  }

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

  /**
   * Obtient la classe CSS du statut.
   */
  getStatusClass(status: ValidationStatus): string {
    const classes: Record<string, string> = {
      'pending': 'status-warning',
      'approved': 'status-success',
      'rejected': 'status-error',
      'cancelled': 'status-neutre',
      'expired': 'status-neutre',
    };
    return classes[status] || 'status-neutre';
  }

  /**
   * Obtient l'icone du type de demande.
   */
  getTypeIcon(type: ValidationRequestType): string {
    const icons: Record<string, string> = {
      'user_registration': 'fi-rr-user-add',
      'site_access': 'fi-rr-marker',
      'plan_access': 'fi-rr-document',
      'admin_deactivation': 'fi-rr-user-slash',
      'referent_validation': 'fi-rr-check',
    };
    return icons[type] || 'fi-rr-check-circle';
  }

  /**
   * Compte les demandes en attente.
   */
  getPendingCount(): number {
    return this.myRequests().filter(r => r.status === 'pending').length;
  }
}
