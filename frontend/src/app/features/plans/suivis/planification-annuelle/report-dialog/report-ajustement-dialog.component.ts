import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { PlanificationAnnuelleService } from '../../../../../core/services/planification-annuelle.service';
import { ApercuReport, ResumeAnnuel } from '../../../../../core/models/planification-annuelle.model';

export interface ReportAjustementData {
  operationId: number;
  annee: number;
  /** Années possibles pour le report (après `annee`, jusqu'à la fin du plan). */
  annees: number[];
  libelle: string;
}

/**
 * #794 — Reporter une action : année cible, report total (la suite est
 * décalée) ou partiel (seul le reste à faire passe sur la cible), aperçu
 * avant / après calculé par le serveur, puis confirmation.
 */
@Component({
  selector: 'app-report-ajustement-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatDialogModule, MatProgressSpinnerModule, TranslateModule],
  templateUrl: './report-ajustement-dialog.component.html',
  styleUrl: './report-ajustement-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ReportAjustementDialogComponent {
  readonly data = inject<ReportAjustementData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ReportAjustementDialogComponent, ApercuReport>);
  private readonly service = inject(PlanificationAnnuelleService);
  private readonly translate = inject(TranslateService);

  anneeReport: number | null = this.data.annees[0] ?? null;
  partiel = false;

  apercu = signal<ApercuReport | null>(null);
  enCours = signal(false);
  erreur = signal<string | null>(null);

  /** Une modification du choix rend l'aperçu périmé. */
  choixModifie(): void {
    this.apercu.set(null);
    this.erreur.set(null);
  }

  voirApercu(): void {
    this.envoyer(true);
  }

  confirmer(): void {
    this.envoyer(false);
  }

  private envoyer(apercu: boolean): void {
    if (this.anneeReport == null) return;
    this.enCours.set(true);
    this.erreur.set(null);
    this.service.reporter(this.data.operationId, this.data.annee, {
      annee_report: this.anneeReport, partiel: this.partiel, apercu,
    }).subscribe({
      next: (resultat) => {
        this.enCours.set(false);
        if (apercu) {
          this.apercu.set(resultat);
        } else {
          this.dialogRef.close(resultat);
        }
      },
      error: (err) => {
        this.enCours.set(false);
        this.apercu.set(null);
        this.erreur.set(err?.error?.detail
          ?? this.translate.instant('plans.suivis.planificationAnnuelle.report.erreur'));
      },
    });
  }

  statut(resume: ResumeAnnuel): string {
    const cle = resume.statut === 'planifiee' && resume.annee_report ? 'reportee_partiel' : resume.statut;
    return this.translate.instant(`plans.suivis.planificationAnnuelle.statut.${cle}`, { annee: resume.annee_report });
  }

  anneesAbandonnees(apercu: ApercuReport): string {
    return apercu.abandonnees.map(x => x.annee).join(', ');
  }

  num(valeur: string | null | undefined): number {
    return Number(valeur ?? 0);
  }
}
