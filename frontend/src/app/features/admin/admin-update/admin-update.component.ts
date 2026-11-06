import { Component, inject, signal, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  SystemUpdateService,
  SystemUpdateOutcome,
  SystemUpdateResult,
  SystemVersionInfo
} from '../../../core/services/system-update.service';

/** Issues d'échec qui ont un libellé propre (#796) */
const FAILURE_OUTCOMES: SystemUpdateOutcome[] = ['annulee', 'echec_retour_fait', 'echec_sans_retour'];

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
const CHECK_POLL_INTERVAL_MS = 2000;
/** Le heartbeat répond en quelques secondes ; au-delà, l'hôte ne prend pas le déclencheur. */
const CHECK_GIVE_UP_AFTER_MS = 60 * 1000;

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
  /** Vérification demandée, en attente de la réponse de l'API de suivi */
  readonly checking = signal(false);

  readonly phase = signal<UpdatePhase>('idle');
  /** Version visée par la mise à jour en cours */
  readonly targetVersion = signal<string | null>(null);
  /** Message d'erreur de l'updater, en phase « failed » */
  readonly failureMessage = signal<string | null>(null);
  /** Issue de l'échec (annulée, retour arrière fait ou non), en phase « failed » (#796) */
  readonly failureOutcome = signal<SystemUpdateOutcome | null>(null);
  /** Version rétablie, ou à rétablir, en phase « failed » */
  readonly failureDepart = signal<string | null>(null);
  /** Commande à lancer sur le serveur quand l'application est restée arrêtée */
  readonly failureCommande = signal<string | null>(null);

  /** Résultat connu avant le clic : un résultat différent = celui de cette mise à jour */
  private resultBefore: string | null = null;
  private pollTimer: ReturnType<typeof setTimeout> | null = null;
  private startedAt = 0;
  private checkTimer: ReturnType<typeof setTimeout> | null = null;
  private checkStartedAt = 0;

  ngOnInit(): void {
    this.loadVersion();
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.stopCheckPolling();
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
    this.failureOutcome.set(null);
    this.failureCommande.set(null);
    this.systemUpdateService.triggerUpdate(latest).subscribe({
      next: () => {
        this.updating.set(false);
        this.startFollowing('scheduled');
      },
      error: (err) => {
        this.updating.set(false);
        // #719 — jamais le message technique d'Angular (« Http failure response… »).
        const msg = err?.error?.error || this.translate.instant('admin.update.error');
        this.snackBar.open(msg, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  /**
   * « Vérifier les mises à jour » : l'hôte interroge l'API de suivi sans
   * attendre le heartbeat de la nuit. On suit le déclencheur jusqu'à ce que
   * le heartbeat l'ait consommé, puis on affiche ce qu'il a rapporté.
   */
  checkForUpdate(): void {
    this.checking.set(true);
    this.systemUpdateService.checkForUpdate().subscribe({
      next: () => {
        this.checkStartedAt = Date.now();
        this.scheduleCheckPoll();
      },
      error: (err) => {
        this.checking.set(false);
        const msg = err?.error?.error || this.translate.instant('admin.update.check.error');
        this.notify(msg);
      }
    });
  }

  private pollCheck(): void {
    this.checkTimer = null;
    this.systemUpdateService.getVersion().subscribe(info => {
      if (info.check_pending) {
        if (Date.now() - this.checkStartedAt > CHECK_GIVE_UP_AFTER_MS) {
          this.checking.set(false);
          this.notify(this.translate.instant('admin.update.check.noHost'));
        } else {
          this.scheduleCheckPoll();
        }
        return;
      }
      this.checking.set(false);
      this.versionInfo.set(info);
      if (info.last_check_error) {
        this.notify(this.translate.instant('admin.update.check.failed'));
      } else if (info.update_available && info.latest_version) {
        this.notify(this.translate.instant('admin.update.check.found', { version: info.latest_version }));
      } else {
        this.notify(this.translate.instant('admin.update.check.upToDate'));
      }
    });
  }

  private scheduleCheckPoll(): void {
    this.checkTimer = setTimeout(() => this.pollCheck(), CHECK_POLL_INTERVAL_MS);
  }

  private stopCheckPolling(): void {
    if (this.checkTimer) {
      clearTimeout(this.checkTimer);
      this.checkTimer = null;
    }
  }

  private notify(message: string): void {
    this.snackBar.open(message, this.translate.instant('common.actions.close'), { duration: 6000 });
  }

  /** Icône et libellé à afficher pour la phase courante */
  get phaseKey(): string {
    const outcome = this.failureOutcome();
    if (this.phase() === 'failed' && outcome && FAILURE_OUTCOMES.includes(outcome)) {
      return `admin.update.outcome.${outcome}`;
    }
    return `admin.update.progress.${this.phase()}`;
  }

  /**
   * #796 — Dernière tentative en échec, à rappeler à l'ouverture de la page
   * tant que la version visée n'est pas en service : sans cela, un échec
   * survenu en l'absence de l'administrateur passait inaperçu.
   */
  lastFailure(): SystemUpdateResult | null {
    const info = this.versionInfo();
    const last = info?.last_update;
    if (!last || last.success || !last.statut || !FAILURE_OUTCOMES.includes(last.statut)) return null;
    if (last.cible && last.cible === info?.current_version) return null;
    return last;
  }

  /** Mise à jour réussie, mais un service déjà en échec avant elle l'est encore (#796) */
  lastWarning(): string | null {
    const last = this.versionInfo()?.last_update;
    return last?.success && last.avertissement ? last.avertissement : null;
  }

  outcomeKey(result: SystemUpdateResult): string {
    return `admin.update.outcome.${result.statut}`;
  }

  get isInProgress(): boolean {
    return ['scheduled', 'running', 'restarting'].includes(this.phase());
  }

  private startFollowing(initial: UpdatePhase): void {
    this.phase.set(initial);
    this.systemUpdateService.markUpdateInProgress();
    this.startedAt = Date.now();
    this.stopPolling();
    this.pollTimer = setTimeout(() => this.poll(), POLL_INTERVAL_MS);
  }

  private poll(): void {
    this.pollTimer = null;
    if (Date.now() - this.startedAt > GIVE_UP_AFTER_MS) {
      this.phase.set('unknown');
      this.systemUpdateService.markUpdateFinished();
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
        this.systemUpdateService.markUpdateFinished();
        this.failureMessage.set(result.error ?? null);
        this.failureOutcome.set(result.statut ?? null);
        this.failureDepart.set(result.depart ?? null);
        this.failureCommande.set(result.commande ?? null);
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

  /** Taille lisible (octets → Mo / Go) */
  formatSize(bytes: number | null | undefined): string {
    const n = Number(bytes) || 0;
    if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Go`;
    return `${Math.max(1, Math.round(n / 1024 ** 2)).toLocaleString('fr-FR')} Mo`;
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
