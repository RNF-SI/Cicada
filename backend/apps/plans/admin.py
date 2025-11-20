"""
Configuration de l'interface d'administration pour les Plans de Gestion.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import PlanGestion, CorSitePg, CorPgFichier


class CorSitePgInline(admin.TabularInline):
    """Inline pour la gestion des sites associés à un plan."""
    model = CorSitePg
    extra = 1
    fields = ['site', 'rang', 'commentaire']
    autocomplete_fields = ['site']
    ordering = ['rang', 'site__nom_site']


class CorPgFichierInline(admin.TabularInline):
    """Inline pour la gestion des fichiers associés à un plan."""
    model = CorPgFichier
    extra = 0
    fields = ['nom_fichier', 'type_fichier', 'titre', 'public', 'ordre_affichage']
    readonly_fields = ['chemin_fichier', 'taille_fichier', 'extension', 'date_upload']
    ordering = ['ordre_affichage', 'nom_fichier']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('id_utilisateur_upload')


@admin.register(PlanGestion)
class PlanGestionAdmin(GISModelAdmin):
    """Interface d'administration pour les Plans de Gestion."""
    
    list_display = [
        'nom', 
        'statut', 
        'periode_gestion_display',
        'nb_sites',
        'gestion_partagee',
        'date_maj',
        'id_utilisateur_ajout'
    ]
    
    list_filter = [
        'statut',
        'gestion_partagee',
        'ct88',
        'risque_incendie',
        'date_ajout',
        'annee_debut',
        'id_evaluation__label_fr',
        'id_redacteur_type__label_fr'
    ]
    
    search_fields = [
        'nom',
        'id_cdr',
        'redacteur_nom',
        'commentaire',
        'sites__site__nom_site'
    ]
    
    readonly_fields = [
        'date_ajout',
        'date_maj', 
        'last_update',
        'sites_lies',
        'organismes_gestionnaires_display'
    ]
    
    autocomplete_fields = [
        'id_evaluation',
        'id_redacteur_type',
        'id_utilisateur_ajout',
        'id_utilisateur_maj',
        'referents'
    ]
    
    filter_horizontal = ['referents']
    
    inlines = [CorSitePgInline, CorPgFichierInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'nom',
                'id_cdr',
                'statut',
                'version',
                'commentaire'
            )
        }),
        ('Période et contraintes', {
            'fields': (
                'annee_debut',
                'annee_fin', 
                'gestion_partagee',
                'ct88',
                'risque_incendie'
            )
        }),
        ('Évaluation et rédaction', {
            'fields': (
                'id_evaluation',
                'id_redacteur_type',
                'redacteur_nom'
            )
        }),
        ('Responsabilités', {
            'fields': (
                'referents',
                'id_utilisateur_ajout',
                'id_utilisateur_maj'
            )
        }),
        ('Géographie', {
            'fields': (
                'geometrie',
                'sites_lies',
                'organismes_gestionnaires_display'
            ),
            'classes': ['collapse']
        }),
        ('Métadonnées', {
            'fields': (
                'date_ajout',
                'date_maj',
                'last_update'
            ),
            'classes': ['collapse']
        })
    )
    
    # Configuration de la carte
    default_lon = 200000  # Lambert-93
    default_lat = 6600000  # Lambert-93
    default_zoom = 6
    map_srid = 4326
    map_width = 800
    map_height = 500
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_evaluation',
            'id_redacteur_type', 
            'id_utilisateur_ajout',
            'id_utilisateur_maj'
        ).prefetch_related('sites__site', 'referents')
    
    def periode_gestion_display(self, obj):
        """Affichage de la période de gestion."""
        return obj.get_periode_gestion()
    periode_gestion_display.short_description = "Période"
    
    def nb_sites(self, obj):
        """Nombre de sites associés."""
        count = obj.sites.count()
        if count > 1:
            return format_html('<strong>{}</strong> sites', count)
        elif count == 1:
            return "1 site"
        return "Aucun site"
    nb_sites.short_description = "Sites"
    
    def sites_lies(self, obj):
        """Affichage des sites liés."""
        sites = obj.get_sites()
        if not sites:
            return "Aucun site associé"
        
        links = []
        for site in sites[:5]:  # Limiter à 5 sites pour l'affichage
            url = reverse('admin:users_site_change', args=[site.id_site])
            links.append(format_html('<a href="{}">{}</a>', url, site.nom_site))
        
        result = ", ".join(links)
        if len(sites) > 5:
            result += f" (+{len(sites) - 5} autres)"
        
        return mark_safe(result)
    sites_lies.short_description = "Sites associés"
    
    def organismes_gestionnaires_display(self, obj):
        """Affichage des organismes gestionnaires."""
        organismes = obj.get_organismes_gestionnaires()
        if not organismes:
            return "Aucun organisme"
        
        links = []
        for org in organismes[:5]:  # Limiter à 5 organismes
            url = reverse('admin:users_biborganismes_change', args=[org.id_organisme])
            links.append(format_html('<a href="{}">{}</a>', url, org.nom_organisme))
        
        result = ", ".join(links)
        if len(organismes) > 5:
            result += f" (+{len(organismes) - 5} autres)"
        
        return mark_safe(result)
    organismes_gestionnaires_display.short_description = "Organismes gestionnaires"
    
    def save_model(self, request, obj, form, change):
        """Enregistrer le plan en ajoutant l'utilisateur actuel."""
        if not change:  # Création
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Champs en lecture seule selon les permissions."""
        readonly = list(self.readonly_fields)
        
        if not request.user.is_superuser:
            if obj and obj.statut == 'valide':
                # Plan validé: certains champs deviennent read-only
                readonly.extend(['nom', 'annee_debut', 'annee_fin'])
        
        return readonly


@admin.register(CorSitePg)
class CorSitePgAdmin(admin.ModelAdmin):
    """Interface d'administration pour les liaisons Site-Plan."""
    
    list_display = [
        'site', 
        'plan_de_gestion',
        'rang',
        'date_association'
    ]
    
    list_filter = [
        'plan_de_gestion__statut',
        'site__id_type_site',
        'date_association',
        'rang'
    ]
    
    search_fields = [
        'site__nom_site',
        'plan_de_gestion__nom',
        'commentaire'
    ]
    
    autocomplete_fields = ['site', 'plan_de_gestion']
    
    readonly_fields = ['date_association']
    
    ordering = ['plan_de_gestion__nom', 'rang', 'site__nom_site']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('site', 'plan_de_gestion')


