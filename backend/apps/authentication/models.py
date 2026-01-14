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
