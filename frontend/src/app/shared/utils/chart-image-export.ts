/**
 * Export image (JPG) des graphiques affichés (#639).
 *
 * Les graphiques du bilan sont des SVG maison (`shared/components/charts`).
 * Plutôt que de les re-dessiner pour l'export, on **recompose une planche SVG**
 * à partir du DOM affiché : chaque tuile devient un `<svg>` imbriqué, précédé de
 * son titre et suivi de sa légende. Ce qui est exporté est donc exactement ce
 * qui est à l'écran, filtres compris — comme pour l'export CSV.
 *
 * Deux contraintes dictent l'implémentation :
 *
 * 1. **Les styles doivent être inlinés.** Un SVG rasterisé via `<img>` est lu en
 *    « secure static mode » : les feuilles de styles du document ne s'appliquent
 *    pas. Sans inlining, les libellés d'axes (`.bar-tick`, `.radar-axis-label`…)
 *    sortiraient en noir 16 px par défaut.
 * 2. **Aucune ressource externe.** Toujours pour la même raison, la police
 *    Nunito (Google Fonts) n'est pas chargée : on garde la pile de polices
 *    calculée, dont le repli sans-serif système.
 *
 * La légende est du HTML (`app-chart-legend`) : elle est redessinée en SVG, une
 * entrée par ligne, en réutilisant la pastille SVG existante (qui porte déjà ses
 * `<pattern>`) — sinon les hachures de la légende divergeraient de celles des
 * barres au premier ajustement.
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

/** Pile de polices de repli : Nunito n'est pas chargeable dans l'image. */
const FONT = "Nunito, 'Segoe UI', Arial, sans-serif";

const PAD = 24;
/** Largeur utile d'une planche (hors marges). */
const CONTENT_W = 760;
/** Hauteur maximale d'un graphique : au-delà, on borne et on centre. */
const CHART_MAX_H = 420;
const GAP = 28;

const TITLE_SIZE = 18;
const SUBTITLE_SIZE = 12;
const CARD_TITLE_SIZE = 14;
const LEGEND_SIZE = 12;
const LEGEND_ROW_H = 22;
const LEGEND_SWATCH = 14;

const PRIMARY = '#025359';
const GRAY_DARK = '#746F6E';
const BLACK = '#343433';

/** En-tête de la planche : titre + rappel des filtres en cours. */
export interface ChartExportHeader {
  title: string;
  lines: string[];
}

/**
 * Propriétés reportées en style inline sur le SVG cloné.
 *
 * Liste volontairement courte : tout ce qui influe sur le rendu d'un graphique
 * (aplats, traits, texte) et rien d'autre, pour ne pas alourdir la sérialisation
 * de centaines de nœuds.
 */
const INLINED_PROPS = [
  'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity',
  'stroke-dasharray', 'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin',
  'opacity', 'font-family', 'font-size', 'font-weight', 'font-style',
  'text-anchor', 'dominant-baseline', 'letter-spacing',
];

/** Le graphique d'une tuile : le premier SVG du corps qui n'est pas une pastille. */
function chartSvgOf(card: Element): SVGSVGElement | null {
  return card.querySelector<SVGSVGElement>('.chart-card__body svg:not(.legend__swatch)');
}

/**
 * Tuiles graphiques exportables d'une zone : celles qui portent un graphique.
 * Les tuiles purement textuelles (budget, synthèse RH) sont écartées — leurs
 * chiffres sont dans l'export CSV, une image n'y ajouterait rien.
 */
export function collectChartCards(root: ParentNode | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>('.chart-card'))
    .filter(card => !!chartSvgOf(card));
}

/** Dimensions du repère d'un SVG source, lues sur son `viewBox`. */
function viewBoxOf(svg: SVGSVGElement): { w: number; h: number } {
  const raw = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
  if (raw.length === 4 && raw[2] > 0 && raw[3] > 0) return { w: raw[2], h: raw[3] };
  return { w: 400, h: 300 };
}

/**
 * Reporte les styles calculés du SVG source sur son clone.
 *
 * Les deux arbres sont parcourus en parallèle (le clone a exactement la même
 * structure), ce qui évite d'avoir à ré-identifier les nœuds.
 */
export function inlineComputedStyles(source: Element, clone: Element): void {
  const view = source.ownerDocument?.defaultView;
  if (!view?.getComputedStyle) return;
  const sources = [source, ...Array.from(source.querySelectorAll('*'))];
  const clones = [clone, ...Array.from(clone.querySelectorAll('*'))];
  sources.forEach((node, i) => {
    const target = clones[i];
    if (!target) return;
    const computed = view.getComputedStyle(node);
    const css = INLINED_PROPS
      .map(prop => [prop, computed.getPropertyValue(prop)] as const)
      .filter(([, value]) => !!value)
      .map(([prop, value]) => `${prop}:${value}`)
      .join(';');
    if (css) target.setAttribute('style', css);
  });
}

/**
 * Texte d'un élément tel qu'il est **affiché**.
 *
 * Les titres de tuiles sont mis en capitales par CSS (`text-transform`) : le
 * `textContent` seul rendrait une image qui ne ressemble pas à l'écran.
 */
function displayedText(el: Element | null): string {
  const raw = el?.textContent?.trim() ?? '';
  const view = el?.ownerDocument?.defaultView;
  const transform = view?.getComputedStyle ? view.getComputedStyle(el as Element).textTransform : '';
  if (transform === 'uppercase') return raw.toUpperCase();
  if (transform === 'lowercase') return raw.toLowerCase();
  return raw;
}

interface TextOptions {
  size: number;
  fill: string;
  weight?: string;
  anchor?: string;
}

