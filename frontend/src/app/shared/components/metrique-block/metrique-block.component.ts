import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

/**
 * Structure plate d'un bloc de scoring (#247).
 *
 * Couvre à la fois le bloc principal d'une métrique (stocké sur `Metrique`)
 * et les blocs complémentaires (modèle `MetriqueScoreBlock`).
 * Les noms de champs correspondent exactement aux colonnes en base.
 */
export interface ScoreBlockData {
  sens_variation: 'CROISSANT' | 'DECROISSANT';

  score_1_inf: number | null; score_1_sup: number | null;
  score_2_inf: number | null; score_2_sup: number | null;
  score_3_inf: number | null; score_3_sup: number | null;
  score_4_inf: number | null; score_4_sup: number | null;
  score_5_inf: number | null; score_5_sup: number | null;

  score_1_sup_inclusive: boolean;
  score_2_sup_inclusive: boolean;
  score_3_sup_inclusive: boolean;
  score_4_sup_inclusive: boolean;
  // #545/#554 — frontière « très bon » utilisée en sens décroissant.
  score_5_sup_inclusive?: boolean;

  has_borne_score1: boolean;
  has_borne_score5: boolean;

  /** Niveaux désactivés via les tags « Niveaux actifs ». Persistés en base. */
  inactive_levels?: number[];
}

export type ScoreLevel = 1 | 2 | 3 | 4 | 5;
export type BoundaryIndex = 1 | 2 | 3 | 4;

interface ScoreMeta {
  level: ScoreLevel;
  labelKey: string;
  shortKey: string;
}

const SCORE_META: ScoreMeta[] = [
  { level: 1, labelKey: 'scores.veryBad',  shortKey: 'scores.short.veryBad' },
  { level: 2, labelKey: 'scores.bad',      shortKey: 'scores.short.bad' },
  { level: 3, labelKey: 'scores.neutral',  shortKey: 'scores.short.neutral' },
  { level: 4, labelKey: 'scores.good',     shortKey: 'scores.short.good' },
  { level: 5, labelKey: 'scores.veryGood', shortKey: 'scores.short.veryGood' },
];

/**
 * Card visuelle d'un bloc de scoring : cartouche `Sens de variation` /
 * `Niveaux actifs` + tableau 9 colonnes (5 paliers + 4 valeurs-limites).
 *
 * Réutilisable pour le bloc principal et les blocs complémentaires (#247) :
 * c'est le même design dans les deux cas.
 */
@Component({
  selector: 'app-metrique-block',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './metrique-block.component.html',
  styleUrl: './metrique-block.component.scss',
})
export class MetriqueBlockComponent {
  /** Donnée du bloc (mutations in-place). */
  @Input({ required: true }) block!: ScoreBlockData;

  /** Émis à chaque modification (utile pour les parents qui veulent dispatcher). */
  @Output() blockChange = new EventEmitter<ScoreBlockData>();

  readonly scoreMeta = SCORE_META;

  get scoreMetaOrdered(): ScoreMeta[] {
    return this.block?.sens_variation === 'DECROISSANT'
      ? [...this.scoreMeta].reverse()
      : this.scoreMeta;
  }

  isLevelActive(level: ScoreLevel): boolean {
    return !this.block.inactive_levels?.includes(level);
  }

  toggleLevelActive(level: ScoreLevel): void {
    this.block.inactive_levels ??= [];
    const i = this.block.inactive_levels.indexOf(level);
    if (i >= 0) {
      this.block.inactive_levels.splice(i, 1);
    } else {
      this.block.inactive_levels.push(level);
      (this.block as any)[`score_${level}_inf`] = null;
      (this.block as any)[`score_${level}_sup`] = null;
    }
    this.emit();
  }

  // ---------------------------------------------------------------------------
  // Valeurs-limites (#345) : une valeur-limite n'existe qu'entre deux niveaux
  // ACTIFS consécutifs. Les colonnes-limites jouxtant un niveau désactivé sont
  // masquées, et la limite « saute » les niveaux désactivés jusqu'au prochain
  // niveau actif. Les méthodes sont indexées par la colonne GAUCHE (index i
  // dans l'ordre d'affichage).
  // ---------------------------------------------------------------------------

  /** Index (dans l'ordre d'affichage) du prochain niveau actif après la colonne i. */
  nextActiveIndex(i: number): number {
    const ordered = this.scoreMetaOrdered;
    for (let k = i + 1; k < ordered.length; k++) {
      if (this.isLevelActive(ordered[k].level)) return k;
    }
    return -1;
  }

  /** La valeur-limite après la colonne i est-elle affichée ? (colonne active + un niveau actif après). */
  isBoundaryVisible(i: number): boolean {
    return this.isLevelActive(this.scoreMetaOrdered[i].level) && this.nextActiveIndex(i) >= 0;
  }

  /** Mnémonique court du niveau actif à droite de la limite après la colonne i. */
  boundaryRightShortKey(i: number): string {
    const k = this.nextActiveIndex(i);
    return k >= 0 ? this.scoreMetaOrdered[k].shortKey : '';
  }

