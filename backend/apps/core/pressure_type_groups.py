"""
Mapping des codes TYPE_PRESSION vers leurs catégories de niveau 0.
Source : PressRef CARET V1 (2026-03-24).

Les 3 catégories de niveau 0 :
  1 = Physiques
  2 = Pollutions et modifications physico-chimiques
  3 = Biologiques
"""

_ROOT_CODE_TO_GROUP = {
    '1': 'Physiques',
    '2': 'Pollutions et modifications physico-chimiques',
    '3': 'Biologiques',
}


def get_pressure_group(cd_nomenclature: str) -> str:
    """
    Retourne le groupe de pression pour un code TYPE_PRESSION donné.
    Dérivé du premier caractère du code hiérarchique.
    Ex: '2.3.1.1' → premier chiffre '2' → 'Pollutions et modifications physico-chimiques'
    """
    if not cd_nomenclature:
        return ''
    root = cd_nomenclature.split('.')[0]
    return _ROOT_CODE_TO_GROUP.get(root, '')
