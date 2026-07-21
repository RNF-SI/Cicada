"""
Protocoles standardisés MhéO (boîte à outils « Milieux humides, évaluation,
observation »).

Ces 5 protocoles ne font pas (encore) partie du catalogue CAMPanule de l'INPN
mais sont des protocoles standardisés à part entière, destinés aux gestionnaires
de zones humides. Ils sont chargés dans les mêmes tables ``ref_campanule.*`` que
le catalogue INPN afin d'être proposés à la sélection d'un protocole d'inventaire
et affichés dans la fiche détail (cf. issue #565).

Source : fiches transmises par RNF (Collectif MhéO). MhéO a vocation à être
intégré à CAMPanule à terme ; les codes sont donc réservés dans une plage haute
(>= ``MHEO_BASE``) pour éviter toute collision avec les codes INPN.
"""

# Plage de codes réservée aux protocoles MhéO (au-dessus des codes INPN).
MHEO_BASE = 900000

_AUTEUR = "Collectif MhéO"
_CATEGORIE = "Zones humides (MhéO)"
_URL = "https://rhomeo-bao.fr/"

_DESCRIPTION_COMMUNE = (
    "La boîte à outils MhéO (BAO MhéO) réunit des protocoles harmonisés, des "
    "indicateurs communs et des fiches d'analyse pour le suivi des zones "
    "humides sur l'ensemble du territoire hexagonal et corse. Elle est "
    "destinée aux gestionnaires des milieux naturels."
)

_OBJECTIF_COMMUN = (
    "Au niveau local (échelle du site), suivre l'évolution de l'état des zones "
    "humides pour comprendre la trajectoire écologique sur le long terme, et "
    "suivre l'efficacité des travaux (restauration, réhabilitation…) à court et "
    "moyen terme."
)


def _protocole(cd, court, complet, cible, indicateur, description, objectif):
    """Construit le dict de champs d'un protocole MhéO."""
    return {
        "cd_protocole": cd,
        "fields": {
            "lb_protocole_court": court,
            "lb_protocole_complet": complet,
            "cible": cible,
            "categorie_prot": _CATEGORIE,
            "prot_auteur": _AUTEUR,
            "indicateur": indicateur,
            "description": f"{_DESCRIPTION_COMMUNE} {description}",
            "descr_objectif_prot": f"{_OBJECTIF_COMMUN} {objectif}",
            "url": _URL,
            "url_perm": _URL,
            "obsolete": "false",
        },
    }


# ---------------------------------------------------------------------------
# Les 5 protocoles
# ---------------------------------------------------------------------------

