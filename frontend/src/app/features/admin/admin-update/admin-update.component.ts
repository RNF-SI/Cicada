import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { SystemUpdateService, SystemVersionInfo } from '../../../core/services/system-update.service';

@Component({
  selector: 'app-admin-update',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    TranslateModule
  ],
  templateUrl: './admin-update.component.html',
  styleUrl: './admin-update.component.scss'
})
export class AdminUpdateComponent implements OnInit {
  private readonly systemUpdateService = inject(SystemUpdateService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly versionInfo = signal<SystemVersionInfo | null>(null);
  readonly loading = signal(true);
  readonly updating = signal(false);

  ngOnInit(): void {
    this.loadVersion();
  }

  loadVersion(): void {
    this.loading.set(true);
    this.systemUpdateService.getVersion().subscribe({
      next: (info) => {
        this.versionInfo.set(info);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  triggerUpdate(): void {
    const info = this.versionInfo();
    const latest = info?.latest_version;
    if (!latest) return;

    const message = this.translate.instant('admin.update.confirmUpdate', { version: latest });
    if (!confirm(message)) return;

    this.updating.set(true);
    this.systemUpdateService.triggerUpdate(latest).subscribe({
      next: (res) => {
        this.updating.set(false);
        this.snackBar.open(
          res.message || this.translate.instant('admin.update.scheduled'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        this.loadVersion();
      },
      error: (err) => {
        this.updating.set(false);
        const msg = err?.error?.error || err?.message || this.translate.instant('admin.update.error');
        this.snackBar.open(msg, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  formatDate(value: string | null): string {
    if (!value) return '—';
    try {
      const d = new Date(value);
      return d.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return value;
    }
  }
}
