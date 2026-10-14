import { Component, inject, signal, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  SystemUpdateService,
  SystemUpdateResult,
  SystemVersionInfo
} from '../../../core/services/system-update.service';

/**
 * Phases d'une mise à jour, telles que la page les suit après le clic :
 * - scheduled  : déclencheur déposé, l'updater de l'hôte ne l'a pas encore pris
 * - running    : paquet et images en cours de téléchargement
 * - restarting : l'application redémarre, l'API ne répond plus
 * - done       : nouvelle version en place, la page va se recharger
 * - failed     : l'updater a signalé une erreur
 * - unknown    : plus de nouvelles depuis trop longtemps
 */
export type UpdatePhase = 'idle' | 'scheduled' | 'running' | 'restarting' | 'done' | 'failed' | 'unknown';

const POLL_INTERVAL_MS = 4000;
const GIVE_UP_AFTER_MS = 15 * 60 * 1000;
const RELOAD_DELAY_MS = 3000;

@Component({
  selector: 'app-admin-update',
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    TranslateModule
],
  templateUrl: './admin-update.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './admin-update.component.scss'
})
export class AdminUpdateComponent implements OnInit, OnDestroy {
  private readonly systemUpdateService = inject(SystemUpdateService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly versionInfo = signal<SystemVersionInfo | null>(null);
  readonly loading = signal(true);
  readonly updating = signal(false);

  readonly phase = signal<UpdatePhase>('idle');
  /** Version visée par la mise à jour en cours */
  readonly targetVersion = signal<string | null>(null);
  /** Message d'erreur de l'updater, en phase « failed » */
  readonly failureMessage = signal<string | null>(null);

  /** Résultat connu avant le clic : un résultat différent = celui de cette mise à jour */
  private resultBefore: string | null = null;
  private pollTimer: ReturnType<typeof setTimeout> | null = null;
  private startedAt = 0;

  ngOnInit(): void {
    this.loadVersion();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  loadVersion(): void {
    this.loading.set(true);
    this.systemUpdateService.getVersion().subscribe({
      next: (info) => {
        this.versionInfo.set(info);
        this.loading.set(false);
        // Mise à jour lancée depuis un autre onglet, ou page rechargée en cours
        // de route : on reprend le suivi là où il en est.
        if (info.update_pending && this.phase() === 'idle') {
          this.resultBefore = this.resultKey(info.last_update);
          this.targetVersion.set(info.latest_version);
          this.startFollowing('scheduled');
        }
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
    this.resultBefore = this.resultKey(info?.last_update);
    this.targetVersion.set(latest);
    this.failureMessage.set(null);
    this.systemUpdateService.triggerUpdate(latest).subscribe({
      next: () => {
        this.updating.set(false);
        this.startFollowing('scheduled');
      },
      error: (err) => {
        this.updating.set(false);
        const msg = err?.error?.error || err?.message || this.translate.instant('admin.update.error');
        this.snackBar.open(msg, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  /** Icône et libellé à afficher pour la phase courante */
  get phaseKey(): string {
    return `admin.update.progress.${this.phase()}`;
  }

  get isInProgress(): boolean {
    return ['scheduled', 'running', 'restarting'].includes(this.phase());
  }

  private startFollowing(initial: UpdatePhase): void {
    this.phase.set(initial);
    this.startedAt = Date.now();
    this.stopPolling();
    this.pollTimer = setTimeout(() => this.poll(), POLL_INTERVAL_MS);
  }

  private poll(): void {
    this.pollTimer = null;
    if (Date.now() - this.startedAt > GIVE_UP_AFTER_MS) {
      this.phase.set('unknown');
      return;
    }
    this.systemUpdateService.pollVersion().subscribe({
      next: (info) => this.onPolled(info),
      error: () => {
        // L'API ne répond pas : l'application redémarre avec la nouvelle version
        this.phase.set('restarting');
        this.scheduleNextPoll();
      }
    });
  }

  private onPolled(info: SystemVersionInfo): void {
    const result = info.last_update ?? null;
    const finished = result && this.resultKey(result) !== this.resultBefore;

    if (finished) {
      this.versionInfo.set(info);
      if (result.success) {
        this.phase.set('done');
        setTimeout(() => window.location.reload(), RELOAD_DELAY_MS);
      } else {
        this.phase.set('failed');
        this.failureMessage.set(result.error ?? null);
      }
      return;
    }

    // Pas encore de résultat : déclencheur toujours en attente, ou updater au travail
    this.phase.set(info.update_pending ? 'scheduled' : 'running');
    this.scheduleNextPoll();
  }

  private scheduleNextPoll(): void {
    this.pollTimer = setTimeout(() => this.poll(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
  }

  private resultKey(result: SystemUpdateResult | null | undefined): string | null {
    return result ? `${result.timestamp}|${result.version ?? ''}|${result.success}` : null;
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
