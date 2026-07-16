import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';

/** Pression candidate (cible d'un partage/copie d'OO). */
export interface SharePressionTarget {
  id_pression: number;
  libelle: string;
  facteurLibelle?: string;
}

/** Enjeu candidat, éventuellement porteur de pressions (cas OO). */
export interface ShareEnjeuTarget {
  id_enjeu: number;
  libelle: string;
  numero?: number | null;
  /** Pressions sous cet enjeu (uniquement pour le partage/copie d'un OO). */
  pressions?: SharePressionTarget[];
}

export interface ShareElementDialogData {
  /** Type d'élément partagé/copié. */
  elementType: 'facteur' | 'oo';
  /** Libellé de l'élément source (affiché dans l'entête). */
  elementLabel: string;
  /** Mode présélectionné selon le bouton cliqué. */
  mode: 'link' | 'copy';
  /**
   * Enjeux candidats du même plan. Pour un facteur, on choisit un enjeu ; pour
   * un OO, on choisit une pression parmi celles listées sous chaque enjeu.
   * Les enjeux/pressions où l'élément est déjà présent doivent être exclus par
   * l'appelant.
   */
  enjeux: ShareEnjeuTarget[];
}

export interface ShareElementDialogResult {
  mode: 'link' | 'copy';
  /** Cible retenue : un enjeu (facteur) ou une pression (OO). */
  targetEnjeuId?: number;
  targetPressionId?: number;
}

@Component({
  selector: 'app-share-element-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    TranslateModule,
  ],
  templateUrl: './share-element-dialog.component.html',
  styleUrl: './share-element-dialog.component.scss',
})
export class ShareElementDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<ShareElementDialogComponent>);
  readonly data: ShareElementDialogData = inject(MAT_DIALOG_DATA);

  readonly mode = signal<'link' | 'copy'>(this.data.mode);
  readonly searchTerm = signal('');
  /** Enjeu sélectionné (facteur) ou pression sélectionnée (OO). */
  readonly selectedEnjeuId = signal<number | null>(null);
  readonly selectedPressionId = signal<number | null>(null);

  readonly isOo = this.data.elementType === 'oo';

  /** i18n racine des libellés selon le type d'élément. */
  readonly typeKey = this.isOo ? 'oo' : 'facteur';

  readonly filteredEnjeux = computed<ShareEnjeuTarget[]>(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const enjeux = this.data.enjeux;
    if (!term) return enjeux;
    return enjeux
      .map((e) => {
        const enjeuMatch = e.libelle.toLowerCase().includes(term);
        if (!this.isOo) return enjeuMatch ? e : null;
        const pressions = (e.pressions || []).filter(
          (p) =>
            p.libelle.toLowerCase().includes(term) ||
            (p.facteurLibelle || '').toLowerCase().includes(term),
        );
        if (enjeuMatch) return e;
        return pressions.length ? { ...e, pressions } : null;
      })
      .filter((e): e is ShareEnjeuTarget => e !== null);
  });

  readonly hasTargets = computed(() => {
    if (this.isOo) {
      return this.data.enjeux.some((e) => (e.pressions || []).length > 0);
    }
    return this.data.enjeux.length > 0;
  });

  readonly canConfirm = computed(() =>
    this.isOo ? this.selectedPressionId() !== null : this.selectedEnjeuId() !== null,
  );

  setMode(mode: 'link' | 'copy'): void {
    this.mode.set(mode);
  }

  selectEnjeu(id: number): void {
    this.selectedEnjeuId.set(this.selectedEnjeuId() === id ? null : id);
  }

  selectPression(id: number): void {
    this.selectedPressionId.set(this.selectedPressionId() === id ? null : id);
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
  }

  confirm(): void {
    if (!this.canConfirm()) return;
    const result: ShareElementDialogResult = { mode: this.mode() };
    if (this.isOo) {
      result.targetPressionId = this.selectedPressionId()!;
    } else {
      result.targetEnjeuId = this.selectedEnjeuId()!;
    }
    this.dialogRef.close(result);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
