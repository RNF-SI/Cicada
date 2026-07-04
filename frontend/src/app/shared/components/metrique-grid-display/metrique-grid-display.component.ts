import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

/**
 * Métrique « grille » telle qu'exposée par le backend (sous-ensemble de
 * `MetriqueRef` / `Metrique`). Les champs de scoring sont accédés dynamiquement
 * (`score_{n}_inf`, `score_{n}_sup`, …), d'où le typage souple.
 */
export type GridMetrique = Record<string, any>;

/**
 * #515 — Affichage en lecture seule de la grille de scoring d'une ou plusieurs
 * métriques (intitulé, unité, pondération, état de référence + 5 paliers).
 *
 * Mutualise le rendu déjà utilisé dans l'arborescence des enjeux pour le rendre
 * disponible ailleurs (fiche d'action notamment), où l'on veut donner « plus
 * d'éléments sur les indicateurs de réponse, notamment les grilles de métriques ».
 *
 * La logique de formatage des intervalles (croissant/décroissant, inclusivité
 * des bornes, fusion de paliers identiques, blocs complémentaires ET/OU) est
 * volontairement identique à celle de l'arborescence pour une lecture cohérente.
 */
@Component({
  selector: 'app-metrique-grid-display',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './metrique-grid-display.component.html',
  styleUrl: './metrique-grid-display.component.scss',
})
export class MetriqueGridDisplayComponent {
  @Input({ required: true }) metriques: GridMetrique[] = [];

  readonly levels = [1, 2, 3, 4, 5];

  constructor(private readonly translate: TranslateService) {}

  getScoreLevelLabel(level: number): string {
    const keys: Record<number, string> = {
      1: 'enjeux.metriques.scores.tresMauvais',
      2: 'enjeux.metriques.scores.mauvais',
      3: 'enjeux.metriques.scores.moyen',
      4: 'enjeux.metriques.scores.bon',
      5: 'enjeux.metriques.scores.tresBon',
    };
    return keys[level] ? this.translate.instant(keys[level]) : '';
  }

  /** Vrai pour une métrique sans grille de scoring (saisie qualitative libre). */
  isIndetermine(met: GridMetrique): boolean {
    return (met['type_metrique_mnemonique'] || '').toString().toUpperCase() === 'INDETERMINE';
  }

  /**
   * #530 — Vrai si l'indicateur de réponse n'utilise PAS de grille de scoring
   * (case « Utiliser une grille de scoring » décochée → format SIMPLE). On
   * n'affiche alors pas les 5 paliers colorés (vides), mais un bloc « saisie
   * libre » décrivant le type de réponse attendu (chiffrée / textuelle).
   */
  isSimple(met: GridMetrique): boolean {
    return (met['format_metrique_mnemonique'] || '').toString().toUpperCase() === 'SIMPLE';
  }

  /**
   * #530 — Clé i18n décrivant la réponse attendue d'une métrique en saisie
   * libre selon son type (chiffrée / textuelle, repli générique).
   */
  simpleTypeKey(met: GridMetrique): string {
    const type = (met['type_metrique_mnemonique'] || '').toString().toUpperCase();
    if (type === 'CHIFFRE') return 'enjeux.metriques.simple.chiffre';
    if (type === 'TEXTE') return 'enjeux.metriques.simple.texte';
    return 'enjeux.metriques.simple.generic';
  }

  /** Vrai si la métrique a au moins un bloc complémentaire (désactive la fusion). */
  hasExtraBlocks(met: GridMetrique): boolean {
    return (met['score_blocks']?.length ?? 0) > 0;
  }

  private formatNum(val: number): string {
    return parseFloat(val.toFixed(2)).toString();
  }

