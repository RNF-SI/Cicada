"""
Signals Django pour les plans de gestion.
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_delete, sender='plans.CorFacteurEnjeu')
def delete_orphaned_facteur_influence(sender, instance, **kwargs):
    """Supprime un facteur d'influence qui n'est plus rattaché à aucun enjeu (#552).

    Depuis le passage au partage M2M, `FacteurInfluence` n'a plus de FK vers
    `Enjeu` : plus rien ne le cascade. Supprimer un enjeu (ou un plan entier)
    n'effaçait donc que les liaisons, laissant derrière le facteur ET tout son
    sous-arbre (pressions → OO → RA → indicateurs).

    On raisonne sur la liaison plutôt que sur l'enjeu, ce qui couvre tous les
    chemins (suppression d'enjeu, de plan, ou simple retrait du facteur d'un
    enjeu) : dès qu'une liaison disparaît, le facteur n'est supprimé que s'il ne
    reste rattaché à aucun autre enjeu — un facteur partagé survit donc à la
    suppression de l'un de ses enjeux, ce qui est tout l'intérêt de #552.
    """
    from django.db.models import QuerySet

    from .models_enjeux import CorFacteurEnjeu, FacteurInfluence

    facteur_id = instance.id_facteur_influence_id
    if facteur_id is None:
        return

    # Le facteur est lui-même à l'origine de la suppression : Django efface ses
    # liaisons (cascade) puis le facteur. Sans ce garde-fou on le supprimerait
    # ici, sous les pieds du collector, qui ne trouverait plus rien à effacer.
    origin = kwargs.get('origin')
    origin_model = origin.model if isinstance(origin, QuerySet) else type(origin)
    if origin_model is FacteurInfluence:
        return

    if CorFacteurEnjeu.objects.filter(id_facteur_influence_id=facteur_id).exists():
        return

    logger.debug(
        "Suppression du facteur d'influence orphelin %s (plus aucun enjeu lié)",
        facteur_id,
    )
    FacteurInfluence.objects.filter(pk=facteur_id).delete()
