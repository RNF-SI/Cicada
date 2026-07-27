"""
Calcul du rattachement administratif des sites (département / région).

Un site est rattaché aux départements que sa géométrie intersecte, puis aux
régions de ces départements. Deux cas particuliers sont traités :

- **site sans polygone** : on retombe sur le point de référence ``geom_pt`` ;
- **site sans intersection terrestre** (réserve marine, géométrie approximative
  au large) : on rattache au département le plus proche, dans la limite de
  :data:`NEAREST_MAX_DEGREES`, en marquant le lien ``source='nearest'`` pour que
  l'approximation reste traçable. Au-delà de cette limite le site n'est rattaché
  à rien, ce qui vaut mieux qu'un rattachement arbitraire.
"""

import logging

from django.contrib.gis.db.models.functions import Distance
from django.db import transaction

from .models import AreaType, CorSiteArea, LArea

logger = logging.getLogger(__name__)

#: Distance maximale (en degrés, ~110 km) au-delà de laquelle on renonce à
#: rattacher un site sans intersection terrestre à un département.
NEAREST_MAX_DEGREES = 1.0


def _site_geometry(site):
    """Géométrie de référence d'un site : son polygone, sinon son point."""
    return site.geom or site.geom_pt


def compute_areas_for_site(site):
    """
    Retourne les rattachements calculés pour un site, sans rien écrire.

    :returns: liste de tuples ``(LArea, source)``.
    """
    geom = _site_geometry(site)
    if geom is None:
        return []

    departements = list(
        LArea.objects.filter(
            id_type__type_code=AreaType.DEPARTEMENT,
            enable=True,
            geom__intersects=geom,
        ).select_related('parent')
    )
    source = CorSiteArea.SOURCE_INTERSECT

    if not departements:
        # `dwithin` sur un champ 4326 raisonne en degrés, ce qui borne la
        # recherche sans avoir à interpréter l'unité de la distance annotée.
        nearest = (
            LArea.objects.filter(
                id_type__type_code=AreaType.DEPARTEMENT,
                enable=True,
                geom__dwithin=(geom, NEAREST_MAX_DEGREES),
            )
            .annotate(distance=Distance('geom', geom))
            .order_by('distance')
            .select_related('parent')
            .first()
        )
        if nearest is None:
            return []
        departements = [nearest]
        source = CorSiteArea.SOURCE_NEAREST

    resultats = [(dep, source) for dep in departements]

    # Les régions correspondantes, dédoublonnées.
    regions = {}
    for dep in departements:
        if dep.parent_id and dep.parent_id not in regions:
            regions[dep.parent_id] = dep.parent
    resultats.extend((region, source) for region in regions.values())

    return resultats


@transaction.atomic
def refresh_site_areas(site):
    """
    Recalcule et réécrit les rattachements d'un site. Retourne leur nombre.
    """
    calcules = compute_areas_for_site(site)

    CorSiteArea.objects.filter(id_site=site).exclude(
        source=CorSiteArea.SOURCE_MANUAL
    ).delete()

    manuels = set(
        CorSiteArea.objects.filter(
            id_site=site, source=CorSiteArea.SOURCE_MANUAL
        ).values_list('id_area_id', flat=True)
    )

    CorSiteArea.objects.bulk_create(
        [
            CorSiteArea(id_site=site, id_area=area, source=source)
            for area, source in calcules
            if area.pk not in manuels
        ],
        ignore_conflicts=True,
    )
    return len(calcules)


def refresh_all_site_areas(queryset=None, stdout=None):
    """
    Recalcule les rattachements de tous les sites (ou d'un queryset donné).

    :returns: dict de statistiques ``{sites, rattaches, sans_geometrie, orphelins}``.
    """
    from apps.users.models import Site

    if queryset is None:
        queryset = Site.objects.all()

    stats = {'sites': 0, 'rattaches': 0, 'sans_geometrie': 0, 'orphelins': 0}

    for site in queryset.iterator():
        stats['sites'] += 1
        if _site_geometry(site) is None:
            stats['sans_geometrie'] += 1
            CorSiteArea.objects.filter(id_site=site).exclude(
                source=CorSiteArea.SOURCE_MANUAL
            ).delete()
            continue

        nb = refresh_site_areas(site)
        if nb:
            stats['rattaches'] += 1
        else:
            stats['orphelins'] += 1
            logger.warning(
                "Site %s (%s) : aucune zone administrative trouvée",
                site.pk, site.nom_site,
            )
            if stdout:
                stdout.write(
                    f"  ! {site.nom_site} : aucune zone administrative trouvée"
                )

    return stats
