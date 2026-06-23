"""
Modèles pour la gestion des utilisateurs, organismes et sites.
"""
import uuid
from datetime import datetime

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.gis.db import models
from django.core.validators import EmailValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class RoleManager(BaseUserManager):
    """Manager personnalisé pour le modèle Role."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Crée et retourne un utilisateur avec email et mot de passe."""
        if not email:
            raise ValueError(_('L\'email est obligatoire'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Crée et retourne un superutilisateur."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('active', True)
        extra_fields.setdefault('role_level', 'super_admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class Role(AbstractUser):
    """
    Modèle utilisateur personnalisé basé sur la table t_roles.
    Utilise l'email comme identifiant unique au lieu du username.
    """
    
    # Niveaux de permission/rôles
    # Note: Le rôle 'referent' a été supprimé. Un utilisateur est considéré comme
    # "référent" s'il est référent d'au moins un site ou plan de gestion.
    ROLE_CHOICES = [
        ('utilisateur', _('Utilisateur')),
        ('admin_og', _('Administrateur Organisme')),
        ('redacteur_principal', _('Rédacteur Général')),
        ('super_admin', _('Super Administrateur')),
    ]
    
    # Désactiver username d'AbstractUser
    username = None
    
    # Champs spécifiques à t_roles
    groupe = models.BooleanField(default=False, verbose_name=_("Est un groupe"))
    id_role = models.AutoField(primary_key=True)
    uuid_role = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    identifiant = models.CharField(max_length=100, null=True, blank=True)
    nom_role = models.CharField(_("Nom"), max_length=50, null=True, blank=True)
    prenom_role = models.CharField(_("Prénom"), max_length=50, null=True, blank=True)
    desc_role = models.TextField(_("Description"), null=True, blank=True)
    pass_plus = models.TextField(null=True, blank=True)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name=_("Adresse email")
    )
    id_organisme = models.ForeignKey(
        'BibOrganismes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_field='uuid_organisme',
        db_column='uuid_organisme',
        verbose_name=_("Organisme")
    )
    remarques = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True, verbose_name=_("Actif"))
    role_level = models.CharField(
        _("Niveau de rôle"),
        max_length=20,
        choices=ROLE_CHOICES,
        default='utilisateur'
    )
    # Champs pour la validation et desactivation
    pending_validation = models.BooleanField(
        default=False,
        verbose_name=_("En attente de validation"),
        help_text=_("Utilisateur inscrit mais en attente de validation")
    )
    deactivation_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Motif de desactivation")
    )
    deactivated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deactivated_users',
        verbose_name=_("Desactive par")
    )
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Desactive le")
    )
    # Champs RGPD pour suppression de compte
    deletion_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Demande de suppression le"),
        help_text=_("Date de demande de suppression du compte (RGPD)")
    )
    is_anonymized = models.BooleanField(
        default=False,
        verbose_name=_("Compte anonymise"),
        help_text=_("Le compte a ete anonymise suite a une demande RGPD")
    )
    anonymized_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Anonymise le")
    )
    champs_addi = models.TextField(_("Champs additionnels"), null=True, blank=True)
    date_insert = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    
    # Manager personnalisé
    objects = RoleManager()
    
    # Spécifique à Django
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom_role', 'prenom_role']

    def __str__(self):
        if self.prenom_role and self.nom_role:
            return f"{self.prenom_role} {self.nom_role}"
        return self.email

    def get_full_name(self):
        """Retourne le nom complet."""
        if self.prenom_role and self.nom_role:
            return f"{self.prenom_role} {self.nom_role}"
        return self.email

    def get_short_name(self):
        """Retourne le prénom ou l'email."""
        return self.prenom_role or self.email
    
    def is_super_admin(self):
        """Vérifie si l'utilisateur est Super Administrateur."""
        return self.role_level == 'super_admin' or self.is_superuser
    
    def is_redacteur_principal(self):
        """Vérifie si l'utilisateur est Rédacteur Principal."""
        return self.role_level == 'redacteur_principal'

    def is_admin_organisme(self):
        """Vérifie si l'utilisateur est Administrateur d'organisme (ou rôle supérieur)."""
        return self.role_level in ['admin_og', 'redacteur_principal', 'super_admin'] or self.is_superuser

    def can_manage_plan_lifecycle(self):
        """Vérifie si l'utilisateur peut gérer le cycle de vie des plans (valider/archiver/évaluation).
        #346 — Le Rédacteur Principal peut désormais gérer le cycle de vie, au même
        titre que l'admin organisme, le super admin et le référent du plan."""
        return self.is_admin_organisme()
    
    def is_referent(self):
        """
        Vérifie si l'utilisateur est considéré comme "référent".
        Un utilisateur est référent s'il :
        - Est admin organisme ou super admin
        - Est référent validé d'au moins un site
        - Est référent d'au moins un plan de gestion
        """
        if self.is_admin_organisme():
            return True
        # Référent d'au moins un site validé ?
        if CorRoleSite.objects.filter(id_role=self, referent=True, referent_valid=True).exists():
            return True
        # Référent d'au moins un plan ?
        if self.plans_referents.exists():
            return True
        return False
    
    def can_manage_organisme(self, organisme):
        """Vérifie si l'utilisateur peut gérer un organisme donné."""
        if self.is_super_admin():
            return True
        if self.is_admin_organisme() and self.id_organisme == organisme:
            return True
        return False
    
    def can_manage_site(self, site):
        """Vérifie si l'utilisateur peut gérer un site donné."""
        if self.is_super_admin():
            return True

        # Vérifier si référent du site
        try:
            cor_role_site = CorRoleSite.objects.get(id_role=self, id_site=site)
            if cor_role_site.referent and cor_role_site.referent_valid:
                return True
        except CorRoleSite.DoesNotExist:
            pass

        # Vérifier si admin organisme gestionnaire
        if self.is_admin_organisme() and self.id_organisme:
            site_organismes = CorOgSite.objects.filter(id_site=site)
            for cor_og_site in site_organismes:
                if cor_og_site.uuid_og.id_organisme == self.id_organisme.id_organisme:
                    return True

        return False

    def accessible_site_ids(self):
        """
        Retourne la liste des id_site auxquels l'utilisateur a accès en lecture.

        Un utilisateur a accès à un site si :
        - il est super admin ou rédacteur principal (accès global) — on renvoie
          alors None pour signaler "tous les sites"
        - il est membre direct du site (CorRoleSite)
        - son organisme gère le site (CorOgSite)

        L'appartenance à un plan de gestion qui couvre le site ne donne
        *pas* automatiquement l'accès au site : dans la page plan, les
        sites non rattachés à l'utilisateur s'affichent en mode verrouillé
        avec un bouton "Se lier au site" pour initier la liaison.

        Used by :
        - SiteViewSet.get_queryset (liste des sites accessibles)
        - PlanSiteListSerializer.get_current_user_has_access (cadenas /
          bouton "Se lier au site" dans la carte du plan)
        """
        if self.is_super_admin() or self.is_redacteur_principal():
            return None  # accès global

        direct = set(
            CorRoleSite.objects.filter(id_role=self).values_list('id_site', flat=True)
        )
        via_org = set()
        if self.id_organisme:
            via_org = set(
                CorOgSite.objects.filter(uuid_og=self.id_organisme)
                .values_list('id_site', flat=True)
            )
        # #440 : sites que l'utilisateur a lui-même créés et qui sont en attente
        # de validation (il n'est pas encore référent et son organisme n'est pas
        # encore rattaché). Sans cela, il ne pourrait ni revoir ni corriger le
        # site qu'il vient de créer tant que la validation n'a pas eu lieu.
        from apps.notifications.models import ValidationRequest
        pending_created = set(
            ValidationRequest.objects.filter(
                request_type='site_creation',
                status='pending',
                requester=self,
                target_site__isnull=False,
            ).values_list('target_site', flat=True)
        )
        return direct | via_org | pending_created

    def has_access_to_site(self, site):
        """Vérifie si l'utilisateur a accès en lecture au site donné."""
        ids = self.accessible_site_ids()
        if ids is None:
            return True
        return site.id_site in ids

    def request_deletion(self):
        """
        Demande la suppression du compte (RGPD).
        Enregistre la date de demande et desactive le compte.
        """
        from django.utils import timezone
        self.deletion_requested_at = timezone.now()
        self.active = False
        self.save(update_fields=['deletion_requested_at', 'active'])

    def anonymize(self):
        """
        Anonymise les donnees personnelles du compte (RGPD).
        Appele apres le delai de grace de 30 jours.
        """
        from django.utils import timezone
        import uuid

        # Generer un identifiant unique pour le compte anonymise
        anon_id = str(uuid.uuid4())[:8]

        # Anonymiser les donnees personnelles
        self.email = f"anonymized_{anon_id}@deleted.local"
        self.nom_role = "Utilisateur"
        self.prenom_role = "Anonymise"
        self.desc_role = None
        self.identifiant = None
        self.remarques = None
        self.champs_addi = None
        self.pass_plus = None

        # Supprimer le mot de passe
        self.set_unusable_password()

        # Marquer comme anonymise
        self.is_anonymized = True
        self.anonymized_at = timezone.now()
        self.active = False

        self.save()

    def can_be_anonymized(self):
        """
        Verifie si le compte peut etre anonymise.
        Le delai de grace est de 30 jours apres la demande.
        """
        from django.utils import timezone
        from datetime import timedelta

        if not self.deletion_requested_at:
            return False
        if self.is_anonymized:
            return False

        grace_period = timedelta(days=30)
        return timezone.now() >= self.deletion_requested_at + grace_period

    class Meta:
        db_table = '"utilisateurs"."t_roles"'
        db_table_comment = 'Table des utilisateurs et groupes'
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")


