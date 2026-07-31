"""
Notation des paliers d'une grille de métrique — source unique pour les exports.

Miroir Python de `frontend/src/app/features/plans/suivis/metrique-seuils.util.ts` :
la saisie affiche « [50 ; 200] », « ]30 ; 50] », « ≥ 50 », « ≤ 10 », et les
exports doivent dire exactement la même chose. Deux implémentations séparées
avaient déjà divergé — l'export « fiche action » notait l'inclusivité, l'export
« arborescence » se contentait de « 30 – 50 » (#619).

Inclusivité **sens-aware** (#545/#554) : seule la borne **supérieure** de chaque
palier porte un drapeau (`score_N_sup_inclusive`). L'inclusivité de la borne
inférieure d'un palier est donc portée par le palier voisin de VALEUR
inférieure — `level - 1` en sens croissant, `level + 1` en décroissant — et une
borne extrême, qui n'a pas de voisin, est inclusive.
"""

from decimal import Decimal, InvalidOperation

#: Paliers d'une grille, du plus mauvais au meilleur.
NIVEAUX = range(1, 6)


def format_seuil(valeur) -> str:
    """
    Formate un seuil sans zéros superflus : « 10 » et non « 10.0000 » (#619).

    Les seuils sont des `DecimalField(decimal_places=4)` : sans normalisation,
    l'export affiche un padding que le gestionnaire n'a jamais saisi.
    """
    if valeur is None or valeur == "":
        return ""
    try:
        decimal = Decimal(str(valeur)).normalize()
    except (InvalidOperation, ValueError):
        return str(valeur)
    # `normalize` peut produire une notation exponentielle (1E+2) : format 'f'.
    return format(decimal, "f")


def intervalle_palier(bloc, niveau, sens=None, inactifs=None) -> str:
    """
    Notation d'un palier : « [0 ; 20] », « ]20 ; 40[ », « ≥ 50 », « ≤ 10 », « ».

    ``bloc`` est indifféremment une :class:`Metrique` (bloc principal) ou un
    :class:`MetriqueScoreBlock` (bloc complémentaire) : les deux exposent les
    mêmes champs ``score_N_inf/sup``, ``score_N_sup_inclusive``,
    ``sens_variation`` et ``inactive_levels``.

    ``sens`` et ``inactifs`` permettent de forcer les valeurs (l'appelant les a
    parfois déjà lues) ; sinon elles sont prises sur le bloc.
    """
    if inactifs is None:
        inactifs = getattr(bloc, "inactive_levels", None) or []
    if niveau in inactifs:
        return ""

    inf = getattr(bloc, f"score_{niveau}_inf", None)
    sup = getattr(bloc, f"score_{niveau}_sup", None)
    if inf is None and sup is None:
        return ""

    if sens is None:
        sens = getattr(bloc, "sens_variation", None)
    decroissant = (sens or "").upper() == "DECROISSANT"

    # Borne inférieure : son inclusivité est portée par le voisin de valeur
    # inférieure. Sans voisin (palier extrême), la borne est inclusive.
    inf_inclusive = True
    if inf is not None:
        voisin = niveau + 1 if decroissant else niveau - 1
        if 1 <= voisin <= 5:
            inf_inclusive = getattr(bloc, f"score_{voisin}_sup_inclusive", True) is False
    sup_inclusive = (
        sup is None
        or getattr(bloc, f"score_{niveau}_sup_inclusive", True) is not False
    )

    # Intervalle ouvert d'un côté → notation compacte, comme à la saisie.
    if sup is None:
        return f"{'≥' if inf_inclusive else '>'} {format_seuil(inf)}"
    if inf is None:
        return f"{'≤' if sup_inclusive else '<'} {format_seuil(sup)}"

    return (
        f"{'[' if inf_inclusive else ']'}{format_seuil(inf)} ; "
        f"{format_seuil(sup)}{']' if sup_inclusive else '['}"
    )
