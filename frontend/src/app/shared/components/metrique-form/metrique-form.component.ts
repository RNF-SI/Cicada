import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MetriqueFormData, MetriqueScoreBlock } from '../../../core/models/enjeu.model';

/**
 * Editor for a single Metrique (numerical type with 5 score levels).
 *
 * Follows the Figma design (KitUI/metriques-saisie/metrique-saisie-numerique.png) :
 *  - Métadonnées (intitulé, unité, type, pondération, état de référence)
 *  - Cartouche « Sens de variation » (croissant/décroissant) + tags « Niveaux actifs »
 *    (toggle individuel sur chaque palier pour le désactiver)
 *  - Tableau à 9 colonnes : 5 paliers (TM, Mauv, Moy, Bon, TB) alternés avec 4 valeurs-limites
 *    saisies par l'utilisateur. Chaque valeur-limite a un toggle d'inclusivité
 *    (la valeur appartient au palier de gauche ou de droite).
 *  - Les intervalles affichés dans les paliers (ex. `20 ≤ x < 30`) sont calculés
 *    automatiquement à partir des valeurs-limites + inclusivités.
 *
 * Le mapping interne convertit les 4 valeurs-limites en `score_N_inf/sup` (champs
 * existants en base, voir #248). Pas de migration backend nécessaire.
 *
 * Pour les types CHIFFRE / TEXTE / INDETERMINE, le composant délègue au comportement
 * historique (à terme, sous-composants dédiés).
 */
export type ScoreLevel = 1 | 2 | 3 | 4 | 5;
export type BoundaryIndex = 1 | 2 | 3 | 4;

/** Métadonnées affichage d'un palier : libellé, couleurs (gras et clair pour cellule valeur). */
interface ScoreMeta {
  level: ScoreLevel;
  labelKey: string;     // clé i18n
  shortKey: string;     // clé i18n abrégée (TM, Mauv., Moy., Bon, TB)
  colorVar: string;     // var SCSS gras (header)
  bgVar: string;        // var SCSS clair (cellule)
}

const SCORE_META: ScoreMeta[] = [
  { level: 1, labelKey: 'scores.veryBad',  shortKey: 'scores.short.veryBad',  colorVar: 'var(--score-very-bad)',  bgVar: 'var(--score-very-bad-bg)' },
  { level: 2, labelKey: 'scores.bad',      shortKey: 'scores.short.bad',      colorVar: 'var(--score-bad)',       bgVar: 'var(--score-bad-bg)' },
  { level: 3, labelKey: 'scores.neutral',  shortKey: 'scores.short.neutral',  colorVar: 'var(--score-neutral)',   bgVar: 'var(--score-neutral-bg)' },
  { level: 4, labelKey: 'scores.good',     shortKey: 'scores.short.good',     colorVar: 'var(--score-good)',      bgVar: 'var(--score-good-bg)' },
  { level: 5, labelKey: 'scores.veryGood', shortKey: 'scores.short.veryGood', colorVar: 'var(--score-very-good)', bgVar: 'var(--score-very-good-bg)' },
];

/** Option dans le dropdown « Type de métrique ». */
export interface TypeMetriqueOption {
  id_nomenclature: number;
  mnemonique: string;
  label: string;
}

@Component({
  selector: 'app-metrique-form',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  templateUrl: './metrique-form.component.html',
  styleUrl: './metrique-form.component.scss',
})
export class MetriqueFormComponent {
  /** Donnée éditée (référence partagée — les mutations se font in-place). */
  @Input({ required: true }) metrique!: MetriqueFormData;

  /** Liste des types de métrique (récupérée via getNomenclaturesByType('TYPE_METRIQUE')). */
  @Input() typeMetriqueOptions: TypeMetriqueOption[] = [];

  /** Émis quand l'utilisateur clique sur la corbeille en haut à droite. */
  @Output() delete = new EventEmitter<void>();

  /** Émis à chaque modification pour permettre la sauvegarde différée. */
  @Output() metriqueChange = new EventEmitter<MetriqueFormData>();

  /**
   * Niveaux actifs : par défaut, les 5 sont actifs. Le toggle individuel sur chaque
   * tag les bascule. Quand un palier est désactivé : ses bornes deviennent `null`
   * en base et la cellule est grisée dans le tableau.
   */
  readonly scoreMeta = SCORE_META;

  /** Affiche les paliers dans l'ordre du sens de variation (CROISSANT : 1→5, DECROISSANT : 5→1). */
  get scoreMetaOrdered(): ScoreMeta[] {
    if (this.metrique?.sens_variation === 'DECROISSANT') {
      return [...this.scoreMeta].reverse();
    }
    return this.scoreMeta;
  }

  /** Vrai si le palier est marqué comme actif (par défaut tous actifs). */
  isLevelActive(level: ScoreLevel): boolean {
    return !this.metrique._inactiveLevels?.includes(level);
  }

  /** Bascule l'état actif/inactif d'un palier. */
  toggleLevelActive(level: ScoreLevel): void {
    this.metrique._inactiveLevels ??= [];
    const i = this.metrique._inactiveLevels.indexOf(level);
    if (i >= 0) {
      this.metrique._inactiveLevels.splice(i, 1);
    } else {
      this.metrique._inactiveLevels.push(level);
      // Effacer les bornes du palier désactivé pour rester cohérent en base.
      this.metrique.scores[level].inf = null;
      this.metrique.scores[level].sup = null;
    }
    this.emitChange();
  }

