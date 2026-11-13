/**
 * Menu du bouton « Générer » des pages d'un plan de gestion (#795).
 *
 * Chaque page propose quelques exports du plan (catalogue partagé avec la page
 * Exports), éventuellement « Imprimer / PDF » (impression du navigateur), et
 * un lien vers la page Exports pour les autres. Le bouton déclencheur reste
 * dans la page, pour garder son style :
 *
 *   <app-plan-generate-menu #gen [planId]="…" [planSlug]="…" [exports]="['docx']" />
 *   <button [matMenuTriggerFor]="gen.menu">Générer</button>
 *
 * La page n'affiche le bouton qu'à qui peut exporter (`peut_exporter`) : les
 * endpoints `export-*` répondent 403 aux autres.
 */
import { ChangeDetectionStrategy, Component, Input, ViewChild, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenu, MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../../core/services/admin.service';
import {
  PlanExportItem,
  PlanExportKey,
  enregistrerFichier,
  planExportCatalog,
} from '../plan-exports.catalog';

@Component({
  selector: 'app-plan-generate-menu',
  standalone: true,
  imports: [RouterLink, TranslateModule, MatMenuModule, MatDividerModule],
  templateUrl: './plan-generate-menu.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class PlanGenerateMenuComponent {
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly catalogue = planExportCatalog(this.adminService);

  @ViewChild(MatMenu, { static: true }) menu!: MatMenu;

  @Input() planId: number | null = null;
  @Input() planSlug: string | null = null;
  /** « Imprimer / PDF » en tête du menu (pages sans export serveur). */
  @Input() imprimer = false;

  items: PlanExportItem[] = [];

  /** Exports proposés, par clé du catalogue (les exports d'une année restent sur la page Exports). */
  @Input() set exports(keys: PlanExportKey[]) {
    this.items = (keys || []).map(k => this.catalogue[k]).filter(i => i && !i.parAnnee);
  }

  readonly enCours = signal<ReadonlySet<string>>(new Set<string>());

  imprimerPage(): void {
    window.print();
  }

  telecharger(item: PlanExportItem): void {
    const id = this.planId;
    if (id == null || this.enCours().has(item.key)) return;
    this.marquer(item.key, true);
    item.request(id, new Date().getFullYear()).subscribe({
      next: blob => {
        this.marquer(item.key, false);
        enregistrerFichier(blob, item.filename(this.planSlug || `plan-${id}`, new Date().getFullYear()));
      },
      error: err => {
        this.marquer(item.key, false);
        this.snackBar.open(
          err?.message || this.translate.instant('plans.exports.downloadError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  private marquer(key: string, actif: boolean): void {
    this.enCours.update(courant => {
      const suivant = new Set(courant);
      if (actif) suivant.add(key);
      else suivant.delete(key);
      return suivant;
    });
  }
}
