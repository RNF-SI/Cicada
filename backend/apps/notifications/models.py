"""
Modeles pour les notifications et validations.
"""
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    Modele pour les notifications in-app.
    Stocke les notifications envoyees aux utilisateurs.
    """

    NOTIFICATION_TYPES = [
        ('welcome', 'Bienvenue'),
        ('validation_request', 'Demande de validation'),
        ('validation_approved', 'Validation approuvee'),
        ('validation_rejected', 'Validation rejetee'),
        ('user_associated_site', 'Utilisateur associe a un site'),
        ('user_associated_plan', 'Utilisateur associe a un plan'),
        ('user_removed_site', 'Utilisateur retire d\'un site'),
        ('user_removed_plan', 'Utilisateur retire d\'un plan'),
        ('account_deactivated', 'Compte desactive'),
        ('account_activated', 'Compte active'),
        ('site_orphaned', 'Site sans utilisateurs'),
        ('organisme_no_admin', 'Organisme sans administrateur'),
        ('system_alert', 'Alerte systeme'),
        ('info', 'Information'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', 'Critique'),
    ]

    id = models.AutoField(primary_key=True)

    # Destinataire de la notification
    recipient = models.ForeignKey(
        'users.Role',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinataire'
    )

    # Type et contenu
    notification_type = models.CharField(
        'Type',
        max_length=30,
        choices=NOTIFICATION_TYPES,
        db_index=True
    )
    title = models.CharField('Titre', max_length=255)
    message = models.TextField('Message')
    priority = models.CharField(
        'Priorite',
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium'
    )

    # Objets lies (references polymorphes)
    related_user = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_notifications',
        verbose_name='Utilisateur lie'
    )
    related_site = models.ForeignKey(
        'users.Site',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Site lie'
    )
    related_plan = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Plan lie'
    )
    related_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Organisme lie'
    )
    related_validation = models.ForeignKey(
        'ValidationRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Demande liee'
    )

    # URL d'action pour le frontend
    action_url = models.CharField(
        'URL d\'action',
        max_length=500,
        null=True,
        blank=True,
        help_text='URL vers laquelle rediriger l\'utilisateur'
    )

    # Statut de lecture
    read = models.BooleanField('Lu', default=False)
    read_at = models.DateTimeField('Lu le', null=True, blank=True)

    # Statut d'envoi email
    email_sent = models.BooleanField('Email envoye', default=False)
    email_sent_at = models.DateTimeField('Email envoye le', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField('Cree le', auto_now_add=True)
    expires_at = models.DateTimeField(
        'Expire le',
        null=True,
        blank=True,
        help_text='Date d\'expiration automatique'
    )

    class Meta:
        db_table = 't_notifications'
        db_table_comment = 'Table des notifications utilisateurs'
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['recipient', 'read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])

    def is_expired(self):
        """Verifie si la notification est expiree."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class ValidationRequest(models.Model):
    """
    Modele pour les demandes de validation.
    Gere: inscription utilisateur, acces site, acces plan, desactivation admin.
    """

    REQUEST_TYPES = [
        ('user_registration', 'Inscription utilisateur'),
        ('site_access', 'Acces a un site'),
        ('plan_access', 'Acces a un plan de gestion'),
        ('admin_deactivation', 'Desactivation admin_og'),
        ('referent_validation', 'Validation referent site'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuve'),
        ('rejected', 'Rejete'),
        ('cancelled', 'Annule'),
        ('expired', 'Expire'),
    ]

    id = models.AutoField(primary_key=True)

    # Type et statut
    request_type = models.CharField(
        'Type de demande',
        max_length=30,
        choices=REQUEST_TYPES,
        db_index=True
    )
    status = models.CharField(
        'Statut',
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Demandeur (l'utilisateur qui fait la demande)
    # Nullable pour les inscriptions (PendingUser pas encore un Role)
    requester = models.ForeignKey(
        'users.Role',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='validation_requests_made',
        verbose_name='Demandeur'
    )

    # Cibles selon le type de demande
    target_site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Site cible'
    )
    target_plan = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Plan cible'
    )
    target_user = models.ForeignKey(
        'users.Role',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='deactivation_requests',
        verbose_name='Utilisateur cible'
    )

    # Pour les inscriptions
    requested_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Organisme demande'
    )
    requested_role_level = models.CharField(
        'Niveau de role demande',
        max_length=20,
        null=True,
        blank=True
    )

    # Details de la demande
    justification = models.TextField(
        'Justification',
        null=True,
        blank=True,
        help_text='Motif de la demande'
    )

    # Validation
    validator = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validations_handled',
        verbose_name='Validateur'
    )
    validation_comment = models.TextField(
        'Commentaire de validation',
        null=True,
        blank=True
    )
    validated_at = models.DateTimeField(
        'Valide le',
        null=True,
        blank=True
    )

    # Metadata
    created_at = models.DateTimeField('Cree le', auto_now_add=True)
    updated_at = models.DateTimeField('Mis a jour le', auto_now=True)
    expires_at = models.DateTimeField(
        'Expire le',
        null=True,
        blank=True,
        help_text='Date d\'expiration automatique de la demande'
    )

    class Meta:
        db_table = 't_validation_requests'
        db_table_comment = 'Table des demandes de validation'
        ordering = ['-created_at']
        verbose_name = 'Demande de validation'
        verbose_name_plural = 'Demandes de validation'
        indexes = [
            models.Index(fields=['status', 'request_type', '-created_at']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        requester_str = str(self.requester) if self.requester else 'Inscription'
        return f"{self.get_request_type_display()} - {requester_str} ({self.get_status_display()})"

    def approve(self, validator, comment=None):
        """Approuve la demande."""
        self.status = 'approved'
        self.validator = validator
        self.validation_comment = comment
        self.validated_at = timezone.now()
        self.save()

    def reject(self, validator, comment=None):
        """Rejette la demande."""
        self.status = 'rejected'
        self.validator = validator
        self.validation_comment = comment
        self.validated_at = timezone.now()
        self.save()

    def cancel(self):
        """Annule la demande (par le demandeur)."""
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])

    def is_pending(self):
        """Verifie si la demande est en attente."""
        return self.status == 'pending'

    def can_be_validated_by(self, user):
        """
        Verifie si l'utilisateur peut valider cette demande.
        La logique exacte est implementee dans services.py
        """
        from .services import ValidationService
        return ValidationService.can_validate_request(user, self)


