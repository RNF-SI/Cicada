"""
Référentiel des nomenclatures (schéma ``ref_nomenclatures``).

Reprise à l'identique du modèle de CICADA (``apps.core``), pour la même raison
que ``ref_geo`` : c'est un référentiel national, identique dans toutes les
instances, et les facettes de l'exploration s'appuient dessus — types d'aires
protégées, catégories d'action, types d'indicateur, types de document.

Les documents publiés transportent les **codes** de ces nomenclatures
(`type_site_codes`, `sous_type`) et non leurs identifiants, qui sont locaux. Le
hub les retraduit en libellés grâce à ce référentiel, ce qui a un avantage sur
la dénormalisation : un libellé corrigé le sera partout à la fois, sans attendre
la republication des documents.

Les tables sont alimentées par ``import_nomenclatures``, depuis les **mêmes
fichiers SQL que CICADA**, montés en lecture seule.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TypeNomenclature(models.Model):
    """Type de nomenclature (« Type d'aire protégée », « Catégorie d'action »…)."""

    id_type = models.AutoField(primary_key=True)
    mnemonique = models.CharField(
        _("Mnémonique"), max_length=255, null=True, blank=True
    )
    label = models.CharField(_("Label"), max_length=255, null=True, blank=True)
    definition = models.TextField(_("Définition"), null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)
    statut = models.CharField(_("Statut"), max_length=50, null=True, blank=True)
    date_ajout = models.DateTimeField(_("Date d'ajout"), null=True, blank=True)
    date_maj = models.DateTimeField(_("Date de mise à jour"), null=True, blank=True)

    class Meta:
        db_table = '"ref_nomenclatures"."bib_nomenclatures_types"'
        verbose_name = _("Type de nomenclature")
        verbose_name_plural = _("Types de nomenclatures")

    def __str__(self):
        return self.label or self.mnemonique or f"Type {self.id_type}"


class Nomenclature(models.Model):
    """Une valeur de nomenclature (« RNN », « Réserve naturelle nationale »)."""

    id_nomenclature = models.AutoField(primary_key=True)
    id_type = models.ForeignKey(
        TypeNomenclature,
        on_delete=models.CASCADE,
        db_column='id_type',
        related_name='valeurs',
        verbose_name=_("Type de nomenclature"),
        null=True, blank=True,
    )
    cd_nomenclature = models.CharField(
        _("Code nomenclature"), max_length=50, null=True, blank=True, db_index=True,
        help_text=_("Code technique unique de la nomenclature (ex: RNN, RNR, PNR)"),
    )
    mnemonique = models.CharField(
        _("Mnémonique"), max_length=255, null=True, blank=True,
        help_text=_(
            "C'est cette valeur qui voyage dans les documents publiés "
            "(`type_site_codes`), l'identifiant étant une séquence locale."
        ),
    )
    label = models.CharField(_("Label"), max_length=255, null=True, blank=True)
    definition = models.TextField(_("Définition"), null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)
    statut = models.CharField(_("Statut"), max_length=50, null=True, blank=True)
    hierarchy = models.CharField(
        _("Hiérarchie"), max_length=255, null=True, blank=True
    )
    date_ajout = models.DateTimeField(_("Date d'ajout"), null=True, blank=True)
    date_maj = models.DateTimeField(_("Date de mise à jour"), null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        db_table = '"ref_nomenclatures"."t_nomenclatures"'
        verbose_name = _("Nomenclature")
        verbose_name_plural = _("Nomenclatures")

    def __str__(self):
        return self.label or self.mnemonique or f"Nomenclature {self.id_nomenclature}"
