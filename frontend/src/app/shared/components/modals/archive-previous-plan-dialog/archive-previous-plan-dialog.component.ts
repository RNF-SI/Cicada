import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem } from '../../../../core/models/admin.model';

export interface ArchivePreviousPlanDialogData {
  /** Identifiant du plan à archiver. */
  previousPlanId: number;
  /** Nom complet du plan précédent (affiché dans la pop-up). */
  previousPlanName: string;
  /** Période optionnelle ("2014 - 2025") affichée à côté du nom. */
  previousPlanPeriod?: string;
}

export interface ArchivePreviousPlanDialogResult {
  /** `true` si l'utilisateur a confirmé l'archivage. */
  confirmed: boolean;
}

/**
 * Cherche dans la chaîne de versions un plan encore au statut `valide`,
 * différent de celui qui vient d'être validé. Si un tel plan existe, il est
 * candidat à l'archivage automatique (#246).
 *
 * V1 : on s'appuie uniquement sur la `version_chain` (lien `plan_parent`).
 * Le cas « nouveau rang sans plan_parent partageant un site » sera couvert
 * par #248 (verrouillage hors brouillon + détection automatique de rang).
 */
export function findPreviousValidatedPlan(
  currentPlanId: number,
  versionChain: PlanVersionChainItem[] | undefined,
): PlanVersionChainItem | null {
  if (!versionChain || versionChain.length === 0) {
    return null;
  }
  return versionChain.find(p => p.id_pg !== currentPlanId && p.statut === 'valide') ?? null;
}

@Component({
  selector: 'app-archive-previous-plan-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TranslateModule],
  templateUrl: './archive-previous-plan-dialog.component.html',
  styleUrl: './archive-previous-plan-dialog.component.scss',
})
export class ArchivePreviousPlanDialogComponent {
  private readonly dialogRef = inject(
    MatDialogRef<ArchivePreviousPlanDialogComponent, ArchivePreviousPlanDialogResult>
  );
  readonly data: ArchivePreviousPlanDialogData = inject(MAT_DIALOG_DATA);

  confirm(): void {
    this.dialogRef.close({ confirmed: true });
  }

  cancel(): void {
    this.dialogRef.close({ confirmed: false });
  }
}
