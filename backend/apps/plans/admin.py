"""
Configuration de l'interface d'administration pour les Plans de Gestion.
"""
import csv
from datetime import datetime

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    PlanGestion, CorSitePg, CorRolePlan, CorPgFichier,
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    ObjectifLongTerme, NiveauExigence,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu,
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
    Metrique, Mesure,
)


# =============================================================================
# Actions pour les Plans de Gestion
# =============================================================================

def valider_plans(modeladmin, request, queryset):
    """Action pour valider les plans sélectionnés (passer de draft à valide)."""
    plans_draft = queryset.filter(statut='draft')
    count = plans_draft.count()
    if count == 0:
        modeladmin.message_user(
            request,
            "Aucun plan en brouillon sélectionné.",
            level='WARNING'
        )
        return

    plans_draft.update(statut='valide', id_utilisateur_maj=request.user)
    modeladmin.message_user(
        request,
        f"{count} plan(s) validé(s) avec succès."
    )
valider_plans.short_description = "✓ Valider les plans sélectionnés (draft → valide)"


def archiver_plans(modeladmin, request, queryset):
    """Action pour archiver les plans sélectionnés."""
    plans_non_archives = queryset.exclude(statut='archive')
    count = plans_non_archives.count()
    if count == 0:
        modeladmin.message_user(
            request,
            "Aucun plan non-archivé sélectionné.",
            level='WARNING'
        )
        return

    plans_non_archives.update(statut='archive', id_utilisateur_maj=request.user)
    modeladmin.message_user(
        request,
        f"{count} plan(s) archivé(s) avec succès."
    )
archiver_plans.short_description = "📦 Archiver les plans sélectionnés"


def remettre_en_brouillon(modeladmin, request, queryset):
    """Action pour remettre les plans en brouillon."""
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Seuls les super-administrateurs peuvent remettre un plan en brouillon.",
            level='ERROR'
        )
        return

    count = queryset.exclude(statut='draft').count()
    if count == 0:
        modeladmin.message_user(
            request,
            "Aucun plan non-brouillon sélectionné.",
            level='WARNING'
        )
        return

    queryset.exclude(statut='draft').update(statut='draft', id_utilisateur_maj=request.user)
    modeladmin.message_user(
        request,
        f"{count} plan(s) remis en brouillon.",
        level='WARNING'
    )
remettre_en_brouillon.short_description = "⚠️ Remettre en brouillon (Super-admin)"


