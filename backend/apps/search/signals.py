"""
Maintien de l'index de recherche.

L'index suit le **cycle de vie du plan**, pas ses écritures de contenu : un plan
n'est indexable qu'une fois validé, et le contenu d'un plan validé est
verrouillé (#248). Deux évènements suffisent donc :

- un changement de statut (validation, archivage, retour en brouillon) →
  réindexation ou désindexation complète ;
- une modification des sites du plan ou de sa période → mise à jour des seules
  facettes, ces opérations restant permises après validation.

Toute erreur d'indexation est journalisée sans être propagée : une recherche
temporairement incomplète est un moindre mal comparé à une validation de plan
qui échoue. `rebuild_search_index` permet de rattraper.
"""

import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.plans.models import CorSitePg, PlanGestion

from .indexing import rafraichir_facettes, synchroniser_plan

logger = logging.getLogger(__name__)

_ETAT_PRECEDENT = '_search_etat_precedent'


@receiver(pre_save, sender=PlanGestion)
def track_plan_indexation_state(sender, instance, **kwargs):
    """Mémorise le statut et la période d'avant enregistrement."""
    if instance.pk is None:
        setattr(instance, _ETAT_PRECEDENT, None)
        return

    ancien = (
        PlanGestion.objects.filter(pk=instance.pk)
        .values('statut', 'annee_debut', 'annee_fin')
        .first()
    )
    setattr(instance, _ETAT_PRECEDENT, ancien)


@receiver(post_save, sender=PlanGestion)
def sync_plan_index(sender, instance, created, **kwargs):
    """Réindexe le plan quand son statut change, sinon rafraîchit ses facettes."""
    ancien = getattr(instance, _ETAT_PRECEDENT, None)
    setattr(instance, _ETAT_PRECEDENT, None)

    try:
        if created or ancien is None or ancien['statut'] != instance.statut:
            synchroniser_plan(instance)
        elif (
            ancien['annee_debut'] != instance.annee_debut
            or ancien['annee_fin'] != instance.annee_fin
        ):
            rafraichir_facettes(instance)
    except Exception:
        logger.exception(
            "Échec de la synchronisation de l'index de recherche pour le plan %s",
            instance.pk,
        )


@receiver(post_save, sender=CorSitePg)
@receiver(post_delete, sender=CorSitePg)
def sync_facettes_on_site_change(sender, instance, **kwargs):
    """Un site ajouté ou retiré change la zone géographique et les gestionnaires."""
    try:
        rafraichir_facettes(instance.plan_de_gestion)
    except PlanGestion.DoesNotExist:
        # Le plan est en cours de suppression : ses lignes d'index partent en
        # CASCADE, il n'y a rien à rafraîchir.
        pass
    except Exception:
        logger.exception(
            "Échec du rafraîchissement des facettes de recherche du plan %s",
            instance.plan_de_gestion_id,
        )
