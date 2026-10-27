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

/** Minuscules, sans accents : « Études » se trouve en tapant « etudes ». */
export function normaliserRecherche(texte: string): string {
  return (texte || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

/**
 * Construit les groupes filtrés pour un autocomplete de nomenclatures.
 * Si le terme de recherche matche un nom de groupe, toutes les options
 * de ce groupe sont affichées (même si elles ne matchent pas individuellement).
 *
 * #751 — recherche plein texte : sans accents, chaque mot tapé doit se
 * retrouver dans le code, le libellé, le titre du groupe (ou la définition) ;
 * le code se cherche avec ou sans ses points (« cs11 » trouve « CS.1.1 »).
 */
export function buildNomenclatureGroups(
  options: NomenclatureOption[],
  searchText: string,
  opts?: BuildNomenclatureGroupsOptions
): NomenclatureGroup[] {
  const mots = normaliserRecherche(searchText).split(/\s+/).filter(Boolean);
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
  if (!mots.length) {
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
    const titre = normaliserRecherche(groupLabel);
    const groupMatches = mots.every(m => titre.includes(m));

    if (groupMatches) {
      groups.push({ groupLabel, options: grpOpts });
    } else {
      const filtered = grpOpts.filter(opt => {
        const code = normaliserRecherche(opt.cd_nomenclature || opt.mnemonique || '');
        const texte = [
          code, code.replace(/[._]/g, ''), normaliserRecherche(opt.label), titre,
          searchDef ? normaliserRecherche(opt.definition || '') : '',
        ].join(' ');
        return mots.every(m => texte.includes(m));
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

/**
 * Profondeur d'indentation basée sur les points dans le code (1=0, 1.1=1, 1.1.1=2).
 * #751 — codes Gestref : la catégorie est le titre du groupe, « CS.1 » est donc
 * au 1er niveau et « CS.1.1 » au 2e.
 */
export function getNomenclatureDepth(option: NomenclatureOption): number {
  const code = option.cd_nomenclature || option.mnemonique || '';
  const points = (code.match(/\./g) || []).length;
  return /^[A-Za-z]+\./.test(code) ? Math.max(points - 1, 0) : points;
}

/** Fonction d'affichage pour mat-autocomplete displayWith */
export function displayNomenclatureFn(option: NomenclatureOption | string | null): string {
  if (!option) return '';
  if (typeof option === 'string') return option;
  const code = option.cd_nomenclature || option.mnemonique || '';
  return `${code} - ${option.label}`;
}
