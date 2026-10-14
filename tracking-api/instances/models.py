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
    attente, en attente de code ou refusée (la structure corrige et redemande),
    jamais une demande acceptée — l'instance est alors enrôlée sur le hub, et la
    retirer est une décision qui se prend sur le hub, pas par un nouvel envoi.

    Seules les empreintes des jetons du hub sont reçues : les jetons restent sur
    l'instance. L'instance demandeuse est celle du jeton de suivi authentifié,
    jamais reprise de la requête.

    Confirmation par code : RNF prend contact avec l'administrateur, puis lui
    envoie par e-mail un code tiré au hasard ; l'administrateur le saisit sur son
    instance, et un code juste vaut acceptation (RNF a décidé en l'envoyant). Seule
    l'empreinte du code est conservée : qui lit la base ne peut pas l'utiliser.
    """
    EN_ATTENTE = 'en_attente'
    CODE_ENVOYE = 'code_envoye'
    ACCEPTEE = 'acceptee'
    REFUSEE = 'refusee'
    STATUTS = [
        (EN_ATTENTE, 'En attente'),
        (CODE_ENVOYE, 'Code envoyé'),
        (ACCEPTEE, 'Acceptée'),
        (REFUSEE, 'Refusée'),
    ]

    instance = models.OneToOneField(Instance, on_delete=models.CASCADE, related_name='adhesion_hub')
    instance_id_demande = models.CharField('identifiant demandé', max_length=50, db_index=True)
    libelle = models.CharField('nom de la structure', max_length=200)
    url_publique = models.CharField('URL publique', max_length=500, blank=True)
    empreinte_depot = models.CharField('empreinte du jeton de dépôt', max_length=64)
    empreinte_lecture = models.CharField('empreinte du jeton de lecture', max_length=64)

    # Contact déclaré par l'administrateur de l'instance dans sa demande.
    contact_nom = models.CharField('nom du contact', max_length=200)
    contact_email = models.EmailField('e-mail du contact')
    contact_telephone = models.CharField('téléphone du contact', max_length=50, blank=True)
    message = models.TextField('message', blank=True)
    # Adresse à laquelle RNF envoie le code : pré-remplie avec celle du contact,
    # mais modifiable — une adresse que RNF connaît déjà vaut mieux que celle
    # que le demandeur a lui-même déclarée.
    email_confirmation = models.EmailField("adresse d'envoi du code", blank=True)

    statut = models.CharField(max_length=20, choices=STATUTS, default=EN_ATTENTE, db_index=True)
    motif_refus = models.TextField('motif du refus', blank=True)
    hub_url = models.CharField('URL du hub', max_length=500, blank=True)

    # Code de confirmation : jamais en clair, ni en base ni dans un journal.
    code_empreinte = models.CharField('empreinte du code', max_length=64, blank=True)
    code_expire_le = models.DateTimeField('code valable jusqu\'au', null=True, blank=True)
    code_essais = models.PositiveSmallIntegerField('essais erronés', default=0)
    code_envoye_le = models.DateTimeField('code envoyé le', null=True, blank=True)
    code_envoye_par = models.CharField('code envoyé par', max_length=150, blank=True)

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

    def invalider_code(self):
        """Oublie le code en cours (empreinte, échéance, compteur)."""
        self.code_empreinte = ''
        self.code_expire_le = None
        self.code_essais = 0
