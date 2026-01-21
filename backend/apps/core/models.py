"""
Modèles de base partagés par toute l'application.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


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
        verbose_name=_("Type de nomenclature"),
        null=True,
        blank=True,
        db_column='id_type'
    )
    cd_nomenclature = models.CharField(
        _("Code nomenclature"),
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Code technique unique de la nomenclature (ex: RNN, RNR, PNR)")
    )
    mnemonique = models.CharField(
        _("Mnémonique"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Mnémonique métier pour retrouver facilement les éléments")
    )
    label = models.CharField(_("Label"), max_length=255, null=True, blank=True)
    definition = models.TextField(_("Définition"), null=True, blank=True)
    source = models.CharField(_("Source"), max_length=255, null=True, blank=True)
    statut = models.CharField(_("Statut"), max_length=50, null=True, blank=True)
    hierarchy = models.CharField(_("Hiérarchie"), max_length=255, null=True, blank=True)
    date_ajout = models.DateTimeField(_("Date d'ajout"), null=True, blank=True)
    date_maj = models.DateTimeField(_("Date de mise à jour"), null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        db_table = '"ref_nomenclatures"."t_nomenclatures"'
        verbose_name = _("Nomenclature")
        verbose_name_plural = _("Nomenclatures")
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
    mnemonique = models.CharField(_("Mnémonique"), max_length=255, null=True, blank=True)
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
        managed = True

    def __str__(self):
        return self.label or self.mnemonique or f"Type {self.id_type}"


class ErrorLog(models.Model):
    """
    Modele pour stocker les logs d'erreurs applicatifs.
    Permet aux super admins de consulter et acquitter les erreurs via l'interface.
    Table t_error_logs dans le schema ccd_commons.
    """

    LEVEL_CHOICES = [
        ('WARNING', _('Avertissement')),
        ('ERROR', _('Erreur')),
        ('CRITICAL', _('Critique')),
    ]

    id = models.AutoField(primary_key=True)
    level = models.CharField(
        _('Niveau'),
        max_length=10,
        choices=LEVEL_CHOICES,
        db_index=True
    )
    message = models.TextField(_('Message'))
    logger_name = models.CharField(
        _('Logger'),
        max_length=255,
        null=True,
        blank=True
    )
    correlation_id = models.CharField(
        _('ID de correlation'),
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('UUID de correlation pour tracer les requetes')
    )

    # Contexte de la requete HTTP
    user = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Utilisateur'),
        related_name='error_logs'
    )
    path = models.CharField(
        _('URL'),
        max_length=500,
        null=True,
        blank=True
    )
    method = models.CharField(
        _('Methode HTTP'),
        max_length=10,
        null=True,
        blank=True
    )

    # Information sur l'exception
    exception_type = models.CharField(
        _("Type d'exception"),
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )
    stack_trace = models.TextField(
        _('Stack trace'),
        null=True,
        blank=True
    )
    context = models.JSONField(
        _('Contexte additionnel'),
        default=dict,
        blank=True
    )

    # Acquittement
    acknowledged = models.BooleanField(
        _('Acquitte'),
        default=False,
        db_index=True
    )
    acknowledged_by = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Acquitte par'),
        related_name='acknowledged_error_logs'
    )
    acknowledged_at = models.DateTimeField(
        _('Acquitte le'),
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        _('Date de creation'),
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = '"ccd_commons"."t_error_logs"'
        verbose_name = _("Log d'erreur")
        verbose_name_plural = _("Logs d'erreurs")
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.message[:50]}..."

    def acknowledge(self, user):
        """Acquitte cette erreur par l'utilisateur specifie."""
        from django.utils import timezone
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['acknowledged', 'acknowledged_by', 'acknowledged_at'])


