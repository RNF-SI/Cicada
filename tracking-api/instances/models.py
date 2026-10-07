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

    # InstanceTokenAuthentication renvoie l'instance comme « utilisateur » de la
    # requête : DRF (permission IsAuthenticated, UserRateThrottle) lit alors
    # request.user.is_authenticated. Sans ces attributs, tout appel authentifié
    # (heartbeat, instances/me) tombait en 500 (#226).
    is_authenticated = True
    is_anonymous = False

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


class AdhesionHub(models.Model):
    """Demande d'adhésion d'une instance au hub d'exploration fédérée (#696).

    Une demande par instance : une nouvelle demande remplace celle qui était en
    attente ou refusée (la structure corrige et redemande), jamais une demande
    acceptée — l'instance est alors enrôlée sur le hub, et la retirer est une
    décision qui se prend sur le hub, pas par un nouvel envoi.

    Seules les empreintes des jetons du hub sont reçues : les jetons restent sur
    l'instance. Le code est recalculé ici à partir du jeton de suivi de l'instance
    authentifiée, jamais repris de la requête.
    """
    EN_ATTENTE = 'en_attente'
    ACCEPTEE = 'acceptee'
    REFUSEE = 'refusee'
    STATUTS = [
        (EN_ATTENTE, 'En attente'),
        (ACCEPTEE, 'Acceptée'),
        (REFUSEE, 'Refusée'),
    ]

    instance = models.OneToOneField(Instance, on_delete=models.CASCADE, related_name='adhesion_hub')
    instance_id_demande = models.CharField('identifiant demandé', max_length=50, db_index=True)
    libelle = models.CharField('nom de la structure', max_length=200)
    url_publique = models.CharField('URL publique', max_length=500, blank=True)
    empreinte_depot = models.CharField('empreinte du jeton de dépôt', max_length=64)
    empreinte_lecture = models.CharField('empreinte du jeton de lecture', max_length=64)
    code = models.CharField('code de vérification', max_length=7)
    statut = models.CharField(max_length=20, choices=STATUTS, default=EN_ATTENTE, db_index=True)
    motif_refus = models.TextField('motif du refus', blank=True)
    hub_url = models.CharField('URL du hub', max_length=500, blank=True)
    demandee_le = models.DateTimeField('demandée le', default=timezone.now)
    traitee_le = models.DateTimeField('traitée le', null=True, blank=True)
    traitee_par = models.CharField('traitée par', max_length=150, blank=True)

    class Meta:
        db_table = 'tracking_adhesions_hub'
        verbose_name = "adhésion au hub"
        verbose_name_plural = "adhésions au hub"
        ordering = ['-demandee_le']

    def __str__(self):
        return f"{self.libelle} ({self.instance_id_demande}) — {self.get_statut_display()}"
