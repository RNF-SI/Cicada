"""
Modèles pour la gestion des Plans de Gestion.
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from datetime import datetime

# Import des modèles Enjeux et Responsabilités pour exposition
from .models_enjeux import (
    Enjeu,
    FacteurInfluence,
    Pression,
    Responsabilite,
    ObjectifLongTerme,
    NiveauExigence,
    ObjectifOperationnel,
    ResultatAttendu,
    CorOoPression,
    CorResponsabiliteTaxon,
    CorResponsabiliteHabitat,
    CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu,
    CorEnjeuTaxon,
    CorEnjeuHabitat,
    CorEnjeuGeologie,
)
from .models_indicateurs import (
    Indicateur,
    CorIndicateurTaxon,
    CorIndicateurHabitat,
    CorIndicateurGeologie,
    Metrique,
    Mesure,
)
from .models_operations import (
    Protocole,
    SuiviInventaire,
    Operation,
    CorOperationSite,
    OperationAnnee,
    FinanceOperation,
)


class PlanGestion(models.Model):
    """
    Modèle principal pour les Plans de Gestion.
    Basé sur t_plan_gestion du schéma general.
    """

    # Statuts possibles
    STATUT_CHOICES = [
        ('draft', _('Brouillon')),
        ('valide', _('Validé')),
        ('archive', _('Archivé')),
    ]
    
    id_pg = models.AutoField(primary_key=True)
    id_cdr = models.IntegerField(_("Identifiant CDR"), null=True, blank=True)
    nom = models.CharField(_("Nom du plan de gestion"), max_length=255, unique=True)
    slug = models.SlugField(
        _("Slug"),
        max_length=300,
        unique=True,
        help_text=_("Identifiant URL lisible, généré automatiquement depuis le nom")
    )

    # Gestion multi-sites
    gestion_partagee = models.BooleanField(
        _("Gestion partagée"),
        default=False,
        help_text=_("Ce plan concerne-t-il plusieurs sites ?")
    )

    # Période de validité
    annee_debut = models.IntegerField(
        _("Année de début"),
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )
    annee_fin = models.IntegerField(
        _("Année de fin"),
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )

    # Rang du plan de gestion
    rang = models.IntegerField(
        _("Rang du plan"),
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_("Numéro du plan (1er, 2ème, 3ème...)")
    )

    # Surface totale concernée
    surface = models.DecimalField(
        _("Surface totale concernée"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Surface en hectares")
    )

    # Contraintes réglementaires
    ct88 = models.BooleanField(
        _("Méthode de rédaction CT88"),
        default=False,
        help_text=_("Plan rédigé selon la méthode CT88")
    )
    risque_incendie = models.BooleanField(
        _("Risque incendie pris en compte"),
        default=False,
        help_text=_("Le risque incendie est-il pris en compte dans le plan ?")
    )

    # Validation CSPN
    date_validation_cspn = models.DateField(
        _("Date de validation CSPN"),
        null=True, blank=True
    )

    # Identifiant Doc'Gestion FCEN
    id_docgestion_fcen = models.CharField(
        _("ID Doc'Gestion FCEN"),
        max_length=100,
        null=True, blank=True
    )

    # Rédacteurs et relecteurs
    redacteurs = models.TextField(
        _("Rédacteurs"),
        null=True, blank=True
    )

    relecteurs = models.TextField(
        _("Relecteurs"),
        null=True, blank=True
    )

    autres_contributeurs = models.TextField(
        _("Autres contributeurs"),
        null=True, blank=True,
        help_text=_("Autres contributeurs au plan de gestion")
    )

    # Relations vers nomenclatures
    id_evaluation = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_evaluation',
        verbose_name=_("Type d'évaluation"),
        help_text=_("Type d'évaluation du plan (ex: évaluation intermédiaire, finale...)")
    )

    id_redacteur_type = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_redacteur_type',
        verbose_name=_("Type de rédacteur"),
        help_text=_("Type de rédacteur (ex: bureau d'étude, gestionnaire, autre...)")
    )

    redacteur_nom = models.CharField(
        _("Nom du rédacteur"),
        max_length=255,
        null=True, blank=True,
        help_text=_("Nom de la personne ou structure ayant rédigé le plan")
    )

    # Contenu
    commentaire = models.TextField(_("Commentaire"), null=True, blank=True)

    # Statut et versioning
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUT_CHOICES,
        default='draft'
    )
    version = models.CharField(
        _("Version"),
        max_length=20,
        default='1.0',
        help_text=_("Version du plan (ex: 1.0, 1.1, 2.0...)")
    )

    plan_parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='children',
        verbose_name=_("Plan parent"),
        help_text=_("Plan dont celui-ci est dérivé")
    )

    id_type_document = models.ForeignKey(
        'core.Nomenclature', on_delete=models.PROTECT,
        null=True, blank=True, related_name='plans_type_document',
        verbose_name=_("Type de document"),
        help_text=_("Plan initial, évaluation mi-parcours, plan révisé...")
    )

    # Géométrie (optionnelle, peut être calculée depuis les sites)
    geometrie = models.MultiPolygonField(
        _("Géométrie du plan"),
        srid=4326,
        null=True, blank=True,
        help_text=_("Emprise géographique du plan (calculée automatiquement si vide)")
    )

    # Métadonnées de traçabilité
    date_ajout = models.DateTimeField(
        _("Date de création"),
        auto_now_add=True
    )
    date_maj = models.DateTimeField(
        _("Date de modification"),
        auto_now=True
    )
    last_update = models.DateTimeField(
        _("Dernière mise à jour"),
        auto_now=True
    )

    # Utilisateurs responsables
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='plans_crees',
        verbose_name=_("Créateur"),
        help_text=_("Utilisateur ayant créé le plan")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_modifies',
        verbose_name=_("Dernier modificateur"),
        help_text=_("Utilisateur ayant effectué la dernière modification")
    )

    # Référents du plan (Many-to-Many)
    referents = models.ManyToManyField(
        'users.Role',
        blank=True,
        related_name='plans_referents',
        verbose_name=_("Référents du plan"),
        help_text=_("Utilisateurs référents pour ce plan")
    )

    class Meta:
        db_table = '"general"."t_plan_gestion"'
        db_table_comment = 'Plans de gestion des espaces naturels'
        verbose_name = _("Plan de gestion")
        verbose_name_plural = _("Plans de gestion")
        ordering = ['-date_maj', 'nom']

    def __str__(self):
        return self.nom

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self

    def save(self, *args, **kwargs):
        """Override save pour mettre à jour automatiquement certains champs."""
        # Mettre à jour l'utilisateur modificateur
        if hasattr(self, '_current_user') and self._current_user:
            if not self.pk:  # Création
                self.id_utilisateur_ajout = self._current_user
            self.id_utilisateur_maj = self._current_user

        # Auto-générer le slug depuis le nom
        if not self.slug:
            self.slug = self._generate_unique_slug()

        super().save(*args, **kwargs)

        # Mettre à jour la géométrie si nécessaire
        if not self.geometrie:
            self.update_geometrie()

    def _generate_unique_slug(self):
        """Génère un slug unique à partir du nom."""
        base_slug = slugify(self.nom)
        if not base_slug:
            base_slug = 'plan'
        slug = base_slug
        counter = 2
        qs = PlanGestion.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def update_geometrie(self):
        """Calcule et met à jour la géométrie du plan basée sur ses sites."""
        from django.contrib.gis.geos import MultiPolygon
        from django.db.models import Q
        
        # Récupérer toutes les géométries des sites liés
        sites_geom = []
        for cor_site_pg in self.sites.select_related('site'):
            if cor_site_pg.site.geom:
                if isinstance(cor_site_pg.site.geom, MultiPolygon):
                    sites_geom.extend(list(cor_site_pg.site.geom))
                else:
                    sites_geom.append(cor_site_pg.site.geom)
        
        if sites_geom:
            # Créer une MultiPolygon avec toutes les géométries
            self.geometrie = MultiPolygon(sites_geom)
            # Ne pas déclencher save() pour éviter la récursion
            PlanGestion.objects.filter(pk=self.pk).update(geometrie=self.geometrie)

    def get_sites(self):
        """Retourne la liste des sites associés au plan."""
        return [cor.site for cor in self.sites.select_related('site')]

    def get_organismes_gestionnaires(self):
        """Retourne la liste des organismes gestionnaires des sites du plan."""
        organismes = set()
        for site in self.get_sites():
            for cor_og_site in site.corogsite_set.select_related('uuid_og'):
                organismes.add(cor_og_site.uuid_og)
        return list(organismes)

    def is_multi_sites(self):
        """Vérifie si le plan concerne plusieurs sites."""
        return self.sites.count() > 1

    def get_periode_gestion(self):
        """Retourne la période de gestion sous forme de chaîne."""
        if self.annee_debut and self.annee_fin:
            return f"{self.annee_debut}-{self.annee_fin}"
        elif self.annee_debut:
            return f"À partir de {self.annee_debut}"
        elif self.annee_fin:
            return f"Jusqu'en {self.annee_fin}"
        return "Période non définie"

    def get_root_plan(self):
        """Remonte la chaîne de versions jusqu'au plan racine."""
        plan = self
        visited = {self.pk}
        while plan.plan_parent_id:
            if plan.plan_parent_id in visited:
                break
            visited.add(plan.plan_parent_id)
            plan = plan.plan_parent
        return plan

    def get_version_chain(self):
        """
        Retourne la chaîne complète de versions ordonnée chronologiquement.
        Remonte au root puis collecte tous les descendants.
        """
        root = self.get_root_plan()

        chain = []
        queue = [root]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current.pk in visited:
                continue
            visited.add(current.pk)
            chain.append({
                'id_pg': current.id_pg,
                'nom': current.nom,
                'slug': current.slug,
                'version': current.version,
                'statut': current.statut,
                'annee_debut': current.annee_debut,
                'annee_fin': current.annee_fin,
                'type_document': current.id_type_document.label if current.id_type_document else None,
                'type_document_mnemonique': current.id_type_document.mnemonique if current.id_type_document else None,
                'is_current': current.pk == self.pk,
            })
            for child in current.children.all().order_by('date_ajout'):
                queue.append(child)

        return chain

    def get_next_version(self):
        """Incrémente la version mineure (1.0 → 1.1, 2.3 → 2.4)."""
        try:
            parts = self.version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            return f"{major}.{minor + 1}"
        except (ValueError, IndexError):
            return '1.1'


