/**
 * Composant pour la page "Mes demandes".
 * Affiche toutes les demandes de validation de l'utilisateur.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ValidationService } from '../../core/services/validation.service';
import { ModuleService } from '../../core/services/module.service';
import { Module } from '../../core/models/module.model';
import {
  ValidationRequestListItem,
  ValidationStatus,
  ValidationRequestType,
  ValidatorInfo,
} from '../../core/models/notification.model';
import { ModuleAccessRequestDialogComponent, ModuleAccessRequestDialogData } from '../../shared/components/module-access-request-dialog/module-access-request-dialog.component';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../shared/components/confirm-dialog/confirm-dialog.component';

/**
 * Interface pour un module avec son statut d'acces.
 */
interface ModuleWithStatus extends Module {
  accessStatus: 'granted' | 'pending' | 'rejected' | 'none';
}

@Component({
  selector: 'app-my-requests',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule
  ],
  templateUrl: './my-requests.component.html',
  styleUrl: './my-requests.component.scss'
})
export class MyRequestsComponent implements OnInit {
  private readonly validationService = inject(ValidationService);
  private readonly moduleService = inject(ModuleService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);

  // Demandes de l'utilisateur
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly loadingRequests = signal(false);

  // Validateurs par demande en attente (qui peut valider) — chargé à la demande
  readonly validatorsByRequest = signal<Record<number, ValidatorInfo[]>>({});

  /** Retourne les validateurs connus pour une demande. */
  getValidators(requestId: number): ValidatorInfo[] {
    return this.validatorsByRequest()[requestId] || [];
  }

  // Modules necessitant un acces (charges depuis l'API)
  readonly availableModules = signal<Module[]>([]);
  readonly loadingModules = signal(false);

  // Colonnes du tableau des demandes
  readonly requestColumns = ['type', 'target', 'date', 'validated_at', 'status', 'validator', 'actions'];

  // Modules avec statut d'acces calcule
  readonly modulesWithStatus = computed(() => {
    const requests = this.myRequests();
    const modules = this.availableModules();

    return modules.map(module => {
      const moduleRequests = requests.filter(
        r => r.request_type === 'module_access' && r.target_name === module.name
      );
      const pendingRequest = moduleRequests.find(r => r.status === 'pending');
      const approvedRequest = moduleRequests.find(r => r.status === 'approved');
      const rejectedRequest = moduleRequests.find(r => r.status === 'rejected');

      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      if (approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      return {
        ...module,
        accessStatus
      } as ModuleWithStatus;
    }).filter(m => m.accessStatus !== 'granted'); // N'afficher que les modules sans acces
  });

  ngOnInit(): void {
    this.loadMyRequests();
    this.loadModulesRequiringAccess();
  }

  /**
   * Charge les modules necessitant un acces depuis l'API.
   */
  private loadModulesRequiringAccess(): void {
    this.loadingModules.set(true);
    this.moduleService.getModulesRequiringAccess().subscribe({
      next: (modules) => {
        this.availableModules.set(modules);
        this.loadingModules.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement modules:', error);
        this.loadingModules.set(false);
      }
    });
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
        this.loadValidatorsForPending(requests);
      },
      error: (error) => {
        console.error('Erreur chargement mes demandes:', error);
        this.snackBar.open(
          this.translate.instant('myRequests.loadError'),
          this.translate.instant('common.actions.close'), {
          duration: 3000
        });
        this.loadingRequests.set(false);
      }
    });
  }

  /**
   * Charge les validateurs (qui peut valider) pour les demandes en attente.
   */
  private loadValidatorsForPending(requests: ValidationRequestListItem[]): void {
    const pending = requests.filter(r => r.status === 'pending');
    for (const req of pending) {
      this.validationService.getRequestValidators(req.id).subscribe({
        next: (res) => {
          this.validatorsByRequest.update(map => ({
            ...map,
            [req.id]: res.validators,
          }));
        },
        error: () => {
          // Non bloquant : on garde simplement le libellé générique
        }
      });
    }
  }

  /**
   * Annule une demande en attente.
   * Pour une création de site (#467), l'annulation supprime définitivement
   * le site créé (encore inactif) : on demande une confirmation explicite.
   */
  cancelRequest(request: ValidationRequestListItem): void {
    if (request.status !== 'pending') return;

    if (request.request_type === 'site_creation') {
      const dialogRef = this.dialog.open(ConfirmDialogComponent, {
        width: '500px',
        data: {
          title: this.translate.instant('myRequests.cancelSiteConfirm.title'),
          message: this.translate.instant('myRequests.cancelSiteConfirm.message', {
            name: request.target_name || '',
          }),
          warningText: this.translate.instant('myRequests.cancelSiteConfirm.warning'),
          confirmText: this.translate.instant('myRequests.cancelSiteConfirm.confirm'),
          destructive: true,
        } as ConfirmDialogData,
      });

      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.performCancel(request);
        }
      });
      return;
    }

    this.performCancel(request);
  }

  /**
   * Effectue l'annulation d'une demande via l'API.
   */
  private performCancel(request: ValidationRequestListItem): void {
    this.validationService.cancelRequest(request.id).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('myRequests.cancelSuccess'),
          this.translate.instant('common.actions.close'), {
          duration: 3000
        });
        this.loadMyRequests();
      },
      error: (error) => {
        console.error('Erreur annulation demande:', error);
        this.snackBar.open(
          this.translate.instant('myRequests.cancelError'),
          this.translate.instant('common.actions.close'), {
          duration: 3000
        });
      }
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
      'site_creation': 'fi-rr-land-layer-location',
      'plan_access': 'fi-rr-document',
      'module_access': 'fi-rr-apps',
      'admin_deactivation': 'fi-rr-user-slash',
      'referent_validation': 'fi-rr-check',
    };
    return icons[type] || 'fi-rr-check-circle';
  }

  /**
   * Ouvre le dialog de demande d'acces a un module.
   */
  openModuleAccessDialog(module: ModuleWithStatus): void {
    const dialogRef = this.dialog.open(ModuleAccessRequestDialogComponent, {
      width: '500px',
      data: {
        moduleCode: module.code,
        moduleName: module.name
      } as ModuleAccessRequestDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadMyRequests();
        this.loadModulesRequiringAccess();
      }
    });
  }

  /**
   * Compte les demandes en attente.
   */
  getPendingCount(): number {
    return this.myRequests().filter(r => r.status === 'pending').length;
  }

  /**
   * Compte les demandes approuvees.
   */
  getApprovedCount(): number {
    return this.myRequests().filter(r => r.status === 'approved').length;
  }

  /**
   * Compte les demandes rejetees.
   */
  getRejectedCount(): number {
    return this.myRequests().filter(r => r.status === 'rejected').length;
  }
}
