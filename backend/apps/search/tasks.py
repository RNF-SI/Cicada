"""
Publication périodique vers le hub d'exploration fédérée (#636).

La publication dépose **l'état complet** de l'index : elle n'a donc pas besoin
d'être fréquente, et rien ne se perd si une exécution est sautée — la suivante
repart de l'état courant. Une fois par nuit suffit : le contenu d'un plan validé
est verrouillé en lecture seule (#248), ce qui bouge d'un jour à l'autre ce sont
les libellés joints (nom d'un site, d'un organisme) et l'entrée ou la sortie
d'un plan du périmètre explorable.
"""

import io
import logging

from celery import shared_task
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)


def _publication_configuree():
    """
    Cette instance est-elle en état de publier — et l'a-t-elle voulu ?

    Trois conditions, et elles ne disent pas la même chose :

    - un hub et un jeton de dépôt : la mécanique est branchée ;
    - ``CICADA_HUB_PUSH_AUTO`` : l'exploitant accepte que ce soit automatique.
      Distinct des deux premiers, parce qu'une instance peut légitimement
      *lire* l'exploration nationale (ce qui exige l'URL du hub) sans vouloir y
      publier autrement qu'à la main.

    Le consentement de la structure (``SiteConfiguration.federation_partage``)
    est vérifié séparément, juste avant l'appel : il vit en base et peut changer
    entre deux exécutions.
    """
    return bool(
        settings.CICADA_HUB_URL
        and settings.CICADA_HUB_PUSH_TOKEN
        and settings.CICADA_HUB_PUSH_AUTO
    )


# Deux heures, contre trente minutes pour les autres tâches : une publication
# complète envoie une page par tranche de dix plans, chacune portant les fiches
# rendues. Un worker tué en cours de dépôt laisse un lot ouvert et jamais
# basculé — sans danger (la publication précédente reste en place), mais la nuit
# est perdue.
@shared_task(soft_time_limit=7200, time_limit=7500)
def publier_vers_le_hub():
    """Dépose l'état complet de l'index sur le hub."""
    if not _publication_configuree():
        logger.debug(
            "Publication vers le hub non configurée sur cette instance — ignorée."
        )
        return "non configurée"

    # Importé ici et non au chargement du module : la tâche est enregistrée au
    # démarrage du worker, bien avant que la base soit forcément joignable.
    from apps.search.push import partage_active

    if not partage_active():
        # Pas une erreur : le partage est un engagement de la structure, qui
        # peut être retiré à tout moment depuis l'interface. Une tâche planifiée
        # qui échouerait bruyamment à chaque nuit ferait passer une décision
        # assumée pour une panne.
        logger.info(
            "Partage avec l'exploration nationale désactivé — rien n'est publié."
        )
        return "partage désactivé"

    sortie = io.StringIO()
    try:
        call_command('push_federation', stdout=sortie, stderr=sortie)
    except Exception:
        # La commande abandonne son lot avant de remonter : la publication
        # précédente est intacte. On journalise et on laisse la nuit suivante
        # reprendre, plutôt que de réessayer en boucle sur un hub peut-être
        # indisponible pour la journée.
        logger.exception(
            "Échec de la publication vers le hub :\n%s", sortie.getvalue()
        )
        raise

    resultat = sortie.getvalue()
    logger.info("Publication vers le hub terminée :\n%s", resultat)
    return resultat
