"""
Modèles pour le référentiel des habitats HabRef (INPN).

Schema PostgreSQL : ref_habitats
Compatible avec l'architecture GeoNature.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Typoref(models.Model):
    """Typologies d'habitats (EUNIS, Corine Biotope, etc.)."""

    cd_typo = models.IntegerField(_("Code typologie"), primary_key=True)
    cd_table = models.CharField(
        _("Code table"), max_length=255, null=True, blank=True
    )
    lb_typo = models.TextField(
        _("Libellé typologie"), null=True, blank=True
    )
    nom_jeu_donnees = models.TextField(
        _("Nom du jeu de données"), null=True, blank=True
    )
    date_creation = models.TextField(
        _("Date de création"), null=True, blank=True
    )
    date_mise_jour = models.TextField(
        _("Date de mise à jour"), null=True, blank=True
    )
    auteur_jeu_donnees = models.TextField(
        _("Auteur"), null=True, blank=True
    )
    territoire = models.TextField(
        _("Territoire"), null=True, blank=True
    )

    class Meta:
        db_table = '"ref_habitats"."typoref"'
        managed = True
        verbose_name = _("Typologie d'habitats")
        verbose_name_plural = _("Typologies d'habitats")

    def __str__(self):
        return self.lb_typo or f"Typo {self.cd_typo}"


class Habref(models.Model):
    """
    Table principale du référentiel HabRef.

    Clé primaire : cd_hab.
    Hiérarchie via cd_hab_sup.
    """

    cd_hab = models.IntegerField(_("Code habitat"), primary_key=True)
    fg_validite = models.CharField(
        _("Flag validité"), max_length=50, null=True, blank=True
    )
    cd_typo = models.IntegerField(
        _("Code typologie"),
        null=True,
        blank=True,
        db_index=True,
    )
    lb_code = models.CharField(
        _("Code label"), max_length=255, null=True, blank=True
    )
    lb_hab_fr = models.CharField(
        _("Nom français"), max_length=1000, null=True, blank=True
    )
    lb_hab_fr_complet = models.TextField(
        _("Nom français complet"), null=True, blank=True
    )
    lb_hab_en = models.CharField(
        _("Nom anglais"), max_length=1000, null=True, blank=True
    )
    lb_auteur = models.CharField(
        _("Auteur"), max_length=500, null=True, blank=True
    )
    niveau = models.IntegerField(
        _("Niveau hiérarchique"), null=True, blank=True
    )
    lb_description = models.TextField(
        _("Description"), null=True, blank=True
    )
    cd_hab_sup = models.IntegerField(
        _("Code habitat supérieur"),
        null=True,
        blank=True,
        db_index=True,
    )
    path_cd_hab = models.CharField(
        _("Chemin hiérarchique"), max_length=500, null=True, blank=True
    )
    cd_corresp_encours = models.CharField(
        _("Correspondance en cours"), max_length=500, null=True, blank=True
    )
    date_creation = models.CharField(
        _("Date de création"), max_length=50, null=True, blank=True
    )
    date_maj = models.CharField(
        _("Date de mise à jour"), max_length=50, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_habitats"."habref"'
        managed = True
        verbose_name = _("Habitat (HabRef)")
        verbose_name_plural = _("Habitats (HabRef)")

    def __str__(self):
        return self.lb_hab_fr or f"cd_hab={self.cd_hab}"


class HabrefCorrespHab(models.Model):
    """Correspondances entre typologies d'habitats."""

    id = models.AutoField(primary_key=True)
    cd_hab = models.IntegerField(
        _("Code habitat"), db_index=True
    )
    cd_hab_entre = models.IntegerField(
        _("Code habitat correspondant"),
        null=True,
        blank=True,
        db_index=True,
    )
    cd_typo_entre = models.IntegerField(
        _("Code typologie correspondante"), null=True, blank=True
    )
    lb_code_entre = models.CharField(
        _("Code label correspondant"), max_length=255, null=True, blank=True
    )
    lb_hab_entre = models.CharField(
        _("Nom habitat correspondant"), max_length=1000, null=True, blank=True
    )
    niveau_entre = models.IntegerField(
        _("Niveau correspondant"), null=True, blank=True
    )
    type_rel = models.CharField(
        _("Type de relation"), max_length=100, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_habitats"."habref_corresp_hab"'
        managed = True
        verbose_name = _("Correspondance habitat")
        verbose_name_plural = _("Correspondances habitats")


class HabrefCorrespTaxon(models.Model):
    """Correspondances habitat-taxon."""

    id = models.AutoField(primary_key=True)
    cd_hab = models.IntegerField(
        _("Code habitat"), db_index=True
    )
    cd_nom = models.IntegerField(
        _("Code nom taxon"), null=True, blank=True, db_index=True
    )
    nom_cite = models.CharField(
        _("Nom cité"), max_length=500, null=True, blank=True
    )

    class Meta:
        db_table = '"ref_habitats"."habref_corresp_taxon"'
        managed = True
        verbose_name = _("Correspondance habitat-taxon")
        verbose_name_plural = _("Correspondances habitats-taxons")


class AutocompleteHabitat(models.Model):
    """
    Table dénormalisée pour l'autocomplete des habitats.

    Indexée avec pg_trgm pour la recherche floue.
    Générée par la commande import_habref.
    """

    cd_hab = models.IntegerField(_("Code habitat"), primary_key=True)
    cd_typo = models.IntegerField(
        _("Code typologie"), null=True, blank=True, db_index=True
    )
    lb_code = models.CharField(
        _("Code label"), max_length=255, null=True, blank=True
    )
    search_name = models.TextField(_("Nom de recherche"))
    lb_hab_fr = models.CharField(
        _("Nom français"), max_length=1000, null=True, blank=True
    )
    lb_hab_fr_complet = models.TextField(
        _("Nom français complet"), null=True, blank=True
    )
    lb_typo = models.CharField(
        _("Libellé typologie"), max_length=500, null=True, blank=True
    )
    niveau = models.IntegerField(
        _("Niveau hiérarchique"), null=True, blank=True
    )

    class Meta:
        db_table = '"ref_habitats"."autocomplete_habitat"'
        managed = True
        verbose_name = _("Autocomplete habitat")
        verbose_name_plural = _("Autocomplete habitats")

    def __str__(self):
        return self.search_name or f"cd_hab={self.cd_hab}"