def export_plans_csv(modeladmin, request, queryset):
    """Exporter les plans sélectionnés en CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="plans_gestion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Nom', 'Statut', 'Version', 'Période', 'Gestion partagée',
        'CT88', 'Risque incendie', 'Type évaluation', 'Rédacteur',
        'Sites', 'Référents', 'Date création', 'Dernière modification'
    ])

    for plan in queryset.select_related('id_evaluation', 'id_redacteur_type').prefetch_related('sites__site', 'referents'):
        sites = ', '.join([cor.site.nom_site for cor in plan.sites.all()])
        referents = ', '.join([f"{r.nom_role} {r.prenom_role}" for r in plan.referents.all()])

        writer.writerow([
            plan.id_pg,
            plan.nom,
            plan.get_statut_display(),
            plan.version,
            plan.get_periode_gestion(),
            'Oui' if plan.gestion_partagee else 'Non',
            'Oui' if plan.ct88 else 'Non',
            'Oui' if plan.risque_incendie else 'Non',
            plan.id_evaluation.label if plan.id_evaluation else '',
            plan.redacteur_nom or '',
            sites,
            referents,
            plan.date_ajout.strftime('%d/%m/%Y %H:%M') if plan.date_ajout else '',
            plan.date_maj.strftime('%d/%m/%Y %H:%M') if plan.date_maj else '',
        ])

    return response
export_plans_csv.short_description = "📥 Exporter en CSV"


def dupliquer_plan(modeladmin, request, queryset):
    """Dupliquer les plans sélectionnés."""
    from .services import PlanDuplicationService

    if queryset.count() > 5:
        modeladmin.message_user(
            request,
            "Vous ne pouvez dupliquer que 5 plans maximum à la fois.",
            level='ERROR'
        )
        return

    count = 0
    for plan in queryset:
        PlanDuplicationService.duplicate_plan(
            source_plan=plan,
            user=request.user,
            copy_sites=True,
            copy_referents=True,
            copy_fichiers=False,
            copy_enjeux=False,
        )
        count += 1

    modeladmin.message_user(
        request,
        f"{count} plan(s) dupliqué(s) avec succès. Les copies sont en statut 'Brouillon'."
    )
dupliquer_plan.short_description = "📋 Dupliquer les plans sélectionnés"


class CorSitePgInline(admin.TabularInline):
    """Inline pour la gestion des sites associés à un plan."""
    model = CorSitePg
    extra = 1
    fields = ['site', 'rang', 'site_type', 'site_surface', 'commentaire']
    readonly_fields = ['site_type', 'site_surface']
    autocomplete_fields = ['site']
    ordering = ['rang', 'site__nom_site']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'site', 'site__id_type_site'
        )

    def site_type(self, obj):
        if obj.pk and obj.site and obj.site.id_type_site:
            return obj.site.id_type_site.label
        return "-"
    site_type.short_description = "Type de site"

    def site_surface(self, obj):
        if obj.pk and obj.site and obj.site.surf_off:
            return f"{obj.site.surf_off:.1f} ha"
        return "-"
    site_surface.short_description = "Surface"


class CorRolePlanInline(admin.TabularInline):
    """Inline pour la gestion des membres/référents d'un plan."""
    model = CorRolePlan
    extra = 1
    fields = ['id_role', 'referent', 'user_organisme', 'user_sites', 'commentaire']
    readonly_fields = ['user_organisme', 'user_sites']
    autocomplete_fields = ['id_role']
    ordering = ['-referent', 'id_role__nom_role']
    verbose_name = "Membre / Référent"
    verbose_name_plural = "Membres et Référents du plan"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_role', 'id_role__id_organisme'
        ).prefetch_related('id_role__corrolesite_set__id_site')

    def user_organisme(self, obj):
        if obj.pk and obj.id_role and obj.id_role.id_organisme:
            return obj.id_role.id_organisme.nom_organisme
        return "-"
    user_organisme.short_description = "Organisme"

    def user_sites(self, obj):
        if obj.pk and obj.id_role:
            sites = [cor.id_site.nom_site for cor in obj.id_role.corrolesite_set.all()[:3]]
            if sites:
                return ", ".join(sites)
        return "-"
    user_sites.short_description = "Sites de l'utilisateur"


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
        'statut_display',
        'periode_gestion_display',
        'nb_sites',
        'nb_referents_display',
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
        'id_evaluation__label',
        'id_redacteur_type__label'
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
        'plan_parent',
        'id_type_document'
    ]

    inlines = [CorSitePgInline, CorRolePlanInline, CorPgFichierInline]

    actions = [valider_plans, archiver_plans, remettre_en_brouillon, dupliquer_plan, export_plans_csv]

    list_per_page = 25
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'nom',
                'id_cdr',
                'statut',
                'version',
                'plan_parent',
                'id_type_document',
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
        ('Géographie', {
            'fields': (
                'geometrie',
                'sites_lies',
                'organismes_gestionnaires_display'
            ),
            'classes': ['collapse']
        }),
        ('Métadonnées et traçabilité', {
            'fields': (
                'id_utilisateur_ajout',
                'id_utilisateur_maj',
                'date_ajout',
                'date_maj',
                'last_update'
            ),
            'classes': ['collapse'],
            'description': 'Les membres et référents du plan se gèrent via la section "Membres et Référents" ci-dessous.'
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
        ).prefetch_related('sites__site', 'referents', 'membres')
    
    def statut_display(self, obj):
        """Affichage du statut avec couleur et icône."""
        statut_config = {
            'draft': ('orange', '📝', 'Brouillon'),
            'valide': ('green', '✓', 'Validé'),
            'archive': ('gray', '📦', 'Archivé'),
        }
        color, icon, label = statut_config.get(obj.statut, ('black', '?', obj.statut))
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{icon} {label}</span>')
    statut_display.short_description = "Statut"
    statut_display.admin_order_field = 'statut'

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

    def nb_referents_display(self, obj):
        """Nombre de référents et membres du plan."""
        membres = list(obj.membres.all())
        refs = sum(1 for m in membres if m.referent)
        total = len(membres)
        if total == 0:
            return mark_safe('<span style="color: red;">Aucun</span>')
        parts = []
        if refs:
            parts.append(f'{refs} réf.')
        non_refs = total - refs
        if non_refs:
            parts.append(f'{non_refs} mbr.')
        return ", ".join(parts)
    nb_referents_display.short_description = "Équipe"
    
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


@admin.register(CorRolePlan)
class CorRolePlanAdmin(admin.ModelAdmin):
    """Interface d'administration pour les liaisons Utilisateur-Plan."""

    list_display = [
        'user_display',
        'plan_de_gestion',
        'referent_display',
        'user_organisme',
        'date_association'
    ]

    list_filter = [
        'referent',
        'plan_de_gestion__statut',
        'id_role__role_level',
        'id_role__id_organisme',
        'date_association'
    ]

    search_fields = [
        'id_role__email',
        'id_role__nom_role',
        'id_role__prenom_role',
        'plan_de_gestion__nom',
        'commentaire'
    ]

    autocomplete_fields = ['id_role', 'plan_de_gestion']

    readonly_fields = ['date_association']

    ordering = ['plan_de_gestion__nom', '-referent', 'id_role__nom_role']

    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_role', 'id_role__id_organisme', 'plan_de_gestion'
        )

    def user_display(self, obj):
        """Affiche l'utilisateur avec nom et email."""
        name = f"{obj.id_role.nom_role or ''} {obj.id_role.prenom_role or ''}".strip()
        if name:
            return f"{name} ({obj.id_role.email})"
        return obj.id_role.email
    user_display.short_description = "Utilisateur"
    user_display.admin_order_field = 'id_role__nom_role'

    def referent_display(self, obj):
        """Affiche le statut référent avec icône."""
        if obj.referent:
            return mark_safe('<span style="color: green; font-weight: bold;">✓ Référent</span>')
        return "Membre"
    referent_display.short_description = "Rôle"
    referent_display.admin_order_field = 'referent'

    def user_organisme(self, obj):
        """Affiche l'organisme de l'utilisateur."""
        if obj.id_role.id_organisme:
            return obj.id_role.id_organisme.nom_organisme
        return "-"
    user_organisme.short_description = "Organisme"
    user_organisme.admin_order_field = 'id_role__id_organisme__nom_organisme'


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