@admin.register(CorPgFichier)
class CorPgFichierAdmin(admin.ModelAdmin):
    """Interface d'administration pour les fichiers des plans."""
    
    list_display = [
        'nom_fichier',
        'plan_de_gestion', 
        'type_fichier',
        'taille_readable',
        'public',
        'date_upload',
        'id_utilisateur_upload'
    ]
    
    list_filter = [
        'type_fichier',
        'public',
        'date_upload',
        'extension',
        'plan_de_gestion__statut'
    ]
    
    search_fields = [
        'nom_fichier',
        'titre',
        'description',
        'auteur',
        'plan_de_gestion__nom'
    ]
    
    readonly_fields = [
        'chemin_fichier',
        'taille_fichier', 
        'extension',
        'date_upload',
        'taille_readable'
    ]
    
    autocomplete_fields = [
        'plan_de_gestion',
        'id_utilisateur_upload'
    ]
    
    fieldsets = (
        ('Fichier', {
            'fields': (
                'nom_fichier',
                'chemin_fichier',
                'type_fichier',
                'taille_fichier',
                'extension'
            )
        }),
        ('Métadonnées', {
            'fields': (
                'titre',
                'description',
                'auteur',
                'date_document',
                'plan_de_gestion'
            )
        }),
        ('Options', {
            'fields': (
                'public',
                'ordre_affichage'
            )
        }),
        ('Traçabilité', {
            'fields': (
                'date_upload',
                'id_utilisateur_upload'
            ),
            'classes': ['collapse']
        })
    )
    
    ordering = ['plan_de_gestion__nom', 'ordre_affichage', 'nom_fichier']
    
    def taille_readable(self, obj):
        """Affichage de la taille du fichier en format lisible."""
        return obj.get_file_size_human()
    taille_readable.short_description = "Taille"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'plan_de_gestion', 
            'id_utilisateur_upload'
        )
    
    def save_model(self, request, obj, form, change):
        """Enregistrer le fichier en ajoutant l'utilisateur actuel."""
        if not change:  # Création
            obj.id_utilisateur_upload = request.user
        super().save_model(request, obj, form, change)