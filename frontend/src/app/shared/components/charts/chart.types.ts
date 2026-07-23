/**
 * Types partagés pour les composants graphiques (kit UI — page « Graphiques »).
 *
 * Ces primitives sont pensées pour la page Bilan mais restent génériques et
 * réutilisables partout dans l'application. Les couleurs doivent provenir de la
 * palette du design system (variables SCSS / palette de scores).
 */

/** Motif de remplissage d'une série (aplat ou hachures). */
export type ChartPattern = 'solid' | 'hatch' | 'cross' | 'dots';

/** Part d'un camembert / donut. */
export interface DonutSlice {
  label: string;
  value: number;
  color: string;
  pattern?: ChartPattern;
}

/** Entrée de légende (pastille + libellé + valeur optionnelle). */
export interface LegendItem {
  label: string;
  color: string;
  pattern?: ChartPattern;
  value?: string | number;
}

/** Un segment (série) d'une barre — empilé ou groupé. */
export interface BarSegment {
  value: number;
  color: string;
  pattern?: ChartPattern;
  /** Libellé de la série (pour l'infobulle / légende). */
  seriesLabel?: string;
}

/** Une barre (une catégorie de l'axe X) et ses segments. */
export interface BarDatum {
  /** Libellé de l'axe X. */
  label: string;
  segments: BarSegment[];
}

/** Un axe du radar (un enjeu / FCR) avec sa valeur moyenne. */
export interface RadarAxis {
  label: string;
  value: number;
  /** Couleur du point (par défaut : couleur principale). */
  color?: string;
}

/** Une courbe du graphe « courbes ». */
export interface LineSeries {
  label: string;
  color: string;
  /** Valeurs alignées sur `xLabels`. `null` = point manquant. */
  points: (number | null)[];
  dashed?: boolean;
  showPoints?: boolean;
}

/** Bande de confiance (enveloppe min–max + écart-type) du graphe courbes. */
export interface LineBand {
  lower: (number | null)[];
  upper: (number | null)[];
  innerLower?: (number | null)[];
  innerUpper?: (number | null)[];
  color?: string;
}

// ---------------------------------------------------------------------------
// Registre de motifs SVG (hachures) — génère des <pattern> uniques par instance.
// ---------------------------------------------------------------------------

export interface PatternDef {
  id: string;
  kind: ChartPattern;
  color: string;
}

/**
 * Attribue un `<pattern>` unique à chaque couple (couleur, motif) non-plein.
 * `ref()` renvoie soit la couleur brute (motif plein) soit `url(#id)`.
 */
export class PatternRegistry {
  private readonly map = new Map<string, PatternDef>();

  constructor(private readonly uid: string) {}

  ref(color: string, pattern: ChartPattern = 'solid'): string {
    if (!pattern || pattern === 'solid') return color;
    const key = `${pattern}:${color}`;
    let def = this.map.get(key);
    if (!def) {
      def = { id: `${this.uid}-pat${this.map.size}`, kind: pattern, color };
      this.map.set(key, def);
    }
    return `url(#${def.id})`;
  }

  defs(): PatternDef[] {
    return [...this.map.values()];
  }
}

/** Compteur d'instances pour générer des identifiants SVG uniques. */
let chartUidCounter = 0;
export function nextChartUid(prefix = 'ccd-chart'): string {
  chartUidCounter += 1;
  return `${prefix}-${chartUidCounter}`;
}

/** Palette de scores (0..5) du design system, réutilisable par les pages. */
export const SCORE_PALETTE: Record<number, string> = {
  0: '#DADADA', // sans donnée
  1: '#FF7579', // très mauvais
  2: '#FA9965', // mauvais
  3: '#F7D35C', // moyen
  4: '#82DB8A', // bon
  5: '#81C9D8', // très bon
};

/** Couleur de score la plus proche d'une moyenne continue (0..5). */
export function scoreColor(value: number): string {
  const idx = Math.max(0, Math.min(5, Math.round(value)));
  return SCORE_PALETTE[idx];
}