class CorSitePg(models.Model):
    """
    Table de liaison entre Sites et Plans de Gestion.
    Un plan peut concerner plusieurs sites, et un site peut avoir plusieurs plans.
    """

    site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        verbose_name=_("Site")
    )
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='sites',
        verbose_name=_("Plan de gestion")
    )
    rang = models.IntegerField(
        _("Rang"),
        null=True, blank=True,
        help_text=_("Ordre d'importance du site dans le plan (1=principal)")
    )

    # Métadonnées
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )
    commentaire = models.TextField(
        _("Commentaire"),
        null=True, blank=True,
        help_text=_("Précisions sur le lien entre ce site et le plan")
    )

    class Meta:
        db_table = '"general"."cor_ep_pg"'
        db_table_comment = 'Liaison entre espaces protégés et plans de gestion'
        verbose_name = _("Espace protégé - Plan de gestion")
        verbose_name_plural = _("Espaces protégés - Plans de gestion")
        unique_together = ['site', 'plan_de_gestion']
        ordering = ['rang', 'site__nom_site']

    def __str__(self):
        rang_str = f" (rang {self.rang})" if self.rang else ""
        return f"{self.site.nom_site} - {self.plan_de_gestion.nom}{rang_str}"


class CorRolePlan(models.Model):
    """
    Table de liaison entre Utilisateurs et Plans de Gestion.
    Permet de définir les membres et référents d'un plan.
    Similaire à CorRoleSite pour les sites.
    """

    id_role = models.ForeignKey(
        'users.Role',
        on_delete=models.CASCADE,
        verbose_name=_("Utilisateur"),
        related_name='plan_associations'
    )
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        verbose_name=_("Plan de gestion"),
        related_name='membres'
    )
    referent = models.BooleanField(
        _("Référent"),
        default=False,
        help_text=_("L'utilisateur est-il référent de ce plan ?")
    )

    # Métadonnées
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )
    commentaire = models.TextField(
        _("Commentaire"),
        null=True, blank=True,
        help_text=_("Précisions sur le rôle de l'utilisateur dans le plan")
    )

    class Meta:
        db_table = '"general"."cor_role_plan"'
        db_table_comment = 'Liaison entre utilisateurs et plans de gestion'
        verbose_name = _("Utilisateur - Plan de gestion")
        verbose_name_plural = _("Utilisateurs - Plans de gestion")
        unique_together = ['id_role', 'plan_de_gestion']
        ordering = ['-referent', 'id_role__nom_role']

    def __str__(self):
        role_type = "Référent" if self.referent else "Membre"
        return f"{self.id_role.email} - {self.plan_de_gestion.nom} ({role_type})"


