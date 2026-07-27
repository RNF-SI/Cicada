"""
Maintien du rattachement administratif des sites.

Le rattachement est recalculé à la création d'un site et à chaque modification
de sa géométrie. Sur les autres champs (nom, surface, type…) rien n'est
recalculé : la comparaison des géométries en `pre_save` évite un travail
spatial inutile à chaque enregistrement.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.users.models import Site

from .services import refresh_site_areas

logger = logging.getLogger(__name__)

#: Attribut posé par `pre_save` et lu par `post_save`.
_GEOM_CHANGED = '_geo_geometry_changed'


def _geom_signature(site):
    """Signature comparable des deux géométries d'un site."""
    return (
        site.geom.ewkb if site.geom else None,
        site.geom_pt.ewkb if site.geom_pt else None,
    )


@receiver(pre_save, sender=Site)
def track_site_geometry_change(sender, instance, **kwargs):
    """Note si la géométrie du site change, pour `post_save`."""
    if instance.pk is None:
        setattr(instance, _GEOM_CHANGED, True)
        return

    ancien = (
        Site.objects.filter(pk=instance.pk)
        .only('geom', 'geom_pt')
        .first()
    )
    setattr(
        instance,
        _GEOM_CHANGED,
        ancien is None or _geom_signature(ancien) != _geom_signature(instance),
    )


@receiver(post_save, sender=Site)
def refresh_site_areas_on_geometry_change(sender, instance, **kwargs):
    """Recalcule le rattachement administratif du site si besoin."""
    if not getattr(instance, _GEOM_CHANGED, False):
        return
    setattr(instance, _GEOM_CHANGED, False)

    try:
        refresh_site_areas(instance)
    except Exception:
        # Un référentiel géographique absent ou une géométrie invalide ne doit
        # jamais empêcher l'enregistrement d'un site : le rattachement pourra
        # être rejoué avec `refresh_site_areas --missing`.
        logger.exception(
            "Échec du calcul du rattachement administratif du site %s",
            instance.pk,
        )