# =============================================================================
# Administration des Enjeux et FCR
# =============================================================================

class CorEnjeuTaxonInline(admin.TabularInline):
    """Inline pour les taxons liés à un enjeu."""
    model = CorEnjeuTaxon
    extra = 0
    fields = ['cd_nom', 'nom_complet', 'nom_vern']
    ordering = ['nom_complet']


class CorEnjeuHabitatInline(admin.TabularInline):
    """Inline pour les habitats liés à un enjeu."""
    model = CorEnjeuHabitat
    extra = 0
    fields = ['cd_hab', 'lb_hab_fr']
    ordering = ['lb_hab_fr']


class CorEnjeuGeologieInline(admin.TabularInline):
    """Inline pour les éléments géologiques liés à un enjeu."""
    model = CorEnjeuGeologie
    extra = 0
    fields = ['id_inpg', 'nom']
    ordering = ['nom']


@admin.register(Enjeu)
class EnjeuAdmin(GISModelAdmin):
    """Interface d'administration pour les Enjeux et FCR."""

    list_display = [
        'libelle',
        'id_pg',
        'categorie_display',
        'rang',
        'categorie_ecologique',
        'type_enjeu_display',
        'date_maj'
    ]

    list_filter = [
        'id_categorie',
        'rang',
        'categorie_ecologique',
        'habitat',
        'espece',
        'processus',
        'id_categorie_fcr',
        'id_pg__statut',
        'date_ajout'
    ]

    search_fields = [
        'libelle',
        'intitule_court',
        'description',
        'etat_enjeu',
        'id_pg__nom'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_pg',
        'id_categorie',
        'id_categorie_fcr',
        'id_importance',
        'id_utilisateur_maj'
    ]

    inlines = [CorEnjeuTaxonInline, CorEnjeuHabitatInline, CorEnjeuGeologieInline]

    list_per_page = 25

    fieldsets = (
        ('Informations générales', {
            'fields': (
                'id_pg',
                'id_categorie',
                'libelle',
                'intitule_court',
                'description'
            )
        }),
        ('Caractéristiques Enjeu', {
            'fields': (
                'rang',
                'categorie_ecologique',
                'habitat',
                'espece',
                'processus',
                'etat_enjeu'
            ),
            'classes': ['collapse'],
            'description': 'Champs spécifiques aux Enjeux de conservation'
        }),
        ('Caractéristiques FCR', {
            'fields': (
                'id_categorie_fcr',
            ),
            'classes': ['collapse'],
            'description': 'Champs spécifiques aux Facteurs Clés de Réussite'
        }),
        ('Options', {
            'fields': (
                'id_importance',
                'geom'
            ),
            'classes': ['collapse']
        }),
        ('Métadonnées', {
            'fields': (
                'date_ajout',
                'date_maj',
                'id_utilisateur_ajout',
                'id_utilisateur_maj'
            ),
            'classes': ['collapse']
        })
    )

    # Configuration de la carte
    default_lon = 200000
    default_lat = 6600000
    default_zoom = 6
    map_srid = 4326
    map_width = 800
    map_height = 400

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_pg',
            'id_categorie',
            'id_categorie_fcr',
            'id_importance',
            'id_utilisateur_ajout',
            'id_utilisateur_maj'
        )

    def categorie_display(self, obj):
        """Affichage de la catégorie (Enjeu ou FCR)."""
        if obj.id_categorie:
            if obj.id_categorie.mnemonique == 'ENJEU':
                return mark_safe('<span style="color: #B74D5D; font-weight: bold;">Enjeu</span>')
            elif obj.id_categorie.mnemonique == 'FCR':
                return mark_safe('<span style="color: #025359; font-weight: bold;">FCR</span>')
        return obj.id_categorie.label if obj.id_categorie else '-'
    categorie_display.short_description = "Type"
    categorie_display.admin_order_field = 'id_categorie'

    def type_enjeu_display(self, obj):
        """Affichage des types d'enjeu (habitat, espèce, processus)."""
        types = []
        if obj.habitat:
            types.append('Habitat')
        if obj.espece:
            types.append('Espèce')
        if obj.processus:
            types.append('Processus')
        return ', '.join(types) if types else '-'
    type_enjeu_display.short_description = "Lié à"

    def save_model(self, request, obj, form, change):
        """Enregistrer l'enjeu en ajoutant l'utilisateur actuel."""
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# Administration des Facteurs d'Influence et Pressions
# =============================================================================

