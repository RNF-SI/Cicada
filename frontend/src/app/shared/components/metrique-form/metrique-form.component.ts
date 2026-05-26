import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { MetriqueFormData, MetriqueScoreBlock } from '../../../core/models/enjeu.model';
import { MetriqueBlockComponent, ScoreBlockData } from '../metrique-block/metrique-block.component';
import { FormFieldComponent } from '../form-field/form-field.component';

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

/**
 * Élément structurant le rendu de la formule logique en parties cliquables.
 *  - `open`/`close` : parenthèse rattachée au bloc d'index `blockIdx` (0 = principal).
 *  - `op` : opérateur ET/OU (non interactif — édité via les onglets sous chaque bloc).
 *  - `block` : nom de bloc cliquable pour la sélection et le groupage.
 */
export interface FormulaPart {
  kind: 'open' | 'close' | 'op' | 'block';
  label?: string;
  blockIdx?: number;
}

@Component({
  selector: 'app-metrique-form',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    DragDropModule,
    MetriqueBlockComponent,
    FormFieldComponent,
  ],
  templateUrl: './metrique-form.component.html',
  styleUrl: './metrique-form.component.scss',
})
export class MetriqueFormComponent {
  @Input({ required: true }) metrique!: MetriqueFormData;
  @Input() typeMetriqueOptions: TypeMetriqueOption[] = [];

  @Output() delete = new EventEmitter<void>();
  @Output() metriqueChange = new EventEmitter<MetriqueFormData>();

