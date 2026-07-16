import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminPlan, PlanStatut, PlanVersionChainItem } from '../../core/models/admin.model';
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
}
