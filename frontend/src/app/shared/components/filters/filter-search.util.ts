/**
 * Utilitaires de recherche dans les filtres (#592).
 *
 * Partagés par `app-filter-option-list` (liste plate) et `app-filter-tree` (arbre) :
 * c'est la seule logique réellement commune aux deux, leurs formes de données différant.
 *
 * Deux contraintes dictent l'implémentation :
 *
 * 1. **Aucune `RegExp` construite depuis la saisie utilisateur.** Un `(` saisi ferait lever
 *    le constructeur, un `.` matcherait tout. On balaie avec `indexOf`.
 *
 * 2. **Correspondance insensible à la casse ET aux accents, en conservant les offsets.**
 *    L'UI est en français : taper `categorie` doit surligner `catégorie`. Or replier via
 *    `normalize('NFD').replace(...)` sur la chaîne entière change sa longueur, donc les
 *    offsets trouvés dans la version repliée ne désignent plus les bons caractères de
 *    l'original — le gras se poserait à côté. On replie donc **caractère par caractère** en
 *    mémorisant, pour chaque caractère replié, l'offset d'origine dont il provient.
 */

/** Marques diacritiques combinantes, à retirer après décomposition NFD. */
const DIACRITICS = /[̀-ͯ]/g;

/** Segment de texte renvoyé par `segmentMatches`. */
export interface MatchSegment {
  text: string;
  match: boolean;
}

/**
 * Replie une chaîne (minuscules, sans accents) en conservant la trace des offsets.
 *
 * @returns `folded` la chaîne repliée, et `map` tel que `map[i]` est l'offset, dans la
 *          chaîne d'origine, du caractère ayant produit `folded[i]`.
 */
export function foldIndexed(text: string): { folded: string; map: number[] } {
  let folded = '';
  const map: number[] = [];
  let offset = 0;

  // `for...of` itère par point de code : les paires de substitution restent intactes.
  for (const char of text) {
    const foldedChar = char.toLowerCase().normalize('NFD').replace(DIACRITICS, '');
    for (const piece of foldedChar) {
      folded += piece;
      map.push(offset);
    }
    offset += char.length;
  }

  return { folded, map };
}

/** Replie une chaîne sans conserver les offsets (comparaison simple). */
export function foldText(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(DIACRITICS, '');
}

/** Indique si `text` contient `query`, insensiblement à la casse et aux accents. */
export function matchesQuery(text: string, query: string): boolean {
  const needle = foldText(query).trim();
  if (!needle) {
    return true;
  }
  return foldText(text).includes(needle);
}

/**
 * Découpe `text` en segments correspondants / non correspondants pour `query`.
 *
 * Renvoie toujours au moins un segment. Une requête vide donne un unique segment
 * non correspondant, ce qui évite tout cas particulier dans les templates.
 */
export function segmentMatches(text: string, query: string): MatchSegment[] {
  const needle = foldText(query ?? '').trim();
  if (!text || !needle) {
    return [{ text: text ?? '', match: false }];
  }

  const { folded, map } = foldIndexed(text);
  const segments: MatchSegment[] = [];
  let cursor = 0; // offset courant dans la chaîne d'origine
  let from = 0; // offset courant dans la chaîne repliée

  while (from <= folded.length - needle.length) {
    const hit = folded.indexOf(needle, from);
    if (hit === -1) {
      break;
    }

    const start = map[hit];
    const endIndex = hit + needle.length;
    // Fin exclusive dans l'original : offset du caractère replié suivant, ou fin de chaîne.
    let end = endIndex < map.length ? map[endIndex] : text.length;
    // Garde-fou : un caractère d'origine peut se replier en plusieurs caractères ; si la
    // correspondance s'arrête au milieu, on englobe le caractère entier plutôt que rien.
    if (end <= start) {
      end = start + 1;
    }

    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), match: false });
    }
    segments.push({ text: text.slice(start, end), match: true });

    cursor = end;
    from = endIndex;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), match: false });
  }

  return segments.length ? segments : [{ text, match: false }];
}
