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

/** Objectif opérationnel candidat (cible d'un partage/copie de RA, #585). */
export interface ShareOoTarget {
  id_oo: number;
  libelle: string;
  numero?: number | null;
  /** Contexte affiché sous le libellé (pression d'origine, ou « FCR »). */
  contexte?: string;
}

/**
 * #585 — Parent candidat au partage d'un indicateur : un niveau d'exigence
 * (indicateur d'état) ou un résultat attendu (indicateur de pression). Les deux
 * se présentent pareil — un intitulé et son contexte — d'où la forme commune.
 */
export interface ShareParentTarget {
  id: number;
  libelle: string;
  /** Contexte affiché sous l'intitulé (OLT porteur, ou OO porteur). */
  contexte?: string;
}

/** Enjeu candidat, éventuellement porteur de pressions (cas OO). */
export interface ShareEnjeuTarget {
  id_enjeu: number;
  libelle: string;
  numero?: number | null;
  /** Pressions sous cet enjeu (uniquement pour le partage/copie d'un OO). */
  pressions?: SharePressionTarget[];
  /** #585 — Objectifs opérationnels sous cet enjeu (partage/copie d'un RA). */
  objectifs?: ShareOoTarget[];
  /** #585 — Niveaux d'exigence / résultats attendus sous cet enjeu (indicateur). */
  parents?: ShareParentTarget[];
}

/** Métrique candidate (cible d'un partage/copie d'action). */
export interface ShareMetriqueTarget {
  id_metrique: number;
  nom: string;
}

/** Indicateur candidat, porteur de ses métriques (cas action, #585). */
export interface ShareIndicateurTarget {
  id_indicateur: number;
  nom: string;
  /** Contexte affiché sous le nom (enjeu / NE ou RA d'origine). */
  contexte?: string;
  metriques: ShareMetriqueTarget[];
}

export interface ShareElementDialogData {
  /**
   * Type d'élément partagé/copié. `indicateurEtat` et `indicateurPression`
   * (#585) désignent les deux branches du partage d'indicateur : par niveau
   * d'exigence, ou par résultat attendu.
   */
  elementType: 'facteur' | 'oo' | 'ra' | 'operation' | 'indicateurEtat' | 'indicateurPression';
  /** Libellé de l'élément source (affiché dans l'entête). */
  elementLabel: string;
  /** Mode présélectionné selon le bouton cliqué. */
  mode: 'link' | 'copy';
  /**
   * Enjeux candidats du même plan. Pour un facteur, on choisit un enjeu ; pour
   * un OO, on choisit une pression parmi celles listées sous chaque enjeu.
   * Les enjeux/pressions où l'élément est déjà présent doivent être exclus par
   * l'appelant. Inutilisé pour une action (cf. `indicateurs`).
   */
  enjeux: ShareEnjeuTarget[];
  /**
   * #585 — Indicateurs candidats, pour le partage/copie d'une action. On choisit
   * soit une métrique, soit l'indicateur lui-même (rattachement direct #367).
   */
  indicateurs?: ShareIndicateurTarget[];
}

export interface ShareElementDialogResult {
  mode: 'link' | 'copy';
  /** Cible retenue : un enjeu (facteur), une pression (OO), un objectif (RA),
   *  un indicateur ou une métrique (action). */
  targetEnjeuId?: number;
  targetPressionId?: number;
  targetOoId?: number;
  targetIndicateurId?: number;
  targetMetriqueId?: number;
  /** #585 — Niveau d'exigence ou résultat attendu retenu (partage d'indicateur). */
  targetParentId?: number;
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
  /** #585 — Objectif opérationnel retenu (cas RA). */
  readonly selectedOoId = signal<number | null>(null);
  /** #585 — Niveau d'exigence ou résultat attendu retenu (cas indicateur). */
  readonly selectedParentId = signal<number | null>(null);

  /** Cible retenue pour une action (#585) : une métrique ou l'indicateur lui-même. */
  readonly selectedIndicateurId = signal<number | null>(null);
  readonly selectedMetriqueId = signal<number | null>(null);

  readonly isOo = this.data.elementType === 'oo';
  readonly isRa = this.data.elementType === 'ra';
  readonly isOperation = this.data.elementType === 'operation';
  /** #585 — Partage d'un indicateur, quelle que soit sa branche. */
  readonly isIndicateur =
    this.data.elementType === 'indicateurEtat' ||
    this.data.elementType === 'indicateurPression';

  /**
   * #585 — Le choix « Lier / Copier » ne s'affiche pas pour un indicateur : la
   * copie a son propre dialogue depuis #262 (`duplicate-indicateur-dialog`, qui
   * accepte plusieurs cibles à la fois et les deux branches). Ce dialogue-ci ne
   * traite donc que le partage, seul point qui manquait.
   */
  readonly showModeChoice = !this.isIndicateur;

  /** i18n racine des libellés selon le type d'élément. */
  readonly typeKey = this.data.elementType;