class Module(models.Model):
    """
    Modele pour les modules applicatifs.
    Definit les modules disponibles dans l'application et leurs caracteristiques.
    Certains modules necessitent une demande d'acces (requires_access=True).
    """

    TILE_COLORS = [
        ('primary', _('Primaire (bleu-vert)')),
        ('salmon', _('Saumon')),
        ('terra-cotta', _('Terra cotta')),
        ('yellow', _('Jaune')),
        ('pale-green', _('Vert pâle')),
    ]

    id = models.AutoField(primary_key=True)

    # Identification
    code = models.CharField(
        _('Code'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Code technique unique du module (ex: plans, sites, zonages)')
    )
    name = models.CharField(
        _('Nom'),
        max_length=100,
        help_text=_('Nom affiche du module')
    )
    description = models.TextField(
        _('Description'),
        null=True,
        blank=True,
        help_text=_('Description du module')
    )

    # Affichage
    icon = models.CharField(
        _('Icône'),
        max_length=100,
        default='fi-rr-apps',
        help_text=_('Classe CSS de l\'icone Flaticon (ex: fi-rr-document)')
    )
    color = models.CharField(
        _('Couleur'),
        max_length=20,
        choices=TILE_COLORS,
        default='primary',
        help_text=_('Couleur de la tuile sur la page d\'accueil')
    )
    route = models.CharField(
        _('Route'),
        max_length=100,
        help_text=_('Route Angular du module (ex: /plans)')
    )

    # Configuration d'acces
    requires_access = models.BooleanField(
        _('Nécessite un accès'),
        default=False,
        help_text=_('Si True, l\'utilisateur doit demander l\'acces a ce module')
    )
    is_active = models.BooleanField(
        _('Actif'),
        default=True,
        help_text=_('Module visible et accessible')
    )

    # Ordre d'affichage
    display_order = models.PositiveIntegerField(
        _('Ordre d\'affichage'),
        default=0,
        help_text=_('Ordre d\'affichage sur la page d\'accueil (0 = premier)')
    )

    # Metadata
    created_at = models.DateTimeField(_('Créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Mis à jour le'), auto_now=True)

    class Meta:
        db_table = '"ccd_commons"."t_modules"'
        db_table_comment = 'Table des modules applicatifs'
        ordering = ['display_order', 'name']
        verbose_name = _('Module')
        verbose_name_plural = _('Modules')

    def __str__(self):
        return self.name


class ActivityLog(models.Model):
    """
    Modele pour l'historique d'activite.
    Trace toutes les actions sur les entites du systeme (sites, plans, users, organismes).
    Separe des Notifications : l'activite est permanente (audit), les notifications sont temporaires.
    Table t_activity_logs dans le schema ccd_commons.
    """

    ENTITY_TYPES = [
        ('site', _('Site')),
        ('plan', _('Plan de gestion')),
        ('user', _('Utilisateur')),
        ('organisme', _('Organisme')),
        ('validation', _('Demande de validation')),
    ]

    ACTION_TYPES = [
        ('create', _('Création')),
        ('update', _('Modification')),
        ('delete', _('Suppression')),
        ('add_member', _('Ajout membre')),
        ('remove_member', _('Retrait membre')),
        ('add_referent', _('Ajout référent')),
        ('remove_referent', _('Retrait référent')),
        ('status_change', _('Changement statut')),
        ('activate', _('Activation')),
        ('deactivate', _('Désactivation')),
        ('rgpd_request', _('Demande RGPD')),
        ('rgpd_cancelled', _('Annulation RGPD')),
        ('rgpd_anonymized', _('Anonymisation RGPD')),
        ('access_granted', _('Accès accordé')),
        ('access_revoked', _('Accès révoqué')),
        ('validation_approved', _('Validation approuvée')),
        ('validation_rejected', _('Validation rejetée')),
        ('file_upload', _('Téléversement fichier')),
        ('file_delete', _('Suppression fichier')),
    ]

    VISIBILITY_LEVELS = [
        ('public', _('Public')),  # Visible a tous les concernes
        ('admin', _('Admin')),    # Visible aux admins de l'organisme
        ('system', _('Système')), # Visible super_admin uniquement
    ]

    id = models.AutoField(primary_key=True)

    # Type d'entite concernee
    entity_type = models.CharField(
        _("Type d'entité"),
        max_length=20,
        choices=ENTITY_TYPES,
        db_index=True
    )
    entity_id = models.IntegerField(
        _("ID de l'entité"),
        db_index=True
    )
    entity_name = models.CharField(
        _("Nom de l'entité"),
        max_length=255,
        help_text=_("Denormalise pour affichage meme apres suppression de l'entite")
    )

    # Acteur (qui a effectue l'action)
    actor = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities_performed',
        verbose_name=_('Acteur')
    )
    actor_name = models.CharField(
        _("Nom de l'acteur"),
        max_length=255,
        help_text=_("Denormalise pour affichage meme apres suppression de l'acteur")
    )

    # Action effectuee
    action = models.CharField(
        _('Action'),
        max_length=30,
        choices=ACTION_TYPES,
        db_index=True
    )
    description = models.TextField(
        _('Description'),
        help_text=_("Description lisible de l'action")
    )

    # Relations optionnelles pour faciliter le filtrage
    related_site = models.ForeignKey(
        'users.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name=_('Site lié')
    )
    related_plan = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name=_('Plan lié')
    )
    related_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name=_('Organisme lié')
    )
    related_user = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs_about_me',
        verbose_name=_('Utilisateur lié')
    )

    # Details des changements
    changes = models.JSONField(
        _('Changements'),
        default=dict,
        blank=True,
        help_text=_("Détail des modifications: {field: {old: value, new: value}}")
    )
    metadata = models.JSONField(
        _('Métadonnées'),
        default=dict,
        blank=True,
        help_text=_("Contexte additionnel")
    )

    # Visibilite
    visibility = models.CharField(
        _('Visibilité'),
        max_length=10,
        choices=VISIBILITY_LEVELS,
        default='public',
        db_index=True
    )

    # Timestamps
    created_at = models.DateTimeField(
        _('Date'),
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = '"ccd_commons"."t_activity_logs"'
        db_table_comment = "Table de l'historique d'activité"
        ordering = ['-created_at']
        verbose_name = _("Log d'activité")
        verbose_name_plural = _("Logs d'activité")
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', '-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['related_site', '-created_at']),
            models.Index(fields=['related_plan', '-created_at']),
            models.Index(fields=['related_organisme', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['visibility', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.action}] {self.entity_type}:{self.entity_name} par {self.actor_name}"