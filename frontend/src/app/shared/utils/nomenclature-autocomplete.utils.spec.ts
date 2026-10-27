import {
  buildNomenclatureGroups, getNomenclatureDepth, NomenclatureOption,
} from './nomenclature-autocomplete.utils';

const opt = (id: number, code: string, label: string, group: string): NomenclatureOption => ({
  id_nomenclature: id, mnemonique: code, cd_nomenclature: code, label, group_label: group,
});

const CS = 'CS — Connaissance et suivis du patrimoine naturel';
const IP = 'IP — Intervention sur le patrimoine naturel';
const OPTIONS = [
  opt(1, 'CS.1', 'Études des eaux', CS),
  opt(2, 'CS.1.1', 'Études hydrologiques', CS),
  opt(3, 'CS.2.1', 'Inventaires de la faune', CS),
  opt(4, 'IP.2.1', 'Restauration de milieux', IP),
];

const codes = (search: string) =>
  buildNomenclatureGroups(OPTIONS, search).flatMap(g => g.options.map(o => o.cd_nomenclature));

describe('buildNomenclatureGroups — recherche plein texte (#751)', () => {
  it('ignore les accents', () => {
    expect(codes('etudes')).toEqual(['CS.1', 'CS.1.1']);
  });

  it('exige chaque mot, dans le libellé ou le titre du groupe', () => {
    expect(codes('connaissance faune')).toEqual(['CS.2.1']);
    expect(codes('faune restauration')).toEqual([]);
  });

  it('trouve un code avec ou sans ses points', () => {
    expect(codes('cs11')).toEqual(['CS.1.1']);
    expect(codes('IP.2')).toEqual(['IP.2.1']);
  });

  it('un titre de groupe trouvé garde tout le groupe', () => {
    expect(codes('intervention')).toEqual(['IP.2.1']);
    expect(codes('connaissance')).toEqual(['CS.1', 'CS.1.1', 'CS.2.1']);
  });
});

describe('getNomenclatureDepth', () => {
  it('codes Eden : profondeur = nombre de points', () => {
    expect(getNomenclatureDepth(opt(1, 'IP1', '', ''))).toBe(0);
    expect(getNomenclatureDepth(opt(1, 'IP1.5.1', '', ''))).toBe(2);
  });

  it('codes Gestref : la catégorie est le groupe, « CS.1 » au 1er niveau', () => {
    expect(getNomenclatureDepth(opt(1, 'CS.1', '', ''))).toBe(0);
    expect(getNomenclatureDepth(opt(1, 'CS.1.1', '', ''))).toBe(1);
  });
});
