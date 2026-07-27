"""
Référentiel géographique administratif (régions, départements).

Schéma PostgreSQL : ``ref_geo``, structuré comme celui de GeoNature
(``bib_areas_types`` + ``l_areas``) pour rester interopérable, avec deux écarts
assumés :

- les géométries sont stockées en EPSG:4326 comme le reste de Cicada
  (``Site.geom``), alors que GeoNature les stocke dans le SRID local ;
- ``LArea.parent`` matérialise le lien département → région, absent de GeoNature,
  mais nécessaire au filtre « zone géographique » de l'exploration des données,
  qui est un arbre à deux niveaux.

Le rattachement d'un site à ses zones administratives est calculé par
intersection PostGIS et matérialisé dans :class:`CorSiteArea` : le recalculer à
chaque requête de recherche coûterait bien plus cher que de le maintenir.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _


class AreaType(models.Model):
    """Type de zone géographique (région, département)."""

    REGION = 'REG'
    DEPARTEMENT = 'DEP'

    id_type = models.AutoField(primary_key=True)
    type_code = models.CharField(_("Code du type"), max_length=25, unique=True)
    type_name = models.CharField(_("Nom du type"), max_length=200)
    type_desc = models.TextField(_("Description"), null=True, blank=True)

    class Meta:
        db_table = '"ref_geo"."bib_areas_types"'
        verbose_name = _("Type de zone géographique")
        verbose_name_plural = _("Types de zones géographiques")

    def __str__(self):
        return self.type_name


class LArea(models.Model):
    """Zone géographique administrative (une région ou un département)."""

    id_area = models.AutoField(primary_key=True)
    id_type = models.ForeignKey(
        AreaType,
        on_delete=models.CASCADE,
        db_column='id_type',
        related_name='areas',
        verbose_name=_("Type de zone"),
    )
    area_code = models.CharField(_("Code"), max_length=25)
    area_name = models.CharField(_("Nom"), max_length=250)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        db_column='id_area_parent',
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Zone parente"),
        help_text=_("Région de rattachement, pour un département."),
    )
    geom = gis_models.MultiPolygonField(_("Géométrie"), srid=4326)
    centroid = gis_models.PointField(
        _("Centroïde"), srid=4326, null=True, blank=True
    )
    enable = models.BooleanField(_("Actif"), default=True)

    class Meta:
        db_table = '"ref_geo"."l_areas"'
        verbose_name = _("Zone géographique")
        verbose_name_plural = _("Zones géographiques")
        constraints = [
            models.UniqueConstraint(
                fields=['id_type', 'area_code'],
                name='uq_l_areas_type_code',
            ),
        ]
        indexes = [
            models.Index(fields=['area_code'], name='idx_l_areas_code'),
        ]

    def __str__(self):
        return f"{self.area_code} — {self.area_name}"


class CorSiteArea(models.Model):
    """
    Rattachement administratif d'un site, calculé par intersection PostGIS.

    Une ligne par couple (site, zone). Un site est rattaché à ses départements
    d'intersection **et** aux régions correspondantes, afin que le filtre de
    l'exploration puisse interroger indifféremment l'un ou l'autre niveau.
    """

    SOURCE_INTERSECT = 'intersect'
    SOURCE_NEAREST = 'nearest'
    SOURCE_MANUAL = 'manual'
    SOURCE_CHOICES = [
        (SOURCE_INTERSECT, _("Intersection géométrique")),
        (SOURCE_NEAREST, _("Zone la plus proche")),
        (SOURCE_MANUAL, _("Saisie manuelle")),
    ]

    id = models.AutoField(primary_key=True)
    id_site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        db_column='id_site',
        related_name='areas',
        verbose_name=_("Site"),
    )
    id_area = models.ForeignKey(
        LArea,
        on_delete=models.CASCADE,
        db_column='id_area',
        related_name='sites',
        verbose_name=_("Zone géographique"),
    )
    source = models.CharField(
        _("Origine du rattachement"),
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_INTERSECT,
        help_text=_(
            "« Zone la plus proche » signale un site sans intersection terrestre "
            "(site marin, ou géométrie approximative rattachée par proximité)."
        ),
    )

    class Meta:
        db_table = '"ref_geo"."cor_site_area"'
        verbose_name = _("Rattachement site / zone géographique")
        verbose_name_plural = _("Rattachements sites / zones géographiques")
        constraints = [
            models.UniqueConstraint(
                fields=['id_site', 'id_area'],
                name='uq_cor_site_area',
            ),
        ]

    def __str__(self):
        return f"{self.id_site_id} → {self.id_area_id}"
