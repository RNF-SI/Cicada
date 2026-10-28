import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  EtatReferentiel, RapportPassage, ReferentielActionsService, VersionDisponible,
} from '../../../core/services/referentiel-actions.service';
import { CheckboxComponent } from '../../../shared/components/checkbox/checkbox.component';
import {
  ConfirmDialogComponent, ConfirmDialogData,
} from '../../../shared/components/confirm-dialog/confirm-dialog.component';

/**
 * #777 — page super-admin « Référentiels », distincte de la mise à jour de
 * l'application : pour chaque référentiel (types d'action, PressRef, TaxRef,
 * HabRef), la version en service, les versions livrées, la simulation puis
 * l'application d'un passage, sa progression et son annulation.
 */
@Component({
  selector: 'app-admin-referentiels',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatProgressSpinnerModule, TranslateModule, CheckboxComponent],
  templateUrl: './admin-referentiels.component.html',
  styleUrl: './admin-referentiels.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class AdminReferentielsComponent implements OnInit {
  private readonly service = inject(ReferentielActionsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly chargement = signal(true);
  readonly referentiels = signal<EtatReferentiel[]>([]);
  readonly erreur = signal<string | null>(null);
  /** Rapport de simulation, par `<référentiel>/<version>`. */
  readonly rapports = signal<Record<string, RapportPassage>>({});
  readonly enCours = signal<string | null>(null);
  readonly sansEmail = signal(false);

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.service.etatAdmin().subscribe({
      next: r => {
        this.referentiels.set(r.referentiels);
        this.chargement.set(false);
      },
      error: () => {
        this.erreur.set(this.translate.instant('admin.referentiels.erreurChargement'));
        this.chargement.set(false);
      },
    });
  }

  cle(ref: EtatReferentiel, v: VersionDisponible): string {
    return `${ref.code}/${v.nom}`;
  }

  rapport(ref: EtatReferentiel, v: VersionDisponible): RapportPassage | undefined {
    return this.rapports()[this.cle(ref, v)];
  }

  /** Nombres du rapport : actions (types d'action) ou objets (autres référentiels). */
  compte(r: RapportPassage, confiance: 'sure' | 'probable' | 'a_arbitrer'): number {
    return (r.actions ?? r.objets ?? {})[confiance] ?? 0;
  }

  simuler(ref: EtatReferentiel, v: VersionDisponible): void {
    this.enCours.set(this.cle(ref, v));
    this.erreur.set(null);
    this.service.simulerAdmin(ref.code, v.nom).subscribe({
      next: r => {
        this.rapports.update(m => ({ ...m, [this.cle(ref, v)]: r.rapport }));
        this.enCours.set(null);
      },
      error: (e: HttpErrorResponse) => this.echec(e),
    });
  }

  appliquer(ref: EtatReferentiel, v: VersionDisponible): void {
    const r = this.rapport(ref, v);
    this.confirmer({
      title: this.translate.instant('admin.referentiels.confirmerAppliquer.titre', { vers: v.libelle }),
      message: this.translate.instant('admin.referentiels.confirmerAppliquer.message', {
        referentiel: ref.libelle, depuis: ref.en_service.libelle, vers: v.libelle,
        auto: r ? this.compte(r, 'sure') + this.compte(r, 'probable') : '?',
        choix: r ? this.compte(r, 'a_arbitrer') : '?',
      }),
      confirmText: this.translate.instant('admin.referentiels.appliquer'),
    }, () => this.lancer(ref, 'appliquer', v.nom));
  }

  annuler(ref: EtatReferentiel): void {
    const p = ref.passage!;
    const v = ref.versions.find(x => x.code === p.vers_code);
    if (!v) return;
    this.confirmer({
      title: this.translate.instant('admin.referentiels.confirmerAnnuler.titre'),
      message: this.translate.instant('admin.referentiels.confirmerAnnuler.message', {
        depuis: p.depuis, vers: p.vers, actualises: p.actualises,
      }),
      confirmText: this.translate.instant('admin.referentiels.annuler'),
      destructive: true,
    }, () => this.lancer(ref, 'annuler', v.nom));
  }

  private confirmer(data: ConfirmDialogData, suite: () => void): void {
    this.dialog.open(ConfirmDialogComponent, { data, width: '640px', maxWidth: '95vw' })
      .afterClosed().subscribe(ok => { if (ok) suite(); });
  }

  private lancer(ref: EtatReferentiel, action: 'appliquer' | 'annuler', nom: string): void {
    this.enCours.set(`${ref.code}/${nom}`);
    this.erreur.set(null);
    this.service.passageAdmin(ref.code, action, nom, this.sansEmail()).subscribe({
      next: r => {
        this.referentiels.set(r.referentiels);
        this.rapports.set({});
        this.enCours.set(null);
        this.snackBar.open(this.translate.instant(`admin.referentiels.${action}Fait`),
          this.translate.instant('common.actions.close'), { duration: 4000 });
      },
      error: (e: HttpErrorResponse) => this.echec(e),
    });
  }

  private echec(e: HttpErrorResponse): void {
    this.enCours.set(null);
    this.erreur.set(e.error?.detail || this.translate.instant('admin.referentiels.erreur'));
  }
}
