import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { TranslateModule } from '@ngx-translate/core';

export interface FrequencyApplyDialogData {
  /** Années de la programmation (ordre du tableau). */
  years: number[];
  /** Libellés des 12 mois. */
  monthLabels: string[];
  /** Fréquence saisie : nombre + unité (mnémonique minuscule). */
  frequenceNombre: number | null;
  frequenceUnite: string | null;
  /** Index de l'année de départ proposée par défaut (1re année saisie). */
  defaultStartYearIndex: number;
  /** Mois de départ proposé par défaut (1-12). */
  defaultStartMonth: number;
}

export interface FrequencyApplyDialogResult {
  /** Périodicité annuelle calculée, par index d'année. */
  yearFlags: boolean[];
  /** Périodicité mensuelle récurrente, clés '1'..'12'. */
  monthFlags: Record<string, boolean>;
}

/**
 * #374 — Modale « Appliquer aux années » : à partir d'une année (et d'un mois)
 * de départ choisis par l'utilisateur, pré-coche les occurrences selon la
 * fréquence saisie, puis laisse ajuster l'aperçu avant d'appliquer. Évite de
 * deviner l'ancrage (on n'est jamais certain de la bonne année/du bon mois).
 */
@Component({
  selector: 'app-frequency-apply-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatSelectModule, TranslateModule],
  templateUrl: './frequency-apply-dialog.component.html',
  styleUrl: './frequency-apply-dialog.component.scss',
})
export class FrequencyApplyDialogComponent implements OnInit {
  private readonly dialogRef = inject(
    MatDialogRef<FrequencyApplyDialogComponent, FrequencyApplyDialogResult | null>
  );
  readonly data: FrequencyApplyDialogData = inject(MAT_DIALOG_DATA);

  startYearIndex = 0;
  startMonth = 1; // 1-12
  /** Aperçu éditable : périodicité par index d'année. */
  yearFlags: boolean[] = [];
  /** Aperçu éditable : périodicité par index de mois (0 = janvier). */
  monthFlags: boolean[] = [];

  ngOnInit(): void {
    this.startYearIndex = this.clampIndex(this.data.defaultStartYearIndex, this.data.years.length);
    this.startMonth = Math.min(12, Math.max(1, this.data.defaultStartMonth || 1));
    this.recompute();
  }

  private clampIndex(i: number, len: number): number {
    if (!Number.isFinite(i) || i < 0) return 0;
    return Math.min(i, Math.max(0, len - 1));
  }

  /** Pas en années selon l'unité (2/5/10 ans → 2/5/10 ; sinon annuel = 1). */
  get yearStep(): number {
    const u = (this.data.frequenceUnite || '').toLowerCase();
    if (u === '2_ans') return 2;
    if (u === '5_ans') return 5;
    if (u === '10_ans') return 10;
    return 1;
  }

  /** Nombre d'occurrences par an (pour répartir les mois récurrents). */
  get occurrencesParAn(): number {
    const u = (this.data.frequenceUnite || '').toLowerCase();
    const n = Math.max(1, this.data.frequenceNombre || 1);
    if (['2_ans', '5_ans', '10_ans'].includes(u)) return 1; // 1 seule occurrence (le mois de départ)
    if (u === 'an') return Math.min(12, n);
    if (u === 'trimestre') return Math.min(12, 4 * n);
    if (u === 'mois') return 12;
    if (u === 'semaine' || u === 'jour') return 12;
    return 1;
  }

  /** Recalcule l'aperçu (années + mois) à partir du départ et de la fréquence. */
  recompute(): void {
    const step = this.yearStep;
    this.yearFlags = this.data.years.map(
      (_, i) => i >= this.startYearIndex && (i - this.startYearIndex) % step === 0
    );

    const count = this.occurrencesParAn;
    const monthStep = Math.max(1, Math.floor(12 / count));
    this.monthFlags = Array(12).fill(false);
    const start0 = this.startMonth - 1; // index 0-based
    for (let k = 0; k < count; k++) {
      this.monthFlags[(start0 + k * monthStep) % 12] = true;
    }
  }

  toggleYear(i: number): void {
    this.yearFlags[i] = !this.yearFlags[i];
  }

  toggleMonth(i: number): void {
    this.monthFlags[i] = !this.monthFlags[i];
  }

  get nbYearsSelected(): number {
    return this.yearFlags.filter(Boolean).length;
  }
  get nbMonthsSelected(): number {
    return this.monthFlags.filter(Boolean).length;
  }

  confirm(): void {
    const monthFlags: Record<string, boolean> = {};
    for (let m = 1; m <= 12; m++) {
      monthFlags[String(m)] = !!this.monthFlags[m - 1];
    }
    this.dialogRef.close({ yearFlags: [...this.yearFlags], monthFlags });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
