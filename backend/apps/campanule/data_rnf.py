"""
Protocoles standardisés portés par Réserves Naturelles de France (#781) :
le Diagnostic d'Ancrage Territorial (DAT) et les deux outils Natur'Adapt.

Comme MhéO (#565), ils ne font pas partie du catalogue CAMPanule de l'INPN : ils
sont chargés dans les mêmes tables ``ref_campanule.*`` pour être proposés à la
sélection d'un protocole et affichés dans la fiche détail. Leurs codes suivent
ceux de MhéO dans la plage réservée (>= ``RNF_BASE``).

Source : fiches transmises par RNF (issue #781). Les liens ont été débarrassés
de leurs paramètres de suivi (« utm_source »).
"""

from apps.campanule.data_mheo import MHEO_BASE

# Plage des protocoles RNF, après celle de MhéO.
RNF_BASE = MHEO_BASE + 100

_URL_DAT = "https://ancrage.reserves-naturelles.org/"
_URL_GUIDE_NATURADAPT = "https://naturadapt.com/groups/communaute/documents/556/get"
_URL_RESSOURCES_NATURADAPT = "https://naturadapt.com/groups/communaute/pages/ressources"

_AUTEUR_NATURADAPT = (
    "Réserves Naturelles de France (RNF) et partenaires du projet LIFE Natur'Adapt."
)
_CATEGORIE_NATURADAPT = "Changement climatique (Natur'Adapt)"
_REFERENCE_GUIDE = (
    "Guide méthodologique Natur'Adapt — 2023. Coudurier C., Petit L., Tissot A.-C., "
    "Lochon I., Dane J. et Champion E. — Réserves Naturelles de France. 86 pages."
)
_RETOURS_EXPERIENCE = (
    "Retours d'expérience : diagnostics et plans d'adaptation élaborés sur les 21 "
    "sites du projet LIFE Natur'Adapt (entre autres), accessibles depuis la "
    "bibliothèque officielle des ressources Natur'Adapt."
)


def _protocole(cd, court, complet, **fields):
    return {
        "cd_protocole": cd,
        "fields": {
            "lb_protocole_court": court,
            "lb_protocole_complet": complet,
            "obsolete": "false",
            **fields,
        },
    }


