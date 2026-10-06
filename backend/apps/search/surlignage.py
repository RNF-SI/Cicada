"""
Désigner le mot retenu quand la recherche s'est rabattue sur l'approximation.

En recherche exacte, `ts_headline` isole le passage qui a répondu et
l'interface surligne les mots de la requête. En repli approximatif (#651),
c'est la similarité trigramme qui a répondu : le mot retenu n'est **pas** celui
qui a été tapé (« flamand » a trouvé « Flamant »), et rien côté SQL ne dit
lequel. Or un résultat sans mot surligné se lit comme une erreur de l'outil —
c'est le reproche central de #681.

On recalcule donc ici, pour la seule page affichée, la similarité de chaque mot
du texte avec chaque mot de la requête, avec la même définition que `pg_trgm`
(trigrammes sur le mot complété de deux espaces devant et d'une derrière).
"""

import re
import unicodedata

#: En deçà, deux mots ne se ressemblent pas assez pour être montrés comme
#: « proches ». Aligné sur le seuil `pg_trgm.word_similarity_threshold` (0,6)
#: avec une marge : la similarité « mot contre mot » calculée ici est un peu
#: plus sévère que `word_similarity`, qui cherche la meilleure sous-chaîne.
SEUIL = 0.5

_MOT = re.compile(r"[^\W_]+", re.UNICODE)


def aplatir(texte):
    """Minuscules sans accents, pour comparer comme `unaccent` le ferait."""
    decompose = unicodedata.normalize('NFD', texte or '')
    return ''.join(c for c in decompose if not unicodedata.combining(c)).lower()


def trigrammes(mot):
    """Trigrammes d'un mot, à la manière de `pg_trgm` (`  mot `)."""
    rembourre = f"  {aplatir(mot)} "
    return {rembourre[i:i + 3] for i in range(len(rembourre) - 2)}


def similarite(a, b):
    ta, tb = trigrammes(a), trigrammes(b)
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def mots_proches(texte, terme, seuil=SEUIL):
    """
    Mots du texte qui ressemblent à un mot de la requête, dans l'ordre du texte.

    Les mots très courts sont ignorés des deux côtés : deux lettres n'ont pas
    assez de trigrammes pour que la ressemblance veuille dire quelque chose.
    """
    cibles = [m for m in _MOT.findall(terme or '') if len(m) >= 3]
    if not cibles or not texte:
        return []
    vus, proches = set(), []
    for mot in _MOT.findall(texte):
        if len(mot) < 3 or mot.lower() in vus:
            continue
        if any(similarite(mot, cible) >= seuil for cible in cibles):
            vus.add(mot.lower())
            proches.append(mot)
    return proches


def extrait_autour(texte, mots, fenetre=6):
    """
    Fenêtre de quelques mots autour de la première occurrence d'un mot donné.

    Tient le même rôle que `ts_headline` pour les extraits de la recherche
    exacte, afin que l'interface n'ait qu'une forme d'extrait à afficher.
    """
    if not texte or not mots:
        return None
    unites = texte.split()
    cibles = {aplatir(m) for m in mots}
    for index, unite in enumerate(unites):
        if aplatir(re.sub(r"^\W+|\W+$", '', unite)) in cibles:
            debut, fin = max(0, index - fenetre), min(len(unites), index + fenetre + 1)
            morceau = ' '.join(unites[debut:fin])
            if debut > 0:
                morceau = '… ' + morceau
            if fin < len(unites):
                morceau += ' …'
            return morceau
    return None
