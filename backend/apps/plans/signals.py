"""
Signals Django pour les plans de gestion.
"""
import logging

from django.db.models.signals import m2m_changed, post_delete, post_save
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


@receiver(post_save, sender='plans.CorRolePlan')
def rattacher_organisme_du_redacteur_membre(sender, instance, created, **kwargs):
    """#714 — un rédacteur externe rattaché au plan rend son organisme rédacteur."""
    if kwargs.get('raw'):
        return
    from .redacteurs import rattacher_organisme_redacteur

    rattacher_organisme_redacteur(instance.plan_de_gestion, instance.id_role)


def rattacher_organisme_du_redacteur_referent(sender, instance, action, pk_set, reverse, **kwargs):
    """#714 — même règle pour le M2M ``PlanGestion.referents``."""
    if action != 'post_add' or not pk_set:
        return
    from apps.users.models import Role

    from .models import PlanGestion
    from .redacteurs import rattacher_organisme_redacteur

    if reverse:
        # ``role.plans_referents.add(plan)`` : instance = utilisateur
        for plan in PlanGestion.objects.filter(pk__in=pk_set):
            rattacher_organisme_redacteur(plan, instance)
    else:
        for user in Role.objects.filter(pk__in=pk_set, role_level='redacteur'):
            rattacher_organisme_redacteur(instance, user)


def _connecter_referents():
    from .models import PlanGestion

    m2m_changed.connect(
        rattacher_organisme_du_redacteur_referent,
        sender=PlanGestion.referents.through,
        dispatch_uid='plans_rattacher_organisme_redacteur_referent',
    )


_connecter_referents()
