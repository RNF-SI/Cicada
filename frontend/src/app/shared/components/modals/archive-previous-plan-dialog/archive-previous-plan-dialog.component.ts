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
 * Cherche dans la chaîne de versions le plan validé **antérieur** à celui qu'on
 * vient de valider/réactiver, candidat à l'archivage automatique (#246).
 *
 * #395 — On ne retient qu'un plan dont l'ordre (rang puis version) est
 * **strictement inférieur** à celui du plan courant, et on prend le plus récent
 * d'entre eux (prédécesseur immédiat). Sans cette contrainte, réactiver un plan
 * ancien proposait d'archiver un plan plus récent, ce qui n'avait pas de sens.
 *
 * On s'appuie sur la `version_chain` (lien `plan_parent`). La `version` étant
 * scopée au rang (#279), on compare d'abord le rang puis la version.
 */
export function findPreviousValidatedPlan(
  currentPlanId: number,
  versionChain: PlanVersionChainItem[] | undefined,
): PlanVersionChainItem | null {
  if (!versionChain || versionChain.length === 0) {
    return null;
  }
  const current = versionChain.find(p => p.id_pg === currentPlanId);
  if (!current) {
    return null;
  }
  const orderKey = (p: PlanVersionChainItem): [number, number] => [p.rang ?? 0, Number(p.version) || 0];
  const [curRang, curVer] = orderKey(current);
  const isBefore = (p: PlanVersionChainItem): boolean => {
    const [r, v] = orderKey(p);
    return r < curRang || (r === curRang && v < curVer);
  };

  const candidates = versionChain.filter(
    p => p.id_pg !== currentPlanId && p.statut === 'valide' && isBefore(p),
  );
  if (candidates.length === 0) {
    return null;
  }
  // Prédécesseur immédiat = le plus récent (ordre le plus élevé) parmi les antérieurs.
  return candidates.reduce((best, p) => {
    const [br, bv] = orderKey(best);
    const [pr, pv] = orderKey(p);
    return pr > br || (pr === br && pv > bv) ? p : best;
  });
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