  /** Intervalle / valeur / libellé d'un palier selon le type de métrique. */
  getScoreRange(met: GridMetrique, level: number): string {
    let mnemonique = met['type_metrique_mnemonique'];
    if (!mnemonique) {
      const hasLabels = this.levels.some(l => met[`score_${l}_label`]?.toString().trim());
      const hasVals = this.levels.some(l => met[`score_${l}_val`] != null);
      const hasBounds = this.levels.some(l => met[`score_${l}_inf`] != null || met[`score_${l}_sup`] != null);
      if (hasLabels && !hasBounds) mnemonique = 'TEXTE';
      else if (hasVals && !hasBounds) mnemonique = 'CHIFFRE';
      else mnemonique = 'NUMERIQUE';
    }

    const inactive: number[] = met['inactive_levels'] || [];

    if (mnemonique === 'CHIFFRE') {
      if (inactive.includes(level)) return '-';
      const val = met[`score_${level}_val`];
      return val != null ? this.formatNum(Number(val)) : '-';
    }
    if (mnemonique === 'TEXTE') {
      if (inactive.includes(level)) return '-';
      const label = met[`score_${level}_label`];
      return label?.toString().trim() || '-';
    }
    // NUMERIQUE
    if (inactive.includes(level)) return '- - -';

    const inf = met[`score_${level}_inf`];
    const sup = met[`score_${level}_sup`];
    if (inf == null && sup == null) return '- - -';

    // Inclusivité de la borne inférieure : déduite de la frontière du palier précédent.
    let infInclusive = true;
    if (level > 1) {
      const prevSupInclusive = met[`score_${level - 1}_sup_inclusive`];
      infInclusive = !(prevSupInclusive === true || prevSupInclusive == null);
    }
    // Inclusivité de la borne supérieure.
    let supInclusive = true;
    if (level < 5) {
      const si = met[`score_${level}_sup_inclusive`];
      supInclusive = (si === true || si == null);
    }

    if (inf != null && sup == null) {
      const op = infInclusive ? '≥' : '>';
      return `${op} ${this.formatNum(Number(inf))}`;
    }
    if (inf == null && sup != null) {
      const op = supInclusive ? '≤' : '<';
      return `${op} ${this.formatNum(Number(sup))}`;
    }
    const leftBracket = infInclusive ? '[' : ']';
    const rightBracket = supInclusive ? ']' : '[';
    return `${leftBracket}${this.formatNum(Number(inf))} ; ${this.formatNum(Number(sup))}${rightBracket}`;
  }

  /** Étiquette d'un bloc (intitulé + unité, repli sur « Bloc A/B »). */
  blockLabel(met: GridMetrique, idx: number): string {
    let intitule: string | null | undefined;
    let unite: string | null | undefined;
    if (idx === 0) {
      intitule = met['bloc_intitule'];
      unite = met['unite'];
    } else {
      const block = (met['score_blocks'] || [])[idx - 1];
      intitule = block?.intitule;
      unite = block?.unite;
    }
    const label = (intitule ?? '').trim();
    if (label) {
      const u = (unite ?? '').trim();
      return u ? `${label} (${u})` : label;
    }
    return this.translate.instant('enjeux.metriques.blockLabel') + ' ' + String.fromCharCode(65 + idx);
  }

  /** Lignes affichées dans une cellule de palier (1 ligne, ou N si blocs ET/OU). */
  getCellLines(met: GridMetrique, level: number): Array<{
    text: string;
    blockLabel: string;
    op?: 'OR' | 'AND';
    openParen?: boolean;
    closeParen?: boolean;
  }> {
    const lines: Array<any> = [];

    const mainText = this.getScoreRange(met, level);
    if (mainText && mainText !== '-' && mainText !== '- - -') {
      lines.push({
        text: mainText,
        blockLabel: this.blockLabel(met, 0),
        openParen: (met['group_open'] ?? 0) > 0,
        closeParen: (met['group_close'] ?? 0) > 0,
      });
    }

    const blocks = met['score_blocks'] || [];
    blocks.forEach((block: any, idx: number) => {
      const text = this.getScoreRange({ ...block, type_metrique_mnemonique: 'NUMERIQUE' }, level);
      if (!text || text === '-' || text === '- - -') return;
      lines.push({
        text,
        blockLabel: this.blockLabel(met, idx + 1),
        op: block.logical_op,
        openParen: (block.group_open ?? 0) > 0,
        closeParen: (block.group_close ?? 0) > 0,
      });
    });

    return lines;
  }

  /** Paliers adjacents de même valeur fusionnés visuellement (colspan > 1). */
  getScoreGroups(met: GridMetrique): Array<{ levels: number[]; colspan: number; value: string; primaryLevel: number }> {
    const values = this.levels.map(l => this.getScoreRange(met, l));
    const groups: Array<{ levels: number[]; colspan: number; value: string; primaryLevel: number }> = [];
    const isEmpty = (v: string) => v === '-' || v === '- - -' || !v;
    let i = 0;
    while (i < 5) {
      const level = i + 1;
      const value = values[i];
      if (isEmpty(value)) {
        groups.push({ levels: [level], colspan: 1, value, primaryLevel: level });
        i++;
        continue;
      }
      const mergedLevels = [level];
      let j = i + 1;
      while (j < 5 && values[j] === value) {
        mergedLevels.push(j + 1);
        j++;
      }
      groups.push({ levels: mergedLevels, colspan: mergedLevels.length, value, primaryLevel: level });
      i = j;
    }
    return groups;
  }
}
