import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { FormFieldComponent } from '../../form-field/form-field.component';
import { TagComponent } from '../../tag/tag.component';

export interface LinkOperationDialogData {
  planId: number;
  /** Contexte métrique (défaut). Absent en mode indicateur (#539). */
  metriqueId?: number;
  metriqueNom?: string;
  /** #539 — Contexte indicateur : permet de lier une action directement à un
   *  indicateur (sans passer par une métrique), utile pour les indicateurs qui
   *  n'ont pas de métrique. */
  indicateurId?: number;
  indicateurNom?: string;
}

export interface LinkOperationDialogResult {
  action: 'create' | 'link' | 'copy' | 'cancel';
  operationId?: number;
}

interface OperationItem {
  id_operation: number;
  libelle: string;
  statut?: 'draft' | 'valide';
  type_action_label?: string;
  priorite_label?: string;
  metrique_ids?: number[];
  id_indicateur?: number | null;
}

@Component({
  selector: 'app-link-operation-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule,
    FormFieldComponent,
    TagComponent,
  ],
  templateUrl: './link-operation-dialog.component.html',
  styleUrl: './link-operation-dialog.component.scss',
})
export class LinkOperationDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<LinkOperationDialogComponent>);
  readonly data: LinkOperationDialogData = inject(MAT_DIALOG_DATA);
  private readonly enjeuService = inject(EnjeuService);
  private readonly translate = inject(TranslateService);

  mode = signal<'choose' | 'link' | 'copy'>('choose');
  isLoading = signal(false);
  searchTerm = signal('');
  allOperations = signal<OperationItem[]>([]);
  selectedOperationId = signal<number | null>(null);

  /** #539 — nom du contexte (métrique ou indicateur) affiché dans le sous-titre. */
  readonly contextNom = this.data.metriqueNom ?? this.data.indicateurNom ?? '';
  /** #539 — vrai quand la liaison se fait au niveau indicateur (sans métrique). */
  readonly isIndicateurMode = this.data.metriqueId == null && this.data.indicateurId != null;

  filteredOperations = computed(() => {
    const ops = this.allOperations();
    const term = this.searchTerm().toLowerCase().trim();
    const metriqueId = this.data.metriqueId;
    const indicateurId = this.data.indicateurId;

    // Exclude operations already linked to this metrique (mode métrique) ou déjà
    // rattachées directement à cet indicateur (#539, mode indicateur).
    let filtered = ops.filter(op => {
      if (metriqueId != null) {
        return !op.metrique_ids || !op.metrique_ids.includes(metriqueId);
      }
      return op.id_indicateur !== indicateurId;
    });

    // Apply search filter
    if (term) {
      filtered = filtered.filter(op =>
        op.libelle.toLowerCase().includes(term) ||
        (op.type_action_label && op.type_action_label.toLowerCase().includes(term)) ||
        (op.priorite_label && op.priorite_label.toLowerCase().includes(term))
      );
    }

    return filtered;
  });

  selectCreate(): void {
    this.dialogRef.close({ action: 'create' } as LinkOperationDialogResult);
  }

  selectLink(): void {
    this.mode.set('link');
    this.loadOperations();
  }

  selectCopy(): void {
    this.mode.set('copy');
    this.loadOperations();
  }

  goBack(): void {
    this.mode.set('choose');
    this.selectedOperationId.set(null);
    this.searchTerm.set('');
  }

  selectOperation(opId: number): void {
    this.selectedOperationId.set(
      this.selectedOperationId() === opId ? null : opId
    );
  }

  /** Valide la phase 2 selon le mode courant (lier une action existante ou en copier une). */
  confirmSelection(): void {
    const opId = this.selectedOperationId();
    if (!opId) return;
    const action = this.mode() === 'copy' ? 'copy' : 'link';
    this.dialogRef.close({ action, operationId: opId } as LinkOperationDialogResult);
  }

  cancel(): void {
    this.dialogRef.close({ action: 'cancel' } as LinkOperationDialogResult);
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
  }

  private loadOperations(): void {
    this.isLoading.set(true);
    this.enjeuService.getOperationsByPlan(this.data.planId).subscribe({
      next: (response) => {
        // Flatten grouped operations
        const ops: OperationItem[] = [];
        for (const group of response.groups || []) {
          for (const op of group.operations || []) {
            ops.push({
              id_operation: op.id_operation,
              libelle: op.libelle,
              statut: op.statut,
              type_action_label: op.type_action_label,
              priorite_label: op.priorite_label,
              metrique_ids: op.metrique_ids,
              id_indicateur: op.id_indicateur,
            });
          }
        }
        this.allOperations.set(ops);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }
}
