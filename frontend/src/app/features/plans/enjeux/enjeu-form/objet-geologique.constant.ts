/**
 * #237 — Typologie des objets géologiques (fournie par Corentin / PatriNat).
 *
 * Structure hiérarchique groupée par type de patrimoine. Les groupes affichés
 * dans le formulaire dépendent des cases patrimoine cochées (in situ, ex situ,
 * documents). Le patrimoine « Autre » n'a pas d'objets : il porte sa propre
 * précision libre (champ `geo_autre_precision`).
 *
 * Parents ET sous-types sont sélectionnables (#237). Les codes sont stables et
 * persistés ; seul le libellé est dénormalisé pour l'affichage / l'export.
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
  patrimoine: 'in_situ' | 'ex_situ' | 'documents';
  titleKey: string;
  options: ObjetGeologiqueOption[];
}

export const GEO_OBJET_GROUPS: ObjetGeologiqueGroup[] = [
  {
    patrimoine: 'in_situ',
    titleKey: 'enjeux.enjeuForm.geoObjets.inSitu',
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
    options: [
      { code: 'ES_COLL_PALEO', libelle: 'Collection paléontologique' },
      { code: 'ES_COLL_MINERALOGIQUE', libelle: 'Collection minéralogique' },
      { code: 'ES_COLL_LITHOLOGIQUE', libelle: 'Collection lithologique' },
      { code: 'ES_AUTRE', libelle: 'Autre', isAutre: true },
    ],
  },
  {
    patrimoine: 'documents',
    titleKey: 'enjeux.enjeuForm.geoObjets.documents',
    options: [
      { code: 'DOC_ARCHIVES', libelle: 'Documents (archives numériques ou papier)' },
      { code: 'DOC_AUTRE', libelle: 'Autre', isAutre: true },
    ],
  },
];

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