  /**
   * #585 — Une action ne peut être rattachée directement qu'à UN seul indicateur
   * (FK `id_indicateur`) : le partage passe forcément par une métrique. En mode
   * « lier », la cible « directement sur l'indicateur » est donc désactivée ;
   * elle reste disponible en mode « copier ».
   */
  readonly canTargetIndicateurDirectly = computed(() => this.mode() === 'copy');

  readonly filteredIndicateurs = computed<ShareIndicateurTarget[]>(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const indicateurs = this.data.indicateurs || [];
    if (!term) return indicateurs;
    return indicateurs
      .map((ind) => {
        const indMatch =
          ind.nom.toLowerCase().includes(term) ||
          (ind.contexte || '').toLowerCase().includes(term);
        if (indMatch) return ind;
        const metriques = ind.metriques.filter((m) => m.nom.toLowerCase().includes(term));
        return metriques.length ? { ...ind, metriques } : null;
      })
      .filter((ind): ind is ShareIndicateurTarget => ind !== null);
  });

  readonly filteredEnjeux = computed<ShareEnjeuTarget[]>(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const enjeux = this.data.enjeux;
    if (!term) return enjeux;
    return enjeux
      .map((e) => {
        const enjeuMatch = e.libelle.toLowerCase().includes(term);
        if (this.isIndicateur) {
          if (enjeuMatch) return e;
          const parents = (e.parents || []).filter(
            (p) =>
              p.libelle.toLowerCase().includes(term) ||
              (p.contexte || '').toLowerCase().includes(term),
          );
          return parents.length ? { ...e, parents } : null;
        }
        if (this.isRa) {
          if (enjeuMatch) return e;
          const objectifs = (e.objectifs || []).filter(
            (o) =>
              o.libelle.toLowerCase().includes(term) ||
              (o.contexte || '').toLowerCase().includes(term),
          );
          return objectifs.length ? { ...e, objectifs } : null;
        }
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
    if (this.isOperation) {
      const indicateurs = this.data.indicateurs || [];
      // En mode « lier », seules les métriques sont des cibles valides.
      return this.canTargetIndicateurDirectly()
        ? indicateurs.length > 0
        : indicateurs.some((ind) => ind.metriques.length > 0);
    }
    if (this.isOo) {
      return this.data.enjeux.some((e) => (e.pressions || []).length > 0);
    }
    if (this.isRa) {
      return this.data.enjeux.some((e) => (e.objectifs || []).length > 0);
    }
    if (this.isIndicateur) {
      return this.data.enjeux.some((e) => (e.parents || []).length > 0);
    }
    return this.data.enjeux.length > 0;
  });

  readonly canConfirm = computed(() => {
    if (this.isOperation) {
      return this.selectedMetriqueId() !== null || this.selectedIndicateurId() !== null;
    }
    if (this.isOo) return this.selectedPressionId() !== null;
    if (this.isRa) return this.selectedOoId() !== null;
    if (this.isIndicateur) return this.selectedParentId() !== null;
    return this.selectedEnjeuId() !== null;
  });

  setMode(mode: 'link' | 'copy'): void {
    this.mode.set(mode);
    // Repasser en « lier » invalide une cible « indicateur direct » déjà choisie.
    if (mode === 'link') {
      this.selectedIndicateurId.set(null);
    }
  }

  selectIndicateur(id: number): void {
    if (!this.canTargetIndicateurDirectly()) return;
    this.selectedMetriqueId.set(null);
    this.selectedIndicateurId.set(this.selectedIndicateurId() === id ? null : id);
  }

  selectMetrique(id: number): void {
    this.selectedIndicateurId.set(null);
    this.selectedMetriqueId.set(this.selectedMetriqueId() === id ? null : id);
  }

  selectEnjeu(id: number): void {
    this.selectedEnjeuId.set(this.selectedEnjeuId() === id ? null : id);
  }

  selectPression(id: number): void {
    this.selectedPressionId.set(this.selectedPressionId() === id ? null : id);
  }

  selectOo(id: number): void {
    this.selectedOoId.set(this.selectedOoId() === id ? null : id);
  }

  /** #585 — Niveau d'exigence ou résultat attendu retenu (partage d'indicateur). */
  selectParent(id: number): void {
    this.selectedParentId.set(this.selectedParentId() === id ? null : id);
  }

  onSearchChange(value: string): void {
    this.searchTerm.set(value);
  }

  confirm(): void {
    if (!this.canConfirm()) return;
    const result: ShareElementDialogResult = { mode: this.mode() };
    if (this.isOperation) {
      if (this.selectedMetriqueId() !== null) {
        result.targetMetriqueId = this.selectedMetriqueId()!;
      } else {
        result.targetIndicateurId = this.selectedIndicateurId()!;
      }
    } else if (this.isOo) {
      result.targetPressionId = this.selectedPressionId()!;
    } else if (this.isRa) {
      result.targetOoId = this.selectedOoId()!;
    } else if (this.isIndicateur) {
      result.targetParentId = this.selectedParentId()!;
    } else {
      result.targetEnjeuId = this.selectedEnjeuId()!;
    }
    this.dialogRef.close(result);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
