"""
Équivalences entre versions de référentiel pour la recherche transverse (#780).

Une instance publie encore « EI3 » (Eden 62) quand une autre publie « CS.1 »
(Gestref V1). Le hub garde toutes les versions et leurs correspondances
(`apps.nomenclatures`, `import_referentiels`) : un filtre sur une catégorie ou
un code retrouve les objets publiés sous un code équivalent, plus ancien ou plus
récent.

⚠️ Même calcul que CICADA (`backend/apps/search/equivalences.py`, qui lit les
mêmes fichiers) : la parité des filtres en dépend.
"""
from __future__ import annotations

import re
from collections import defaultdict


def categorie_du_code(code: str) -> str:
    m = re.match(r'[A-Za-z]+', code or '')
    return m.group(0).upper() if m else ''


def graphe() -> tuple[dict, dict]:
    """(suivants, precedents) : {(référentiel, code): {codes}} dans chaque sens."""
    from apps.nomenclatures.models import CorrespondanceReferentiel

    suivants, precedents = defaultdict(set), defaultdict(set)
    rows = CorrespondanceReferentiel.objects.values_list(
        'version__referentiel', 'ancien_code', 'nouveau_code', 'options')
    for ref, ancien, nouveau, options in rows:
        cibles = list(options or [])
        if nouveau and nouveau not in cibles:
            cibles.insert(0, nouveau)
        for cible in cibles:
            if ancien and cible and cible != ancien:
                suivants[(ref, ancien)].add(cible)
                precedents[(ref, cible)].add(ancien)
    return dict(suivants), dict(precedents)


def _fermeture(ref: str, codes, sens: dict) -> set:
    vus, pile = set(), list(codes)
    while pile:
        code = pile.pop()
        for suite in sens.get((ref, code), ()):
            if suite not in vus:
                vus.add(suite)
                pile.append(suite)
    return vus


def equivalents(ref: str, codes) -> set:
    """Les codes donnés, leurs successeurs et leurs prédécesseurs (toutes versions)."""
    suivants, precedents = graphe()
    codes = set(codes)
    return codes | _fermeture(ref, codes, suivants) | _fermeture(ref, codes, precedents)


def codes_des_categories(categories) -> set:
    """Codes de types d'action (toutes versions) qui mènent à une des catégories,
    ou en viennent : « CS » retrouve « EI3 » si EI3 devient CS.1 en Gestref V1."""
    suivants, precedents = graphe()
    categories = {c.upper() for c in categories}
    out = set()
    for ref, code in set(suivants) | set(precedents):
        if ref != 'TYPE_ACTION':
            continue
        proches = (_fermeture(ref, [code], suivants) | _fermeture(ref, [code], precedents))
        if categorie_du_code(code) not in categories and any(
                categorie_du_code(c) in categories for c in proches):
            out.add(code)
    return out


def prefixer(ref: str, codes) -> list[str]:
    return sorted(f'{ref}:{c}' for c in codes)