  /**
   * Récupère la valeur-limite entre 2 paliers adjacents (selon le sens de variation).
   * Boundary N (N = 1..4) sépare les paliers N et N+1 dans l'ordre d'affichage.
   */
  getBoundaryValue(boundary: BoundaryIndex): number | null {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    return this.metrique.scores[leftLevel].sup;
  }

  /** Met à jour la valeur-limite entre 2 paliers adjacents (mirror sup palier N ↔ inf palier N+1). */
  setBoundaryValue(boundary: BoundaryIndex, value: number | null): void {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    const rightLevel = ordered[boundary].level;
    this.metrique.scores[leftLevel].sup = value;
    this.metrique.scores[rightLevel].inf = value;
    this.emitChange();
  }

  /**
   * Vrai si la valeur-limite est incluse dans le palier de GAUCHE (sup inclusive du palier left).
   * Quand `false`, la valeur appartient au palier de droite.
   */
  isBoundaryInLeft(boundary: BoundaryIndex): boolean {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    const key = `score_${leftLevel}_sup_inclusive` as keyof MetriqueFormData;
    return this.metrique[key] as boolean;
  }

  toggleBoundaryInclusion(boundary: BoundaryIndex): void {
    const ordered = this.scoreMetaOrdered;
    const leftLevel = ordered[boundary - 1].level;
    const key = `score_${leftLevel}_sup_inclusive` as keyof MetriqueFormData;
    (this.metrique as any)[key] = !this.metrique[key];
    this.emitChange();
  }

  /**
   * Texte affiché dans la cellule d'un palier (ex: `20 ≤ x < 30`, `x > 30`, `x ≤ 0`).
   * Tient compte du sens de variation et des inclusivités des frontières.
   */
  getIntervalText(level: ScoreLevel): string {
    if (!this.isLevelActive(level)) return '';
    const s = this.metrique.scores[level];
    const inf = s.inf;
    const sup = s.sup;
    if (inf == null && sup == null) return '—';

    // Inclusivité côté inf : on regarde le score précédent dans l'ordre.
    const ordered = this.scoreMetaOrdered;
    const idx = ordered.findIndex(m => m.level === level);
    const prev = idx > 0 ? ordered[idx - 1].level : null;
    const next = idx < ordered.length - 1 ? ordered[idx + 1].level : null;
    // Frontière gauche : le palier précédent a son sup_inclusive ; si TRUE, la valeur est dans le précédent donc on ouvre ici.
    const infInclusive = prev ? !this.boundarySupInclusiveFor(prev) : true;
    const supInclusive = next ? this.boundarySupInclusiveFor(level) : true;

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

  /** Helper : `score_N_sup_inclusive` pour un palier donné. */
  private boundarySupInclusiveFor(level: ScoreLevel): boolean {
    const key = `score_${level}_sup_inclusive` as keyof MetriqueFormData;
    return (this.metrique[key] as boolean) ?? true;
  }

  /** Formatage léger : strip trailing zeros. */
  private fmt(v: number): string {
    return Number(v).toString();
  }

  onSensVariationChange(value: 'CROISSANT' | 'DECROISSANT'): void {
    if (this.metrique.sens_variation === value) return;
    this.metrique.sens_variation = value;
    this.emitChange();
  }

  onMetriqueDelete(): void {
    this.delete.emit();
  }

  emitChange(): void {
    this.metriqueChange.emit(this.metrique);
  }

  /** Pour la dropdown `Type de métrique`. */
  trackByOptionId = (_i: number, opt: TypeMetriqueOption) => opt.id_nomenclature;

  // =====================================================================
  // #247 — Blocs de scoring complémentaires
  // =====================================================================
  // L'UI complète (card par bloc) sera ajoutée dans un commit dédié.
  // Pour l'instant : exposition simple des blocs en lecture seule + ajout/suppression.

  get blocks(): MetriqueScoreBlock[] {
    this.metrique.score_blocks ??= [];
    return this.metrique.score_blocks;
  }

  /** Ajoute un bloc complémentaire vide (croissant, OR avec le précédent). */
  addBlock(): void {
    const block: MetriqueScoreBlock = {
      position: this.blocks.length + 1,
      logical_op: 'OR',
      group_open: 0,
      group_close: 0,
      sens_variation: 'CROISSANT',
      score_1_inf: null, score_1_sup: null,
      score_2_inf: null, score_2_sup: null,
      score_3_inf: null, score_3_sup: null,
      score_4_inf: null, score_4_sup: null,
      score_5_inf: null, score_5_sup: null,
      score_1_sup_inclusive: true,
      score_2_sup_inclusive: true,
      score_3_sup_inclusive: true,
      score_4_sup_inclusive: true,
      has_borne_score1: false,
      has_borne_score5: false,
    };
    this.blocks.push(block);
    this.emitChange();
  }

  removeBlock(idx: number): void {
    this.blocks.splice(idx, 1);
    this.blocks.forEach((b, i) => { b.position = i + 1; });
    this.emitChange();
  }

  /** Label court (TM, Mauv., …) pour un palier donné. */
  getShortLabelKey(level: ScoreLevel): string {
    const meta = this.scoreMeta.find(m => m.level === level);
    return meta?.shortKey ?? '';
  }
}
