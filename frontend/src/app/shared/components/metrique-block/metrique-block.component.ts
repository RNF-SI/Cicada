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

  has_borne_score1: boolean;
  has_borne_score5: boolean;

  /** Niveaux désactivés via les tags « Niveaux actifs » (uniquement front). */
  _inactiveLevels?: number[];
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
    return !this.block._inactiveLevels?.includes(level);
  }

  toggleLevelActive(level: ScoreLevel): void {
    this.block._inactiveLevels ??= [];
    const i = this.block._inactiveLevels.indexOf(level);
    if (i >= 0) {
      this.block._inactiveLevels.splice(i, 1);
    } else {
      this.block._inactiveLevels.push(level);
      (this.block as any)[`score_${level}_inf`] = null;
      (this.block as any)[`score_${level}_sup`] = null;
    }
    this.emit();
  }

  getBoundaryValue(boundary: BoundaryIndex): number | null {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    return (this.block as any)[`score_${leftLevel}_sup`];
  }

  setBoundaryValue(boundary: BoundaryIndex, value: number | null): void {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    const rightLevel = ordered[boundary].level;
    (this.block as any)[`score_${leftLevel}_sup`] = value;
    (this.block as any)[`score_${rightLevel}_inf`] = value;
    this.emit();
  }

  isBoundaryInLeft(boundary: BoundaryIndex): boolean {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    return (this.block as any)[`score_${leftLevel}_sup_inclusive`];
  }

  toggleBoundaryInclusion(boundary: BoundaryIndex): void {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    const key = `score_${leftLevel}_sup_inclusive`;
    (this.block as any)[key] = !(this.block as any)[key];
    this.emit();
  }

  getIntervalText(level: ScoreLevel): string {
    if (!this.isLevelActive(level)) return '';
    const inf = (this.block as any)[`score_${level}_inf`];
    const sup = (this.block as any)[`score_${level}_sup`];
    if (inf == null && sup == null) return '—';

    const ordered = this.scoreMetaOrdered;
    const idx = ordered.findIndex(m => m.level === level);
    const prev = idx > 0 ? ordered[idx - 1].level : null;
    const next = idx < ordered.length - 1 ? ordered[idx + 1].level : null;
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
    this.emit();
  }

  emit(): void {
    this.blockChange.emit(this.block);
  }
}
