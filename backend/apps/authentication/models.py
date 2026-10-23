"""
Modeles pour l'authentification.
"""
from django.db import models
from django.conf import settings


class ImpersonationLog(models.Model):
    """
    Journal d'audit des sessions d'impersonation.
    Enregistre toutes les actions d'impersonation pour la tracabilite.
    """

    impersonator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='impersonation_logs_as_admin',
        verbose_name="Super Admin",
        help_text="L'administrateur qui effectue l'impersonation"
    )

    impersonated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='impersonation_logs_as_target',
        verbose_name="Utilisateur cible",
        help_text="L'utilisateur dont le compte est visualise"
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Debut de session"
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fin de session"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )

    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name="User Agent"
    )

    reason = models.TextField(
        blank=True,
        default='',
        verbose_name="Motif",
        help_text="Raison optionnelle de l'impersonation"
    )

    class Meta:
        db_table = '"ccd_commons"."t_impersonation_log"'
        verbose_name = "Log d'impersonation"
        verbose_name_plural = "Logs d'impersonation"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['impersonator', 'started_at']),
            models.Index(fields=['impersonated_user', 'started_at']),
        ]

    def __str__(self):
        return f"{self.impersonator.email} -> {self.impersonated_user.email} ({self.started_at})"

    @property
    def is_active(self):
        """Retourne True si la session d'impersonation est toujours active."""
        return self.ended_at is None

    @property
    def duration(self):
        """Retourne la duree de la session en secondes."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None


class ConnexionGeoNature(models.Model):
    """
    Connexion GeoNature / UsersHub réglée dans Administration > Paramètres (#769).

    **Singleton** (``pk=1``). Pendant de ``RaccordementHub`` (#695) : brancher
    une instance sur son UsersHub ne demande plus d'éditer le ``.env`` ni de
    relancer les conteneurs. Lu à chaque connexion (``apps.authentication.reglages``).

    Précédence : le **mode** choisi ici prime sur ``AUTH_PROVIDER`` (l'installeur
    écrit toujours cette variable, l'écran n'aurait sinon jamais d'effet) ; les
    **autres réglages** viennent du ``.env`` quand ils y sont renseignés (champ
    verrouillé à l'écran), d'ici sinon.

    Le mot de passe du compte de lecture est chiffré (clé dérivée de la
    ``SECRET_KEY``) et n'est jamais renvoyé par l'API.
    """

    MODE_CHOICES = [
        ('', "Selon la configuration du serveur"),
        ('local', "Comptes CICADA"),
        ('geonature', "Comptes GeoNature / UsersHub"),
    ]

    mode = models.CharField("Mode de connexion", max_length=20, blank=True, default='', choices=MODE_CHOICES)
    libelle = models.CharField("Libellé du bouton de connexion", max_length=100, blank=True, default='')
    organismes_exclus = models.CharField("id_organisme UsersHub ignorés", max_length=500, blank=True, default='')
    code_application = models.CharField("Code de l'application CICADA", max_length=100, blank=True, default='')
    db_host = models.CharField("Hôte de la base UsersHub", max_length=255, blank=True, default='')
    db_port = models.PositiveIntegerField("Port", null=True, blank=True)
    db_name = models.CharField("Base", max_length=100, blank=True, default='')
    db_user = models.CharField("Compte de lecture", max_length=100, blank=True, default='')
    db_password_chiffre = models.TextField("Mot de passe (chiffré)", blank=True, default='')
    db_sslmode = models.CharField("Chiffrement", max_length=20, blank=True, default='')
    modifie_le = models.DateTimeField("Modifié le", auto_now=True)
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="Modifié par",
    )

    class Meta:
        db_table = '"ccd_commons"."t_connexion_geonature"'
        verbose_name = "Connexion GeoNature"
        verbose_name_plural = "Connexion GeoNature"

    @classmethod
    def charger(cls):
        """La ligne unique, ou une instance vierge non enregistrée."""
        return cls.objects.filter(pk=1).first() or cls(pk=1)

    def __str__(self):
        return f"Connexion GeoNature ({self.mode or 'selon le serveur'})"
