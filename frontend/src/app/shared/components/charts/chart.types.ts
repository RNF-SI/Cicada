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
  /**
   * Symbole de la série (kit UI) : `swatch` = pastille carrée (défaut),
   * `line` = trait plein + point (une courbe), `dashed` = trait pointillé
   * (une enveloppe min–max). Une courbe annoncée par un carré plein ne se
   * reconnaît pas dans le graphe.
   */
  shape?: 'swatch' | 'line' | 'dashed';
  /** Opacité de la pastille — une bande se signale par sa transparence. */
  opacity?: number;
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

// ---------------------------------------------------------------------------
// Lissage des tracés (kit UI — page « Graphiques »)
// ---------------------------------------------------------------------------

export interface ChartPoint { x: number; y: number; }

/**
 * Suite de points → tracé SVG **lissé** (Béziers cubiques, Catmull-Rom).
 *
 * Les graphiques du kit UI (courbes d'évolution, polygone du radar) sont
 * dessinés en courbes, pas en segments droits : c'est ce que produisent les
 * outils de design, et la différence se voit immédiatement sur un radar à cinq
 * axes ou sur une série annuelle.
 *
 * `tension` règle l'ampleur des courbes (0 = polyligne, 0.5 ≈ le rendu Figma).
 * `closed` referme la courbe sur elle-même — le cas du radar, où le dernier
 * point doit rejoindre le premier sans cassure.
 */
export function smoothPath(points: ChartPoint[], tension = 0.5, closed = false): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  // Deux points : une courbe n'apporte rien et la tangente serait arbitraire.
  if (points.length === 2 && !closed) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
  }

  const at = (i: number): ChartPoint => {
    if (closed) return points[(i + points.length) % points.length];
    return points[Math.max(0, Math.min(points.length - 1, i))];
  };

  const k = tension / 3;
  let d = `M ${points[0].x} ${points[0].y}`;
  const last = closed ? points.length : points.length - 1;
  for (let i = 0; i < last; i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    const c1 = { x: p1.x + (p2.x - p0.x) * k, y: p1.y + (p2.y - p0.y) * k };
    const c2 = { x: p2.x - (p3.x - p1.x) * k, y: p2.y - (p3.y - p1.y) * k };
    d += ` C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${p2.x} ${p2.y}`;
  }
  return closed ? `${d} Z` : d;
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