RNF_PROTOCOLES = [
    {
        **_protocole(
            cd=RNF_BASE + 1,
            court="Diagnostic d'ancrage territorial (DAT)",
            complet="Diagnostic d'Ancrage Territorial (DAT)",
            cible="Acteurs-clés du territoire",
            descr_cible_prot=(
                "Acteurs-clés du territoire : acteurs leviers permettant par la "
                "suite d'agir sur les pressions d'origine anthropique."
            ),
            categorie_prot="Ancrage territorial (RNF)",
            prot_auteur="RNF, LPO",
            description=(
                "Le Diagnostic d'Ancrage Territorial (DAT) est une méthodologie "
                "élaborée par Réserves Naturelles de France en collaboration avec "
                "la LPO à la suite de la thèse de Clara Therville soutenue en 2013. "
                "Le protocole, qui a vu le jour en 2019 avec la création d'une "
                "boîte à outils en ligne, s'inscrit dans une démarche sociologique "
                "qui s'appuie sur des données qualitatives issues des perceptions "
                "des acteurs locaux rencontrés dans le cadre d'entretiens "
                "semi-directifs. L'ancrage est un processus permettant de "
                "renforcer la place et le poids de l'aire protégée sur le "
                "territoire, mais aussi ses liens avec les acteurs locaux. Ce "
                "processus est constitué de deux composantes : l'appropriation de "
                "l'AP par la population locale, et l'intégration de l'AP au "
                "territoire.\n"
                "Le DAT propose d'évaluer l'ancrage lors d'une enquête permettant "
                "de faire un état des lieux de la perception de l'aire protégée "
                "auprès d'acteurs ciblés. Pour cela, trois indicateurs sont "
                "mesurés : le niveau de connaissance, d'intérêt, et d'implication. "
                "Cet état des lieux permet ensuite de cibler des points "
                "d'amélioration de l'ancrage, dans le but d'inclure les résultats "
                "du DAT directement dans le plan de gestion. L'ancrage est en "
                "effet considéré comme un facteur clé de réussite dans la gestion "
                "des ENP."
            ),
            descr_objectif_prot=(
                "Apporter au gestionnaire d'une aire protégée un état de référence "
                "et des recommandations pour améliorer l'intégration de son site à "
                "l'échelle locale et lui permettre de travailler sur les pressions "
                "d'origine anthropique qui y sont exercées. L'étude doit permettre "
                "de mieux saisir les interactions qui existent entre l'AP et son "
                "territoire et d'identifier des leviers d'action pour améliorer "
                "son ancrage."
            ),
            indicateur=(
                "Connaissance : 10 métriques, correspondant chacune à une question "
                "de la trame d'entretien, permettant d'évaluer le niveau de "
                "connaissance de l'acteur sur différents aspects (missions, "
                "réglementation, outils de communication, etc.).\n"
                "Intérêt : 9 métriques, correspondant chacune à une question de la "
                "trame d'entretien, permettant d'évaluer le niveau d'intérêt de "
                "l'acteur par rapport à l'aire protégée (fréquence de visite, avis "
                "sur les animations, contraintes éventuelles, etc.).\n"
                "Implication : 6 métriques, correspondant chacune à une question de "
                "la trame d'entretien, permettant d'évaluer le niveau d'implication "
                "de l'acteur par rapport à l'aire protégée (liens avec l'AP, "
                "participation aux animations, échanges, etc.).\n"
                "D'autres métriques complémentaires sont également analysées : "
                "l'implication dans le CCG, la matrice AFOM (Atouts, Faiblesses, "
                "Opportunités, Menaces) et les attentes des acteurs envers l'AP."
            ),
            nature_donnees="Données qualitatives (entretiens semi-directifs)",
            echelle_restit="Locale (aire protégée et son territoire)",
            url=_URL_DAT,
            url_perm=_URL_DAT,
        ),
        "echantillonnage": {
            "periode_an": "Principalement en amont du plan de gestion",
            "duree": "L'enquête dure environ 6 mois",
            "commentaire": (
                "Qui le réalise ? Une personne extérieure au site afin d'avoir le "
                "regard le plus objectif : idéalement un stagiaire ou un CDD. La "
                "personne doit avoir une expérience en conduite d'entretiens (ex. "
                "profils sociologie, géographie).\n"
                "Combien ça coûte ? Prévoir le budget nécessaire pour la "
                "rémunération de l'enquêteur (le plus souvent stagiaire) et la "
                "prise en compte de ses frais de déplacement pour les entretiens, "
                "et potentiellement un accompagnement RNF à la réalisation du DAT.\n"
                "Ressources : boîte à outils de diagnostic « RNF - Diagnostic "
                "d'Ancrage Territorial ». Prestations d'appui au DAT proposées par "
                "RNF : contacter ombeline.chidaine@rnfrance.org."
            ),
        },
        "methode": (
            "Enquête sociologique auprès d'acteurs ciblés du territoire, par "
            "entretiens semi-directifs suivant une trame commune, pour établir un "
            "état des lieux de la perception de l'aire protégée (connaissance, "
            "intérêt, implication)."
        ),
        "techniques": [
            ("Entretien semi-directif", None),
        ],
    },
    {
        **_protocole(
            cd=RNF_BASE + 2,
            court="Natur'Adapt — Diagnostic de vulnérabilité et d'opportunité",
            complet=(
                "Natur'Adapt — Diagnostic de vulnérabilité et d'opportunité au "
                "changement climatique"
            ),
            cible="Patrimoine naturel, activités humaines, gestion",
            descr_cible_prot=(
                "Patrimoine naturel, fonctionnalités écologiques, activités "
                "humaines, gestion des aires protégées."
            ),
            categorie_prot=_CATEGORIE_NATURADAPT,
            prot_auteur=_AUTEUR_NATURADAPT,
            description=(
                "Le diagnostic de vulnérabilité et d'opportunité au changement "
                "climatique est un outil développé dans le cadre de la démarche "
                "Natur'Adapt, portée par Réserves Naturelles de France dans le "
                "cadre du LIFE Biodiv'France. Il vise à analyser et anticiper les "
                "impacts potentiels du changement climatique sur une aire "
                "protégée, son patrimoine naturel, ses activités humaines et sa "
                "gestion.\n"
                "Il repose sur la caractérisation du climat passé et futur, "
                "l'identification des objets d'analyse pertinents pour le "
                "territoire et l'évaluation de leur sensibilité et de leur "
                "capacité d'adaptation face aux évolutions climatiques et à leurs "
                "effets.\n"
                "La démarche mobilise les connaissances scientifiques disponibles, "
                "les projections climatiques, les données naturalistes existantes "
                "ainsi que l'expertise des gestionnaires et des acteurs du "
                "territoire. Elle permet d'identifier les principaux facteurs de "
                "vulnérabilité, mais également les opportunités éventuelles "
                "associées aux changements attendus.\n"
                "Le diagnostic constitue une aide à la décision pour anticiper les "
                "transformations écologiques et orienter les stratégies de gestion "
                "des aires protégées. Ce DVO sert à rédiger un plan d'adaptation, "
                "qui viendra par la suite s'intégrer aux documents de gestion."
            ),
            descr_objectif_prot=(
                "Évaluer les vulnérabilités et les opportunités d'une aire protégée "
                "face au changement climatique afin d'identifier les enjeux "
                "prioritaires et d'éclairer les décisions de gestion et "
                "d'adaptation."
            ),
            nature_donnees=(
                "Livrables : diagnostic de vulnérabilité et d'opportunité, "
                "comprenant un récit climatique, des fiches objets et des matrices "
                "de vulnérabilité."
            ),
            echelle_restit="Locale (aire protégée et territoire environnant)",
            date_publi="2023",
            url=_URL_GUIDE_NATURADAPT,
            url_perm=_URL_GUIDE_NATURADAPT,
            url_complementaire=_URL_RESSOURCES_NATURADAPT,
        ),
        "echantillonnage": {
            "periode_an": (
                "Diagnostic à actualiser en fonction de l'évolution des "
                "connaissances, des conditions climatiques et des enjeux de "
                "gestion. Généralement recommandé de le mettre à jour lors des "
                "révisions de plans de gestion ou documents de gestion."
            ),
            "commentaire": (
                "Articulation : constitue une base pour l'élaboration du plan "
                "d'adaptation au changement climatique.\n"
                f"Références : {_REFERENCE_GUIDE} Diagnostic : fiches pratiques "
                "n°5, 6 et 7, consacrées à l'analyse des effets, à l'évaluation des "
                "vulnérabilités et opportunités et au contenu du diagnostic.\n"
                f"{_RETOURS_EXPERIENCE}"
            ),
        },
        "methode": (
            "Caractérisation du climat passé et futur, identification des objets "
            "d'analyse du territoire, puis évaluation de leur sensibilité et de "
            "leur capacité d'adaptation face aux évolutions climatiques."
        ),
        "techniques": [
            ("Analyse documentaire et bibliographique", None),
            ("Analyse de données et de projections climatiques", None),
            ("Identification et caractérisation des objets d'analyse", None),
            ("Évaluation qualitative des vulnérabilités et opportunités", None),
            ("Mobilisation de l'expertise locale et concertation avec les acteurs du territoire", None),
        ],
    },
    {
        **_protocole(
            cd=RNF_BASE + 3,
            court="Natur'Adapt — Plan d'adaptation au changement climatique",
            complet="Natur'Adapt — Plan d'adaptation au changement climatique",
            cible="Gestion des aires protégées",
            categorie_prot=_CATEGORIE_NATURADAPT,
            prot_auteur=_AUTEUR_NATURADAPT,
            description=(
                "Le plan d'adaptation au changement climatique est un outil d'aide "
                "à la décision et de planification développé dans le cadre de la "
                "démarche Natur'Adapt. Il s'appuie sur les résultats du diagnostic "
                "de vulnérabilité et d'opportunité pour définir les orientations et "
                "les actions permettant d'adapter la gestion d'une aire protégée "
                "aux évolutions climatiques et écologiques attendues.\n"
                "Son élaboration repose sur une réflexion prospective concernant le "
                "devenir du patrimoine naturel, les objectifs de conservation et "
                "pratiques de gestion, ainsi que les activités humaines. Elle vise "
                "à identifier les évolutions nécessaires pour prendre en compte les "
                "effets du changement climatique, notamment en matière de "
                "préservation des fonctionnalités écologiques, d'accompagnement des "
                "dynamiques naturelles et d'évolution des interventions de "
                "gestion.\n"
                "Le plan d'adaptation permet de formaliser une stratégie "
                "d'adaptation. Il peut notamment conduire à maintenir certaines "
                "actions, à les modifier, à en développer de nouvelles ou à "
                "reconsidérer certains objectifs de conservation devenus "
                "difficilement atteignables dans un contexte climatique évolutif.\n"
                "La démarche s'appuie sur les connaissances disponibles, "
                "l'expertise des gestionnaires et la concertation avec les "
                "partenaires et acteurs du territoire. Elle privilégie une approche "
                "prospective et itérative de la gestion, tenant compte des "
                "incertitudes associées aux projections climatiques et aux réponses "
                "des écosystèmes.\n"
                "Le plan d'adaptation ne constitue pas un programme d'actions "
                "standardisé : son contenu dépend des vulnérabilités identifiées, "
                "des caractéristiques écologiques du site, des moyens disponibles "
                "et du contexte territorial."
            ),
            descr_objectif_prot=(
                "Définir et planifier une stratégie d'adaptation de la gestion "
                "d'une aire protégée au changement climatique, à partir des "
                "vulnérabilités et opportunités identifiées, afin d'accompagner "
                "les transformations écologiques et de renforcer les capacités "
                "d'adaptation du territoire. Aller vers des écosystèmes plus "
                "résilients, avec une mosaïque d'habitats et d'espèces."
            ),
            nature_donnees=(
                "Livrables : plan d'adaptation au changement climatique comprenant "
                "des orientations stratégiques et des mesures opérationnelles."
            ),
            echelle_restit="Locale (aire protégée, interactions avec le territoire)",
            date_publi="2023",
            url=_URL_GUIDE_NATURADAPT,
            url_perm=_URL_GUIDE_NATURADAPT,
            url_complementaire=_URL_RESSOURCES_NATURADAPT,
        ),
        "echantillonnage": {
            "periode_an": (
                "Plan à réévaluer et actualiser régulièrement en fonction des "
                "résultats du suivi et de l'évolution des connaissances et des "
                "conditions environnementales."
            ),
            "commentaire": (
                "Articulation : élaboré à partir du diagnostic de vulnérabilité et "
                "d'opportunité ; peut alimenter la révision des documents de "
                "gestion existants.\n"
                f"Références : {_REFERENCE_GUIDE} Plan d'adaptation : fiche "
                "pratique n°8, présentant des exemples de mesures d'adaptation.\n"
                f"{_RETOURS_EXPERIENCE}"
            ),
        },
        "methode": (
            "À partir des résultats du diagnostic de vulnérabilité et "
            "d'opportunité, réflexion prospective, définition et hiérarchisation "
            "des objectifs d'adaptation, puis programmation des mesures de gestion "
            "et de leurs modalités de suivi et d'évaluation."
        ),
        "techniques": [
            ("Analyse des résultats du diagnostic de vulnérabilité et d'opportunité", None),
            ("Réflexion prospective", None),
            ("Définition et hiérarchisation des objectifs d'adaptation", None),
            ("Identification des mesures de gestion", None),
            ("Concertation avec les parties prenantes", None),
            ("Programmation des actions et définition des modalités de suivi et d'évaluation", None),
        ],
    },
]
