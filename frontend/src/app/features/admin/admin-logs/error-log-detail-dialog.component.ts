/**
 * Dialog pour afficher le detail d'un log d'erreur.
 */
import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ErrorLogService } from '../../../core/services/error-log.service';
import { ErrorLogDetail, ErrorLogLevel } from '../../../core/models/error-log.model';

interface DialogData {
  errorLogId: number;
}

@Component({
  selector: 'app-error-log-detail-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDividerModule,
    MatTooltipModule,
    TranslateModule
  ],
  template: `
    <h2 mat-dialog-title>
      <i class="fi fi-rr-bug"></i>
      {{ 'admin.logs.detail.title' | translate }}
    </h2>

    <mat-dialog-content>
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (errorLog()) {
        <div class="error-log-detail">
          <!-- En-tete -->
          <div class="detail-header">
            <mat-chip [ngClass]="getLevelClass(errorLog()!.level)">
              <i class="fi" [ngClass]="getLevelIcon(errorLog()!.level)"></i>
              {{ errorLog()!.level_display }}
            </mat-chip>
            <span class="date">{{ formatDate(errorLog()!.created_at) }}</span>
            @if (errorLog()!.acknowledged) {
              <span class="acknowledged-badge">
                <i class="fi fi-rr-check"></i>
                {{ 'admin.logs.detail.acknowledgedBy' | translate }}
                {{ errorLog()!.acknowledged_by_name }}
              </span>
            }
          </div>

          <!-- Message -->
          <div class="detail-section">
            <h4>{{ 'admin.logs.detail.message' | translate }}</h4>
            <p class="message">{{ errorLog()!.message }}</p>
          </div>

          <!-- Info requete -->
          @if (errorLog()!.path || errorLog()!.user_name) {
            <div class="detail-section">
              <h4>{{ 'admin.logs.detail.requestInfo' | translate }}</h4>
              <div class="info-grid">
                @if (errorLog()!.path) {
                  <div class="info-item">
                    <span class="label">{{ 'admin.logs.detail.path' | translate }}</span>
                    <span class="value path">
                      <span class="method">{{ errorLog()!.method || 'GET' }}</span>
                      {{ errorLog()!.path }}
                    </span>
                  </div>
                }
                @if (errorLog()!.user_name) {
                  <div class="info-item">
                    <span class="label">{{ 'admin.logs.detail.user' | translate }}</span>
                    <span class="value">{{ errorLog()!.user_name }} ({{ errorLog()!.user_email }})</span>
                  </div>
                }
                @if (errorLog()!.correlation_id) {
                  <div class="info-item">
                    <span class="label">{{ 'admin.logs.detail.correlationId' | translate }}</span>
                    <span class="value mono" [matTooltip]="'Cliquer pour copier'">
                      {{ errorLog()!.correlation_id }}
                    </span>
                  </div>
                }
                @if (errorLog()!.logger_name) {
                  <div class="info-item">
                    <span class="label">{{ 'admin.logs.detail.logger' | translate }}</span>
                    <span class="value mono">{{ errorLog()!.logger_name }}</span>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Exception -->
          @if (errorLog()!.exception_type || errorLog()!.stack_trace) {
            <div class="detail-section">
              <h4>{{ 'admin.logs.detail.exception' | translate }}</h4>
              @if (errorLog()!.exception_type) {
                <p class="exception-type">{{ errorLog()!.exception_type }}</p>
              }
              @if (errorLog()!.stack_trace) {
                <pre class="stack-trace">{{ errorLog()!.stack_trace }}</pre>
              }
            </div>
          }

          <!-- Contexte -->
          @if (errorLog()!.context && hasContext()) {
            <div class="detail-section">
              <h4>{{ 'admin.logs.detail.context' | translate }}</h4>
              <pre class="context">{{ formatContext() }}</pre>
            </div>
          }
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      @if (errorLog() && !errorLog()!.acknowledged) {
        <button
          mat-flat-button
          color="primary"
          (click)="acknowledge()"
          [disabled]="acknowledging()"
        >
          @if (acknowledging()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <i class="fi fi-rr-check"></i>
            {{ 'admin.logs.actions.acknowledge' | translate }}
          }
        </button>
      }
      <button mat-stroked-button mat-dialog-close>
        {{ 'common.actions.close' | translate }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .loading-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 200px;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #025359;
    }

    h2[mat-dialog-title] i {
      font-size: 1.2rem;
    }

    mat-dialog-content {
      min-height: 200px;
      max-height: 70vh;
      overflow-y: auto;
    }

    .error-log-detail .detail-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }

    .error-log-detail .detail-header .date {
      color: #746F6E;
      font-size: 0.9rem;
    }

    .error-log-detail .detail-header .acknowledged-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #04854B;
      font-size: 0.85rem;
    }

    .error-log-detail .detail-header .acknowledged-badge i {
      font-size: 0.9rem;
    }

    .error-log-detail .detail-section {
      margin-bottom: 24px;
    }

    .error-log-detail .detail-section h4 {
      margin: 0 0 8px 0;
      color: #025359;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .error-log-detail .detail-section .message {
      margin: 0;
      padding: 16px;
      background: #F5F5F5;
      border-radius: 4px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .info-grid {
      display: grid;
      gap: 8px;
    }

    .info-grid .info-item {
      display: flex;
      gap: 16px;
    }

    .info-grid .info-item .label {
      color: #746F6E;
      min-width: 120px;
      font-weight: 500;
    }

    .info-grid .info-item .value {
      color: #343433;
    }

    .info-grid .info-item .value.path {
      font-family: monospace;
      font-size: 0.9rem;
    }

    .info-grid .info-item .value.path .method {
      background: #E0E0E0;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.75rem;
      font-weight: 600;
      margin-right: 8px;
    }

    .info-grid .info-item .value.mono {
      font-family: monospace;
      font-size: 0.85rem;
    }

    .exception-type {
      margin: 0 0 8px 0;
      color: #E12329;
      font-family: monospace;
      font-weight: 600;
    }

    .stack-trace,
    .context {
      margin: 0;
      padding: 16px;
      background: #1e1e1e;
      color: #d4d4d4;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.8rem;
      overflow-x: auto;
      white-space: pre;
      max-height: 300px;
      overflow-y: auto;
    }

    /* Status classes pour les chips - Regles accessibilite WCAG AA */
    /* WARNING: Orange (#FA9965) avec texte noir (#343433) */
    .status-warning {
      --mdc-chip-elevated-container-color: #FA9965;
      --mdc-chip-label-text-color: #343433;
      color: #343433;
    }

    .status-warning i {
      color: #343433;
    }

    /* ERROR: Rouge (#E12329) avec texte blanc */
    .status-error {
      --mdc-chip-elevated-container-color: #E12329;
      --mdc-chip-label-text-color: #FFFFFF;
      color: #FFFFFF;
    }

    .status-error i {
      color: #FFFFFF;
    }

    /* CRITICAL: Bleu-vert primaire (#025359) avec texte blanc */
    .status-critical {
      --mdc-chip-elevated-container-color: #025359;
      --mdc-chip-label-text-color: #FFFFFF;
      color: #FFFFFF;
    }

    .status-critical i {
      color: #FFFFFF;
    }

    mat-chip i {
      margin-right: 4px;
    }

    mat-dialog-actions {
      padding: 16px 24px;
    }

    mat-dialog-actions button i {
      margin-right: 4px;
    }
  `]
})
export class ErrorLogDetailDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<ErrorLogDetailDialogComponent>);
  private readonly data: DialogData = inject(MAT_DIALOG_DATA);
  private readonly errorLogService = inject(ErrorLogService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly loading = signal(true);
  readonly acknowledging = signal(false);
  readonly errorLog = signal<ErrorLogDetail | null>(null);

  ngOnInit(): void {
    this.loadErrorLog();
  }

  loadErrorLog(): void {
    this.loading.set(true);

    this.errorLogService.getErrorLog(this.data.errorLogId).subscribe({
      next: (log) => {
        this.errorLog.set(log);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement log:', error);
        this.snackBar.open(
          this.translate.instant('admin.logs.messages.loadError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.dialogRef.close();
      }
    });
  }

  acknowledge(): void {
    if (!this.errorLog() || this.errorLog()!.acknowledged) {
      return;
    }

    this.acknowledging.set(true);

    this.errorLogService.acknowledge(this.data.errorLogId).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.logs.messages.acknowledged'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.dialogRef.close('acknowledged');
      },
      error: (error) => {
        this.acknowledging.set(false);
        this.snackBar.open(
          error.error?.detail || this.translate.instant('admin.logs.messages.acknowledgeError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  getLevelClass(level: ErrorLogLevel): string {
    const classes: Record<string, string> = {
      'WARNING': 'status-warning',
      'ERROR': 'status-error',
      'CRITICAL': 'status-critical'
    };
    return classes[level] || 'status-neutre';
  }

  getLevelIcon(level: ErrorLogLevel): string {
    const icons: Record<string, string> = {
      'WARNING': 'fi-rr-exclamation',
      'ERROR': 'fi-rr-cross-circle',
      'CRITICAL': 'fi-rr-flame'
    };
    return icons[level] || 'fi-rr-info';
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  hasContext(): boolean {
    const ctx = this.errorLog()?.context;
    return ctx !== null && ctx !== undefined && Object.keys(ctx).length > 0;
  }

  formatContext(): string {
    const ctx = this.errorLog()?.context;
    if (!ctx) return '';
    return JSON.stringify(ctx, null, 2);
  }
}
