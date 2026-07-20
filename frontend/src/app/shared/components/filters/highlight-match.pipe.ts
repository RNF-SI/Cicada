import { Pipe, PipeTransform } from '@angular/core';
import { MatchSegment, segmentMatches } from './filter-search.util';

/**
 * Découpe un libellé en segments correspondants / non correspondants à une recherche,
 * pour mettre la portion trouvée en gras (spec Figma #592).
 *
 * Renvoie des **segments**, jamais du HTML : le template rend des nœuds texte via
 * l'interpolation Angular, donc aucun `innerHTML`, aucun `DomSanitizer`, aucune surface XSS.
 *
 * @example
 * ```html
 * @for (seg of option.label | highlightMatch: query(); track $index) {
 *   @if (seg.match) { <strong>{{ seg.text }}</strong> } @else { {{ seg.text }} }
 * }
 * ```
 */
@Pipe({
  name: 'highlightMatch',
  standalone: true,
})
export class HighlightMatchPipe implements PipeTransform {
  transform(text: string, query: string): ReadonlyArray<MatchSegment> {
    return segmentMatches(text ?? '', query ?? '');
  }
}
