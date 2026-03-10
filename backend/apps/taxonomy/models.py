"""
Modèles pour le référentiel taxonomique TaxRef (INPN).

Schema PostgreSQL : taxonomie
Compatible avec l'architecture GeoNature.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BibTaxrefRang(models.Model):
    """Rangs taxonomiques (famille, genre, espèce, etc.)."""

    id_rang = models.CharField(
        _("Code rang"),
        max_length=10,
        primary_key=True,
    )
    nom_rang = models.CharField(_("Nom du rang"), max_length=100)
    tri_rang = models.IntegerField(_("Ordre de tri"), null=True, blank=True)

    class Meta:
        db_table = '"taxonomie"."bib_taxref_rangs"'
        managed = True
        verbose_name = _("Rang taxonomique")
        verbose_name_plural = _("Rangs taxonomiques")

    def __str__(self):
        return self.nom_rang


class BibTaxrefHabitat(models.Model):
    """Types d'habitats associés aux taxons."""

    id_habitat = models.IntegerField(_("Code habitat"), primary_key=True)
    nom_habitat = models.CharField(_("Nom de l'habitat"), max_length=255)

    class Meta:
        db_table = '"taxonomie"."bib_taxref_habitats"'
        managed = True
        verbose_name = _("Type d'habitat TaxRef")
        verbose_name_plural = _("Types d'habitats TaxRef")

    def __str__(self):
        return self.nom_habitat


class BibTaxrefStatut(models.Model):
    """Statuts taxonomiques (valide, synonyme, etc.)."""

    id_statut = models.CharField(
        _("Code statut"),
        max_length=50,
        primary_key=True,
    )
    nom_statut = models.CharField(_("Nom du statut"), max_length=255)

    class Meta:
        db_table = '"taxonomie"."bib_taxref_statuts"'
        managed = True
        verbose_name = _("Statut taxonomique")
        verbose_name_plural = _("Statuts taxonomiques")

    def __str__(self):
        return self.nom_statut


class Taxref(models.Model):
    """
    Table principale du référentiel TaxRef (INPN).

    Clé primaire : cd_nom (identifiant unique du taxon).
    cd_ref pointe vers le nom de référence (peut être = cd_nom si c'est déjà le nom valide).
    """

    cd_nom = models.IntegerField(_("Code nom"), primary_key=True)
    id_statut = models.CharField(
        _("Statut"),
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )
    id_habitat = models.IntegerField(
        _("Habitat"),
        null=True,
        blank=True,
    )
    id_rang = models.CharField(
        _("Rang"),
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
    )
    regne = models.CharField(
        _("Règne"), max_length=50, null=True, blank=True, db_index=True
    )
    phylum = models.CharField(
        _("Phylum"), max_length=50, null=True, blank=True
    )
    classe = models.CharField(
        _("Classe"), max_length=50, null=True, blank=True
    )
    ordre = models.CharField(
        _("Ordre"), max_length=50, null=True, blank=True
    )
    famille = models.CharField(
        _("Famille"), max_length=50, null=True, blank=True
    )
    sous_famille = models.CharField(
        _("Sous-famille"), max_length=50, null=True, blank=True
    )
    tribu = models.CharField(
        _("Tribu"), max_length=50, null=True, blank=True
    )
    cd_taxsup = models.IntegerField(
        _("Code taxon supérieur"), null=True, blank=True
    )
    cd_sup = models.IntegerField(
        _("Code supérieur"), null=True, blank=True
    )
    cd_ref = models.IntegerField(
        _("Code référence"),
        null=True,
        blank=True,
        db_index=True,
    )
    lb_nom = models.CharField(
        _("Nom latin"), max_length=500, null=True, blank=True
    )
    lb_auteur = models.CharField(
        _("Auteur"), max_length=500, null=True, blank=True
    )
    nom_complet = models.CharField(
        _("Nom complet"), max_length=500, null=True, blank=True
    )
    nom_complet_html = models.CharField(
        _("Nom complet HTML"), max_length=500, null=True, blank=True
    )
    nom_valide = models.CharField(
        _("Nom valide"), max_length=500, null=True, blank=True
    )
    nom_vern = models.TextField(
        _("Nom vernaculaire"), null=True, blank=True
    )
    nom_vern_eng = models.TextField(
        _("Nom vernaculaire anglais"), null=True, blank=True
    )
    group1_inpn = models.CharField(
        _("Groupe 1 INPN"), max_length=100, null=True, blank=True
    )
    group2_inpn = models.CharField(
        _("Groupe 2 INPN"),
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )
    group3_inpn = models.CharField(
        _("Groupe 3 INPN"), max_length=100, null=True, blank=True
    )
    url = models.TextField(
        _("URL fiche INPN"), null=True, blank=True
    )

    class Meta:
        db_table = '"taxonomie"."taxref"'
        managed = True
        verbose_name = _("Taxon (TaxRef)")
        verbose_name_plural = _("Taxons (TaxRef)")

    def __str__(self):
        return self.nom_complet or self.lb_nom or f"cd_nom={self.cd_nom}"


class TMetaTaxref(models.Model):
    """Versioning du référentiel TaxRef."""

    id = models.AutoField(primary_key=True)
    referential_name = models.CharField(
        _("Nom du référentiel"), max_length=100
    )
    version = models.CharField(
        _("Version"), max_length=50
    )
    update_date = models.DateTimeField(
        _("Date de mise à jour"), auto_now=True
    )

    class Meta:
        db_table = '"taxonomie"."t_meta_taxref"'
        managed = True
        verbose_name = _("Métadonnée TaxRef")
        verbose_name_plural = _("Métadonnées TaxRef")

    def __str__(self):
        return f"{self.referential_name} v{self.version}"


class VMTaxrefListForAutocomplete(models.Model):
    """
    Vue matérialisée pour l'autocomplete des taxons.

    Concatène nom latin + nom vernaculaire dans un champ search_name
    indexé avec pg_trgm pour la recherche floue.

    Note : Ce modèle est non-managé (managed=False).
    La vue est créée via une migration SQL brute.
    """

    cd_nom = models.IntegerField(_("Code nom"), primary_key=True)
    cd_ref = models.IntegerField(_("Code référence"), null=True, blank=True)
    search_name = models.TextField(_("Nom de recherche"))
    nom_valide = models.CharField(
        _("Nom valide"), max_length=500, null=True, blank=True
    )
    nom_vern = models.TextField(
        _("Nom vernaculaire"), null=True, blank=True
    )
    lb_nom = models.CharField(
        _("Nom latin"), max_length=500, null=True, blank=True
    )
    regne = models.CharField(
        _("Règne"), max_length=50, null=True, blank=True
    )
    group2_inpn = models.CharField(
        _("Groupe 2 INPN"), max_length=100, null=True, blank=True
    )
    id_rang = models.CharField(
        _("Rang"), max_length=10, null=True, blank=True
    )

    class Meta:
        db_table = '"taxonomie"."vm_taxref_list_forautocomplete"'
        managed = False
        verbose_name = _("Autocomplete taxon")
        verbose_name_plural = _("Autocomplete taxons")

    def __str__(self):
        return self.search_name or f"cd_nom={self.cd_nom}"