class PressionInline(admin.TabularInline):
    """Inline pour les pressions liées à un facteur d'influence."""
    model = Pression
    extra = 0
    fields = ['libelle', 'description', 'id_pressref']
    ordering = ['libelle']


@admin.register(FacteurInfluence)
class FacteurInfluenceAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Facteurs d'Influence."""

    list_display = [
        'libelle',
        'id_enjeu',
        'nb_pressions',
        'date_maj'
    ]

    list_filter = [
        'id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'libelle',
        'description',
        'id_enjeu__libelle'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_enjeu',
        'id_utilisateur_maj'
    ]

    inlines = [PressionInline]

    list_per_page = 25

    def nb_pressions(self, obj):
        return obj.pressions.count()
    nb_pressions.short_description = "Pressions"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_enjeu', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        ).prefetch_related('pressions')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                instance.id_utilisateur_ajout = request.user
            instance.id_utilisateur_maj = request.user
            instance.save()
        formset.save_m2m()


@admin.register(Pression)
class PressionAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Pressions."""

    list_display = [
        'libelle',
        'id_facteur_influence',
        'id_pressref',
        'date_maj'
    ]

    list_filter = [
        'id_facteur_influence__id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'libelle',
        'description',
        'id_facteur_influence__libelle'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_facteur_influence',
        'id_utilisateur_maj'
    ]

    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_facteur_influence', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# Administration des Responsabilités
# =============================================================================

class CorResponsabiliteTaxonInline(admin.TabularInline):
    """Inline pour les taxons liés à une responsabilité."""
    model = CorResponsabiliteTaxon
    extra = 0
    fields = ['cd_nom', 'nom_complet', 'nom_vern']
    ordering = ['nom_complet']


class CorResponsabiliteHabitatInline(admin.TabularInline):
    """Inline pour les habitats liés à une responsabilité."""
    model = CorResponsabiliteHabitat
    extra = 0
    fields = ['cd_hab', 'lb_hab_fr']
    ordering = ['lb_hab_fr']


class CorResponsabiliteGeologieInline(admin.TabularInline):
    """Inline pour les éléments géologiques liés à une responsabilité."""
    model = CorResponsabiliteGeologie
    extra = 0
    fields = ['id_inpg', 'nom']
    ordering = ['nom']


class CorResponsabiliteEnjeuInline(admin.TabularInline):
    """Inline pour les enjeux liés à une responsabilité."""
    model = CorResponsabiliteEnjeu
    extra = 0
    autocomplete_fields = ['id_enjeu']


@admin.register(Responsabilite)
class ResponsabiliteAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Responsabilités."""

    list_display = [
        'id_site',
        'id_type_responsabilite',
        'id_niveau_responsabilite',
        'date_maj'
    ]

    list_filter = [
        'id_type_responsabilite',
        'id_niveau_responsabilite',
        'id_site__id_type_site',
        'date_ajout'
    ]

    search_fields = [
        'id_site__nom_site',
        'description'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_site',
        'id_type_responsabilite',
        'id_niveau_responsabilite',
        'id_utilisateur_maj'
    ]

    inlines = [
        CorResponsabiliteTaxonInline,
        CorResponsabiliteHabitatInline,
        CorResponsabiliteGeologieInline,
        CorResponsabiliteEnjeuInline
    ]

    list_per_page = 25

    fieldsets = (
        ('Informations générales', {
            'fields': (
                'id_site',
                'id_type_responsabilite',
                'id_niveau_responsabilite',
                'description'
            )
        }),
        ('Métadonnées', {
            'fields': (
                'date_ajout',
                'date_maj',
                'id_utilisateur_ajout',
                'id_utilisateur_maj'
            ),
            'classes': ['collapse']
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_site',
            'id_type_responsabilite',
            'id_niveau_responsabilite',
            'id_utilisateur_ajout',
            'id_utilisateur_maj'
        )

    def save_model(self, request, obj, form, change):
        """Enregistrer la responsabilité en ajoutant l'utilisateur actuel."""
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# Administration des États Actuels, OLT et Niveaux d'Exigence
# =============================================================================

@admin.register(ObjectifLongTerme)
class ObjectifLongTermeAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Objectifs à Long Terme."""

    list_display = [
        'libelle',
        'id_enjeu',
        'nb_niveaux_exigence',
        'date_maj'
    ]

    list_filter = [
        'id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'libelle',
        'description',
        'id_enjeu__libelle'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_enjeu',
        'id_utilisateur_maj'
    ]

    list_per_page = 25

    def nb_niveaux_exigence(self, obj):
        return obj.niveaux_exigence.count()
    nb_niveaux_exigence.short_description = "Niveaux d'exigence"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_enjeu', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        ).prefetch_related('niveaux_exigence')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


@admin.register(NiveauExigence)
class NiveauExigenceAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Niveaux d'Exigence."""

    list_display = [
        'libelle',
        'id_olt',
        'date_maj'
    ]

    list_filter = [
        'id_olt__id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'libelle',
        'description',
        'id_olt__libelle'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_olt',
        'id_utilisateur_maj'
    ]

    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_olt', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# Administration des Indicateurs, Métriques et Mesures
# =============================================================================

class CorIndicateurTaxonInline(admin.TabularInline):
    """Inline pour les taxons liés à un indicateur."""
    model = CorIndicateurTaxon
    extra = 0
    fields = ['cd_nom', 'nom_complet', 'nom_vern']
    ordering = ['nom_complet']


class CorIndicateurHabitatInline(admin.TabularInline):
    """Inline pour les habitats liés à un indicateur."""
    model = CorIndicateurHabitat
    extra = 0
    fields = ['cd_hab', 'lb_hab_fr']
    ordering = ['lb_hab_fr']


class CorIndicateurGeologieInline(admin.TabularInline):
    """Inline pour les éléments géologiques liés à un indicateur."""
    model = CorIndicateurGeologie
    extra = 0
    fields = ['id_inpg', 'nom']
    ordering = ['nom']


@admin.register(Indicateur)
class IndicateurAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Indicateurs."""

    list_display = [
        'nom_indicateur',
        'id_ne',
        'type_indicateur',
        'est_standardise',
        'nb_metriques',
        'date_maj'
    ]

    list_filter = [
        'type_indicateur',
        'est_standardise',
        'id_ne__id_olt__id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'nom_indicateur',
        'description',
        'id_ne__libelle'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_ne',
        'type_indicateur',
        'id_utilisateur_maj'
    ]

    inlines = [CorIndicateurTaxonInline, CorIndicateurHabitatInline, CorIndicateurGeologieInline]

    list_per_page = 25

    def nb_metriques(self, obj):
        return obj.metriques.count()
    nb_metriques.short_description = "Métriques"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_ne', 'type_indicateur', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        ).prefetch_related('metriques')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


@admin.register(Metrique)
class MetriqueAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Métriques."""

    list_display = [
        'nom_metrique',
        'id_indicateur',
        'type_metrique',
        'unite',
        'nb_mesures',
        'date_maj'
    ]

    list_filter = [
        'type_metrique',
        'id_indicateur__id_ne__id_olt__id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'nom_metrique',
        'description',
        'id_indicateur__nom_indicateur'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_indicateur',
        'type_metrique',
        'id_utilisateur_maj'
    ]

    list_per_page = 25

    fieldsets = (
        ('Informations générales', {
            'fields': (
                'id_indicateur',
                'nom_metrique',
                'description',
                'type_metrique',
                'unite',
                'ponderation',
                'etat_reference'
            )
        }),
        ('Seuils de scores', {
            'fields': (
                ('score_1_inf', 'score_1_sup', 'score_1_val', 'score_1_label'),
                ('score_2_inf', 'score_2_sup', 'score_2_val', 'score_2_label'),
                ('score_3_inf', 'score_3_sup', 'score_3_val', 'score_3_label'),
                ('score_4_inf', 'score_4_sup', 'score_4_val', 'score_4_label'),
                ('score_5_inf', 'score_5_sup', 'score_5_val', 'score_5_label'),
            ),
            'classes': ['collapse'],
            'description': 'Seuils numériques, valeurs simples et labels qualitatifs pour les 5 niveaux de score'
        }),
        ('Métadonnées', {
            'fields': (
                'date_ajout',
                'date_maj',
                'id_utilisateur_ajout',
                'id_utilisateur_maj'
            ),
            'classes': ['collapse']
        })
    )

    def nb_mesures(self, obj):
        return obj.mesures.count()
    nb_mesures.short_description = "Mesures"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_indicateur', 'type_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        ).prefetch_related('mesures')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)


@admin.register(Mesure)
class MesureAdmin(admin.ModelAdmin):
    """Interface d'administration pour les Mesures."""

    list_display = [
        'valeur',
        'id_metrique',
        'date_mesure',
        'date_maj'
    ]

    list_filter = [
        'date_mesure',
        'id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg',
        'date_ajout'
    ]

    search_fields = [
        'valeur',
        'commentaire',
        'id_metrique__nom_metrique'
    ]

    readonly_fields = [
        'date_ajout',
        'date_maj',
        'id_utilisateur_ajout'
    ]

    autocomplete_fields = [
        'id_metrique',
        'id_utilisateur_maj'
    ]

    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'id_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.id_utilisateur_ajout = request.user
        obj.id_utilisateur_maj = request.user
        super().save_model(request, obj, form, change)