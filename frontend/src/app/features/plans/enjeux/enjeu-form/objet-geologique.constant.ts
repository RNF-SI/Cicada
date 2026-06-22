/**
 * #237 — Typologie des objets géologiques (fichier « Typologie enjeux géol
 * CICADA », onglet « Typologie CICADA V2 », colonnes après la colonne C).
 *
 * Seuls les patrimoines « in situ » et « ex situ » portent un détail d'objets :
 * dans la V2, les patrimoines « Documents » et « Autre » n'ont aucun sous-type
 * (le patrimoine « Autre » porte uniquement sa précision libre via le champ
 * `geo_autre_precision`).
 *
 * Le détail est présenté sous forme de liste déroulante multi-select par
 * patrimoine coché (#237). Parents ET sous-types sont sélectionnables. Les codes
 * sont stables et persistés ; seul le libellé est dénormalisé pour l'affichage /
 * l'export.
 */

export interface ObjetGeologiqueOption {
  code: string;
  libelle: string;
  /** `true` → l'objet attend une précision libre (« Autre »). */
  isAutre?: boolean;
  children?: ObjetGeologiqueOption[];
}

export interface ObjetGeologiqueGroup {
  /** Patrimoine déclencheur (case à cocher correspondante). */
  patrimoine: 'in_situ' | 'ex_situ';
  titleKey: string;
  /** Nom du contrôle de formulaire de la case à cocher patrimoine. */
  control: 'geo_in_situ' | 'geo_ex_situ';
  options: ObjetGeologiqueOption[];
}

export const GEO_OBJET_GROUPS: ObjetGeologiqueGroup[] = [
  {
    patrimoine: 'in_situ',
    titleKey: 'enjeux.enjeuForm.geoObjets.inSitu',
    control: 'geo_in_situ',
    options: [
      {
        code: 'IS_SITE_PALEO',
        libelle: 'Site paléontologique',
        children: [
          { code: 'IS_GISEMENT_FOSSILIFERE', libelle: 'Gisement fossilifère' },
          { code: 'IS_ICHNOSITE', libelle: 'Ichnosite (site à empreintes fossiles)' },
        ],
      },
      { code: 'IS_AFFLEUREMENT', libelle: 'Affleurement remarquable' },
      { code: 'IS_STRATOTYPE', libelle: 'Stratotype / coupe stratigraphique' },
      { code: 'IS_TECTONIQUE', libelle: 'Site tectonique ou structural' },
      { code: 'IS_MINERALOGIQUE', libelle: 'Site minéralogique' },
      { code: 'IS_VOLCANIQUE', libelle: 'Site volcanique' },
      { code: 'IS_GEOMORPHO', libelle: 'Site géomorphologique, paysage géologique remarquable' },
      { code: 'IS_HYDROGEO', libelle: 'Site hydrogéologique' },
      {
        code: 'IS_SOUTERRAIN',
        libelle: 'Site souterrain',
        children: [
          { code: 'IS_CAVITE_NATURELLE', libelle: 'Cavité naturelle' },
          { code: 'IS_CAVITE_ANTHROPIQUE', libelle: 'Cavité anthropique' },
        ],
      },
      { code: 'IS_HISTORIQUE', libelle: 'Site historique (localité type, site fondateur, lieu de découverte)' },
      { code: 'IS_AUTRE', libelle: 'Autre', isAutre: true },
    ],
  },
  {
    patrimoine: 'ex_situ',
    titleKey: 'enjeux.enjeuForm.geoObjets.exSitu',
    control: 'geo_ex_situ',
    options: [
      { code: 'ES_COLL_PALEO', libelle: 'Collection paléontologique' },
      { code: 'ES_COLL_MINERALOGIQUE', libelle: 'Collection minéralogique' },
      { code: 'ES_COLL_LITHOLOGIQUE', libelle: 'Collection lithologique' },
      { code: 'ES_AUTRE', libelle: 'Autre', isAutre: true },
    ],
  },
];

/** Liste tous les codes d'un groupe (parents + enfants), pour la synchro multi-select. */
export function groupObjetCodes(group: ObjetGeologiqueGroup): string[] {
  const codes: string[] = [];
  for (const opt of group.options) {
    codes.push(opt.code);
    for (const child of opt.children || []) codes.push(child.code);
  }
  return codes;
}

/** Aplatit la typologie en { code → option } (parents + enfants). */
export const GEO_OBJET_BY_CODE: Record<string, ObjetGeologiqueOption> = (() => {
  const map: Record<string, ObjetGeologiqueOption> = {};
  for (const group of GEO_OBJET_GROUPS) {
    for (const opt of group.options) {
      map[opt.code] = opt;
      for (const child of opt.children || []) map[child.code] = child;
    }
  }
  return map;
})();
