"""
Modèles pour la gestion des Plans de Gestion.
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime


class PlanGestion(models.Model):
    """
    Modèle principal pour les Plans de Gestion.
    Basé sur t_plan_gestion du schéma general.
    """
    
    # Statuts possibles
    STATUT_CHOICES = [
        ('draft', 'Brouillon'),
        ('valide', 'Validé'), 
        ('archive', 'Archivé'),
    ]
    
    id_pg = models.AutoField(primary_key=True)
    id_cdr = models.IntegerField("Identifiant CDR", null=True, blank=True)
    nom = models.CharField("Nom du plan de gestion", max_length=255)
    
    # Gestion multi-sites
    gestion_partagee = models.BooleanField(
        "Gestion partagée", 
        default=False,
        help_text="Ce plan concerne-t-il plusieurs sites ?"
    )
    
    # Période de validité
    annee_debut = models.IntegerField(
        "Année de début",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )
    annee_fin = models.IntegerField(
        "Année de fin", 
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )
    
    # Contraintes réglementaires
    ct88 = models.BooleanField(
        "Circulaire CT88",
        default=False,
        help_text="Plan soumis à la circulaire CT88"
    )
    risque_incendie = models.BooleanField(
        "Risque incendie pris en compte",
        default=False,
        help_text="Le risque incendie est-il pris en compte dans le plan ?"
    )
    
    # Relations vers nomenclatures
    id_evaluation = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_evaluation',
        verbose_name="Type d'évaluation",
        help_text="Type d'évaluation du plan (ex: évaluation intermédiaire, finale...)"
    )
    
    id_redacteur_type = models.ForeignKey(
        'core.Nomenclature', 
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_redacteur_type',
        verbose_name="Type de rédacteur",
        help_text="Type de rédacteur (ex: bureau d'étude, gestionnaire, autre...)"
    )
    
    redacteur_nom = models.CharField(
        "Nom du rédacteur",
        max_length=255,
        null=True, blank=True,
        help_text="Nom de la personne ou structure ayant rédigé le plan"
    )
    
    # Contenu
    commentaire = models.TextField("Commentaire", null=True, blank=True)
    
    # Statut et versioning
    statut = models.CharField(
        "Statut", 
        max_length=20,
        choices=STATUT_CHOICES,
        default='draft'
    )
    version = models.CharField(
        "Version", 
        max_length=20, 
        default='1.0',
        help_text="Version du plan (ex: 1.0, 1.1, 2.0...)"
    )
    
    # Géométrie (optionnelle, peut être calculée depuis les sites)
    geometrie = models.MultiPolygonField(
        "Géométrie du plan",
        srid=4326,
        null=True, blank=True,
        help_text="Emprise géographique du plan (calculée automatiquement si vide)"
    )
    
    # Métadonnées de traçabilité
    date_ajout = models.DateTimeField(
        "Date de création",
        auto_now_add=True
    )
    date_maj = models.DateTimeField(
        "Date de modification", 
        auto_now=True
    )
    last_update = models.DateTimeField(
        "Dernière mise à jour",
        auto_now=True
    )
    
    # Utilisateurs responsables
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='plans_crees',
        verbose_name="Créateur",
        help_text="Utilisateur ayant créé le plan"
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT, 
        null=True, blank=True,
        related_name='plans_modifies',
        verbose_name="Dernier modificateur",
        help_text="Utilisateur ayant effectué la dernière modification"
    )
    
    # Référents du plan (Many-to-Many)
    referents = models.ManyToManyField(
        'users.Role',
        blank=True,
        related_name='plans_referents',
        verbose_name="Référents du plan",
        help_text="Utilisateurs référents pour ce plan"
    )

    class Meta:
        db_table = 't_plan_gestion'
        db_table_comment = 'Plans de gestion des espaces naturels'
        verbose_name = "Plan de gestion"
        verbose_name_plural = "Plans de gestion"
        ordering = ['-date_maj', 'nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        """Override save pour mettre à jour automatiquement certains champs."""
        # Mettre à jour l'utilisateur modificateur
        if hasattr(self, '_current_user') and self._current_user:
            if not self.pk:  # Création
                self.id_utilisateur_ajout = self._current_user
            self.id_utilisateur_maj = self._current_user
            
        super().save(*args, **kwargs)
        
        # Mettre à jour la géométrie si nécessaire
        if not self.geometrie:
            self.update_geometrie()

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


class CorSitePg(models.Model):
    """
    Table de liaison entre Sites et Plans de Gestion.
    Un plan peut concerner plusieurs sites, et un site peut avoir plusieurs plans.
    """
    
    site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        verbose_name="Site"
    )
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='sites',
        verbose_name="Plan de gestion"
    )
    rang = models.IntegerField(
        "Rang",
        null=True, blank=True,
        help_text="Ordre d'importance du site dans le plan (1=principal)"
    )
    
    # Métadonnées
    date_association = models.DateTimeField(
        "Date d'association",
        auto_now_add=True
    )
    commentaire = models.TextField(
        "Commentaire",
        null=True, blank=True,
        help_text="Précisions sur le lien entre ce site et le plan"
    )

    class Meta:
        db_table = 'cor_site_pg'
        db_table_comment = 'Liaison entre sites et plans de gestion'
        verbose_name = "Site - Plan de gestion"
        verbose_name_plural = "Sites - Plans de gestion"
        unique_together = ['site', 'plan_de_gestion']
        ordering = ['rang', 'site__nom_site']

    def __str__(self):
        rang_str = f" (rang {self.rang})" if self.rang else ""
        return f"{self.site.nom_site} - {self.plan_de_gestion.nom}{rang_str}"


class CorPgFichier(models.Model):
    """
    Table de liaison entre Plans de Gestion et fichiers joints.
    Gestion des pièces jointes et documents associés aux plans.
    """
    
    TYPE_FICHIER_CHOICES = [
        ('document', 'Document principal'),
        ('annexe', 'Annexe'),
        ('carte', 'Carte'),
        ('photo', 'Photographie'),
        ('rapport', 'Rapport d\'étude'),
        ('autre', 'Autre'),
    ]
    
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='fichiers',
        verbose_name="Plan de gestion"
    )
    
    # Informations sur le fichier
    nom_fichier = models.CharField(
        "Nom du fichier",
        max_length=255,
        help_text="Nom original du fichier uploadé"
    )
    chemin_fichier = models.CharField(
        "Chemin du fichier", 
        max_length=500,
        help_text="Chemin d'accès au fichier sur le serveur"
    )
    type_fichier = models.CharField(
        "Type de fichier",
        max_length=20,
        choices=TYPE_FICHIER_CHOICES,
        default='document'
    )
    taille_fichier = models.BigIntegerField(
        "Taille du fichier (bytes)",
        null=True, blank=True
    )
    extension = models.CharField(
        "Extension",
        max_length=10,
        null=True, blank=True
    )
    
    # Métadonnées descriptives
    titre = models.CharField(
        "Titre",
        max_length=255,
        null=True, blank=True,
        help_text="Titre descriptif du document"
    )
    description = models.TextField(
        "Description", 
        null=True, blank=True
    )
    auteur = models.CharField(
        "Auteur", 
        max_length=255,
        null=True, blank=True
    )
    date_document = models.DateField(
        "Date du document",
        null=True, blank=True,
        help_text="Date de création/rédaction du document"
    )
    
    # Métadonnées techniques
    date_upload = models.DateTimeField(
        "Date d'upload",
        auto_now_add=True
    )
    id_utilisateur_upload = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        verbose_name="Utilisateur ayant uploadé",
        help_text="Utilisateur ayant ajouté ce fichier"
    )
    
    # Options d'affichage
    public = models.BooleanField(
        "Fichier public",
        default=False,
        help_text="Le fichier est-il accessible publiquement ?"
    )
    ordre_affichage = models.IntegerField(
        "Ordre d'affichage",
        default=0,
        help_text="Ordre d'affichage dans la liste des fichiers"
    )

    class Meta:
        db_table = 'cor_pg_fichier'
        db_table_comment = 'Fichiers associés aux plans de gestion'
        verbose_name = "Fichier plan de gestion"
        verbose_name_plural = "Fichiers plans de gestion"
        ordering = ['ordre_affichage', 'nom_fichier']

    def __str__(self):
        return f"{self.titre or self.nom_fichier} ({self.plan_de_gestion.nom})"

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