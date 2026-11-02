"""
Contrôle d'une grille de scores de métrique (5 paliers), partagé par la saisie
(``MetriqueSerializer.validate``) et l'import de l'arborescence (#787) : un
classeur ne doit pas pouvoir créer une grille que l'écran refuserait.

``valeurs`` porte les champs d'un bloc à la manière du modèle
(``score_N_inf`` / ``score_N_sup`` / ``score_N_val`` / ``score_N_label``).
La fonction renvoie la liste des erreurs ``(champ, message)`` dans l'ordre où
la saisie les signale ; liste vide = grille acceptée.
"""
from django.utils.translation import gettext as _

NIVEAUX = range(1, 6)
LIBELLES_PALIERS = {
    1: "Très mauvais", 2: "Mauvais", 3: "Moyen", 4: "Bon", 5: "Très bon",
}
SENS = ("CROISSANT", "DECROISSANT")


def _inactifs(inactive) -> set:
    try:
        return {int(x) for x in (inactive or [])}
    except (TypeError, ValueError):
        return set()


def erreurs_grille(*, type_mnemo, format_mnemo, sens, inactive, valeurs) -> list:
    if format_mnemo == "SIMPLE":
        return []
    inactifs = _inactifs(inactive)
    erreurs = []

    # Chiffre / Texte : chaque niveau actif porte une valeur (Chiffre) ou un
    # libellé (Texte), sinon le score serait faussé.
    if type_mnemo in ("CHIFFRE", "TEXTE"):
        champ = "val" if type_mnemo == "CHIFFRE" else "label"
        for n in NIVEAUX:
            if n in inactifs:
                continue
            nom = f"score_{n}_{champ}"
            v = valeurs.get(nom)
            manque = v is None if type_mnemo == "CHIFFRE" else not (v or "").strip()
            if manque:
                erreurs.append((nom, _(
                    "Chaque niveau actif doit avoir une valeur (ou être marqué « non utilisé »).")))
        return erreurs

    # Type absent = numérique (comportement historique).
    if type_mnemo not in (None, "NUMERIQUE"):
        return []

    for n in NIVEAUX:
        if n in inactifs:
            continue
        inf, sup = valeurs.get(f"score_{n}_inf"), valeurs.get(f"score_{n}_sup")
        if inf is not None and sup is not None and inf >= sup:
            erreurs.append((f"score_{n}_sup", _(
                "La borne sup doit être strictement supérieure à la borne inf.")))

    # Continuité entre paliers voisins, en sautant les niveaux « non utilisés ».
    # Croissant : sup(N) == inf(N+1) ; décroissant : inf(N) == sup(N+1).
    for n in range(1, 5):
        if n in inactifs or (n + 1) in inactifs:
            continue
        if sens == "DECROISSANT":
            a, b = valeurs.get(f"score_{n}_inf"), valeurs.get(f"score_{n + 1}_sup")
        else:
            a, b = valeurs.get(f"score_{n}_sup"), valeurs.get(f"score_{n + 1}_inf")
        if a is not None and b is not None and a != b:
            erreurs.append((None, _(
                "Les bornes entre les scores %(n)s et %(next)s doivent être égales "
                "pour assurer la continuité.") % {"n": n, "next": n + 1}))
    return erreurs
