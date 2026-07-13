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
   * #530 — Vrai si la métrique n'utilise PAS de grille de scoring : on affiche
   * alors un bloc « saisie libre » au lieu des 5 paliers colorés (vides).
   *
   * Règle (retour #530) : pour un indicateur de réponse, la grille est
   * *opt-in* — elle n'apparaît que si la case « Utiliser une grille de scoring »
   * a été cochée (format GRILLE). Or une case jamais cochée laisse le format à
   * NULL (et pas SIMPLE) : il faut donc traiter REPONSE + (SIMPLE ou NULL sans
   * données de grille) comme « saisie libre ». Les métriques d'état/pression
   * (sans format) conservent leur grille historique.
   */
  isSimple(met: GridMetrique): boolean {
    const format = (met['format_metrique_mnemonique'] || '').toString().toUpperCase();
    if (format === 'GRILLE') return false;
    if (format === 'SIMPLE') return true;
    // Format non renseigné : pas de grille pour un indicateur de réponse SAUF
    // s'il porte déjà une grille (donnée héritée d'avant #452), pour ne pas la
    // masquer. État/pression → grille (comportement historique).
    if ((met['indicateur_type'] || '').toString().toUpperCase() === 'REPONSE') {
      return !this.hasGridData(met);
    }
    return false;
  }

  /** Vrai si la métrique porte au moins une donnée de grille (borne, valeur,
   *  libellé de palier ou bloc complémentaire). */
  private hasGridData(met: GridMetrique): boolean {
    if ((met['score_blocks']?.length ?? 0) > 0) return true;
    return this.levels.some(l =>
      met[`score_${l}_inf`] != null ||
      met[`score_${l}_sup`] != null ||
      met[`score_${l}_val`] != null ||
      (met[`score_${l}_label`]?.toString().trim())
    );
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
    // #555 — la base stocke jusqu'à 4 décimales (DecimalField). L'ancien
    // `toFixed(2)` arrondissait l'affichage (0.665 → 0.67, 0.148 → 0.15), ce qui
    // faussait les intervalles. On préserve la précision saisie (≤ 4 décimales)
    // en supprimant seulement les zéros terminaux et les artefacts flottants.
    return parseFloat(val.toFixed(4)).toString();
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

    // #545/#554 — inclusivité sens-aware, cohérente avec l'éditeur
    // (metrique-block) et le scoring (computeMetriqueScore / backend). La borne
    // inf est portée par le flag sup du voisin de VALEUR inférieure (`level-1` en
    // croissant, `level+1` en décroissant) ; la borne sup par le flag propre du
    // niveau. Une borne absente = palier ouvert (raccourcis niveau 1/5 supprimés,
    // faux en décroissant où le niveau 5 est ouvert vers le bas et le 1 vers le haut).
    const dec = met['sens_variation'] === 'DECROISSANT';
    let infInclusive = true;
    if (inf != null) {
      const lower = dec ? level + 1 : level - 1;
      // Borne extrême (pas de voisin de valeur inférieure) → inclusive (cohérent
      // avec l'éditeur : « ≥ » / « ≤ » pour les paliers ouverts bornés).
      infInclusive = (lower < 1 || lower > 5) ? true : (met[`score_${lower}_sup_inclusive`] === false);
    }
    let supInclusive = true;
    if (sup != null) {
      const si = met[`score_${level}_sup_inclusive`];
      supInclusive = (si !== false);
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