class PendingUser(models.Model):
    """
    Stockage temporaire pour les inscriptions en attente de validation.
    Les donnees sont transferees vers Role lors de l'approbation,
    puis le PendingUser est supprime.
    """

    id = models.AutoField(primary_key=True)

    # Informations de base
    email = models.EmailField('Email', unique=True)
    password_hash = models.CharField(
        'Mot de passe (hash)',
        max_length=255,
        help_text='Mot de passe hashe avec make_password'
    )
    nom_role = models.CharField('Nom', max_length=50, null=True, blank=True)
    prenom_role = models.CharField('Prenom', max_length=50, null=True, blank=True)

    # Affiliation demandee
    requested_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Organisme demande'
    )
    justification = models.TextField(
        'Justification',
        null=True,
        blank=True,
        help_text='Motif de l\'inscription'
    )

    # Lien vers la demande de validation
    validation_request = models.OneToOneField(
        ValidationRequest,
        on_delete=models.CASCADE,
        related_name='pending_user',
        verbose_name='Demande de validation'
    )

    # Metadata de securite
    created_at = models.DateTimeField('Cree le', auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        'Adresse IP',
        null=True,
        blank=True
    )
    user_agent = models.CharField(
        'User Agent',
        max_length=500,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 't_pending_users'
        db_table_comment = 'Table des utilisateurs en attente de validation'
        verbose_name = 'Utilisateur en attente'
        verbose_name_plural = 'Utilisateurs en attente'

    def __str__(self):
        name = f"{self.prenom_role} {self.nom_role}".strip() if self.prenom_role or self.nom_role else self.email
        return f"{name} (en attente)"

    def get_full_name(self):
        """Retourne le nom complet."""
        if self.prenom_role and self.nom_role:
            return f"{self.prenom_role} {self.nom_role}"
        return self.email
