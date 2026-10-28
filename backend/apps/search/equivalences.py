"""
Équivalences entre versions de référentiel pour l'exploration (#780).

Deux instances ne passent pas à une nouvelle version au même moment : l'une
publie encore « EI3 » (Eden 62) quand l'autre publie « CS.1 » (Gestref V1). Les
tables de correspondance livrées avec CICADA (`nomenclatures_data/
referentiels_types_action/*` et `referentiels_versions/*/*`) relient les codes
d'une version à l'autre ; un filtre sur une catégorie ou un code retrouve ainsi
les objets publiés sous un code équivalent, plus ancien ou plus récent.

Le hub tient le même graphe en base (`hub/apps/index/equivalences.py`, importé
depuis les mêmes fichiers) : les deux calculs doivent rester identiques — c'est
la règle de parité de `filters.py`.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

DONNEES = Path(__file__).resolve().parents[2] / 'nomenclatures_data'


def categorie_du_code(code: str) -> str:
    m = re.match(r'[A-Za-z]+', code or '')
    return m.group(0).upper() if m else ''


def _fichiers(racine: Path):
    """(référentiel, chemin de correspondance.csv) de toutes les versions livrées."""
    for f in sorted((racine / 'referentiels_types_action').glob('*/correspondance.csv')):
        yield 'TYPE_ACTION', f
    for f in sorted((racine / 'referentiels_versions').glob('*/*/correspondance.csv')):
        yield f.parent.parent.name.upper(), f


@lru_cache(maxsize=4)
def _graphe(racine: str) -> tuple[dict, dict]:
    """(suivants, precedents) : {(référentiel, code): {codes}} dans chaque sens."""
    suivants, precedents = defaultdict(set), defaultdict(set)
    for ref, chemin in _fichiers(Path(racine)):
        with open(chemin, encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                ancien = (row.get('ancien_code') or '').strip()
                cibles = [c.strip() for c in (row.get('options') or '').split('|') if c.strip()]
                nouveau = (row.get('nouveau_code') or '').strip()
                if nouveau and nouveau not in cibles:
                    cibles.insert(0, nouveau)
                for cible in cibles:
                    if ancien and cible and cible != ancien:
                        suivants[(ref, ancien)].add(cible)
                        precedents[(ref, cible)].add(ancien)
    return dict(suivants), dict(precedents)


def graphe(racine: Path = None) -> tuple[dict, dict]:
    return _graphe(str(racine or DONNEES))


def _fermeture(ref: str, codes, sens: dict) -> set:
    vus, pile = set(), list(codes)
    while pile:
        code = pile.pop()
        for suite in sens.get((ref, code), ()):
            if suite not in vus:
                vus.add(suite)
                pile.append(suite)
    return vus


def equivalents(ref: str, codes, racine: Path = None) -> set:
    """Les codes donnés, leurs successeurs et leurs prédécesseurs (toutes versions)."""
    suivants, precedents = graphe(racine)
    codes = set(codes)
    return codes | _fermeture(ref, codes, suivants) | _fermeture(ref, codes, precedents)


def codes_des_categories(categories, racine: Path = None) -> set:
    """Codes de types d'action (toutes versions) qui mènent à une des catégories,
    ou en viennent : « CS » retrouve « EI3 » si EI3 devient CS.1 en Gestref V1."""
    suivants, precedents = graphe(racine)
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