MHEO_PROTOCOLES = [
    {
        **_protocole(
            cd=MHEO_BASE + 1,
            court="MhéO — Amphibiens",
            complet="Protocole MhéO Amphibiens",
            cible="Amphibiens",
            indicateur="Intégrité du peuplement d'amphibiens (I11)",
            description=(
                "Le protocole Amphibiens vise à comparer un peuplement observé "
                "à une liste d'espèces sténoèces de référence (peuplement "
                "attendu). L'indicateur associé est « Intégrité du peuplement "
                "d'amphibiens »."
            ),
            objectif=(
                "L'objectif du protocole amphibiens est de réaliser un "
                "inventaire calibré et reproductible du peuplement d'amphibiens "
                "de la zone humide, le plus complet possible dans un minimum de "
                "temps. Les méthodes d'échantillonnage de la première campagne "
                "doivent être reproduites les années suivantes."
            ),
        ),
        "echantillonnage": {
            "passages_an": "3 visites annuelles (dont une de nuit)",
            "periode_an": (
                "1er passage 15 fév.–15 mars (températures nocturnes > 4 °C) ; "
                "2e passage 15 avr.–15 mai ; 3e passage 15 juin–15 juil."
            ),
            "commentaire": (
                "Échantillonnage stratifié afin de répartir la pression sur les "
                "différents habitats herpétologiques et de les échantillonner "
                "de manière représentative. Le recours à la capture "
                "d'amphibiens nécessite une demande préalable d'autorisation "
                "auprès de la DREAL de votre région."
            ),
        },
        "methode": (
            "Recherche des amphibiens s'appuyant sur plusieurs méthodes. Les "
            "données collectées sont des présences/absences (données "
            "qualitatives), complétées d'informations semi-quantitatives, sur "
            "un réseau de points d'observation afin d'analyser le peuplement à "
            "l'échelle du site."
        ),
        "techniques": [
            ("Point d'écoute", None),
            ("Épuisette", None),
            ("Recherche à la torche (torching)", None),
            ("Piégeage", None),
        ],
    },
    {
        **_protocole(
            cd=MHEO_BASE + 2,
            court="MhéO — Flore",
            complet="Protocole MhéO Flore",
            cible="Flore",
            indicateur=(
                "Indice floristique d'engorgement (I02) ; "
                "Indice floristique de fertilité du sol (I06)"
            ),
            description=(
                "Le protocole Flore vise à relever sur chaque placette "
                "l'ensemble des espèces présentes et à noter leur recouvrement "
                "estimé. Les indicateurs associés sont « Indice floristique "
                "d'engorgement » et « Indice floristique de fertilité du sol »."
            ),
            objectif=(
                "La flore d'un site est évaluée par la réalisation de relevés "
                "sur un ensemble de placettes réparties de manière à "
                "échantillonner le plus d'habitats naturels possibles. À chaque "
                "taxon sont associées des valeurs indicatrices (engorgement, "
                "fertilité) qui servent au calcul des indicateurs."
            ),
        ),
        "echantillonnage": {
            "passages_an": "1 passage",
            "periode_an": (
                "Fin de période printanière (mai–juin), selon les habitats en "
                "présence"
            ),
            "commentaire": (
                "Points de relevés réalisés à intervalles réguliers le long de "
                "transects préalablement positionnés pour être les plus "
                "représentatifs de la diversité des milieux présents sur le "
                "site ou de la zone d'influence des travaux."
            ),
        },
        "methode": (
            "Sur chaque placette, l'ensemble des espèces présentes est noté "
            "ainsi que leur recouvrement estimé. La taille de la placette, la "
            "physionomie de la végétation, le recouvrement et la hauteur des "
            "différentes strates sont également notés. La position des "
            "placettes est mesurée au GPS."
        ),
        "techniques": [
            ("Relevé phytosociologique", None),
        ],
    },
    {
        **_protocole(
            cd=MHEO_BASE + 3,
            court="MhéO — Odonates",
            complet="Protocole MhéO Odonates",
            cible="Odonates",
            indicateur="Intégrité du peuplement d'odonates (I10)",
            description=(
                "Le protocole Odonates vise à comparer un peuplement observé à "
                "une liste d'espèces sténoèces de référence (peuplement "
                "attendu). L'indicateur associé est « Intégrité du peuplement "
                "d'odonates »."
            ),
            objectif=(
                "L'objectif du protocole odonates est de réaliser un inventaire "
                "du peuplement d'odonates de la zone humide le plus complet "
                "possible dans un minimum de temps, en appliquant une pression "
                "d'observation calibrée et reproductible."
            ),
        ),
        "echantillonnage": {
            "passages_an": "3 visites",
            "periode_an": (
                "avril/mai (espèces précoces) ; juin/juillet ; "
                "août/septembre (espèces tardives)"
            ),
            "commentaire": (
                "Échantillonnage stratifié pour répartir la pression "
                "d'observation sur les différents habitats odonatologiques. Au "
                "sein de chaque habitat, au moins 3 points d'observation (et "
                "jusqu'à 6). S'appuyer sur la liste des habitats "
                "odonatologiques identifiés sur la zone humide."
            ),
        },
        "methode": (
            "Pour les imagos, le relevé consiste à noter : l'espèce observée, "
            "la présence d'un ou plusieurs individus, la présence de mâles et "
            "de femelles, et le comportement reproducteur le plus significatif "
            "(émergence/exuvie, néonate/ponte, accouplement/tandem, défense "
            "territoriale). Le comportement reproducteur est essentiel pour "
            "l'exploitation des données."
        ),
        "techniques": [
            ("Transect", None),
            ("Point d'observation", None),
            (
                "Recherche d'exuvies",
                "Les exuvies d'anisoptères sont recherchées et récoltées "
                "durant un laps de temps dédié ; indispensables pour repérer "
                "certaines espèces discrètes au stade imago.",
            ),
        ],
    },
    {
        **_protocole(
            cd=MHEO_BASE + 4,
            court="MhéO — Pédologie",
            complet="Protocole MhéO Pédologie",
            cible="Sol / nappe (hydromorphie)",
            indicateur=(
                "Niveau d'humidité du sol – pédologie / niveau d'hydromorphie "
                "(I01)"
            ),
            description=(
                "Le protocole Pédologie vise à décrire le sol après "
                "prélèvement. L'indicateur associé est « Niveau d'humidité du "
                "sol – pédologie – Niveau d'hydromorphie »."
            ),
            objectif=(
                "Caractériser le niveau d'hydromorphie du sol par des sondages "
                "pédologiques répartis sur le gradient d'humidité de la zone "
                "humide."
            ),
        ),
        "echantillonnage": {
            "periode_an": (
                "Idéalement début de période printanière (mars–avril) pour "
                "favoriser l'observation des niveaux hauts de la nappe ; "
                "possible toute l'année (la période estivale est la moins "
                "favorable)"
            ),
            "commentaire": (
                "Sondages réalisés à intervalles réguliers le long de "
                "transects, généralement de la périphérie vers le centre de la "
                "zone humide. En règle générale, un sondage tous les 50 à "
                "100 m ; la pression de sondage varie selon la taille, la "
                "configuration et la topographie de la zone humide."
            ),
        },
        "methode": (
            "Une fois le prélèvement réalisé, l'échantillon de sol est divisé "
            "en horizons (couches homogènes) décrits dans la fiche de terrain. "
            "Chaque horizon est caractérisé par les modalités (généralement 4) "
            "de 17 descripteurs de texture, de structure et de couleur."
        ),
        "techniques": [
            ("Relevé / prélèvement de sol (tarière)", None),
        ],
    },
    {
        **_protocole(
            cd=MHEO_BASE + 5,
            court="MhéO — Piézométrie",
            complet="Protocole MhéO Piézométrie",
            cible="Nappe d'eau dans le sol",
            indicateur="Dynamique hydrologique de la nappe – piézomètres (I03)",
            description=(
                "Le protocole Piézométrie vise à suivre les variations de la "
                "nappe d'eau dans le sol et à traduire la dynamique "
                "hydrologique de la zone humide. L'indicateur associé est "
                "« Dynamique hydrologique de la nappe - piézomètres »."
            ),
            objectif=(
                "Suivre les variations de la nappe d'eau dans le sol et "
                "traduire la dynamique hydrologique de la zone humide."
            ),
        ),
        "echantillonnage": {
            "passages_an": (
                "Relevé automatique (pas de temps préconisé : 1 relevé / heure)"
            ),
            "commentaire": (
                "Pour un suivi de la trajectoire écologique, un seul "
                "piézomètre équipé peut être installé par site. L'évaluation "
                "des effets d'une restauration nécessite au moins un second "
                "piézomètre, voire un réseau de plusieurs piézomètres."
            ),
        },
        "methode": (
            "Un piézomètre servant de puits d'observation est installé et "
            "équipé d'une sonde de pression permettant l'enregistrement "
            "automatique des valeurs de nappe. S'agissant de mesurer les "
            "variations proches de la surface, les piézomètres peuvent ne pas "
            "excéder deux mètres de hauteur."
        ),
        "techniques": [
            ("Piézomètre équipé d'une sonde de pression", None),
        ],
    },
]