class CorRedacteurPlan(models.Model):
    """
    Table de liaison entre Plans de Gestion et Organismes Rédacteurs.
    Un organisme rédacteur peut éditer le plan mais n'apparaît pas
    dans la ventilation budgétaire (réservée aux organismes gestionnaires).
    """

    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        verbose_name=_("Plan de gestion"),
        related_name='organismes_redacteurs'
    )
    uuid_og = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.CASCADE,
        to_field='uuid_organisme',
        db_column='uuid_og',
        verbose_name=_("Organisme rédacteur")
    )
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )

    class Meta:
        db_table = '"general"."cor_redacteur_plan"'
        db_table_comment = 'Organismes rédacteurs des plans de gestion'
        verbose_name = _("Organisme rédacteur - Plan")
        verbose_name_plural = _("Organismes rédacteurs - Plans")
        unique_together = ['plan_de_gestion', 'uuid_og']

    def __str__(self):
        return f"{self.uuid_og.nom_organisme} - {self.plan_de_gestion.nom}"


class CorPgFichier(models.Model):
    """
    Table de liaison entre Plans de Gestion et fichiers joints.
    Gestion des pièces jointes et documents associés aux plans.
    """

    TYPE_FICHIER_CHOICES = [
        ('document', _('Document principal')),
        ('annexe', _('Annexe')),
        ('carte', _('Carte')),
        ('photo', _('Photographie')),
        ('rapport', _("Rapport d'étude")),
        ('autre', _('Autre')),
    ]

    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='fichiers',
        verbose_name=_("Plan de gestion")
    )

    # Informations sur le fichier
    nom_fichier = models.CharField(
        _("Nom du fichier"),
        max_length=255,
        help_text=_("Nom original du fichier uploadé")
    )
    chemin_fichier = models.CharField(
        _("Chemin du fichier"),
        max_length=500,
        help_text=_("Chemin d'accès au fichier sur le serveur")
    )
    type_fichier = models.CharField(
        _("Type de fichier"),
        max_length=20,
        choices=TYPE_FICHIER_CHOICES,
        default='document'
    )
    taille_fichier = models.BigIntegerField(
        _("Taille du fichier (bytes)"),
        null=True, blank=True
    )
    extension = models.CharField(
        _("Extension"),
        max_length=10,
        null=True, blank=True
    )

    # Métadonnées descriptives
    titre = models.CharField(
        _("Titre"),
        max_length=255,
        null=True, blank=True,
        help_text=_("Titre descriptif du document")
    )
    description = models.TextField(
        _("Description"),
        null=True, blank=True
    )
    auteur = models.CharField(
        _("Auteur"),
        max_length=255,
        null=True, blank=True
    )
    date_document = models.DateField(
        _("Date du document"),
        null=True, blank=True,
        help_text=_("Date de création/rédaction du document")
    )

    # Métadonnées techniques
    date_upload = models.DateTimeField(
        _("Date d'upload"),
        auto_now_add=True
    )
    id_utilisateur_upload = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        verbose_name=_("Utilisateur ayant uploadé"),
        help_text=_("Utilisateur ayant ajouté ce fichier")
    )

    # Options d'affichage
    public = models.BooleanField(
        _("Fichier public"),
        default=False,
        help_text=_("Le fichier est-il accessible publiquement ?")
    )
    ordre_affichage = models.IntegerField(
        _("Ordre d'affichage"),
        default=0,
        help_text=_("Ordre d'affichage dans la liste des fichiers")
    )

    class Meta:
        db_table = '"fichiers"."t_fichiers"'
        db_table_comment = 'Fichiers associés aux plans de gestion'
        verbose_name = _("Fichier plan de gestion")
        verbose_name_plural = _("Fichiers plans de gestion")
        ordering = ['ordre_affichage', 'nom_fichier']

    def __str__(self):
        return f"{self.titre or self.nom_fichier} ({self.plan_de_gestion.nom})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.plan_de_gestion

    def get_file_size_human(self):
        """Retourne la taille du fichier dans un format lisible."""
        if not self.taille_fichier:
            return "Taille inconnue"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.taille_fichier < 1024.0:
                return f"{self.taille_fichier:.1f} {unit}"
            self.taille_fichier /= 1024.0
        return f"{self.taille_fichier:.1f} TB"

    def is_image(self):
        """Vérifie si le fichier est une image."""
        if self.extension:
            return self.extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']
        return False

    def is_document(self):
        """Vérifie si le fichier est un document.""" 
        if self.extension:
            return self.extension.lower() in ['.pdf', '.doc', '.docx', '.odt', '.txt']
        return False
    
    def handle_file_upload(self, uploaded_file):
        """Gère l'upload d'un fichier."""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage
        
        # Déterminer le nom du fichier s'il n'est pas déjà défini
        if not self.nom_fichier:
            self.nom_fichier = uploaded_file.name
        
        # Déterminer l'extension
        _, ext = os.path.splitext(self.nom_fichier)
        self.extension = ext.lower()
        
        # Déterminer la taille
        self.taille_fichier = uploaded_file.size
        
        # Déterminer le type de fichier automatiquement
        if self.is_image():
            self.type_fichier = 'image'
        elif self.extension in ['.pdf']:
            self.type_fichier = 'document'
        elif self.extension in ['.jpg', '.jpeg', '.png', '.gif'] and 'carte' in self.nom_fichier.lower():
            self.type_fichier = 'carte'
        
        # Définir le chemin de stockage
        upload_dir = f"plans/{self.plan_de_gestion.id_pg}"
        
        # Créer le répertoire s'il n'existe pas
        full_upload_dir = os.path.join(settings.MEDIA_ROOT, upload_dir)
        os.makedirs(full_upload_dir, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = os.path.join(upload_dir, self.nom_fichier)
        self.chemin_fichier = default_storage.save(file_path, uploaded_file)
        
        # Sauvegarder les métadonnées
        self.save()