function textNode(doc: Document, x: number, y: number, content: string, o: TextOptions): SVGTextElement {
  const el = doc.createElementNS(SVG_NS, 'text');
  el.setAttribute('x', String(x));
  el.setAttribute('y', String(y));
  el.setAttribute('font-family', FONT);
  el.setAttribute('font-size', String(o.size));
  el.setAttribute('fill', o.fill);
  if (o.weight) el.setAttribute('font-weight', o.weight);
  if (o.anchor) el.setAttribute('text-anchor', o.anchor);
  el.textContent = content;
  return el;
}

/** Entrées de légende d'une tuile, lues sur le DOM d'`app-chart-legend`. */
function legendItemsOf(card: Element): Array<{ swatch: SVGSVGElement | null; label: string; value: string }> {
  return Array.from(card.querySelectorAll('.legend__item')).map(item => ({
    swatch: item.querySelector<SVGSVGElement>('svg.legend__swatch'),
    label: item.querySelector('.legend__label')?.textContent?.trim() ?? '',
    value: item.querySelector('.legend__value')?.textContent?.trim() ?? '',
  }));
}

/**
 * Compose la planche SVG : en-tête, puis une section par tuile graphique.
 *
 * Fonction pure (hors lecture du DOM source) : c'est elle qui est testée, la
 * rasterisation dépendant d'un `<canvas>` indisponible en test unitaire.
 */
export function buildChartsSvg(
  cards: HTMLElement[],
  header: ChartExportHeader,
  doc: Document = document,
): SVGSVGElement {
  const svg = doc.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('xmlns', SVG_NS);
  const width = CONTENT_W + PAD * 2;

  const background = doc.createElementNS(SVG_NS, 'rect');
  background.setAttribute('width', String(width));
  background.setAttribute('fill', '#FFFFFF');
  svg.appendChild(background);

  let y = PAD + TITLE_SIZE;
  svg.appendChild(textNode(doc, PAD, y, header.title, { size: TITLE_SIZE, fill: PRIMARY, weight: '700' }));
  y += 6;
  for (const line of header.lines) {
    y += SUBTITLE_SIZE + 6;
    svg.appendChild(textNode(doc, PAD, y, line, { size: SUBTITLE_SIZE, fill: GRAY_DARK }));
  }
  y += GAP;

  for (const card of cards) {
    const source = chartSvgOf(card);
    if (!source) continue;

    const title = displayedText(card.querySelector('.chart-card__title'));
    if (title) {
      y += CARD_TITLE_SIZE;
      svg.appendChild(textNode(doc, PAD, y, title, { size: CARD_TITLE_SIZE, fill: PRIMARY, weight: '700' }));
      y += 12;
    }

    const box = viewBoxOf(source);
    let w = CONTENT_W;
    let h = (w * box.h) / box.w;
    if (h > CHART_MAX_H) {
      h = CHART_MAX_H;
      w = (h * box.w) / box.h;
    }
    const clone = source.cloneNode(true) as SVGSVGElement;
    inlineComputedStyles(source, clone);
    clone.setAttribute('x', String(PAD + (CONTENT_W - w) / 2));
    clone.setAttribute('y', String(y));
    clone.setAttribute('width', String(w));
    clone.setAttribute('height', String(h));
    clone.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    // Les tuiles sont empilées : un débordement viendrait mordre la suivante.
    clone.setAttribute('overflow', 'hidden');
    clone.removeAttribute('class');
    svg.appendChild(clone);
    y += h + 8;

    for (const item of legendItemsOf(card)) {
      if (item.swatch) {
        const swatch = item.swatch.cloneNode(true) as SVGSVGElement;
        inlineComputedStyles(item.swatch, swatch);
        swatch.setAttribute('x', String(PAD));
        swatch.setAttribute('y', String(y));
        swatch.setAttribute('width', String(LEGEND_SWATCH));
        swatch.setAttribute('height', String(LEGEND_SWATCH));
        swatch.removeAttribute('class');
        svg.appendChild(swatch);
      }
      const label = item.value ? `${item.label} : ${item.value}` : item.label;
      svg.appendChild(textNode(doc, PAD + LEGEND_SWATCH + 6, y + 11, label, { size: LEGEND_SIZE, fill: BLACK }));
      y += LEGEND_ROW_H;
    }

    y += GAP;
  }

  const height = Math.max(y - GAP + PAD, PAD * 2);
  svg.setAttribute('width', String(width));
  svg.setAttribute('height', String(height));
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  background.setAttribute('height', String(height));
  return svg;
}

/** Sérialise la planche en data URI, seule forme sûre pour un `<img>` (pas de taint). */
export function svgToDataUri(svg: SVGSVGElement): string {
  const raw = new XMLSerializer().serializeToString(svg);
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(raw)}`;
}

/**
 * Rasterise la planche en JPEG. `scale` > 1 pour rester net en impression.
 */
export function svgToJpeg(svg: SVGSVGElement, scale = 2, quality = 0.92): Promise<Blob> {
  const width = Number(svg.getAttribute('width')) || CONTENT_W;
  const height = Number(svg.getAttribute('height')) || CONTENT_W;
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      const ctx = canvas.getContext('2d');
      if (!ctx) { reject(new Error('canvas 2d context unavailable')); return; }
      // Le JPEG n'a pas de transparence : sans ce fond, le PNG intermédiaire
      // sortirait sur du noir.
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        blob => blob ? resolve(blob) : reject(new Error('canvas.toBlob returned null')),
        'image/jpeg',
        quality,
      );
    };
    image.onerror = () => reject(new Error('SVG rasterization failed'));
    image.src = svgToDataUri(svg);
  });
}

/** Déclenche le téléchargement d'un blob sous le nom donné. */
export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
