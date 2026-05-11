import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MetriqueFormData, MetriqueScoreBlock } from '../../../core/models/enjeu.model';
import { MetriqueBlockComponent, ScoreBlockData } from '../metrique-block/metrique-block.component';

/**
 * Form complet de saisie d'une métrique numérique (#247 + #208 + design Figma).
 *
 * Structure :
 *  - Métadonnées (intitulé + corbeille, unité, type, pondération, état de référence)
 *  - Card du bloc principal : cartouche sens-variation/niveaux-actifs + tableau 9 colonnes
 *  - Pour chaque bloc complémentaire : sélecteur ET/OU + parens + card identique au principal
 *  - Bouton « + Ajouter un bloc »
 *
 * La card est rendue par :class:`MetriqueBlockComponent` (réutilisé pour les deux
 * types de blocs). Le mapping main `metrique.scores[N].*` ↔ flat `score_N_*` est
 * fait via les getter/setter `mainBlock`.
 */

export interface TypeMetriqueOption {
  id_nomenclature: number;
  mnemonique: string;
  label: string;
}

@Component({
  selector: 'app-metrique-form',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MetriqueBlockComponent,
  ],
  templateUrl: './metrique-form.component.html',
  styleUrl: './metrique-form.component.scss',
})
export class MetriqueFormComponent {
  @Input({ required: true }) metrique!: MetriqueFormData;
  @Input() typeMetriqueOptions: TypeMetriqueOption[] = [];

  @Output() delete = new EventEmitter<void>();
  @Output() metriqueChange = new EventEmitter<MetriqueFormData>();

  // =====================================================================
  // Vue flat du bloc principal (proxy vers metrique.scores[N].*)
  // =====================================================================

  get mainBlock(): ScoreBlockData {
    const m = this.metrique;
    return {
      sens_variation: m.sens_variation,
      score_1_inf: m.scores[1]?.inf ?? null, score_1_sup: m.scores[1]?.sup ?? null,
      score_2_inf: m.scores[2]?.inf ?? null, score_2_sup: m.scores[2]?.sup ?? null,
      score_3_inf: m.scores[3]?.inf ?? null, score_3_sup: m.scores[3]?.sup ?? null,
      score_4_inf: m.scores[4]?.inf ?? null, score_4_sup: m.scores[4]?.sup ?? null,
      score_5_inf: m.scores[5]?.inf ?? null, score_5_sup: m.scores[5]?.sup ?? null,
      score_1_sup_inclusive: m.score_1_sup_inclusive,
      score_2_sup_inclusive: m.score_2_sup_inclusive,
      score_3_sup_inclusive: m.score_3_sup_inclusive,
      score_4_sup_inclusive: m.score_4_sup_inclusive,
      has_borne_score1: m.has_score1_optional_bound,
      has_borne_score5: m.has_score5_optional_bound,
      _inactiveLevels: m._inactiveLevels,
    };
  }

  /** Recopie les mutations du bloc principal vers les champs imbriqués `scores[N]`. */
  onMainBlockChange(block: ScoreBlockData): void {
    const m = this.metrique;
    m.sens_variation = block.sens_variation;
    for (let level = 1; level <= 5; level++) {
      m.scores[level] ??= { inf: null, sup: null, val: null, label: '' };
      m.scores[level].inf = (block as any)[`score_${level}_inf`];
      m.scores[level].sup = (block as any)[`score_${level}_sup`];
    }
    m.score_1_sup_inclusive = block.score_1_sup_inclusive;
    m.score_2_sup_inclusive = block.score_2_sup_inclusive;
    m.score_3_sup_inclusive = block.score_3_sup_inclusive;
    m.score_4_sup_inclusive = block.score_4_sup_inclusive;
    m.has_score1_optional_bound = block.has_borne_score1;
    m.has_score5_optional_bound = block.has_borne_score5;
    m._inactiveLevels = block._inactiveLevels;
    this.emitChange();
  }

  // =====================================================================
  // Blocs complémentaires
  // =====================================================================

  get blocks(): MetriqueScoreBlock[] {
    this.metrique.score_blocks ??= [];
    return this.metrique.score_blocks;
  }

  /** Ajoute un bloc complémentaire vide (CROISSANT, OR, pas de parens). */
  addBlock(): void {
    const newBlock: MetriqueScoreBlock = {
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
    this.blocks.push(newBlock);
    this.emitChange();
  }

  removeBlock(idx: number): void {
    this.blocks.splice(idx, 1);
    this.blocks.forEach((b, i) => { b.position = i + 1; });
    this.emitChange();
  }

  onBlockChange(_block: ScoreBlockData): void {
    this.emitChange();
  }

  setBlockLogicalOp(idx: number, op: 'OR' | 'AND'): void {
    this.blocks[idx].logical_op = op;
    this.emitChange();
  }

  toggleParensOpen(idx: number): void {
    const b = this.blocks[idx];
    b.group_open = b.group_open > 0 ? 0 : 1;
    this.emitChange();
  }

  toggleParensClose(idx: number): void {
    const b = this.blocks[idx];
    b.group_close = b.group_close > 0 ? 0 : 1;
    this.emitChange();
  }

  onMetriqueDelete(): void {
    this.delete.emit();
  }

  emitChange(): void {
    this.metriqueChange.emit(this.metrique);
  }

  trackByOptionId = (_i: number, opt: TypeMetriqueOption) => opt.id_nomenclature;
}
