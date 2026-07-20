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
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ValidationService, ValidationFilters, ValidationTypeOption } from '../../../core/services/validation.service';
import { NotificationService } from '../../../core/services/notification.service';
import {
  ValidationRequestListItem,
  ValidationStatus,
  ValidationRequestType
} from '../../../core/models/notification.model';

import { TagComponent } from '../../../shared/components/tag/tag.component';
import {
  FilterBarComponent,
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
} from '../../../shared/components/filters';
import { createFilterSet } from '../../../shared/utils/filter-set';
import { TagAppearance, getValidationStatusTag } from '../../../shared/utils/tag-icons';

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
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    TagComponent,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
    MatTooltipModule,
    FilterBarComponent,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective
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
  // #592 — mono-sélection stockée en tableau (contrat d'`app-filter-option-list`).
  readonly filters = createFilterSet({
    status: [] as string[],
    requestType: [] as string[],
  });

  // Colonnes du tableau
  readonly displayedColumns = ['type', 'requester', 'target', 'date', 'validated_at', 'status', 'validator', 'actions'];

  // Options de filtres (chargées dynamiquement depuis l'API)
  // L'option « Tous » n'est plus une entrée à valeur vide : c'est la ligne `allLabel`
  // du composant de liste, qui vide la sélection.
  readonly statusOptions = signal<ValidationTypeOption[]>([]);
  readonly typeOptions = signal<ValidationTypeOption[]>([]);

  ngOnInit(): void {
    this.loadTypes();
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
   * Charge les types et statuts depuis l'API.
   */
  private loadTypes(): void {
    this.validationService.getTypes().subscribe({
      next: (response) => {
        this.statusOptions.set(response.statuses);
        this.typeOptions.set(response.request_types);
      },
      error: (error) => {
        console.error('Erreur chargement des types:', error);
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
      if (result) {
        this.loadValidations();
        this.notificationService.refresh().subscribe();
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

    const status = this.filters.status()[0];
    const requestType = this.filters.requestType()[0];
    if (status) {
      filters.status = status;
    }
    if (requestType) {
      filters.request_type = requestType;
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

    // Si la demande est bloquée par un site_org_link en attente, ouvrir le dialog
    if (validation.blocked_by_org_link) {
      this.openDetail(validation);
      return;
    }

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
   * Obtient l'apparence du tag de statut (couleur + icône).
   * Mapping centralisé dans `shared/utils/tag-icons.ts`.
   */
  getStatusTag(status: ValidationStatus): TagAppearance {
    return getValidationStatusTag(status);
  }

  /**
   * Obtient l'icone du type de demande.
   */
  getTypeIcon(type: ValidationRequestType): string {
    const icons: Record<string, string> = {
      'user_registration': 'fi-rr-user-add',
      'site_creation': 'fi-rr-marker-plus',
      'site_access': 'fi-rr-marker',
      'plan_access': 'fi-rr-document',
      'module_access': 'fi-rr-apps',
      'admin_deactivation': 'fi-rr-user-slash',
      'admin_promotion': 'fi-rr-user-crown',
      'admin_demotion': 'fi-rr-user-minus',
      'referent_validation': 'fi-rr-badge-check',
      'site_org_link': 'fi-rr-link',
      'invite_org_to_site': 'fi-rr-building',
      'invite_user_to_site': 'fi-rr-user-add',
      'organisme_creation': 'fi-rr-building',
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
