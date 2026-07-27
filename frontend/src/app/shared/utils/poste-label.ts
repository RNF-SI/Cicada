/**
 * Libellé d'affichage d'un poste du plan de gestion.
 *
 * Les postes se nomment d'après leurs fonctions : deux « Animateur nature »
 * créés dans le même plan portent donc le même libellé. Dans une liste de
 * tuiles c'est acceptable (l'organisme et la quotité les distinguent), mais
 * dans un menu déroulant — « à quel poste j'affecte ces jours ? » — les deux
 * options deviennent impossibles à départager (#611).
 *
 * On suffixe donc l'indice d'occurrence dès qu'un libellé est porté par
 * plusieurs postes : « Animateur nature 1 », « Animateur nature 2 ». Les
 * libellés uniques ne sont jamais numérotés.
 */

/** Forme minimale attendue : de quoi identifier et nommer un poste. */
export interface LabelablePoste {
  /** Optionnel comme dans `Poste` : un poste non encore enregistré n'en a pas. */
  id_poste?: number;
  libelle?: string | null;
}

/**
 * @param poste  Poste à nommer.
 * @param postes Ensemble des postes du plan (référence pour les homonymes).
 * @param fallback Libellé de repli si le poste n'en porte pas.
 */
export function posteDisplayLabel(
  poste: LabelablePoste | null | undefined,
  postes: readonly LabelablePoste[],
  fallback = '',
): string {
  if (!poste) return fallback;
  const base = poste.libelle || fallback;
  // Sans libellé (ni repli), rien à numéroter.
  if (!base) return base;
  const sameLabel = postes.filter(p => (p.libelle || '') === (poste.libelle || ''));
  if (sameLabel.length <= 1) return base;
  const index = poste.id_poste == null
    ? -1
    : sameLabel.findIndex(p => p.id_poste === poste.id_poste);
  // Poste absent de la liste de référence : pas d'indice fiable à afficher.
  return index < 0 ? base : `${base} ${index + 1}`;
}

/** Même libellé, résolu depuis un identifiant de poste. */
export function posteDisplayLabelById(
  posteId: number | null | undefined,
  postes: readonly LabelablePoste[],
  fallback = '',
): string {
  if (posteId == null) return fallback;
  return posteDisplayLabel(
    postes.find(p => p.id_poste === posteId),
    postes,
    fallback,
  );
}
