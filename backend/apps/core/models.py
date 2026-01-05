"""
Modèles de base partagés par toute l'application.
"""
from django.db import models


class Nomenclature(models.Model):
    """
    Modele pour les nomenclatures et referentiels.
    Table t_nomenclatures dans le schema referentiels.
    Structure adaptee aux donnees ODASE.

    - cd_nomenclature: Code technique unique (ex: 'RNN', 'RNR', 'PNR')
    - mnemonique: Mnemonique metier pour retrouver facilement les elements
    - label: Label affiche a l'utilisateur
    """

    id_nomenclature = models.AutoField(primary_key=True)
    id_type = models.ForeignKey(
        'TypeNomenclature',
        on_delete=models.CASCADE,
        verbose_name="Type de nomenclature",
        null=True,
        blank=True,
        db_column='id_type'
    )
    cd_nomenclature = models.CharField(
        "Code nomenclature",
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Code technique unique de la nomenclature (ex: RNN, RNR, PNR)"
    )
    mnemonique = models.CharField(
        "Mnemonique",
        max_length=255,
        null=True,
        blank=True,
        help_text="Mnemonique metier pour retrouver facilement les elements"
    )
    label = models.CharField("Label", max_length=255, null=True, blank=True)
    definition = models.TextField("Definition", null=True, blank=True)
    source = models.CharField("Source", max_length=255, null=True, blank=True)
    statut = models.CharField("Statut", max_length=50, null=True, blank=True)
    hierarchy = models.CharField("Hierarchie", max_length=255, null=True, blank=True)
    date_ajout = models.DateTimeField("Date d'ajout", null=True, blank=True)
    date_maj = models.DateTimeField("Date de mise a jour", null=True, blank=True)
    actif = models.BooleanField("Actif", default=True)

    class Meta:
        db_table = 't_nomenclatures'
        verbose_name = "Nomenclature"
        verbose_name_plural = "Nomenclatures"
        managed = True

    def __str__(self):
        return self.label or self.mnemonique or f"Nomenclature {self.id_nomenclature}"


class TypeNomenclature(models.Model):
    """
    Types de nomenclatures.
    Table bib_nomenclatures_types dans le schéma referentiels.
    Structure adaptée aux données ODASE.
    """
    
    id_type = models.AutoField(primary_key=True)
    mnemonique = models.CharField("Mnémonique", max_length=255, null=True, blank=True)
    label = models.CharField("Label", max_length=255, null=True, blank=True)
    definition = models.TextField("Définition", null=True, blank=True)
    source = models.CharField("Source", max_length=255, null=True, blank=True)
    statut = models.CharField("Statut", max_length=50, null=True, blank=True)
    date_ajout = models.DateTimeField("Date d'ajout", null=True, blank=True)
    date_maj = models.DateTimeField("Date de mise à jour", null=True, blank=True)

    class Meta:
        db_table = 'bib_nomenclatures_types'
        verbose_name = "Type de nomenclature"
        verbose_name_plural = "Types de nomenclatures"
        managed = True

    def __str__(self):
        return self.label or self.mnemonique or f"Type {self.id_type}"