class BibOrganismes(models.Model):
    """
    Modèle pour les organismes gestionnaires.
    Table bib_organismes dans le schéma utilisateurs.
    """
    
    id_organisme = models.AutoField(primary_key=True)
    uuid_organisme = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)
    nom_organisme = models.CharField(_("Nom"), max_length=255, null=True, blank=True)
    adresse_organisme = models.TextField(_("Adresse"), null=True, blank=True)
    cp_organisme = models.CharField(_("Code postal"), max_length=10, null=True, blank=True)
    ville_organisme = models.CharField(_("Ville"), max_length=100, null=True, blank=True)
    tel_organisme = models.CharField(_("Téléphone"), max_length=20, null=True, blank=True)
    fax_organisme = models.CharField(_("Fax"), max_length=20, null=True, blank=True)
    email_organisme = models.EmailField(_("Email"), null=True, blank=True)
    url_organisme = models.URLField(_("Site web"), null=True, blank=True)
    url_logo = models.URLField(_("Logo"), null=True, blank=True)
    id_parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Organisme parent")
    )
    id_type_organisme = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'id_type__mnemonique': 'TYPE_ORGANISME'},
        db_column='id_type_organisme',
        verbose_name=_("Type d'organisme"),
        help_text=_("CEN, RNF, DREAL, PNR, OFB, etc."),
        related_name='organismes_type'
    )
    additional_data = models.JSONField(default=dict, null=True, blank=True)
    meta_create_date = models.DateTimeField(auto_now_add=True)
    meta_update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"utilisateurs"."bib_organismes"'
        db_table_comment = 'Table des organismes gestionnaires'
        verbose_name = _("Organisme")
        verbose_name_plural = _("Organismes")

    def __str__(self):
        return self.nom_organisme or f"Organisme {self.id_organisme}"


