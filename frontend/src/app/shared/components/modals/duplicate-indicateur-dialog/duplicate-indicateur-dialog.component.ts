/**
 * Modale de duplication d'un indicateur sur un ou plusieurs niveaux
 * d'exigence et/ou résultats attendus (#262).
 *
 * Reçoit la source via MAT_DIALOG_DATA + la liste des cibles disponibles
 * (NE et RA) qu'elle affiche en deux colonnes de checkboxes. À la
 * confirmation, retourne au composant appelant la liste des `ne_ids` et
 * `ra_ids` choisis ; l'appel API et le snackbar restent à la charge de
 * l'appelant pour rester cohérent avec les autres patterns du module.
 */
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { TranslateModule } from '@ngx-translate/core';

export interface DuplicateIndicateurTargetNe {
  id_ne: number;
  libelle: string;
  // Contexte pour aider l'utilisateur à se repérer
  enjeu_libelle?: string;
  olt_libelle?: string;
}

export interface DuplicateIndicateurTargetRa {
  id_ra: number;
  libelle: string;
  enjeu_libelle?: string;
  oo_libelle?: string;
}

export interface DuplicateIndicateurDialogData {
  /** Nom de l'indicateur source, affiché dans l'en-tête */
  sourceName: string;
  /** ID du parent NE actuel (à exclure de la liste pour ne pas dupliquer en place) */
  currentNeId?: number | null;
  /** ID du parent RA actuel (à exclure) */
  currentRaId?: number | null;
  /** Liste des NE candidats dans le plan */
  availableNe: DuplicateIndicateurTargetNe[];
  /** Liste des RA candidats dans le plan */
  availableRa: DuplicateIndicateurTargetRa[];
}

export interface DuplicateIndicateurDialogResult {
  ne_ids: number[];
  ra_ids: number[];
}

@Component({
  selector: 'app-duplicate-indicateur-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatCheckboxModule,
    TranslateModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ 'enjeux.indicateurs.duplicate.title' | translate }}</h2>
    <mat-dialog-content>
      <p class="source-line">
        <strong>{{ 'enjeux.indicateurs.duplicate.source' | translate }} :</strong>
        {{ data.sourceName }}
      </p>
      <p class="hint">{{ 'enjeux.indicateurs.duplicate.hint' | translate }}</p>

      @if (filteredNe().length > 0) {
        <h3 class="section-title">{{ 'enjeux.indicateurs.duplicate.targetsNe' | translate }}</h3>
        <div class="targets-list">
          @for (ne of filteredNe(); track ne.id_ne) {
            <mat-checkbox
              color="primary"
              [checked]="selectedNeIds().has(ne.id_ne)"
              (change)="toggleNe(ne.id_ne, $event.checked)">
              <span class="target-label">{{ ne.libelle }}</span>
              @if (ne.enjeu_libelle || ne.olt_libelle) {
                <small class="target-context">
                  @if (ne.enjeu_libelle) { · {{ ne.enjeu_libelle }} }
                  @if (ne.olt_libelle) { › {{ ne.olt_libelle }} }
                </small>
              }
            </mat-checkbox>
          }
        </div>
      }

      @if (filteredRa().length > 0) {
        <h3 class="section-title">{{ 'enjeux.indicateurs.duplicate.targetsRa' | translate }}</h3>
        <div class="targets-list">
          @for (ra of filteredRa(); track ra.id_ra) {
            <mat-checkbox
              color="primary"
              [checked]="selectedRaIds().has(ra.id_ra)"
              (change)="toggleRa(ra.id_ra, $event.checked)">
              <span class="target-label">{{ ra.libelle }}</span>
              @if (ra.enjeu_libelle || ra.oo_libelle) {
                <small class="target-context">
                  @if (ra.enjeu_libelle) { · {{ ra.enjeu_libelle }} }
                  @if (ra.oo_libelle) { › {{ ra.oo_libelle }} }
                </small>
              }
            </mat-checkbox>
          }
        </div>
      }

      @if (filteredNe().length === 0 && filteredRa().length === 0) {
        <p class="empty">{{ 'enjeux.indicateurs.duplicate.empty' | translate }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="onCancel()">
        {{ 'common.actions.cancel' | translate }}
      </button>
      <button mat-flat-button color="primary"
              [disabled]="totalSelected() === 0"
              (click)="onConfirm()">
        {{ 'enjeux.indicateurs.duplicate.confirm' | translate }}
        @if (totalSelected() > 0) {
          ({{ totalSelected() }})
        }
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2 { margin: 0; font-weight: 600; }
    mat-dialog-content {
      padding: 16px 0;
      max-height: 60vh;
    }
    .source-line {
      margin: 0 0 8px 0;
      color: #343433;
    }
    .hint {
      margin: 0 0 16px 0;
      color: #746F6E;
      font-size: 13px;
    }
    .section-title {
      margin: 16px 0 8px 0;
      font-size: 14px;
      font-weight: 600;
      color: #025359;
    }
    .targets-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 8px 0;
    }
    .target-label { font-weight: 500; }
    .target-context {
      display: block;
      color: #746F6E;
      font-size: 12px;
      margin-top: 2px;
    }
    .empty {
      color: #746F6E;
      font-style: italic;
      padding: 16px 0;
    }
    mat-dialog-actions { padding-top: 16px; gap: 8px; }
  `],
})
export class DuplicateIndicateurDialogComponent {
  protected readonly data = inject<DuplicateIndicateurDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<DuplicateIndicateurDialogComponent, DuplicateIndicateurDialogResult | null>);

  selectedNeIds = signal(new Set<number>());
  selectedRaIds = signal(new Set<number>());

  filteredNe(): DuplicateIndicateurTargetNe[] {
    return this.data.availableNe.filter(ne => ne.id_ne !== this.data.currentNeId);
  }

  filteredRa(): DuplicateIndicateurTargetRa[] {
    return this.data.availableRa.filter(ra => ra.id_ra !== this.data.currentRaId);
  }

  totalSelected(): number {
    return this.selectedNeIds().size + this.selectedRaIds().size;
  }

  toggleNe(id: number, checked: boolean): void {
    this.selectedNeIds.update(s => {
      const ns = new Set(s);
      if (checked) ns.add(id); else ns.delete(id);
      return ns;
    });
  }

  toggleRa(id: number, checked: boolean): void {
    this.selectedRaIds.update(s => {
      const ns = new Set(s);
      if (checked) ns.add(id); else ns.delete(id);
      return ns;
    });
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }

  onConfirm(): void {
    this.dialogRef.close({
      ne_ids: Array.from(this.selectedNeIds()),
      ra_ids: Array.from(this.selectedRaIds()),
    });
  }
}
