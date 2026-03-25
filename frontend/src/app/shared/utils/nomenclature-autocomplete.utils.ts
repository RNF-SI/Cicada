/**
 * Utilitaires partagés pour les autocomplete de nomenclatures groupées.
 * Utilisé par : operation-form, inventaire-form, enjeux-list (pressions).
 */

export interface NomenclatureOption {
  id_nomenclature: number;
  mnemonique: string;
  cd_nomenclature?: string;
  label: string;
  definition?: string;
  hierarchy?: string;
  group_label?: string;
}

export interface NomenclatureGroup {
  groupLabel: string;
  options: NomenclatureOption[];
}

/**
 * Construit les groupes filtrés pour un autocomplete de nomenclatures.
 * Si le terme de recherche matche un nom de groupe, toutes les options
 * de ce groupe sont affichées (même si elles ne matchent pas individuellement).
 */
export function buildNomenclatureGroups(
  options: NomenclatureOption[],
  searchText: string
): NomenclatureGroup[] {
  const searchTerm = searchText.toLowerCase();

  // 1) Construire tous les groupes avec toutes leurs options
  const allGroups = new Map<string, NomenclatureOption[]>();
  for (const opt of options) {
    const groupKey = opt.group_label || '';
    if (!allGroups.has(groupKey)) {
      allGroups.set(groupKey, []);
    }
    allGroups.get(groupKey)!.push(opt);
  }

  // 2) Si pas de recherche, tout afficher
  if (!searchTerm) {
    const groups: NomenclatureGroup[] = [];
    for (const [groupLabel, opts] of allGroups) {
      groups.push({ groupLabel, options: opts });
    }
    return groups;
  }

  // 3) Filtrer : si le titre du groupe matche → afficher toutes ses options
  //    sinon → afficher seulement les options qui matchent
  const groups: NomenclatureGroup[] = [];
  for (const [groupLabel, opts] of allGroups) {
    const groupMatches = groupLabel.toLowerCase().includes(searchTerm);

    if (groupMatches) {
      groups.push({ groupLabel, options: opts });
    } else {
      const filtered = opts.filter(opt => {
        const code = opt.cd_nomenclature || opt.mnemonique || '';
        return code.toLowerCase().includes(searchTerm)
          || opt.label.toLowerCase().includes(searchTerm);
      });
      if (filtered.length > 0) {
        groups.push({ groupLabel, options: filtered });
      }
    }
  }
  return groups;
}

/** Profondeur d'indentation basée sur les points dans le code (1=0, 1.1=1, 1.1.1=2) */
export function getNomenclatureDepth(option: NomenclatureOption): number {
  const code = option.cd_nomenclature || option.mnemonique || '';
  return (code.match(/\./g) || []).length;
}

/** Fonction d'affichage pour mat-autocomplete displayWith */
export function displayNomenclatureFn(option: NomenclatureOption | string | null): string {
  if (!option) return '';
  if (typeof option === 'string') return option;
  const code = option.cd_nomenclature || option.mnemonique || '';
  return `${code} - ${option.label}`;
}
