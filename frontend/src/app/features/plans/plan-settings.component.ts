import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import {
  AdminPlan,
  PlanStatut,
  PlanVersionChainItem,
  ArborescenceImportReport,
  ArborescenceImportIssue,
} from '../../core/models/admin.model';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { PlanSidebarComponent } from './shared/plan-sidebar/plan-sidebar.component';
import { TagComponent } from '../../shared/components/tag/tag.component';
import { TagAppearance, getPlanStatusTag } from '../../shared/utils/tag-icons';
import {
  ConfirmDialogComponent,
  ConfirmDialogData,
} from '../../shared/components/confirm-dialog/confirm-dialog.component';

/**
 * #348 — Page « Paramètres du plan de gestion ».
 *
 * Gestion avancée : suppression de la VERSION AFFICHÉE (pour éviter les
 * suppressions de versions par erreur, on n'agit que sur le plan courant).
 * Supprimer une version mi-parcours annule de fait l'évaluation à mi-parcours.
 * Accessible uniquement au référent du plan, admin organisme et super admin.
 */
@Component({
  selector: 'app-plan-settings',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatTooltipModule,
    TranslateModule,
    HeaderComponent,
    PlanSidebarComponent,
    TagComponent,
  ],
  templateUrl: './plan-settings.component.html',
  styleUrl: './plan-settings.component.scss',
})
export class PlanSettingsComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly slug = signal<string>(this.route.snapshot.paramMap.get('slug') ?? '');
  readonly plan = signal<AdminPlan | null>(null);
  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly deleting = signal(false);

  /** Versions de la chaîne, triées (rang puis version) — affichées en contexte. */
  readonly versions = computed<PlanVersionChainItem[]>(() => {
    const chain = this.plan()?.version_chain ?? [];
    return [...chain].sort((a, b) => {
      const ra = a.rang ?? 0;
      const rb = b.rang ?? 0;
      if (ra !== rb) return ra - rb;
      return (parseInt(a.version, 10) || 0) - (parseInt(b.version, 10) || 0);
    });
  });

  /** Seuls référent du plan, admin_og et super_admin accèdent aux paramètres. */
  readonly canManage = computed<boolean>(() => {
    if (
      this.authService.isSuperAdmin() ||
      this.authService.isRedacteurPrincipal() ||
      this.authService.isAdminOrganisme()
    ) {
      return true;
    }
    const p = this.plan();
    const currentUser = this.authService.currentUser();
    if (!p || !currentUser) return false;
    return p.referents?.some(r => r.id_role === currentUser.id) || false;
  });

  constructor() {
    this.loadPlan();
  }

  private loadPlan(): void {
    const slug = this.slug();
    if (!slug) {
      this.errorMessage.set(this.translate.instant('plans.settings.deleteError'));
      this.isLoading.set(false);
      return;
    }
    this.isLoading.set(true);
    this.adminService.getPlanBySlug(slug).subscribe({
      next: plan => {
        this.plan.set(plan);
        this.isLoading.set(false);
      },
      error: err => {
        this.errorMessage.set(err?.message || this.translate.instant('plans.settings.deleteError'));
        this.isLoading.set(false);
      },
    });
  }

  /**
   * Apparence du tag de statut (variante + icône), issue de la source de
   * vérité unique `shared/utils/tag-icons.ts` (Figma « 🧩 Tags »).
   */
  statusTag(statut: PlanStatut): TagAppearance {
    return getPlanStatusTag(statut);
  }

  /** Confirme et supprime la version actuellement affichée. */
  confirmDeleteCurrent(): void {
    const p = this.plan();
    if (!p) return;
    const data: ConfirmDialogData = {
      title: this.translate.instant('plans.settings.deleteVersionConfirmTitle'),
      message: this.translate.instant('plans.settings.deleteVersionConfirmMessage', {
        name: p.nom,
        version: p.version ?? '1',
      }),
      confirmText: this.translate.instant('plans.settings.deleteVersion'),
      cancelText: this.translate.instant('common.actions.cancel'),
      confirmColor: 'warn',
    };
    const dialogRef = this.dialog.open(ConfirmDialogComponent, { width: '520px', data });
    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) this.deleteCurrent();
    });
  }

  private deleteCurrent(): void {
    const p = this.plan();
    if (!p) return;
    this.deleting.set(true);

    this.adminService.deletePlanVersion(p.id_pg).subscribe({
      next: () => {
        this.deleting.set(false);
        this.snackBar.open(
          this.translate.instant('plans.settings.deleteSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
        // La version affichée a été supprimée : retour à la liste des plans.
        this.router.navigate(['/plans']);
      },
      error: err => {
        this.deleting.set(false);
        const detail = err?.message || this.translate.instant('plans.settings.deleteError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  // -------------------------------------------------------------------------
  // Import / export de l'arborescence (V1, sans IA)
  // -------------------------------------------------------------------------

  readonly downloading = signal(false);
  readonly importFile = signal<File | null>(null);
  readonly importReport = signal<ArborescenceImportReport | null>(null);
  readonly importValidating = signal(false);
  readonly importing = signal(false);

  /** L'import n'est possible que sur un plan en brouillon. */
  readonly isDraft = computed<boolean>(() => this.plan()?.statut === 'draft');

  /** Anomalies bloquantes du dernier rapport de validation. */
  readonly importErrors = computed<ArborescenceImportIssue[]>(
    () => this.importReport()?.issues.filter(i => i.level === 'error') ?? [],
  );

  /** Avertissements (non bloquants) du dernier rapport de validation. */
  readonly importWarnings = computed<ArborescenceImportIssue[]>(
    () => this.importReport()?.issues.filter(i => i.level === 'warning') ?? [],
  );

  /** Télécharge le classeur (pré-rempli ou vierge) et déclenche le download. */
  downloadTemplate(empty: boolean): void {
    const p = this.plan();
    if (!p) return;
    this.downloading.set(true);
    this.adminService.downloadArborescenceTemplate(p.id_pg, empty).subscribe({
      next: blob => {
        this.downloading.set(false);
        const suffix = empty ? 'modele' : p.slug || `plan-${p.id_pg}`;
        this.triggerBlobDownload(blob, `arborescence-${suffix}.xlsx`);
      },
      error: err => {
        this.downloading.set(false);
        const detail = err?.message || this.translate.instant('plans.import.downloadError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  /** Fichier choisi : on lance immédiatement une validation (dry-run). */
  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.importReport.set(null);
    this.importFile.set(file);
    if (file) {
      this.validateImport(file);
    }
  }

  private validateImport(file: File): void {
    const p = this.plan();
    if (!p) return;
    this.importValidating.set(true);
    this.adminService.validateArborescenceImport(p.id_pg, file).subscribe({
      next: report => {
        this.importValidating.set(false);
        this.importReport.set(report);
      },
      error: err => {
        this.importValidating.set(false);
        const detail = err?.message || this.translate.instant('plans.import.validateError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  /** Annule la sélection de fichier. */
  clearImport(): void {
    this.importFile.set(null);
    this.importReport.set(null);
  }

  /** Exécute l'import (création seule). */
  runImport(): void {
    const p = this.plan();
    const file = this.importFile();
    const report = this.importReport();
    if (!p || !file || !report?.can_import) return;
    this.importing.set(true);
    this.adminService.importArborescence(p.id_pg, file).subscribe({
      next: result => {
        this.importing.set(false);
        this.snackBar.open(
          this.translate.instant('plans.import.importSuccess', { total: result.total }),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
        // L'arborescence a été créée : diriger vers la page des enjeux.
        this.router.navigate(['/plans', p.slug, 'enjeux']);
      },
      error: (err: HttpErrorResponse) => {
        this.importing.set(false);
        // 400 = échec de validation : le corps porte le rapport.
        const body = err?.error as ArborescenceImportReport | { error?: string } | undefined;
        if (body && 'issues' in body) {
          this.importReport.set(body);
        }
        const detail =
          (body && 'error' in body && body.error) ||
          this.translate.instant('plans.import.importError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  // -------------------------------------------------------------------------
  // Module 2 : import des actions
  // -------------------------------------------------------------------------

  readonly downloadingActions = signal(false);
  readonly actionsFile = signal<File | null>(null);
  readonly actionsReport = signal<ArborescenceImportReport | null>(null);
  readonly actionsValidating = signal(false);
  readonly actionsImporting = signal(false);

  readonly actionsErrors = computed<ArborescenceImportIssue[]>(
    () => this.actionsReport()?.issues.filter(i => i.level === 'error') ?? [],
  );
  readonly actionsWarnings = computed<ArborescenceImportIssue[]>(
    () => this.actionsReport()?.issues.filter(i => i.level === 'warning') ?? [],
  );

  /** Télécharge le classeur d'actions (indicateurs du plan pré-remplis). */
  downloadActionsTemplate(): void {
    const p = this.plan();
    if (!p) return;
    this.downloadingActions.set(true);
    this.adminService.downloadActionsTemplate(p.id_pg).subscribe({
      next: blob => {
        this.downloadingActions.set(false);
        this.triggerBlobDownload(blob, `actions-${p.slug || `plan-${p.id_pg}`}.xlsx`);
      },
      error: err => {
        this.downloadingActions.set(false);
        const detail = err?.message || this.translate.instant('plans.import.downloadError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  onActionsFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.actionsReport.set(null);
    this.actionsFile.set(file);
    if (file) {
      this.validateActionsImport(file);
    }
  }

  private validateActionsImport(file: File): void {
    const p = this.plan();
    if (!p) return;
    this.actionsValidating.set(true);
    this.adminService.validateActionsImport(p.id_pg, file).subscribe({
      next: report => {
        this.actionsValidating.set(false);
        this.actionsReport.set(report);
      },
      error: err => {
        this.actionsValidating.set(false);
        const detail = err?.message || this.translate.instant('plans.import.validateError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  clearActionsImport(): void {
    this.actionsFile.set(null);
    this.actionsReport.set(null);
  }

  runActionsImport(): void {
    const p = this.plan();
    const file = this.actionsFile();
    const report = this.actionsReport();
    if (!p || !file || !report?.can_import) return;
    this.actionsImporting.set(true);
    this.adminService.importActions(p.id_pg, file).subscribe({
      next: result => {
        this.actionsImporting.set(false);
        this.snackBar.open(
          this.translate.instant('plans.import.actionsImportSuccess', { total: result.total }),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
        this.router.navigate(['/plans', p.slug, 'enjeux']);
      },
      error: (err: HttpErrorResponse) => {
        this.actionsImporting.set(false);
        const body = err?.error as ArborescenceImportReport | { error?: string } | undefined;
        if (body && 'issues' in body) {
          this.actionsReport.set(body);
        }
        const detail =
          (body && 'error' in body && body.error) ||
          this.translate.instant('plans.import.importError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }
}
