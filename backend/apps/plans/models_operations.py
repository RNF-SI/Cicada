"""
Modèles pour les Opérations (Actions).
Hiérarchie : Métrique → Opération(s) (FK simple, une opération = une métrique)
"""
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class Protocole(models.Model):
    """
    Protocole associé à un suivi/inventaire.
    Contient les informations du protocole (Campanule) et les détails associés.
    """

    id_protocole = models.AutoField(primary_key=True)

    # Champs extraits de SuiviInventaire
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
        default='',
        help_text=_("Nom du protocole dans Campanule")
    )
    cd_protocole_campanule = models.IntegerField(
        _("Code protocole Campanule"),
        null=True,
        blank=True,
        help_text=_("Code du protocole dans le référentiel CAMPanule")
    )
    nb_etp_cycle = models.DecimalField(
        _("Nombre d'ETP par cycle"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Nombre d'ETP nécessaire par cycle de collecte")
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
        default='',
        help_text=_("Pourquoi ne respectez-vous pas le protocole ?")
    )
    differences_protocole = models.TextField(
        _("Différences avec le protocole"),
        blank=True,
        default='',
        help_text=_("Quelques différences avec le protocole ?")
    )

    nom_protocole = models.CharField(
        _("Nom du protocole"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Nom du protocole (si non Campanule)")
    )
    mode_validation = models.CharField(
        _("Mode et champ de validation"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Mode et champ de validation du protocole")
    )

    # Nouveaux champs (Figma)
    description_protocole = models.TextField(
        _("Description du protocole"),
        blank=True,
        default='',
        help_text=_("Description du protocole (depuis Campanule)")
    )
    objectif_protocole = models.TextField(
        _("Objectif du protocole"),
        blank=True,
        default='',
        help_text=_("Détails de l'objectif du protocole")
    )
    periode_echantillonnage = models.CharField(
        _("Période d'échantillonnage"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Période d'échantillonnage du protocole")
    )

    # Champs ajoutés (Figma v2)
    periode_suivi = models.CharField(
        _("Période de suivi"),
        max_length=50,
        blank=True,
        default='',
        help_text=_("Mois de suivi (mnémonique nomenclature PERIODE_SUIVI)")
    )
    documentation_disponible = models.BooleanField(
        _("Documentation disponible"),
        null=True,
        blank=True,
        help_text=_("Une documentation décrivant le protocole est-elle disponible ?")
    )
    url_documentation = models.CharField(
        _("URL de la documentation"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("URL de la documentation du protocole")
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
        db_table = '"general"."t_protocoles"'
        db_table_comment = "Protocoles associés aux suivis/inventaires"
        verbose_name = _("Protocole")
        verbose_name_plural = _("Protocoles")

    def __str__(self):
        return self.protocole_campanule_nom or f"Protocole #{self.id_protocole}"


class SuiviInventaire(models.Model):
    """
    Suivi ou inventaire associé à une opération.
    Contient les détails de la bancarisation et du suivi.
    Le protocole est dans une table dédiée (Protocole).
    """

    id_suivi_inventaire = models.AutoField(primary_key=True)

    # Champs standalone
    intitule = models.CharField(
        _("Intitulé"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Nom affiché dans la liste des suivis/inventaires")
    )
    prix_indicatif = models.DecimalField(
        _("Prix indicatif (€/an)"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Prix indicatif en euros par an")
    )
    id_type_suivi = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_type',
        db_column='id_type_suivi',
        verbose_name=_("Type de suivi"),
        help_text=_("Type : Suivi, Inventaire, ou Suivi et inventaire"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_SUIVI'}
    )
    id_type_action = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_type_action',
        db_column='id_type_action',
        verbose_name=_("Type d'action"),
        help_text=_("Code d'action CS associé (ex: CS8 = Inventaire de la faune)"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_ACTION'}
    )
    integre_plan_gestion = models.BooleanField(
        _("Intégré dans un plan de gestion"),
        null=True,
        blank=True,
        help_text=_("Ce suivi est-il intégré dans un plan de gestion ?")
    )
    id_pg = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_inventaires',
        db_column='id_pg',
        verbose_name=_("Plan de gestion lié"),
        help_text=_("Plan de gestion associé (optionnel)")
    )
    suit_indicateur = models.BooleanField(
        _("Suit un indicateur"),
        null=True,
        blank=True,
        help_text=_("Le suivi/inventaire permet-il de suivre un indicateur ?")
    )
    type_indicateur = models.CharField(
        _("Type d'indicateur"),
        max_length=50,
        blank=True,
        default='',
        help_text=_("Type d'indicateur (mnémonique nomenclature TYPE_INDICATEUR : ETAT, PRESSION, REPONSE)")
    )
    cible_secondaire = models.CharField(
        _("Cible secondaire"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Cible secondaire du suivi/inventaire")
    )
    habitat_ref = models.CharField(
        _("Référentiel habitat"),
        max_length=500,
        blank=True,
        default='',
        help_text=_("Référentiel habitat associé")
    )
    id_statut = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis_statut',
        db_column='id_statut',
        verbose_name=_("Statut"),
        help_text=_("Statut du suivi (En cours, Terminé, A venir)"),
        limit_choices_to={'id_type__mnemonique': 'STATUT_SUIVI'}
    )
    actif = models.BooleanField(
        _("Actif"),
        default=True,
        help_text=_("Suivi actif ou inactif")
    )
    annee_fin_suivi = models.IntegerField(
        _("Année de fin du suivi"),
        null=True,
        blank=True,
        help_text=_("Année de fin du suivi")
    )
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
    frequence_unite_precision = models.CharField(
        _("Précision fréquence (autre)"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Précision si fréquence 'Autre'")
    )
    commentaires = models.TextField(
        _("Commentaires"),
        blank=True,
        default='',
        help_text=_("Détails et commentaires")
    )

    # Détails de l'inventaire ou du suivi
    objectif_principal = models.CharField(
        _("Objectif principal"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Objectif principal de la collecte de données (mnémonique nomenclature OBJECTIF_SUIVI)")
    )
    objectif_secondaire = models.CharField(
        _("Objectif secondaire"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Objectif secondaire optionnel (mnémonique nomenclature OBJECTIF_SUIVI)")
    )
    cibles_principales = models.CharField(
        _("Cible principale"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Cible principale (mnémonique nomenclature CIBLE_SUIVI)")
    )
    taxon_taxref = models.CharField(
        _("Taxon - Taxref"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Référence taxon dans Taxref")
    )
    date_lancement_suivi = models.DateField(
        _("Date de lancement du suivi"),
        null=True,
        blank=True,
        help_text=_("Date de lancement du suivi")
    )

    # Protocole (FK vers table dédiée)
    id_protocole = models.ForeignKey(
        Protocole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suivis',
        db_column='id_protocole',
        verbose_name=_("Protocole"),
        help_text=_("Protocole associé au suivi/inventaire")
    )

    # Bancarisation et stockage
    outil_bancarisation = models.CharField(
        _("Outil de bancarisation"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Outil de bancarisation utilisé")
    )
    outil_saisie = models.CharField(
        _("Outil de saisie"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Existe t-il un outil de saisie ?")
    )
    transmission_donnee = models.BooleanField(
        _("Transmission de la donnée"),
        null=True,
        blank=True,
        help_text=_("Transmission de la donnée à l'organisme porteur ?")
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
        db_table = '"general"."t_suivi_inventaires"'
        db_table_comment = "Suivis et inventaires associés aux opérations"
        verbose_name = _("Suivi / Inventaire")
        verbose_name_plural = _("Suivis / Inventaires")

    def __str__(self):
        return self.intitule or f"Suivi #{self.id_suivi_inventaire}"


class Operation(models.Model):
    """
    Opération (action) rattachée à une métrique (FK simple).
    L'indicateur est déduit via metrique.id_indicateur.
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
        help_text=_("Type d'action (IP1, CS2, CI2, SP1, etc.)"),
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

    # Lien vers un suivi/inventaire existant
    est_suivi_existant = models.BooleanField(
        _("Inventaire ou suivi existant"),
        default=False,
        help_text=_("Inventaire ou suivi déjà saisi dans le module Mes inventaires et suivis ?")
    )
    id_suivi = models.ForeignKey(
        SuiviInventaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations',
        db_column='id_suivi',
        verbose_name=_("Suivi / Inventaire lié"),
        help_text=_("Suivi ou inventaire associé à cette opération")
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

    # FK vers Métrique (une opération est liée à une seule métrique)
    id_metrique = models.ForeignKey(
        'plans.Metrique',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations',
        db_column='id_metrique',
        verbose_name=_("Métrique"),
        help_text=_("Métrique associée à cette opération")
    )

    # M2M vers Site (zones d'application)
    sites = models.ManyToManyField(
        'users.Site',
        through='CorOperationSite',
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


class OperationAnneeOrganisme(models.Model):
    """
    Ventilation budget/travail par organisme pour une année d'opération.
    """

    id_operation_annee_organisme = models.AutoField(primary_key=True)
    id_operation_annee = models.ForeignKey(
        OperationAnnee,
        on_delete=models.CASCADE,
        related_name='organismes',
        db_column='id_operation_annee',
        verbose_name=_("Année d'opération")
    )
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.CASCADE,
        db_column='id_organisme',
        verbose_name=_("Organisme")
    )
    budget_fonctionnement = models.DecimalField(
        _("Budget fonctionnement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    budget_investissement = models.DecimalField(
        _("Budget investissement (€)"),
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    etp = models.DecimalField(
        _("Travail prévisionnel (jours)"),
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )

    class Meta:
        db_table = '"general"."t_operation_annee_organismes"'
        db_table_comment = "Ventilation budget/travail par organisme et par année"
        verbose_name = _("Organisme - Année d'opération")
        verbose_name_plural = _("Organismes - Années d'opération")
        unique_together = ['id_operation_annee', 'id_organisme']
        ordering = ['id_organisme__nom_organisme']

    def __str__(self):
        return f"OpAnnée {self.id_operation_annee_id} - Org {self.id_organisme_id}"


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
