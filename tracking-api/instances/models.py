"""
Modèles pour le suivi des instances CICADA
"""
import uuid
from django.db import models
from django.utils import timezone


class Instance(models.Model):
    """Instance CICADA enregistrée"""
    # Identifiant unique
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Données techniques (toujours collectées)
    version = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Données nominatives (uniquement si consentement RGPD)
    admin_name = models.CharField(max_length=200, null=True, blank=True)
    admin_email = models.EmailField(null=True, blank=True)
    structure_name = models.CharField(max_length=200, null=True, blank=True)
    rgpd_consent = models.BooleanField(default=False)
    rgpd_consent_date = models.DateTimeField(null=True, blank=True)
    rgpd_withdrawal_date = models.DateTimeField(null=True, blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tracking_instances'
        indexes = [
            models.Index(fields=['version']),
            models.Index(fields=['last_heartbeat']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Instance {self.token} (v{self.version})"


class Heartbeat(models.Model):
    """Historique des heartbeats (optionnel)"""
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='heartbeats')
    timestamp = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'tracking_heartbeats'
        indexes = [
            models.Index(fields=['instance', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"Heartbeat {self.instance.token} at {self.timestamp}"