  /** Index du bloc actuellement sélectionné dans la formule (0 = principal, 1+ = complémentaires).
   *  Le second clic groupe la sélection avec ce bloc. Null = aucune sélection. */
  selectedFormulaIdx: number | null = null;

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
      inactive_levels: m._inactiveLevels,
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
    m._inactiveLevels = block.inactive_levels;
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
      inactive_levels: [],
      _letter: this.nextAvailableLetter(),
    };
    this.blocks.push(newBlock);
    this.emitChange();
  }

  /** Calcule la prochaine lettre libre (A, B, C, …) parmi le principal + complémentaires. */
  private nextAvailableLetter(): string {
    const used = new Set<string>([
      this.metrique._letter ?? 'A',
      ...this.blocks.map(b => b._letter ?? ''),
    ]);
    for (let i = 0; i < 26 * 26; i++) {
      const candidate = this.indexToLetter(i);
      if (!used.has(candidate)) return candidate;
    }
    return '?';
  }

  private indexToLetter(idx: number): string {
    let result = '';
    let n = idx;
    while (n >= 0) {
      result = String.fromCharCode(65 + (n % 26)) + result;
      n = Math.floor(n / 26) - 1;
    }
    return result;
  }

  removeBlock(idx: number): void {
    this.blocks.splice(idx, 1);
    this.blocks.forEach((b, i) => { b.position = i + 1; });
    this.clearFormulaSelection();
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

  /**
   * #4 — Réordonnancement de tous les blocs (principal inclus) via drag-and-drop.
   *
   * Le principal est représenté à l'index 0 d'une liste unifiée ; les
   * complémentaires suivent. Après `moveItemInArray`, le bloc à l'index 0
   * devient le nouveau principal (recopié dans les champs de `Metrique`), et
   * les suivants deviennent les `score_blocks` (le serializer remplace tout).
   *
   * Une conséquence : un `logical_op` éventuel sur le bloc qui finit en index 0
   * est ignoré (le principal n'a pas de prédécesseur). De même, l'ancien
   * principal qui descend en position complémentaire reçoit `logical_op='OR'`
   * par défaut s'il n'en avait pas.
   */
  onBlockDrop(event: CdkDragDrop<MetriqueScoreBlock[]>): void {
    if (event.previousIndex === event.currentIndex) return;
    this.clearFormulaSelection();

    // Snapshot positionnel des parens et opérateurs AVANT le déplacement.
    // L'utilisateur attend que « (Bloc A OU Bloc B) ET Bloc C » reste
    // « (… OU …) ET … » après un swap : les parenthèses et l'opérateur sont
    // attachés à un emplacement de la formule, pas au contenu d'un bloc.
    const positionalParens = [
      { open: this.metrique.group_open ?? 0, close: this.metrique.group_close ?? 0 },
      ...this.blocks.map(b => ({ open: b.group_open ?? 0, close: b.group_close ?? 0 })),
    ];
    const positionalOps = this.blocks.map(b => b.logical_op);

    const unified = [this.extractMainAsUnified(), ...this.blocks.map(b => ({ ...b }))];
    moveItemInArray(unified, event.previousIndex, event.currentIndex);

    // Réimpose les parens et opérateurs positionnels (le contenu a bougé,
    // mais l'enveloppe « (…) ET / OU » reste accrochée à la position).
    unified.forEach((b: any, i: number) => {
      b.group_open = positionalParens[i].open;
      b.group_close = positionalParens[i].close;
      if (i > 0) {
        b.logical_op = positionalOps[i - 1];
      }
    });

    // unified[0] devient le nouveau principal
    this.applyUnifiedToMain(unified[0]);

    // unified[1..] deviennent les complémentaires (positions renumérotées)
    this.metrique.score_blocks = unified.slice(1).map((b, i) => ({
      id_score_block: undefined, // serializer recrée toujours les complémentaires
      position: i + 1,
      logical_op: (b.logical_op as 'OR' | 'AND') ?? 'OR',
      group_open: b.group_open ?? 0,
      group_close: b.group_close ?? 0,
      sens_variation: b.sens_variation,
      score_1_inf: b.score_1_inf, score_1_sup: b.score_1_sup,
      score_2_inf: b.score_2_inf, score_2_sup: b.score_2_sup,
      score_3_inf: b.score_3_inf, score_3_sup: b.score_3_sup,
      score_4_inf: b.score_4_inf, score_4_sup: b.score_4_sup,
      score_5_inf: b.score_5_inf, score_5_sup: b.score_5_sup,
      score_1_sup_inclusive: b.score_1_sup_inclusive,
      score_2_sup_inclusive: b.score_2_sup_inclusive,
      score_3_sup_inclusive: b.score_3_sup_inclusive,
      score_4_sup_inclusive: b.score_4_sup_inclusive,
      has_borne_score1: b.has_borne_score1,
      has_borne_score5: b.has_borne_score5,
      inactive_levels: Array.isArray(b.inactive_levels) ? [...b.inactive_levels] : [],
      _letter: b._letter,
    }));

    this.emitChange();
  }

  /** Construit une représentation unifiée du bloc principal pour le drag-drop. */
  private extractMainAsUnified(): any {
    const m = this.metrique;
    return {
      logical_op: 'OR' as const, // placeholder, ignoré tant que c'est le principal
      group_open: m.group_open ?? 0,
      group_close: m.group_close ?? 0,
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
      inactive_levels: m._inactiveLevels ? [...m._inactiveLevels] : [],
      // La lettre voyage avec les données du bloc.
      _letter: m._letter,
    };
  }

  /** Recopie un bloc unifié dans les champs principaux de la métrique. */
  private applyUnifiedToMain(b: any): void {
    const m = this.metrique;
    m.sens_variation = b.sens_variation;
    m.scores = {
      1: { inf: b.score_1_inf, sup: b.score_1_sup, val: m.scores[1]?.val ?? null, label: m.scores[1]?.label ?? '' },
      2: { inf: b.score_2_inf, sup: b.score_2_sup, val: m.scores[2]?.val ?? null, label: m.scores[2]?.label ?? '' },
      3: { inf: b.score_3_inf, sup: b.score_3_sup, val: m.scores[3]?.val ?? null, label: m.scores[3]?.label ?? '' },
      4: { inf: b.score_4_inf, sup: b.score_4_sup, val: m.scores[4]?.val ?? null, label: m.scores[4]?.label ?? '' },
      5: { inf: b.score_5_inf, sup: b.score_5_sup, val: m.scores[5]?.val ?? null, label: m.scores[5]?.label ?? '' },
    };
    m.score_1_sup_inclusive = b.score_1_sup_inclusive;
    m.score_2_sup_inclusive = b.score_2_sup_inclusive;
    m.score_3_sup_inclusive = b.score_3_sup_inclusive;
    m.score_4_sup_inclusive = b.score_4_sup_inclusive;
    m.has_score1_optional_bound = b.has_borne_score1;
    m.has_score5_optional_bound = b.has_borne_score5;
    m._inactiveLevels = Array.isArray(b.inactive_levels) ? [...b.inactive_levels] : [];
    m.group_open = b.group_open ?? 0;
    m.group_close = b.group_close ?? 0;
    m._letter = b._letter ?? m._letter;
  }

  // =====================================================================
  // Parenthésage du bloc principal (#247 — symétrie avec les complémentaires).
  // =====================================================================

  toggleMainParensOpen(): void {
    this.metrique.group_open = (this.metrique.group_open ?? 0) > 0 ? 0 : 1;
    this.emitChange();
  }

  toggleMainParensClose(): void {
    this.metrique.group_close = (this.metrique.group_close ?? 0) > 0 ? 0 : 1;
    this.emitChange();
  }

  /** Profondeur de groupe pendant le rendu du bloc principal. */
  getMainBlockDepth(): number {
    return this.metrique.group_open ?? 0;
  }

  onMetriqueDelete(): void {
    this.delete.emit();
  }

  emitChange(): void {
    this.metriqueChange.emit(this.metrique);
  }

  trackByOptionId = (_i: number, opt: TypeMetriqueOption) => opt.id_nomenclature;

  // =====================================================================
  // #247 — Aide visuelle pour le parenthésage
  // =====================================================================

  /**
   * Profondeur de groupe au début du rendu du bloc à `idx` (depuis le sequence
   * principal + complémentaires). 0 = pas dans un groupe, 1 = dans un groupe,
   * 2 = dans un groupe imbriqué, etc.
   *
   * Prend en compte les parens du principal : si le principal a `group_open=1`,
   * tous les blocs suivants sont par défaut à profondeur +1 jusqu'à `group_close`.
   */
  getBlockDepth(idx: number): number {
    // Profondeur héritée du principal : on ouvre les parens du principal puis on
    // ne les ferme que si le principal a un group_close.
    let depth = (this.metrique.group_open ?? 0) - (this.metrique.group_close ?? 0);
    for (let i = 0; i <= idx; i++) {
      depth += this.blocks[i].group_open ?? 0;
      if (i < idx) {
        depth -= this.blocks[i].group_close ?? 0;
      }
    }
    return depth;
  }

  /** Profondeur après le bloc à `idx` (utilisée pour la cohérence visuelle). */
  getBlockDepthAfter(idx: number): number {
    return this.getBlockDepth(idx) - (this.blocks[idx].group_close ?? 0);
  }

  /**
   * Formule textuelle représentant la logique : « Bloc 1 OU (Bloc 2 ET Bloc 3)
   * OU Bloc 4 ». Aide l'utilisateur à valider visuellement son parenthésage.
   */
  getFormulaText(): string {
    const mainOpens = '('.repeat(this.metrique.group_open ?? 0);
    const mainCloses = ')'.repeat(this.metrique.group_close ?? 0);
    const mainLabel = this.formatBlockLabel(this.metrique._letter ?? 'A');
    const parts: string[] = [`${mainOpens}${mainLabel}${mainCloses}`];
    this.blocks.forEach((block) => {
      const op = ' ' + this.translate(block.logical_op === 'AND'
        ? 'enjeux.metriques.opAnd'
        : 'enjeux.metriques.opOr') + ' ';
      const opens = '('.repeat(block.group_open ?? 0);
      const closes = ')'.repeat(block.group_close ?? 0);
      const label = this.formatBlockLabel(block._letter ?? '?');
      parts.push(`${op}${opens}${label}${closes}`);
    });
    return parts.join('');
  }

  /** Wrapper léger sans dépendance directe à TranslateService dans le squelette. */
  private translate(key: string): string {
    // Fallback simple : utilise la clé telle quelle si non traduite.
    // Idéalement on injecterait TranslateService, mais on évite la dép. pour
    // garder le composant indépendant — appelé via le pipe `translate` dans
    // le template pour les libellés visibles. Cette méthode sert uniquement
    // pour la formule textuelle dynamique.
    const dict: Record<string, string> = {
      'enjeux.metriques.principal': 'Bloc 1',
      'enjeux.metriques.blockLabel': 'Bloc',
      'enjeux.metriques.opAnd': 'ET',
      'enjeux.metriques.opOr': 'OU',
    };
    return dict[key] ?? key;
  }

  /** Solde de parens (ouvertes - fermées). 0 = équilibré. */
  getParensBalance(): number {
    let balance = (this.metrique.group_open ?? 0) - (this.metrique.group_close ?? 0);
    for (const b of this.blocks) {
      balance += (b.group_open ?? 0) - (b.group_close ?? 0);
    }
    return balance;
  }

  /** Vrai s'il y a des parens (principal ou complémentaires) à afficher dans la formule. */
  hasAnyParens(): boolean {
    if ((this.metrique.group_open ?? 0) > 0 || (this.metrique.group_close ?? 0) > 0) return true;
    return this.blocks.some(b => (b.group_open ?? 0) > 0 || (b.group_close ?? 0) > 0);
  }

  // =====================================================================
  // Formule interactive (#247 — groupage par clic dans la formule)
  // =====================================================================

  /**
   * Construit la séquence de parties affichables. Permet au template de
   * rendre des éléments cliquables (chips de bloc, parens) au lieu d'une
   * chaîne plate. Le groupage se fait en cliquant successivement deux blocs
   * dans la formule.
   */
  getFormulaParts(): FormulaPart[] {
    const parts: FormulaPart[] = [];

    // Parenthèses ouvrantes du principal
    for (let k = 0; k < (this.metrique.group_open ?? 0); k++) {
      parts.push({ kind: 'open', blockIdx: 0 });
    }
    parts.push({
      kind: 'block',
      blockIdx: 0,
      label: this.formatBlockLabel(this.metrique._letter ?? 'A'),
    });
    for (let k = 0; k < (this.metrique.group_close ?? 0); k++) {
      parts.push({ kind: 'close', blockIdx: 0 });
    }

    this.blocks.forEach((block, i) => {
      // L'opérateur appartient au bloc complémentaire (idx i+1 dans la liste unifiée).
      // On stocke blockIdx pour pouvoir le basculer au clic.
      parts.push({
        kind: 'op',
        blockIdx: i + 1,
        label: block.logical_op === 'AND'
          ? this.translate('enjeux.metriques.opAnd')
          : this.translate('enjeux.metriques.opOr'),
      });
      for (let k = 0; k < (block.group_open ?? 0); k++) {
        parts.push({ kind: 'open', blockIdx: i + 1 });
      }
      parts.push({
        kind: 'block',
        blockIdx: i + 1,
        label: this.formatBlockLabel(block._letter ?? '?'),
      });
      for (let k = 0; k < (block.group_close ?? 0); k++) {
        parts.push({ kind: 'close', blockIdx: i + 1 });
      }
    });

    return parts;
  }

  /** Formate le libellé visible : "Bloc A", "Bloc B", … */
  private formatBlockLabel(letter: string): string {
    return this.translate('enjeux.metriques.blockLabel') + ' ' + letter;
  }

  /**
   * Premier clic : sélectionne le bloc. Second clic :
   *  - Sur le même bloc → désélectionne.
   *  - Sur un autre bloc déjà groupé avec le premier → enlève la paire de parens.
   *  - Sinon → ajoute une paire de parens autour de la plage [a, b].
   */
  onFormulaBlockClick(idx: number): void {
    const current = this.selectedFormulaIdx;
    if (current === null) {
      this.selectedFormulaIdx = idx;
      return;
    }
    if (current === idx) {
      this.selectedFormulaIdx = null;
      return;
    }
    const a = Math.min(current, idx);
    const b = Math.max(current, idx);
    if (this.hasMatchingGroup(a, b)) {
      this.removeGroupParens(a, b);
    } else {
      this.addGroupParens(a, b);
    }
    this.selectedFormulaIdx = null;
  }

  /** Pose une paire de parens autour de la plage [a, b] (indices unifiés). */
  private addGroupParens(a: number, b: number): void {
    if (a === 0) {
      this.metrique.group_open = (this.metrique.group_open ?? 0) + 1;
    } else {
      this.blocks[a - 1].group_open = (this.blocks[a - 1].group_open ?? 0) + 1;
    }
    if (b === 0) {
      this.metrique.group_close = (this.metrique.group_close ?? 0) + 1;
    } else {
      this.blocks[b - 1].group_close = (this.blocks[b - 1].group_close ?? 0) + 1;
    }
    this.emitChange();
  }

  /** Enlève une paire de parens autour de [a, b]. */
  private removeGroupParens(a: number, b: number): void {
    if (a === 0) {
      this.metrique.group_open = Math.max(0, (this.metrique.group_open ?? 0) - 1);
    } else {
      this.blocks[a - 1].group_open = Math.max(0, (this.blocks[a - 1].group_open ?? 0) - 1);
    }
    if (b === 0) {
      this.metrique.group_close = Math.max(0, (this.metrique.group_close ?? 0) - 1);
    } else {
      this.blocks[b - 1].group_close = Math.max(0, (this.blocks[b - 1].group_close ?? 0) - 1);
    }
    this.emitChange();
  }

  /**
   * Heuristique : la sélection [a, b] correspond à une paire existante de
   * parens si le bloc a a au moins une ouvrante et le bloc b au moins une
   * fermante. V1 simple — convient au cas courant (paire unique).
   */
  private hasMatchingGroup(a: number, b: number): boolean {
    const getOpen = (idx: number) =>
      idx === 0 ? (this.metrique.group_open ?? 0) : (this.blocks[idx - 1].group_open ?? 0);
    const getClose = (idx: number) =>
      idx === 0 ? (this.metrique.group_close ?? 0) : (this.blocks[idx - 1].group_close ?? 0);
    return getOpen(a) >= 1 && getClose(b) >= 1;
  }

  /** Bascule l'opérateur logique du bloc complémentaire (OR ↔ AND). */
  onFormulaOpClick(blockIdx: number): void {
    if (blockIdx < 1 || blockIdx > this.blocks.length) return;
    const block = this.blocks[blockIdx - 1];
    block.logical_op = block.logical_op === 'AND' ? 'OR' : 'AND';
    this.emitChange();
  }

  /**
   * Drag-and-drop d'un chip de bloc dans la formule.
   * Les indices CDK sont des indices parmi les chips draggables (0 = principal,
   * 1+ = complémentaires), donc on réutilise la logique d'`onBlockDrop`.
   */
  onFormulaDrop(event: CdkDragDrop<unknown>): void {
    this.clearFormulaSelection();
    this.onBlockDrop(event as CdkDragDrop<MetriqueScoreBlock[]>);
  }

  /**
   * Clic sur une parenthèse de la formule : la supprime (décrémente le
   * compteur correspondant). Si la formule devient déséquilibrée,
   * l'avertissement « parenthèses non équilibrées » sert de filet.
   */
  onFormulaParenClick(blockIdx: number, side: 'open' | 'close'): void {
    if (blockIdx === 0) {
      if (side === 'open') {
        this.metrique.group_open = Math.max(0, (this.metrique.group_open ?? 0) - 1);
      } else {
        this.metrique.group_close = Math.max(0, (this.metrique.group_close ?? 0) - 1);
      }
    } else {
      const block = this.blocks[blockIdx - 1];
      if (side === 'open') {
        block.group_open = Math.max(0, (block.group_open ?? 0) - 1);
      } else {
        block.group_close = Math.max(0, (block.group_close ?? 0) - 1);
      }
    }
    this.emitChange();
  }

  /** Réinitialise la sélection (utile au reset suite à un drag-drop ou suppression). */
  clearFormulaSelection(): void {
    this.selectedFormulaIdx = null;
  }
}
