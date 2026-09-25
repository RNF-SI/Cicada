"""
Référentiel géographique administratif (régions, départements).

Reprise du schéma ``ref_geo`` de CICADA, **amputée de ``cor_site_area``** : ce
rattachement lie une zone à un site, or le hub n'héberge aucun site. Les
documents qu'il reçoit arrivent avec leurs zones déjà résolues par l'instance
émettrice, sous forme de codes INSEE.

Pourquoi ce référentiel est ici plutôt que transmis avec les documents : le
découpage administratif est **national et identique dans toutes les instances**.
Seuls les identifiants techniques (`id_area`) diffèrent d'une base à l'autre,
pas les codes. Les documents voyagent donc en codes, et c'est le hub qui les
retraduit — ce qui lui permet aussi de proposer la liste complète des régions et
départements dans les facettes, y compris ceux qu'aucun plan publié ne touche
encore.

Le fichier source des contours est **le même que celui de CICADA**, monté en
lecture seule (cf. ``docker-compose.hub.yml``). Les faire diverger casserait la
résolution des codes.
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
            # C'est cette contrainte qui fait de `(type, code)` une clé stable
            # entre instances, et donc ce qui autorise les documents à voyager
            # en codes plutôt qu'en identifiants.
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
