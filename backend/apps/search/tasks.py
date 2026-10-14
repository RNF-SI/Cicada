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
    # Importé ici : la tâche est enregistrée au démarrage du worker, avant que
    # la base (où vit une adhésion acceptée, #696) soit forcément joignable.
    from apps.search.raccordement import hub_url, jeton_depot, raccordement

    if not settings.CICADA_HUB_PUSH_AUTO:
        return False
    ligne = raccordement()
    return bool(hub_url(ligne) and jeton_depot(ligne))


def _ignoree(message):
    """
    Trace une nuit sans publication (#698).

    Sans cette ligne, l'historique d'une instance mal configurée resterait
    vide, et rien ne distinguerait « jamais tenté » de « tenté et retenu ».
    """
    from apps.search.models import PublicationHub

    PublicationHub.enregistrer(
        PublicationHub.ORIGINE_NUIT, PublicationHub.RESULTAT_IGNOREE, message=message,
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
        _ignoree("Publication non configurée (hub, jeton de dépôt ou publication automatique).")
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
        _ignoree("Partage avec l'exploration nationale désactivé.")
        return "partage désactivé"

    sortie = io.StringIO()
    try:
        # `origine` : c'est la commande qui écrit l'historique (#698), réussite
        # comme échec — la tâche n'a donc rien à enregistrer ici.
        call_command('push_federation', origine='nuit', stdout=sortie, stderr=sortie)
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


@shared_task
def actualiser_adhesion_hub():
    """
    Relit auprès du suivi une demande d'adhésion au hub en cours (#696) :
    en attente, ou dont le code de confirmation a été envoyé.

    Les décisions de RNF (envoi du code, refus) se prennent ailleurs, dans
    l'admin de l'API de suivi : sans cette relecture, l'instance ne les
    apprendrait qu'à la prochaine visite d'un super administrateur sur la page
    des paramètres. Hors demande en cours, rien à faire — pas même un appel
    réseau.
    """
    from apps.search.raccordement import (
        STATUTS_A_ACTUALISER, actualiser_adhesion, raccordement,
    )

    ligne = raccordement()
    if ligne.adhesion_statut not in STATUTS_A_ACTUALISER:
        return "rien à actualiser"
    erreur = actualiser_adhesion(ligne)
    return erreur or ligne.adhesion_statut


@shared_task(soft_time_limit=7200, time_limit=7500)
def publier_apres_consentement():
    """
    Republie dès que la structure recoche le partage (ou le coche).

    Distincte de la publication de nuit sur deux points : elle ignore
    ``CICADA_HUB_PUSH_AUTO`` — ce n'est pas une automatisation mais la suite
    immédiate d'une décision prise à l'écran —, et elle s'inscrit comme
    publication manuelle. Le consentement est relu ici, au moment d'agir : s'il a
    été retiré entre-temps, rien ne part.
    """
    from apps.search.push import partage_active
    from apps.search.raccordement import retrait_possible

    if not (partage_active() and retrait_possible()):
        return "rien à publier"
    sortie = io.StringIO()
    try:
        call_command('push_federation', origine='manuelle', stdout=sortie, stderr=sortie)
    except Exception:
        # Consigné par la commande dans l'historique ; la nuit reprendra.
        logger.exception("Échec de la publication après consentement :\n%s", sortie.getvalue())
        raise
    return sortie.getvalue()


@shared_task
def relancer_retrait_hub():
    """
    Relance le retrait du hub tant qu'il est en attente.

    Un consentement retiré alors que le hub était injoignable laisse les plans
    de l'instance publiés — et, par la réciprocité, son accès à l'exploration
    nationale ouvert. Chaque heure, tant que le drapeau est levé, on réessaie.
    Hors attente : rien, pas même un appel réseau. Si la structure a recoché
    le partage entre-temps, le retrait n'a plus d'objet.
    """
    from apps.search.models import PublicationHub
    from apps.search.push import partage_active
    from apps.search.raccordement import ErreurRaccordement, raccordement, retirer_du_hub

    ligne = raccordement()
    if not ligne.retrait_en_attente:
        return "rien à retirer"
    if partage_active():
        ligne.retrait_en_attente = False
        ligne.save()
        return "partage réactivé"
    try:
        purges = retirer_du_hub(PublicationHub.ORIGINE_RELANCE)
    except ErreurRaccordement as erreur:
        logger.warning("Retrait du hub toujours impossible : %s", erreur.message)
        return f"en attente : {erreur.cle}"
    return f"{purges} plan(s) retiré(s)"