  /** Niveau (1..5) actif à droite de la limite après la colonne i (pour la couleur). */
  boundaryRightLevel(i: number): number {
    const k = this.nextActiveIndex(i);
    return k >= 0 ? this.scoreMetaOrdered[k].level : 0;
  }

  getBoundaryValueAt(i: number): number | null {
    return (this.block as any)[`score_${this.scoreMetaOrdered[i].level}_sup`];
  }

  setBoundaryValueAt(i: number, value: number | null): void {
    const leftLevel = this.scoreMetaOrdered[i].level;
    const k = this.nextActiveIndex(i);
    (this.block as any)[`score_${leftLevel}_sup`] = value;
    if (k >= 0) {
      (this.block as any)[`score_${this.scoreMetaOrdered[k].level}_inf`] = value;
    }
    this.emit();
  }

  isBoundaryInLeftAt(i: number): boolean {
    // #450 — Appliquer le même défaut (`?? true`) que `supInclusiveFor` : sans
    // cela, l'indicateur du toggle divergeait de l'intervalle affiché pour la
    // frontière dont le flag n'a pas de valeur par défaut (score_5_sup_inclusive,
    // utilisé par la frontière « très bon / bon » en sens décroissant).
    return (this.block as any)[`score_${this.scoreMetaOrdered[i].level}_sup_inclusive`] ?? true;
  }

  toggleBoundaryInclusionAt(i: number): void {
    const key = `score_${this.scoreMetaOrdered[i].level}_sup_inclusive`;
    // #450 — basculer la valeur EFFECTIVE (défaut `true`) : sans le `?? true`,
    // un flag undefined (ex. score_5_sup_inclusive en décroissant) donnait
    // `!undefined === true` et le toggle restait bloqué côté gauche.
    (this.block as any)[key] = !((this.block as any)[key] ?? true);
    this.emit();
  }

  getIntervalText(level: ScoreLevel): string {
    if (!this.isLevelActive(level)) return '';

    const ordered = this.scoreMetaOrdered;
    const idx = ordered.findIndex(m => m.level === level);
    // Voisins ACTIFS (un niveau désactivé est « traversé » : la borne provient
    // du prochain niveau actif). #345.
    let prevIdx = -1;
    for (let i = idx - 1; i >= 0; i--) { if (this.isLevelActive(ordered[i].level)) { prevIdx = i; break; } }
    let nextIdx = -1;
    for (let i = idx + 1; i < ordered.length; i++) { if (this.isLevelActive(ordered[i].level)) { nextIdx = i; break; } }
    const prev = prevIdx >= 0 ? ordered[prevIdx].level : null;
    const next = nextIdx >= 0 ? ordered[nextIdx].level : null;

    // #341 — la borne inf d'un niveau = la valeur-limite à sa gauche (sup du
    // voisin actif précédent), pas `score_${level}_inf` qui peut ne pas être
    // renseigné (ex. niveau extrême « très mauvais » en sens décroissant).
    const inf = prev != null
      ? (this.block as any)[`score_${prev}_sup`]
      : (this.block as any)[`score_${level}_inf`];
    const sup = (this.block as any)[`score_${level}_sup`];
    if (inf == null && sup == null) return '—';

    const infInclusive = prev ? !this.supInclusiveFor(prev) : true;
    const supInclusive = next ? this.supInclusiveFor(level) : true;

    const infOp = infInclusive ? '≤' : '<';
    const supOp = supInclusive ? '≤' : '<';

    if (inf != null && sup != null) {
      return `${this.fmt(inf)} ${infOp} x ${supOp} ${this.fmt(sup)}`;
    }
    if (inf != null) {
      return `x ${infOp.replace('≤', '≥').replace('<', '>')} ${this.fmt(inf)}`;
    }
    if (sup != null) {
      return `x ${supOp} ${this.fmt(sup)}`;
    }
    return '—';
  }

  private supInclusiveFor(level: ScoreLevel): boolean {
    return (this.block as any)[`score_${level}_sup_inclusive`] ?? true;
  }

  private fmt(v: number): string {
    return Number(v).toString();
  }

  onSensVariationChange(value: 'CROISSANT' | 'DECROISSANT'): void {
    if (this.block.sens_variation === value) return;
    this.block.sens_variation = value;
    // #451 — Les bornes et leurs inclusivités sont propres à un sens : les
    // colonnes utilisées diffèrent entre croissant (score_1..4_sup) et
    // décroissant (score_5..2_sup). Sans réinitialisation, les valeurs saisies
    // dans l'ancien sens « fuyaient » dans le nouveau (mélange à la sauvegarde).
    // On repart donc d'une grille de bornes vierge ; les niveaux actifs sont
    // conservés (indépendants du sens).
    for (let level = 1; level <= 5; level++) {
      (this.block as any)[`score_${level}_inf`] = null;
      (this.block as any)[`score_${level}_sup`] = null;
    }
    for (let level = 1; level <= 5; level++) {
      (this.block as any)[`score_${level}_sup_inclusive`] = true;
    }
    this.emit();
  }

  emit(): void {
    this.blockChange.emit(this.block);
  }
}
