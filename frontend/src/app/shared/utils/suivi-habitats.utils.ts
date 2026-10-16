import { HabitatRef } from '../../core/models/enjeu.model';

/**
 * Habitats d'un suivi/inventaire (#715).
 *
 * Un suivi range ses habitats dans deux champs : `habitats` (liste structurée
 * avec `cd_hab`, nécessaire aux correspondances EUNIS/Corine) et `habitat_ref`
 * (les noms seuls, conservé pour l'affichage hérité). La fiche action et le
 * module Inventaires lisaient et écrivaient chacun l'un des deux : une
 * modification faite d'un côté n'était pas vue de l'autre, puis écrasée. Les
 * deux écrans passent désormais par ces deux fonctions.
 */

export interface StoredSuiviHabitat {
  cd_hab: string | null;
  lb_hab_fr?: string;
  lb_code?: string;
  lb_typo?: string;
  lb_hab_fr_complet?: string;
}

interface SuiviAvecHabitats {
  habitats?: { cd_hab?: string | null; lb_hab_fr?: string }[] | null;
  habitat_ref?: string | null;
}

/** Liste structurée en priorité, sinon les noms de `habitat_ref`. */
export function parseSuiviHabitats(suivi: SuiviAvecHabitats | null | undefined): HabitatRef[] {
  if (!suivi) return [];
  if (Array.isArray(suivi.habitats) && suivi.habitats.length > 0) {
    return suivi.habitats.map((h: any) => ({
      cd_hab: h.cd_hab ?? '',
      lb_hab_fr: h.lb_hab_fr ?? '',
      lb_code: h.lb_code,
      lb_typo: h.lb_typo,
      lb_hab_fr_complet: h.lb_hab_fr_complet,
    }));
  }
  if (suivi.habitat_ref) {
    return suivi.habitat_ref
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s)
      .map((name) => ({ cd_hab: '', lb_hab_fr: name }));
  }
  return [];
}

/**
 * Les deux champs, toujours renseignés ensemble : une liste vide les efface
 * tous les deux (sinon `habitat_ref` survivait et les habitats réapparaissaient).
 * #368 — un habitat « libre » (sans cd_hab, ex. Outre-mer) est conservé.
 */
export function serializeSuiviHabitats(
  items: HabitatRef[] | null | undefined,
): { habitat_ref: string; habitats: StoredSuiviHabitat[] } {
  const clean = (items ?? []).filter((h) => h && (h.cd_hab || (h.lb_hab_fr || '').trim()));
  return {
    habitat_ref: clean.map((h) => h.lb_hab_fr || h.cd_hab).join(', '),
    habitats: clean.map((h) => ({
      cd_hab: h.cd_hab || null,
      lb_hab_fr: h.lb_hab_fr,
      lb_code: h.lb_code,
      lb_typo: h.lb_typo,
      lb_hab_fr_complet: h.lb_hab_fr_complet,
    })),
  };
}