class Site(models.Model):
    """
    Modèle pour les sites (ex-espaces protégés).
    Table t_site dans le schéma referentiels.
    """

    id_site = models.AutoField(primary_key=True)
    slug = models.SlugField(
        _("Slug"),
        max_length=280,
        unique=True,
        blank=True,
        help_text=_("Identifiant URL unique généré automatiquement à partir du nom")
    )
    id_local = models.CharField(_("Identifiant local"), max_length=50, null=True, blank=True)
    id_inpn = models.CharField(_("Identifiant INPN"), max_length=50, null=True, blank=True, unique=True)
    id_type_site = models.ForeignKey(
        'core.Nomenclature',  # À créer dans core app
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Type de site")
    )
    type_site_precision = models.CharField(
        _("Précision du type de site"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Précision quand le type est 'Autre'")
    )
    date_crea = models.DateField(_("Date de création"), null=True, blank=True)
    nom_site = models.CharField(_("Nom du site"), max_length=255)
    jonction_nom = models.CharField(_("Jonction nom"), max_length=50, null=True, blank=True)
    surf_off = models.FloatField(_("Surface officielle (ha)"), null=True, blank=True)
    geom = models.MultiPolygonField(_("Géométrie"), srid=4326, null=True, blank=True)
    geom_pt = models.PointField(_("Point de référence"), srid=4326, null=True, blank=True)
    modif_adm = models.DateField(_("Modification administrative"), null=True, blank=True)
    modif_geo = models.DateField(_("Modification géographique"), null=True, blank=True)
    marin = models.BooleanField(_("Milieu marin"), default=False)
    outre_mer = models.BooleanField(_("Outre-mer"), default=False)
    active = models.BooleanField(_("Actif"), default=True)

    class Meta:
        db_table = '"referentiels"."t_espace_protege"'
        db_table_comment = 'Table des espaces protégés'
        verbose_name = _("Espace protégé")
        verbose_name_plural = _("Espaces protégés")

    def __str__(self):
        return self.nom_site

    def save(self, *args, **kwargs):
        """Génère automatiquement le slug à partir du nom du site."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """
        Génère un slug unique à partir du nom du site.
        Si le slug existe déjà, ajoute un suffixe numérique.
        """
        base_slug = slugify(self.nom_site, allow_unicode=False)
        if not base_slug:
            base_slug = f"site-{self.id_site or 'new'}"

        slug = base_slug
        counter = 1

        # Chercher un slug unique
        while Site.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug


class CorRoleSite(models.Model):
    """
    Table de liaison entre utilisateurs et sites avec permissions.
    """

    id_site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        db_column='id_site'
    )
    id_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        db_column='id_role'
    )
    referent = models.BooleanField(_("Référent"), default=False)
    referent_valid = models.BooleanField(_("Référent validé"), default=False)
    conservateur = models.BooleanField(_("Conservateur"), default=False)

    class Meta:
        db_table = '"utilisateurs"."cor_role_ep"'
        db_table_comment = 'Liaison utilisateurs - espaces protégés'
        unique_together = ['id_site', 'id_role']
        verbose_name = _("Utilisateur - Espace protégé")
        verbose_name_plural = _("Utilisateurs - Espaces protégés")

    def __str__(self):
        return f"{self.id_role} - {self.id_site}"


class CorOgSite(models.Model):
    """
    Table de liaison entre organismes et sites.
    Un seul organisme peut être gestionnaire principal par site.
    """

    id_site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        db_column='id_site'
    )
    uuid_og = models.ForeignKey(
        BibOrganismes,
        on_delete=models.CASCADE,
        to_field='uuid_organisme',
        db_column='uuid_organisme'
    )
    principal = models.BooleanField(_("Gestionnaire principal"), default=False)

    class Meta:
        db_table = '"referentiels"."cor_ep_og"'
        db_table_comment = 'Liaison espaces protégés - organismes gestionnaires'
        unique_together = ['id_site', 'uuid_og']
        verbose_name = _("Espace protégé - Organisme")
        verbose_name_plural = _("Espaces protégés - Organismes")

    def __str__(self):
        return f"{self.id_site} - {self.uuid_og}"

    def save(self, *args, **kwargs):
        """
        Override save pour garantir un seul organisme principal par site.
        Si cet organisme est défini comme principal, les autres perdent ce statut.
        """
        if self.principal:
            # Retirer le statut principal des autres organismes pour ce site
            CorOgSite.objects.filter(
                id_site=self.id_site,
                principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    @classmethod
    def set_principal(cls, site, organisme):
        """
        Définit un organisme comme gestionnaire principal d'un site.
        Retourne True si la modification a été effectuée, False sinon.
        """
        try:
            cor_og_site = cls.objects.get(id_site=site, uuid_og=organisme)
            if not cor_og_site.principal:
                cor_og_site.principal = True
                cor_og_site.save()
                return True
            return False  # Déjà principal
        except cls.DoesNotExist:
            return False

    @classmethod
    def get_principal(cls, site):
        """
        Retourne l'organisme gestionnaire principal d'un site, ou None.
        """
        try:
            cor = cls.objects.get(id_site=site, principal=True)
            return cor.uuid_og
        except cls.DoesNotExist:
            return None


class CorRedacteurSite(models.Model):
    """
    Table de liaison entre sites et organismes rédacteurs.
    Distinct de CorOgSite (organismes gestionnaires).
    L'organisme rédacteur n'est pas gestionnaire mais peut contribuer à la rédaction.
    """

    id_site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        db_column='id_site',
        related_name='organismes_redacteurs'
    )
    uuid_og = models.ForeignKey(
        BibOrganismes,
        on_delete=models.CASCADE,
        to_field='uuid_organisme',
        db_column='uuid_organisme',
        verbose_name=_("Organisme rédacteur")
    )
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )

    class Meta:
        db_table = '"referentiels"."cor_redacteur_site"'
        db_table_comment = 'Organismes rédacteurs des sites'
        verbose_name = _("Site - Organisme rédacteur")
        verbose_name_plural = _("Sites - Organismes rédacteurs")
        unique_together = ['id_site', 'uuid_og']

    def __str__(self):
        return f"{self.id_site} - {self.uuid_og} (rédacteur)"


class BulkImportJob(models.Model):
    """
    Suivi des imports en masse de sites.
    Utilisé pour les imports asynchrones (>50 sites) via Celery.
    """

    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('processing', _('En cours')),
        ('completed', _('Terminé')),
        ('failed', _('Échoué')),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='bulk_import_jobs',
        verbose_name=_('Utilisateur'),
    )
    status = models.CharField(
        _('Statut'),
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
    )
    total_sites = models.IntegerField(_('Total sites'), default=0)
    processed_sites = models.IntegerField(_('Sites traités'), default=0)
    created_sites = models.IntegerField(_('Sites créés'), default=0)
    failed_sites = models.IntegerField(_('Sites échoués'), default=0)
    validation_pending_sites = models.IntegerField(_('Sites en attente de validation'), default=0)
    import_data = models.JSONField(_('Données d\'import'), default=dict)
    result_data = models.JSONField(_('Données de résultat'), default=dict)
    created_at = models.DateTimeField(_('Créé le'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Terminé le'), null=True, blank=True)

    class Meta:
        db_table = '"ccd_commons"."t_bulk_import_jobs"'
        verbose_name = _('Job d\'import en masse')
        verbose_name_plural = _('Jobs d\'import en masse')
        ordering = ['-created_at']

    def __str__(self):
        return f"BulkImportJob #{self.id} - {self.status} ({self.processed_sites}/{self.total_sites})"