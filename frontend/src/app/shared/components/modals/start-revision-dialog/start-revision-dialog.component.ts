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
import { FormFieldComponent } from '../../form-field/form-field.component';

export interface StartRevisionDialogData {
  /** Plan source qui va être marqué en révision. */
  plan: AdminPlan;
}

/**
 * Résultat de la modale.
 *
 * `mode = 'create'`  : on a créé un nouveau brouillon ; `nextRangPlanId` est l'ID du brouillon créé
 *                       (le composant a déjà appelé `createNextRangPlan`).
 * `mode = 'link'`    : on lie au plan dont l'ID est dans `nextRangPlanId`.
 * `mode = 'none'`    : on marque la révision sans lier de plan suivant.
 * `mode = 'cancel'`  : l'utilisateur a annulé.
 */
export interface StartRevisionDialogResult {
  mode: 'create' | 'link' | 'none' | 'cancel';
  nextRangPlanId?: number | null;
}

type ChoiceMode = 'create' | 'link' | 'none';

@Component({
  selector: 'app-start-revision-dialog',
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
    FormFieldComponent,
  ],
  templateUrl: './start-revision-dialog.component.html',
  styleUrl: './start-revision-dialog.component.scss',
})
export class StartRevisionDialogComponent implements OnInit {
  private readonly dialogRef = inject(
    MatDialogRef<StartRevisionDialogComponent, StartRevisionDialogResult>
  );
  private readonly adminService = inject(AdminService);
  readonly data: StartRevisionDialogData = inject(MAT_DIALOG_DATA);

  mode: ChoiceMode = 'create';

  // Option « créer »
  nom = '';
  anneeDebut: number | null = null;
  anneeFin: number | null = null;

  // Option « lier »
  availableDrafts: AdminPlan[] = [];
  selectedDraftId: number | null = null;
  loadingDrafts = false;

  // Soumission
  submitting = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    const source = this.data.plan;
    const newRang = (source.rang ?? 1) + 1;
    this.nom = `Plan de gestion rang ${newRang} - ${source.nom}`;
    this.anneeDebut = source.annee_fin ? source.annee_fin + 1 : null;
    this.anneeFin = source.annee_fin ? source.annee_fin + 10 : null;

    // Si le plan a déjà un brouillon enfant, bascule par défaut sur « link »
    // ou « none » (l'option « create » sera désactivée).
    if (source.has_draft_child) {
      this.mode = 'link';
    }

    this.loadAvailableDrafts();
  }

  get hasDraftChild(): boolean {
    return !!this.data.plan.has_draft_child;
  }

  private loadAvailableDrafts(): void {
    this.loadingDrafts = true;
    this.adminService.getPlans({ statut: 'draft', page_size: 100 }).subscribe({
      next: (response) => {
        // Exclure le plan courant lui-même au cas où (ne devrait pas être draft de toute façon)
        this.availableDrafts = response.results.filter((p) => p.id_pg !== this.data.plan.id_pg);
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
    if (this.mode === 'create') {
      return !!(this.nom && this.anneeDebut && this.anneeFin && this.anneeDebut <= this.anneeFin);
    }
    if (this.mode === 'link') {
      return this.selectedDraftId != null;
    }
    return true; // 'none'
  }

  confirm(): void {
    this.errorMessage = null;
    if (this.mode === 'create') {
      this.submitting = true;
      this.adminService.createNextRangPlan(this.data.plan.id_pg, {
        nom: this.nom,
        annee_debut: this.anneeDebut!,
        annee_fin: this.anneeFin!,
      }).subscribe({
        next: (newPlan) => {
          this.submitting = false;
          this.dialogRef.close({ mode: 'create', nextRangPlanId: newPlan.id_pg });
        },
        error: (err) => {
          this.submitting = false;
          this.errorMessage = err?.error?.error || 'Erreur lors de la création du brouillon.';
        },
      });
      return;
    }
    if (this.mode === 'link') {
      this.dialogRef.close({ mode: 'link', nextRangPlanId: this.selectedDraftId! });
      return;
    }
    this.dialogRef.close({ mode: 'none', nextRangPlanId: null });
  }

  cancel(): void {
    this.dialogRef.close({ mode: 'cancel' });
  }
}
