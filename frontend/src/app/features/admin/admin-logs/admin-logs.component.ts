/**
 * Composant pour la page d'administration des logs d'erreur.
 * Permet aux super admins de consulter et acquitter les erreurs.
 */
import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';
import { SearchBarComponent } from '../../../shared/components/search-bar/search-bar.component';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import { TagAppearance, getLogLevelTag } from '../../../shared/utils/tag-icons';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ErrorLogService } from '../../../core/services/error-log.service';
import {
  ErrorLog,
  ErrorLogLevel,
  ErrorLogFilters
} from '../../../core/models/error-log.model';
import { ErrorLogDetailDialogComponent } from './error-log-detail-dialog.component';

@Component({
  selector: 'app-admin-logs',
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
    FormFieldComponent,
    SearchBarComponent,
    TagComponent,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
    MatTooltipModule,
    MatDatepickerModule,
    MatNativeDateModule,
    TranslateModule
  ],
  templateUrl: './admin-logs.component.html',
  styleUrl: './admin-logs.component.scss'
})
export class AdminLogsComponent implements OnInit, OnDestroy {
  private readonly errorLogService = inject(ErrorLogService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  // Etat
  readonly loading = signal(false);
  readonly errorLogs = signal<ErrorLog[]>([]);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = 20;

  // Filtres
  levelFilter: ErrorLogLevel | '' = '';
  acknowledgedFilter: string = '';
  searchFilter = '';

  // Colonnes du tableau
  readonly displayedColumns = ['level', 'message', 'path', 'user', 'correlation_id', 'date', 'acknowledged', 'actions'];

  // Options de filtres
  readonly levelOptions = [
    { value: '', label: 'Tous les niveaux' },
    { value: 'WARNING', label: 'Avertissement' },
    { value: 'ERROR', label: 'Erreur' },
    { value: 'CRITICAL', label: 'Critique' }
  ];

  readonly acknowledgedOptions = [
    { value: '', label: 'Tous' },
    { value: 'true', label: 'Acquittes' },
    { value: 'false', label: 'Non acquittes' }
  ];

  ngOnInit(): void {
    this.loadErrorLogs();
    // Demarrer le rafraichissement automatique du count
    this.errorLogService.startAutoRefresh(60000);
  }

  ngOnDestroy(): void {
    this.errorLogService.stopAutoRefresh();
  }

  /**
   * Charge les logs d'erreur.
   */
  loadErrorLogs(): void {
    this.loading.set(true);

    const filters: ErrorLogFilters = {
      page: this.currentPage(),
    };

    if (this.levelFilter) {
      filters.level = this.levelFilter as ErrorLogLevel;
    }
    if (this.acknowledgedFilter !== '') {
      filters.acknowledged = this.acknowledgedFilter === 'true';
    }
    if (this.searchFilter) {
      filters.search = this.searchFilter;
    }

    this.errorLogService.getErrorLogs(filters).subscribe({
      next: (response) => {
        this.errorLogs.set(response.results);
        this.totalCount.set(response.count);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement logs:', error);
        this.snackBar.open(
          this.translate.instant('admin.logs.messages.loadError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loading.set(false);
      }
    });
  }

  /**
   * Change de page.
   */
  onPageChange(event: PageEvent): void {
    this.currentPage.set(event.pageIndex + 1);
    this.loadErrorLogs();
  }

  /**
   * Applique les filtres.
   */
  applyFilters(): void {
    this.currentPage.set(1);
    this.loadErrorLogs();
  }

  /**
   * Reinitialise les filtres.
   */
  resetFilters(): void {
    this.levelFilter = '';
    this.acknowledgedFilter = '';
    this.searchFilter = '';
    this.currentPage.set(1);
    this.loadErrorLogs();
  }

  /**
   * Ouvre le detail d'un log.
   */
  openDetail(errorLog: ErrorLog): void {
    const dialogRef = this.dialog.open(ErrorLogDetailDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { errorLogId: errorLog.id }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === 'acknowledged') {
        this.loadErrorLogs();
      }
    });
  }

  /**
   * Acquitte un log rapidement.
   */
  quickAcknowledge(errorLog: ErrorLog, event: Event): void {
    event.stopPropagation();

    if (errorLog.acknowledged) {
      return;
    }

    this.errorLogService.acknowledge(errorLog.id).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.logs.messages.acknowledged'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadErrorLogs();
      },
      error: (error) => {
        this.snackBar.open(
          error.error?.detail || this.translate.instant('admin.logs.messages.acknowledgeError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /**
   * Acquitte tous les logs non acquittes.
   */
  acknowledgeAll(): void {
    const filters: ErrorLogFilters = {};

    if (this.levelFilter) {
      filters.level = this.levelFilter as ErrorLogLevel;
    }
    if (this.searchFilter) {
      filters.search = this.searchFilter;
    }

    this.errorLogService.acknowledgeAll(filters).subscribe({
      next: (response) => {
        const count = response.acknowledged_count || 0;
        this.snackBar.open(
          this.translate.instant('admin.logs.messages.acknowledgedAll', { count }),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadErrorLogs();
      },
      error: (error) => {
        this.snackBar.open(
          error.error?.detail || this.translate.instant('admin.logs.messages.acknowledgeError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /**
   * Obtient l'apparence du tag de niveau (couleur + icône).
   * Mapping centralisé dans `shared/utils/tag-icons.ts`.
   */
  getLevelTag(level: ErrorLogLevel): TagAppearance {
    return getLogLevelTag(level);
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

  /**
   * Tronque un message.
   */
  truncateMessage(message: string, maxLength: number = 80): string {
    if (message.length <= maxLength) {
      return message;
    }
    return message.substring(0, maxLength) + '...';
  }
}
