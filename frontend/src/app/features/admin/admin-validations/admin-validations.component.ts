/**
 * Composant pour la page de gestion des validations (administration).
 * Affiche les demandes a valider pour les administrateurs.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ValidationService, ValidationFilters } from '../../../core/services/validation.service';
import { NotificationService } from '../../../core/services/notification.service';
import {
  ValidationRequestListItem,
  ValidationStatus,
  ValidationRequestType
} from '../../../core/models/notification.model';

import { ValidationDetailDialogComponent } from './validation-detail-dialog.component';

@Component({
  selector: 'app-admin-validations',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
    MatTooltipModule
  ],
  templateUrl: './admin-validations.component.html',
  styleUrl: './admin-validations.component.scss'
})
export class AdminValidationsComponent implements OnInit {
  private readonly validationService = inject(ValidationService);
  private readonly notificationService = inject(NotificationService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly route = inject(ActivatedRoute);

  // Etat
  readonly loading = signal(false);
  readonly validations = signal<ValidationRequestListItem[]>([]);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = 20;

  // Filtres (proprietes simples pour ngModel)
  statusFilter = '';
  typeFilter = '';

  // Colonnes du tableau
  readonly displayedColumns = ['type', 'requester', 'target', 'date', 'validated_at', 'status', 'validator', 'actions'];

  // Options de filtres
  readonly statusOptions = [
    { value: '', label: 'Tous les statuts' },
    { value: 'pending', label: 'En attente' },
    { value: 'approved', label: 'Approuve' },
    { value: 'rejected', label: 'Rejete' },
    { value: 'cancelled', label: 'Annule' },
  ];

  readonly typeOptions = [
    { value: '', label: 'Tous les types' },
    { value: 'user_registration', label: 'Inscription' },
    { value: 'site_access', label: 'Acces site' },
    { value: 'plan_access', label: 'Acces plan' },
    { value: 'admin_deactivation', label: 'Desactivation admin' },
  ];

  ngOnInit(): void {
    this.loadValidations();

    // Verifier si un query param 'open' est present pour ouvrir directement une validation
    this.route.queryParams.subscribe(params => {
      const openId = params['open'];
      if (openId) {
        this.openValidationById(parseInt(openId, 10));
      }
    });
  }

  /**
   * Ouvre le dialog de detail pour une validation par son ID.
   * Utilise quand on arrive depuis une notification avec ?open=id
   */
  private openValidationById(validationId: number): void {
    const dialogRef = this.dialog.open(ValidationDetailDialogComponent, {
      width: '600px',
      data: { validationId }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === 'updated') {
        this.loadValidations();
      }
    });
  }

  /**
   * Charge les demandes de validation.
   */
  loadValidations(): void {
    this.loading.set(true);

    const filters: ValidationFilters = {
      page: this.currentPage(),
    };

    if (this.statusFilter) {
      filters.status = this.statusFilter;
    }
    if (this.typeFilter) {
      filters.request_type = this.typeFilter;
    }

    this.validationService.getValidationRequests(filters).subscribe({
      next: (response) => {
        this.validations.set(response.results);
        this.totalCount.set(response.count);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement validations:', error);
        this.snackBar.open('Erreur lors du chargement des validations', 'Fermer', {
          duration: 3000
        });
        this.loading.set(false);
      }
    });
  }

  /**
   * Change de page.
   */
  onPageChange(event: PageEvent): void {
    this.currentPage.set(event.pageIndex + 1);
    this.loadValidations();
  }

  /**
   * Applique les filtres.
   */
  applyFilters(): void {
    this.currentPage.set(1);
    this.loadValidations();
  }

  /**
   * Ouvre le detail d'une demande.
   */
  openDetail(validation: ValidationRequestListItem): void {
    const dialogRef = this.dialog.open(ValidationDetailDialogComponent, {
      width: '600px',
      data: { validationId: validation.id }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // Rafraichir si action effectuee
        this.loadValidations();
        this.notificationService.refresh().subscribe();
      }
    });
  }

  /**
   * Vérifie si une demande nécessite le choix référent/utilisateur.
   * Dans ce cas, on force l'ouverture du dialog au lieu d'approuver directement.
   */
  private requiresReferentChoice(validation: ValidationRequestListItem): boolean {
    return (validation.request_type === 'site_creation' || validation.request_type === 'site_access')
           && validation.request_as_referent === true;
  }

  /**
   * Approuve une demande rapidement.
   * Si la demande nécessite un choix référent/utilisateur, ouvre le dialog à la place.
   */
  quickApprove(validation: ValidationRequestListItem, event: Event): void {
    event.stopPropagation();

    // Si la demande nécessite un choix référent/utilisateur, ouvrir le dialog
    if (this.requiresReferentChoice(validation)) {
      this.openDetail(validation);
      return;
    }

    this.validationService.approveRequest(validation.id).subscribe({
      next: () => {
        this.snackBar.open('Demande approuvee', 'OK', { duration: 3000 });
        this.loadValidations();
        this.notificationService.refresh().subscribe();
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Erreur lors de l\'approbation', 'Fermer', {
          duration: 5000
        });
      }
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
   * Formate la date.
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
