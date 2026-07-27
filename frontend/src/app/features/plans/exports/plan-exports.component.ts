/**
 * Page « Exports » d'un plan de gestion (#617).
 *
 * Route : /plans/:slug/exports
 *
 * Regroupe tous les exports du plan (documents rédigés, classeurs de
 * présentation, budget et RH). Contrairement à la page « Paramètres », cette
 * page n'est PAS réservée aux gestionnaires : les exports sont de la lecture,
 * donc accessibles à tout utilisateur qui a accès au plan (le backend
 * n'applique d'ailleurs aucune restriction sur ces endpoints GET).
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Observable } from 'rxjs';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';

/** Un export téléchargeable du plan. */
export interface PlanExportItem {
  /** Identifiant interne (clé de l'indicateur de chargement). */
  key: string;
  /** `data-testid` du bouton (stable pour les tests E2E). */
  testId: string;
  /** Classe d'icône Flaticon. */
  icon: string;
  labelKey: string;
  hintKey: string;
  request: (planId: number) => Observable<Blob>;
  filename: (slug: string) => string;
}

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
  styleUrl: './plan-exports.component.scss',
})
export class PlanExportsComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly planId = signal<number | null>(null);
  readonly planSlug = signal<string | null>(null);
  readonly planNom = signal<string>('');
  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  /** Clés des exports en cours de téléchargement (plusieurs en parallèle possible). */
  readonly downloading = signal<ReadonlySet<string>>(new Set<string>());

  readonly groups: PlanExportGroup[] = [
    {
      titleKey: 'plans.exports.groups.documents',
      items: [
        {
          key: 'docx',
          testId: 'plan-docx-export',
          icon: 'fi-rr-file-word',
          labelKey: 'plans.exports.docx',
          hintKey: 'plans.exports.docxHint',
          request: id => this.adminService.downloadPlanDocx(id),
          filename: slug => `plan-de-gestion-${slug}.docx`,
        },
        {
          key: 'presentation',
          testId: 'arbo-export-presentation',
          icon: 'fi-rr-file-spreadsheet',
          labelKey: 'plans.exports.presentation',
          hintKey: 'plans.exports.presentationHint',
          request: id => this.adminService.downloadArborescencePresentation(id),
          filename: slug => `arborescence-presentation-${slug}.xlsx`,
        },
        {
          key: 'fiches',
          testId: 'fiches-actions-export',
          icon: 'fi-rr-clipboard-list',
          labelKey: 'plans.exports.fichesActions',
          hintKey: 'plans.exports.fichesActionsHint',
          request: id => this.adminService.downloadFichesActions(id),
          filename: slug => `fiches-actions-${slug}.xlsx`,
        },
      ],
    },
    {
      titleKey: 'plans.exports.groups.finance',
      items: [
        {
          key: 'budget-prev',
          testId: 'budget-prev-export',
          icon: 'fi-rr-coins',
          labelKey: 'plans.exports.budgetPrev',
          hintKey: 'plans.exports.budgetPrevHint',
          request: id => this.adminService.downloadBudgetPrevisionnel(id),
          filename: slug => `budget-previsionnel-${slug}.xlsx`,
        },
        {
          key: 'budget-suivi',
          testId: 'budget-suivi-export',
          icon: 'fi-rr-coins',
          labelKey: 'plans.exports.budgetSuivi',
          hintKey: 'plans.exports.budgetSuiviHint',
          request: id => this.adminService.downloadBudgetSuivi(id),
          filename: slug => `budget-suivi-${slug}.xlsx`,
        },
        {
          key: 'rh-prev',
          testId: 'rh-prev-export',
          icon: 'fi-rr-users',
          labelKey: 'plans.exports.rhPrev',
          hintKey: 'plans.exports.rhPrevHint',
          request: id => this.adminService.downloadRhPrevisionnel(id),
          filename: slug => `rh-previsionnel-${slug}.xlsx`,
        },
        {
          key: 'rh-suivi',
          testId: 'rh-suivi-export',
          icon: 'fi-rr-users',
          labelKey: 'plans.exports.rhSuivi',
          hintKey: 'plans.exports.rhSuiviHint',
          request: id => this.adminService.downloadRhSuivi(id),
          filename: slug => `rh-suivi-${slug}.xlsx`,
        },
      ],
    },
    {
      titleKey: 'plans.exports.groups.data',
      items: [
        {
          key: 'arborescence',
          testId: 'arbo-export-prefilled',
          icon: 'fi-rr-download',
          labelKey: 'plans.exports.arborescence',
          hintKey: 'plans.exports.arborescenceHint',
          request: id => this.adminService.downloadArborescenceTemplate(id, false),
          filename: slug => `arborescence-${slug}.xlsx`,
        },
      ],
    },
  ];

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
    if (id == null || this.isDownloading(item.key)) return;
    this.setDownloading(item.key, true);
    item.request(id).subscribe({
      next: blob => {
        this.setDownloading(item.key, false);
        this.triggerBlobDownload(blob, item.filename(this.planSlug() || `plan-${id}`));
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
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }
}
