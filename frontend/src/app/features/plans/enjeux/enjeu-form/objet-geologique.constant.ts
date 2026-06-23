/**
 * #237 — Typologie des objets géologiques (in situ / ex situ).
 *
 * La typologie n'est plus codée en dur : elle provient désormais du référentiel
 * de nomenclatures `TYPE_OBJET_GEOLOGIQUE` (cf. nomenclatures_data), chargé via
 * `GET /api/nomenclatures/?type=TYPE_OBJET_GEOLOGIQUE`. Ce module ne fait que
 * **transformer** la liste plate des nomenclatures en arbre groupé par patrimoine
 * (in situ / ex situ) avec parents et sous-types.
 *
 * Encodage :
 *  - patrimoine dérivé du préfixe de code (`IS_` → in situ, `ES_` → ex situ) ;
 *  - hiérarchie + ordre via le champ `hierarchy` (chemin pointé zero-paddé :
 *    `1.01` = option, `1.01.01` = sous-type) ;
 *  - objet « Autre » détecté via le suffixe de code (`_AUTRE`).
 *
 * Les patrimoines « Documents » (fichiers) et « Autre » (précision libre) n'ont
 * pas d'objets de typologie.
 */

/** Forme minimale d'une nomenclature renvoyée par l'API. */
export interface GeoObjetNomenclature {
  id_nomenclature: number;
  cd_nomenclature: string;
  label: string;
  hierarchy?: string | null;
}

export interface ObjetGeologiqueOption {
  /** id_nomenclature — clé de sélection et de persistance. */
  id: number;
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

/** Configuration statique des groupes (ordre, libellé, case à cocher). */
const PATRIMOINE_CONFIG: { patrimoine: 'in_situ' | 'ex_situ'; prefix: string; titleKey: string; control: 'geo_in_situ' | 'geo_ex_situ'; }[] = [
  { patrimoine: 'in_situ', prefix: 'IS_', titleKey: 'enjeux.enjeuForm.geoObjets.inSitu', control: 'geo_in_situ' },
  { patrimoine: 'ex_situ', prefix: 'ES_', titleKey: 'enjeux.enjeuForm.geoObjets.exSitu', control: 'geo_ex_situ' },
];

function depthOf(hierarchy: string | null | undefined): number {
  return ((hierarchy || '').match(/\./g) || []).length;
}

/**
 * Construit l'arbre groupé (par patrimoine, parents → sous-types) à partir de la
 * liste plate des nomenclatures TYPE_OBJET_GEOLOGIQUE.
 */
export function buildGeoObjetGroups(nomenclatures: GeoObjetNomenclature[]): ObjetGeologiqueGroup[] {
  const sorted = [...(nomenclatures || [])].sort(
    (a, b) => (a.hierarchy || '').localeCompare(b.hierarchy || ''),
  );

  return PATRIMOINE_CONFIG.map(cfg => {
    const items = sorted.filter(n => (n.cd_nomenclature || '').startsWith(cfg.prefix));
    // Index par hierarchy pour rattacher les enfants à leur parent.
    const byHierarchy = new Map<string, ObjetGeologiqueOption>();
    const options: ObjetGeologiqueOption[] = [];

    for (const n of items) {
      const opt: ObjetGeologiqueOption = {
        id: n.id_nomenclature,
        code: n.cd_nomenclature,
        libelle: n.label,
        isAutre: (n.cd_nomenclature || '').endsWith('_AUTRE') || undefined,
      };
      const hier = n.hierarchy || '';
      byHierarchy.set(hier, opt);
      if (depthOf(hier) >= 2) {
        // Sous-type : rattacher au parent (hierarchy sans le dernier segment).
        const parentHier = hier.slice(0, hier.lastIndexOf('.'));
        const parent = byHierarchy.get(parentHier);
        if (parent) {
          (parent.children ||= []).push(opt);
          continue;
        }
      }
      options.push(opt);
    }

    return { patrimoine: cfg.patrimoine, titleKey: cfg.titleKey, control: cfg.control, options };
  });
}

/** Liste tous les ids d'un groupe (parents + enfants), pour la synchro multi-select. */
export function groupObjetIds(group: ObjetGeologiqueGroup): number[] {
  const ids: number[] = [];
  for (const opt of group.options) {
    ids.push(opt.id);
    for (const child of opt.children || []) ids.push(child.id);
  }
  return ids;
}
