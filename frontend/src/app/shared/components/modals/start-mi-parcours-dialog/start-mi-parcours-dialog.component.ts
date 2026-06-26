import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

import { AdminService } from '../../../../core/services/admin.service';
import { AdminPlan } from '../../../../core/models/admin.model';

export interface StartMiParcoursDialogData {
  /** Plan source — un plan validé qui n'a pas encore d'évaluation mi-parcours dans sa chaîne. */
  plan: AdminPlan;
}

/**
 * Résultat de la modale.
 *
 * `mode = 'create'` : on a créé un brouillon EVAL_MI_PARCOURS via `create-evaluation` ;
 *                     `newPlanSlug` est le slug du brouillon créé pour navigation.
 * `mode = 'link'`   : on lie à un brouillon EVAL_MI_PARCOURS existant ;
 *                     `linkedPlanSlug` est le slug pour navigation.
 * `mode = 'cancel'` : annulation.
 */
export interface StartMiParcoursDialogResult {
  mode: 'create' | 'link' | 'cancel';
  newPlanSlug?: string;
  linkedPlanSlug?: string;
}

type ChoiceMode = 'create' | 'link';

@Component({
  selector: 'app-start-mi-parcours-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatProgressSpinnerModule,
    TranslateModule,
  ],
  templateUrl: './start-mi-parcours-dialog.component.html',
  styleUrl: './start-mi-parcours-dialog.component.scss',
})
export class StartMiParcoursDialogComponent implements OnInit {
  private readonly dialogRef = inject(
    MatDialogRef<StartMiParcoursDialogComponent, StartMiParcoursDialogResult>
  );
  private readonly adminService = inject(AdminService);
  readonly data: StartMiParcoursDialogData = inject(MAT_DIALOG_DATA);

  mode: ChoiceMode = 'create';

  // Option « lier »
  availableDrafts: AdminPlan[] = [];
  selectedDraftId: number | null = null;
  loadingDrafts = false;

  // Soumission
  submitting = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    // Si le parent a déjà un brouillon enfant, on bascule par défaut sur
    // « lier à un brouillon existant » (l'option « créer » sera désactivée).
    if (this.data.plan.has_draft_child) {
      this.mode = 'link';
    }
    this.loadAvailableDrafts();
  }

  get hasDraftChild(): boolean {
    return !!this.data.plan.has_draft_child;
  }

  /**
   * Charge les brouillons EVAL_MI_PARCOURS accessibles à l'utilisateur.
   * On filtre côté client sur `type_document_display` ou via la chaîne du plan.
   */
  private loadAvailableDrafts(): void {
    this.loadingDrafts = true;
    this.adminService.getPlans({ statut: 'draft', page_size: 100 }).subscribe({
      next: (response) => {
        // On garde uniquement les brouillons de type EVAL_MI_PARCOURS, et on exclut le plan courant.
        this.availableDrafts = response.results.filter((p) => {
          if (p.id_pg === this.data.plan.id_pg) return false;
          // Filtre par type_document_display (libellé "Évaluation mi-parcours")
          const td = (p as any).type_document_display || '';
          return typeof td === 'string' && td.toLowerCase().includes('mi-parcours');
        });
        this.loadingDrafts = false;
      },
      error: () => {
        this.availableDrafts = [];
        this.loadingDrafts = false;
      },
    });
  }

  get canConfirm(): boolean {
    if (this.submitting) return false;
    if (this.mode === 'link') {
      return this.selectedDraftId != null;
    }
    return true; // 'create' is always valid
  }

  confirm(): void {
    this.errorMessage = null;
    if (this.mode === 'create') {
      this.submitting = true;
      this.adminService.createEvaluation(this.data.plan.id_pg).subscribe({
        next: (newPlan) => {
          this.submitting = false;
          this.dialogRef.close({
            mode: 'create',
            newPlanSlug: newPlan.slug,
          });
        },
        error: (err) => {
          this.submitting = false;
          // #349 — `AdminService.handleError` renvoie un `Error(message)` :
          // on lit `err.message` (ex. « Un brouillon est déjà en cours sur ce
          // plan… ») au lieu de `err.error.error`, toujours indéfini ici.
          this.errorMessage = err?.message || err?.error?.error || 'Erreur lors de la création du brouillon.';
        },
      });
      return;
    }
    if (this.mode === 'link') {
      const selected = this.availableDrafts.find((p) => p.id_pg === this.selectedDraftId);
      this.dialogRef.close({
        mode: 'link',
        linkedPlanSlug: selected?.slug,
      });
      return;
    }
  }

  cancel(): void {
    this.dialogRef.close({ mode: 'cancel' });
  }
}
