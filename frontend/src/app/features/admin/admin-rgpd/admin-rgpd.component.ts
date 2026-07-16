import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../core/services/admin.service';
import { RgpdRequest } from '../../../core/models/admin.model';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import { USER_STATUS_TAG } from '../../../shared/utils/tag-icons';

@Component({
  selector: 'app-admin-rgpd',
  standalone: true,
  imports: [
    CommonModule,
    DatePipe,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatCardModule,
    TagComponent,
    MatSnackBarModule,
    MatDialogModule,
    TranslateModule
  ],
  templateUrl: './admin-rgpd.component.html',
  styleUrl: './admin-rgpd.component.scss'
})
export class AdminRgpdComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);

  // State
  readonly requests = signal<RgpdRequest[]>([]);
  readonly loading = signal(true);
  readonly authProvider = signal<string>('local');
  readonly processingIds = signal<Set<number>>(new Set());

  // Table columns
  readonly displayedColumns = ['user', 'email', 'organisme', 'requested_at', 'days', 'status', 'actions'];

  // Apparence des tags de statut de compte (mapping centralisé, cf. shared/utils/tag-icons.ts)
  readonly activeTag = USER_STATUS_TAG['active'];
  readonly inactiveTag = USER_STATUS_TAG['inactive'];

  // Computed
  readonly isKeycloak = computed(() => this.authProvider() === 'keycloak');
  readonly hasRequests = computed(() => this.requests().length > 0);

  ngOnInit(): void {
    this.loadAuthProvider();
    this.loadRequests();
  }

  private loadAuthProvider(): void {
    this.adminService.getAuthProvider().subscribe({
      next: (response) => {
        this.authProvider.set(response.provider);
      },
      error: () => {
        // Default to local if error
        this.authProvider.set('local');
      }
    });
  }

  loadRequests(): void {
    this.loading.set(true);
    this.adminService.getRgpdRequests().subscribe({
      next: (response) => {
        this.requests.set(response.results);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.showError(this.translate.instant('admin.rgpd.messages.loadError'));
        console.error('Error loading RGPD requests:', err);
      }
    });
  }

  isProcessing(userId: number): boolean {
    return this.processingIds().has(userId);
  }

  private addProcessing(userId: number): void {
    this.processingIds.update(set => new Set(set).add(userId));
  }

  private removeProcessing(userId: number): void {
    this.processingIds.update(set => {
      const newSet = new Set(set);
      newSet.delete(userId);
      return newSet;
    });
  }

  deactivateUser(request: RgpdRequest): void {
    if (!confirm(this.translate.instant('admin.rgpd.confirmDeactivate', { name: request.full_name }))) {
      return;
    }

    this.addProcessing(request.id_role);
    this.adminService.deactivateUserRgpd(request.id_role).subscribe({
      next: () => {
        this.removeProcessing(request.id_role);
        this.showSuccess(this.translate.instant('admin.rgpd.messages.deactivated'));
        this.loadRequests();
      },
      error: (err) => {
        this.removeProcessing(request.id_role);
        this.showError(err.message || this.translate.instant('errors.generic'));
      }
    });
  }

  anonymizeUser(request: RgpdRequest): void {
    if (!confirm(this.translate.instant('admin.rgpd.confirmAnonymize', { name: request.full_name }))) {
      return;
    }

    this.addProcessing(request.id_role);
    this.adminService.anonymizeUserRgpd(request.id_role).subscribe({
      next: () => {
        this.removeProcessing(request.id_role);
        this.showSuccess(this.translate.instant('admin.rgpd.messages.anonymized'));
        this.loadRequests();
      },
      error: (err) => {
        this.removeProcessing(request.id_role);
        this.showError(err.message || this.translate.instant('errors.generic'));
      }
    });
  }

  rejectRequest(request: RgpdRequest): void {
    if (!confirm(this.translate.instant('admin.rgpd.confirmReject', { name: request.full_name }))) {
      return;
    }

    this.addProcessing(request.id_role);
    this.adminService.rejectRgpdRequest(request.id_role).subscribe({
      next: () => {
        this.removeProcessing(request.id_role);
        this.showSuccess(this.translate.instant('admin.rgpd.messages.rejected'));
        this.loadRequests();
      },
      error: (err) => {
        this.removeProcessing(request.id_role);
        this.showError(err.message || this.translate.instant('errors.generic'));
      }
    });
  }

  private showSuccess(message: string): void {
    this.snackBar.open(message, this.translate.instant('common.actions.close'), {
      duration: 3000,
      panelClass: ['snackbar-success']
    });
  }

  private showError(message: string): void {
    this.snackBar.open(message, this.translate.instant('common.actions.close'), {
      duration: 5000,
      panelClass: ['snackbar-error']
    });
  }
}
