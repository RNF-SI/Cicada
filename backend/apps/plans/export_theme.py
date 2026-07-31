"""
Couleur des exports, paramétrable par instance (#601).

CICADA est déployé par plusieurs structures (RNF, un CEN, une DREAL…). Les
classeurs Excel et les documents Word qu'elles produisent portent leur nom :
leurs bandeaux, titres et en-têtes doivent donc pouvoir prendre **leur** couleur,
choisie par l'administrateur de l'instance (`SiteConfiguration.export_color`).

Ne sont PAS concernées :

- les **couleurs de score** (rouge → cyan) : elles forment la légende de la
  grille de lecture, un lecteur doit les reconnaître d'un plan à l'autre et
  d'une structure à l'autre ;
- la palette de l'export « arborescence », relevée sur le modèle Excel de
  référence (#620) : la changer ferait diverger l'export du modèle attendu.

Les modules d'export gardent leurs styles en variables de module (openpyxl
construit des objets Font/PatternFill immuables). Ils appellent
``rafraichir(module_globals, ...)`` au début de chaque construction de classeur
pour les réaligner sur la couleur courante : l'écriture est idempotente — toutes
les requêtes d'un même déploiement écrivent la même valeur — et prend donc effet
dès que l'administrateur change la couleur, sans redémarrage.
"""

import logging

#: Couleur de CICADA, valeur par défaut d'une instance qui n'a rien choisi.
COULEUR_DEFAUT = '#025359'

logger = logging.getLogger(__name__)


def couleur_instance() -> str:
    """Couleur des exports de cette instance, au format ``#RRGGBB``."""
    from apps.core.models import SiteConfiguration

    try:
        couleur = SiteConfiguration.get_instance().export_color
    except Exception:  # base non migrée, table absente en test unitaire…
        logger.debug("Couleur d'export indisponible, repli sur le défaut")
        return COULEUR_DEFAUT
    return couleur or COULEUR_DEFAUT


def argb(couleur: str | None = None) -> str:
    """``#RRGGBB`` → ``FFRRGGBB`` (notation openpyxl, alpha en tête)."""
    couleur = couleur or couleur_instance()
    return 'FF' + couleur.lstrip('#').upper()


def rgb(couleur: str | None = None) -> tuple[int, int, int]:
    """``#RRGGBB`` → ``(r, g, b)`` (notation python-docx)."""
    couleur = (couleur or couleur_instance()).lstrip('#')
    return tuple(int(couleur[i:i + 2], 16) for i in (0, 2, 4))
