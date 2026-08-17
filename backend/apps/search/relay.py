"""
Relais de l'exploration vers le hub (#636).

Quand ``CICADA_EXPLORATION_SOURCE`` vaut ``hub``, les vues d'exploration ne
lisent plus l'index local : elles transmettent la requête au hub et renvoient sa
réponse telle quelle.

## Pourquoi le backend relaie plutôt que le navigateur n'appelle le hub

Trois raisons, dans cet ordre :

1. **le jeton reste côté serveur** — un appel direct depuis le navigateur
   l'exposerait à quiconque ouvre les outils de développement ;
2. **pas de CORS ni de second domaine à déclarer** dans le déploiement ;
3. **la bascule est invisible pour le frontend** — même URL, même forme de
   réponse. C'est ce qui permet de revenir en arrière par un simple réglage.

## Pourquoi il n'y a pas de repli sur l'index local

Un repli silencieux servirait des résultats *partiels* — ceux de cette instance
seulement — sous une interface qui promet une recherche transverse. L'utilisateur
n'aurait aucun moyen de savoir que les plans des autres organismes manquent, et
conclurait qu'ils n'existent pas. Une erreur franche est moins nuisible qu'une
réponse incomplète qui se fait passer pour complète.
"""

import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

#: L'exploration est une interface interactive : on préfère échouer vite plutôt
#: que laisser tourner une roue pendant une minute.
DELAI = 30


def relais_actif():
    """Vrai si l'exploration doit être servie par le hub."""
    return (
        settings.CICADA_EXPLORATION_SOURCE == 'hub'
        and bool(settings.CICADA_HUB_URL)
    )


def relayer(chemin, params=None):
    """
    Transmet une requête de lecture au hub et renvoie sa réponse.

    Les paramètres sont transmis **tels quels** : les facettes, le tri et la
    pagination portent les mêmes noms des deux côtés, précisément pour que ce
    relais n'ait rien à traduire. Toute traduction ici serait un endroit de plus
    où les deux implémentations peuvent diverger.
    """
    url = f"{settings.CICADA_HUB_URL}{chemin}"
    try:
        reponse = requests.get(
            url,
            params=dict(params.lists()) if hasattr(params, 'lists') else params,
            headers={'X-Hub-Token': settings.CICADA_HUB_READ_TOKEN},
            timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.error("Hub d'exploration injoignable (%s) : %s", url, erreur)
        return Response(
            {
                'detail': (
                    "L'exploration centralisée est momentanément indisponible. "
                    "Les résultats ne peuvent pas être affichés."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if reponse.status_code >= 500:
        logger.error(
            "Hub d'exploration en erreur (%s) : %s", url, reponse.status_code
        )
        return Response(
            {'detail': "L'exploration centralisée a renvoyé une erreur."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    try:
        corps = reponse.json()
    except ValueError:
        return Response(
            {'detail': "Réponse illisible de l'exploration centralisée."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(corps, status=reponse.status_code)


def reference_plan(identifiant):
    """
    Complète un identifiant de plan en référence « instance:slug ».

    Le frontend navigue encore par slug seul, hérité de l'époque où tous les
    plans étaient locaux. Un slug nu est donc interprété comme désignant un plan
    **de cette instance** — ce qui est vrai de tous les liens existants. Les
    tuiles servies par le hub portent déjà une `reference` complète, que le
    frontend transmettra telle quelle quand il l'utilisera.

    Cette tolérance disparaîtra avec l'index local.
    """
    if ':' in identifiant:
        return identifiant
    return f"{settings.CICADA_INSTANCE_ID}:{identifiant}"
