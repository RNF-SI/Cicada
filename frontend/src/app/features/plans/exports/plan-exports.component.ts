/**
 * Page « Exports » d'un plan de gestion (#617).
 *
 * Route : /plans/:slug/exports
 *
 * Regroupe tous les exports du plan (documents rédigés, classeurs de
 * présentation, budget et RH). Comme la page « Paramètres », elle est réservée
 * aux référents du plan et gestionnaires (admin organisme, rédacteur principal,
 * super admin) : un export extrait l'intégralité du contenu du plan, ce qui va
 * au-delà de la consultation en lecture seule ouverte aux utilisateurs
 * simplement liés au plan (#610). Le backend applique la même règle sur les
 * endpoints `export-*` (403 sinon).
 */
import { Component, OnInit, computed, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import { AuthService } from '../../../core/services/auth.service';
import { AdminPlan } from '../../../core/models/admin.model';
import { planEndYear } from '../../../shared/utils/plan-periode';
import {
  PLAN_EXPORT_GROUPS,
  PlanExportItem,
  enregistrerFichier,
  planExportCatalog,
} from './plan-exports.catalog';

export type { PlanExportItem } from './plan-exports.catalog';

/** Groupe d'exports affiché en section. */
export interface PlanExportGroup {
  titleKey: string;
  items: PlanExportItem[];
}

@Component({
  selector: 'app-plan-exports',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TranslateModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    HeaderComponent,
    PlanSidebarComponent,
  ],
  templateUrl: './plan-exports.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './plan-exports.component.scss',
})
export class PlanExportsComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly plan = signal<AdminPlan | null>(null);
  readonly planId = signal<number | null>(null);
  readonly planSlug = signal<string | null>(null);
  readonly planNom = signal<string>('');
  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  /**
   * Seuls référent du plan, admin organisme, rédacteur principal et super admin
   * accèdent aux exports (même règle que « Paramètres » et « Suivis »).
   */
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

  /** #727 — années du plan (prolongation comprise), pour les exports par année. */
  readonly anneesPlan = computed<number[]>(() => {
    const p = this.plan();
    if (!p?.annee_debut) return [];
    const fin = planEndYear(p) ?? p.annee_debut;
    return Array.from({ length: fin - p.annee_debut + 1 }, (_, i) => p.annee_debut! + i);
  });

  private readonly anneeChoisie = signal<number | null>(null);
  /** Année proposée : celle choisie, sinon l'année courante bornée au plan. */
  readonly anneeSuivi = computed<number>(() => {
    const annees = this.anneesPlan();
    const choisie = this.anneeChoisie();
    if (choisie != null) return choisie;
    const y = new Date().getFullYear();
    if (!annees.length) return y;
    return Math.min(Math.max(y, annees[0]), annees[annees.length - 1]);
  });

  setAnneeSuivi(annee: number): void {
    this.anneeChoisie.set(Number(annee));
  }

  /** Clés des exports en cours de téléchargement (plusieurs en parallèle possible). */
  readonly downloading = signal<ReadonlySet<string>>(new Set<string>());

  private readonly catalogue = planExportCatalog(this.adminService);

  readonly groups: PlanExportGroup[] = PLAN_EXPORT_GROUPS.map(g => ({
    titleKey: g.titleKey,
    items: g.keys.map(k => this.catalogue[k]),
  }));

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      this.planSlug.set(slug);
      if (!slug) {
        this.isLoading.set(false);
        return;
      }
      this.adminService.getPlanBySlug(slug).subscribe({
        next: plan => {
          this.plan.set(plan);
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.isLoading.set(false);
        },
        error: () => {
          this.errorMessage.set(
            this.translate.instant('plans.suivis.saisie.errors.planNotFound'),
          );
          this.isLoading.set(false);
        },
      });
    });
  }

  isDownloading(key: string): boolean {
    return this.downloading().has(key);
  }

  /** Lance le téléchargement d'un export et déclenche la sauvegarde du blob. */
  download(item: PlanExportItem): void {
    const id = this.planId();
    if (id == null || !this.canManage() || this.isDownloading(item.key)) return;
    this.setDownloading(item.key, true);
    const annee = this.anneeSuivi();
    item.request(id, annee).subscribe({
      next: blob => {
        this.setDownloading(item.key, false);
        this.triggerBlobDownload(blob, item.filename(this.planSlug() || `plan-${id}`, annee));
      },
      error: err => {
        this.setDownloading(item.key, false);
        const detail = err?.message || this.translate.instant('plans.exports.downloadError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), {
          duration: 5000,
        });
      },
    });
  }

  private setDownloading(key: string, active: boolean): void {
    this.downloading.update(current => {
      const next = new Set(current);
      if (active) {
        next.add(key);
      } else {
        next.delete(key);
      }
      return next;
    });
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    enregistrerFichier(blob, filename);
  }

}
