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

export interface BuildNomenclatureGroupsOptions {
  /** Chercher aussi dans le champ definition (exemples, etc.) */
  searchInDefinition?: boolean;
}

/**
 * Construit les groupes filtrés pour un autocomplete de nomenclatures.
 * Si le terme de recherche matche un nom de groupe, toutes les options
 * de ce groupe sont affichées (même si elles ne matchent pas individuellement).
 */
export function buildNomenclatureGroups(
  options: NomenclatureOption[],
  searchText: string,
  opts?: BuildNomenclatureGroupsOptions
): NomenclatureGroup[] {
  const searchTerm = searchText.toLowerCase();
  const searchDef = opts?.searchInDefinition ?? false;

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
    for (const [groupLabel, grpOpts] of allGroups) {
      groups.push({ groupLabel, options: grpOpts });
    }
    return groups;
  }

  // 3) Filtrer : si le titre du groupe matche → afficher toutes ses options
  //    sinon → afficher seulement les options qui matchent
  const groups: NomenclatureGroup[] = [];
  for (const [groupLabel, grpOpts] of allGroups) {
    const groupMatches = groupLabel.toLowerCase().includes(searchTerm);

    if (groupMatches) {
      groups.push({ groupLabel, options: grpOpts });
    } else {
      const filtered = grpOpts.filter(opt => {
        const code = opt.cd_nomenclature || opt.mnemonique || '';
        if (code.toLowerCase().includes(searchTerm)) return true;
        if (opt.label.toLowerCase().includes(searchTerm)) return true;
        if (searchDef && opt.definition?.toLowerCase().includes(searchTerm)) return true;
        return false;
      });
      if (filtered.length > 0) {
        groups.push({ groupLabel, options: filtered });
      }
    }
  }
  return groups;
}

/**
 * Parse une définition de nomenclature contenant des exemples.
 * Format attendu : "Définition...\n\nExemples : Exemple1, Exemple2"
 */
export function parseNomenclatureDefinition(def: string | undefined): { definition: string; examples: string } {
  if (!def) return { definition: '', examples: '' };
  const delimiter = '\\n\\nExemples : ';
  const idx = def.indexOf(delimiter);
  if (idx === -1) return { definition: def, examples: '' };
  return {
    definition: def.substring(0, idx),
    examples: def.substring(idx + delimiter.length)
  };
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
