"""
Modèles de base partagés par toute l'application.
"""
from django.db import models


class Nomenclature(models.Model):
    """
    Modèle pour les nomenclatures et référentiels.
    Table t_nomenclatures dans le schéma referentiels.
    """
    
    id_nomenclature = models.AutoField(primary_key=True)
    id_type = models.ForeignKey(
        'TypeNomenclature',
        on_delete=models.CASCADE,
        verbose_name="Type de nomenclature"
    )
    cd_nomenclature = models.CharField("Code", max_length=50)
    mnemonique = models.CharField("Mnémonique", max_length=255, null=True, blank=True)
    label_default = models.CharField("Label par défaut", max_length=255)
    definition_default = models.TextField("Définition par défaut", null=True, blank=True)
    label_fr = models.CharField("Label français", max_length=255, null=True, blank=True)
    definition_fr = models.TextField("Définition française", null=True, blank=True)
    id_broader = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Nomenclature parente"
    )
    hierarchy = models.CharField("Hiérarchie", max_length=255, null=True, blank=True)
    active = models.BooleanField("Actif", default=True)
    meta_create_date = models.DateTimeField(auto_now_add=True)
    meta_update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_nomenclatures'
        db_table_comment = 'Table des nomenclatures'
        verbose_name = "Nomenclature"
        verbose_name_plural = "Nomenclatures"
        unique_together = ['id_type', 'cd_nomenclature']

    def __str__(self):
        return self.label_fr or self.label_default


class TypeNomenclature(models.Model):
    """
    Types de nomenclatures.
    Table bib_nomenclatures_types dans le schéma referentiels.
    """
    
    id_type = models.AutoField(primary_key=True)
    mnemonique = models.CharField("Mnémonique", max_length=255, unique=True)
    label_default = models.CharField("Label par défaut", max_length=255)
    definition_default = models.TextField("Définition par défaut", null=True, blank=True)
    label_fr = models.CharField("Label français", max_length=255, null=True, blank=True)
    definition_fr = models.TextField("Définition française", null=True, blank=True)
    source = models.CharField("Source", max_length=255, null=True, blank=True)
    statut = models.CharField("Statut", max_length=50, null=True, blank=True)
    meta_create_date = models.DateTimeField(auto_now_add=True)
    meta_update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bib_nomenclatures_types'
        db_table_comment = 'Types de nomenclatures'
        verbose_name = "Type de nomenclature"
        verbose_name_plural = "Types de nomenclatures"

    def __str__(self):
        return self.label_fr or self.label_default