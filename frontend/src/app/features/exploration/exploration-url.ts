/**
 * Conversion entre les critères d'exploration et les paramètres d'URL.
 *
 * L'URL est la source de vérité de la recherche : elle rend un résultat
 * partageable par simple copie du lien et fait fonctionner le bouton
 * « précédent » du navigateur. Ces deux fonctions sont le seul endroit qui
 * connaisse le nom des paramètres, et elles sont volontairement symétriques.
 */

import { ParamMap } from '@angular/router';

import {
  ExplorationCriteres,
  ExplorationStatut,
  ExplorationTri,
  ExplorationType,
} from '../../core/models/exploration.model';

function texte(params: ParamMap, cle: string): string[] | undefined {
  const brut = params.get(cle);
  if (!brut) {
    return undefined;
  }
  const valeurs = brut.split(',').map((v) => v.trim()).filter(Boolean);
  return valeurs.length ? valeurs : undefined;
}

function entiers(params: ParamMap, cle: string): number[] | undefined {
  return texte(params, cle)
    ?.map((valeur) => Number(valeur))
    .filter((valeur) => Number.isFinite(valeur));
}

/** Lit les critères depuis les query params. */
export function criteresDepuisUrl(params: ParamMap): ExplorationCriteres {
  const page = Number(params.get('page'));

  return {
    q: params.get('q') ?? undefined,
    // Le mode « titres uniquement » est le défaut : seule sa désactivation
    // apparaît dans l'URL.
    titresSeulement: params.get('titres_seulement') === 'false' ? false : undefined,
    types: texte(params, 'types') as ExplorationType[] | undefined,
    onglet: texte(params, 'onglet') as ExplorationType[] | undefined,
    zones: entiers(params, 'zones'),
    organismes: entiers(params, 'organismes'),
    typesSite: texte(params, 'types_site'),
    categoriesEnjeu: texte(params, 'categories_enjeu'),
    typesIndicateur: texte(params, 'types_indicateur'),
    categoriesAction: texte(params, 'categories_action'),
    statuts: texte(params, 'statuts') as ExplorationStatut[] | undefined,
    tri: (params.get('tri') as ExplorationTri | null) ?? undefined,
    page: Number.isFinite(page) && page > 1 ? page : undefined,
  };
}

/**
 * Écrit les critères dans des query params.
 *
 * Les valeurs vides sont mises à `null` plutôt qu'omises : Angular retire
 * ainsi le paramètre de l'URL au lieu de conserver l'ancienne valeur.
 */
export function criteresVersUrl(
  criteres: ExplorationCriteres,
): Record<string, string | null> {
  const multiple = (valeurs?: (string | number)[]) =>
    valeurs?.length ? valeurs.join(',') : null;

  return {
    q: criteres.q?.trim() || null,
    titres_seulement: criteres.titresSeulement === false ? 'false' : null,
    types: multiple(criteres.types),
    onglet: multiple(criteres.onglet),
    zones: multiple(criteres.zones),
    organismes: multiple(criteres.organismes),
    types_site: multiple(criteres.typesSite),
    categories_enjeu: multiple(criteres.categoriesEnjeu),
    types_indicateur: multiple(criteres.typesIndicateur),
    categories_action: multiple(criteres.categoriesAction),
    statuts: multiple(criteres.statuts),
    tri: criteres.tri && criteres.tri !== 'pertinence' ? criteres.tri : null,
    page: criteres.page && criteres.page > 1 ? String(criteres.page) : null,
  };
}
