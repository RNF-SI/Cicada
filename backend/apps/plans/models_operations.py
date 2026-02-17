"""
Modèles pour les Opérations (Actions).
Hiérarchie : Indicateur(s) ←M2M→ Opération(s)
"""
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class Operation(models.Model):
    """
    Opération (action) rattachée à un ou plusieurs indicateurs
    via la table de liaison cor_operation_indicateur.
    """

    id_operation = models.AutoField(primary_key=True)
    libelle = models.CharField(
        _("Libellé"),
        max_length=500,
        help_text=_("Intitulé de l'opération")
    )
    id_priorite = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_priorite',
        db_column='id_priorite',
        verbose_name=_("Priorité"),
        help_text=_("Niveau de priorité de l'opération"),
        limit_choices_to={'id_type__mnemonique': 'PRIORITE_OPERATION'}
    )
    id_type_action = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_type_action',
        db_column='id_type_action',
        verbose_name=_("Type d'action"),
        help_text=_("Type d'action (SE, CS, TU, PI, etc.)"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_ACTION'}
    )
    id_referentiel_operations = models.CharField(
        _("Référentiel opérations"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Identifiant dans le référentiel d'opérations")
    )
    code_operation = models.CharField(
        _("Code opération"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Code de l'opération")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'opération")
    )
    annee_min = models.IntegerField(
        _("Année min"),
        null=True,
        blank=True,
        help_text=_("Année de début de l'opération")
    )
    annee_max = models.IntegerField(
        _("Année max"),
        null=True,
        blank=True,
        help_text=_("Année de fin de l'opération")
    )

    # Section "Détails de l'inventaire ou du suivi"
    objectif_principal = models.TextField(
        _("Objectif principal"),
        blank=True,
        null=True,
        help_text=_("Objectif principal de l'action")
    )
    cibles_principales = models.CharField(
        _("Cible(s) principale(s)"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Cible(s) principale(s) (Flore, Faune, Habitat, etc.)")
    )
    taxon_taxref = models.CharField(
        _("Taxon - Taxref"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Référence taxon dans Taxref")
    )
    protocole_dans_campanule = models.BooleanField(
        _("Protocole répertorié dans Campanule"),
        null=True,
        blank=True,
        help_text=_("Le protocole est-il répertorié dans Campanule ?")
    )
    protocole_campanule_nom = models.CharField(
        _("Protocole (Campanule)"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Nom du protocole dans Campanule")
    )
    respect_protocole = models.BooleanField(
        _("Respect strict du protocole"),
        null=True,
        blank=True,
        help_text=_("Respectez-vous strictement le protocole ?")
    )
    justification_non_respect = models.TextField(
        _("Justification non-respect"),
        blank=True,
        null=True,
        help_text=_("Pourquoi ne respectez-vous pas le protocole ?")
    )
    differences_protocole = models.TextField(
        _("Différences avec le protocole"),
        blank=True,
        null=True,
        help_text=_("Quelques différences avec le protocole ?")
    )
    annee_lancement_suivi = models.IntegerField(
        _("Année de lancement du suivi"),
        null=True,
        blank=True,
        help_text=_("Année de lancement du suivi (si antérieur)")
    )
    outil_bancarisation = models.CharField(
        _("Outil de bancarisation"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Outil de bancarisation utilisé")
    )
    outil_saisie = models.CharField(
        _("Outil de saisie"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Existe t-il un outil de saisie ?")
    )
    transmission_donnee = models.BooleanField(
        _("Transmission de la donnée"),
        null=True,
        blank=True,
        help_text=_("Transmission de la donnée à l'organisme porteur ?")
    )

    # Fréquence de l'action
    frequence_nombre = models.IntegerField(
        _("Fréquence (nombre)"),
        null=True,
        blank=True,
        help_text=_("Nombre de répétitions")
    )
    frequence_unite = models.CharField(
        _("Fréquence (unité)"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Unité de fréquence (jour, semaine, mois, an)")
    )

    # Acteurs
    operateurs = models.TextField(
        _("Opérateurs"),
        blank=True,
        null=True,
        help_text=_("Opérateurs de l'action")
    )
    partenaires = models.TextField(
        _("Partenaires"),
        blank=True,
        null=True,
        help_text=_("Partenaires de l'action")
    )
    financeurs = models.TextField(
        _("Financeurs"),
        blank=True,
        null=True,
        help_text=_("Financeurs de l'action")
    )

    # Programmation (JSON) - legacy
    programmation_annuelle = models.JSONField(
        _("Programmation annuelle"),
        default=dict,
        blank=True,
        help_text=_('Format: {"2024": true, "2025": false, ...}')
    )
    programmation_mensuelle = models.JSONField(
        _("Programmation mensuelle"),
        default=dict,
        blank=True,
        help_text=_('Format: {"2024": {"1": true, "2": false, ...}}')
    )

    # Template mensuel appliqué identiquement à toutes les années
    programmation_mensuelle_defaut = models.JSONField(
        _("Programmation mensuelle par défaut"),
        default=dict,
        blank=True,
        help_text=_('Template mensuel appliqué à toutes les années en mode récurrent. '
                     'Format: {"1": true, "2": false, ..., "12": true}')
    )

    # Emprise spatiale (PostGIS)
    geom = models.GeometryField(
        _("Emprise spatiale"),
        srid=4326,
        null=True,
        blank=True,
        help_text=_("Emprise géographique de l'opération")
    )

    # M2M vers Indicateur via table explicite
    indicateurs = models.ManyToManyField(
        'plans.Indicateur',
        through='CorOperationIndicateur',
        related_name='operations',
        blank=True
    )

    # M2M vers Site (zones d'application)
    sites = models.ManyToManyField(
        'users.Site',
        through='CorOperationSite',
        related_name='operations',
        blank=True
    )

    # M2M vers Metrique (métriques associées)
    metriques = models.ManyToManyField(
        'plans.Metrique',
        through='CorOperationMetrique',
        related_name='operations',
        blank=True
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_operations"'
        db_table_comment = "Opérations (actions) des plans de gestion"
        verbose_name = _("Opération")
        verbose_name_plural = _("Opérations")
        ordering = ['libelle']

    def __str__(self):
        return self.libelle


class CorOperationIndicateur(models.Model):
    """
    Table de liaison entre Opérations et Indicateurs (M2M).
    """

    id = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_indicateur = models.ForeignKey(
        'plans.Indicateur',
        on_delete=models.CASCADE,
        db_column='id_indicateur',
        verbose_name=_("Indicateur")
    )

    class Meta:
        db_table = '"general"."cor_operation_indicateur"'
        db_table_comment = "Liaison opérations - indicateurs"
        verbose_name = _("Opération - Indicateur")
        verbose_name_plural = _("Opérations - Indicateurs")
        unique_together = ['id_operation', 'id_indicateur']

    def __str__(self):
        return f"Opération {self.id_operation_id} - Indicateur {self.id_indicateur_id}"


class CorOperationSite(models.Model):
    """
    Table de liaison entre Opérations et Sites (zones d'application).
    """

    id = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        db_column='id_site',
        verbose_name=_("Site")
    )

    class Meta:
        db_table = '"general"."cor_operation_site"'
        db_table_comment = "Liaison opérations - sites"
        verbose_name = _("Opération - Site")
        verbose_name_plural = _("Opérations - Sites")
        unique_together = ['id_operation', 'id_site']

    def __str__(self):
        return f"Opération {self.id_operation_id} - Site {self.id_site_id}"


class CorOperationMetrique(models.Model):
    """
    Table de liaison entre Opérations et Métriques.
    """

    id = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    id_metrique = models.ForeignKey(
        'plans.Metrique',
        on_delete=models.CASCADE,
        db_column='id_metrique',
        verbose_name=_("Métrique")
    )

    class Meta:
        db_table = '"general"."cor_operation_metrique"'
        db_table_comment = "Liaison opérations - métriques"
        verbose_name = _("Opération - Métrique")
        verbose_name_plural = _("Opérations - Métriques")
        unique_together = ['id_operation', 'id_metrique']

    def __str__(self):
        return f"Opération {self.id_operation_id} - Métrique {self.id_metrique_id}"


class OperationAnnee(models.Model):
    """
    Programmation annuelle d'une opération.
    Une ligne par année entre annee_min et annee_max de l'opération.
    """

    id_operation_annee = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name='operation_annees',
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    annee = models.IntegerField(_("Année"))
    periodicite = models.BooleanField(_("Périodicité"), default=False)
    budget = models.DecimalField(
        _("Budget prévisionnel (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    etp = models.DecimalField(
        _("Travail prévisionnel (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    id_operateur = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operation_annees_operateur',
        db_column='id_operateur',
        verbose_name=_("Type d'opérateur"),
        limit_choices_to={'id_type__mnemonique': 'OPERATEUR_TYPE'}
    )
    periodicite_mensuelle = models.JSONField(
        _("Périodicité mensuelle"),
        default=dict, blank=True,
        help_text=_('Format: {"1": true, "2": false, ..., "12": true}')
    )
    geom = models.GeometryField(
        _("Emprise spatiale"),
        srid=4326, null=True, blank=True
    )

    class Meta:
        db_table = '"general"."t_operation_annees"'
        db_table_comment = "Programmation annuelle des opérations"
        verbose_name = _("Année d'opération")
        verbose_name_plural = _("Années d'opération")
        unique_together = ['id_operation', 'annee']
        ordering = ['annee']

    def __str__(self):
        return f"Opération {self.id_operation_id} - {self.annee}"


class FinanceOperation(models.Model):
    """
    Source de financement d'une opération.
    """

    id_finance_operation = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name='finances',
        db_column='id_operation',
        verbose_name=_("Opération")
    )
    libelle = models.CharField(_("Libellé"), max_length=255)
    id_categorie = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='finances_categorie',
        db_column='id_categorie',
        verbose_name=_("Catégorie de financement"),
        limit_choices_to={'id_type__mnemonique': 'CATEGORIE_FINANCE'}
    )

    class Meta:
        db_table = '"general"."t_finances_operations"'
        db_table_comment = "Sources de financement des opérations"
        verbose_name = _("Financement d'opération")
        verbose_name_plural = _("Financements d'opération")
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} (Opération {self.id_operation_id})"
