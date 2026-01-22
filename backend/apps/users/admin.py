"""
Administration Django pour les utilisateurs, organismes et sites.
"""
import csv
from datetime import datetime
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.gis import admin as gis_admin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from apps.plans.models import PlanGestion, CorSitePg


class RoleCreationForm(forms.ModelForm):
    """Formulaire de création d'utilisateur."""
    
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmation mot de passe', widget=forms.PasswordInput)

    class Meta:
        model = Role
        fields = ('email', 'nom_role', 'prenom_role', 'role_level')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class RoleChangeForm(forms.ModelForm):
    """Formulaire de modification d'utilisateur."""
    
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Role
        fields = ('email', 'password', 'nom_role', 'prenom_role', 'role_level', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial["password"]


class CorRoleSiteInline(admin.TabularInline):
    """Inline amélioré pour les relations utilisateur-site."""
    model = CorRoleSite
    extra = 0
    fields = ('id_site', 'referent', 'referent_valid', 'conservateur')
    autocomplete_fields = ['id_site']
    verbose_name = "Site assigné"
    verbose_name_plural = "Sites assignés"
    
    def get_queryset(self, request):
        """Optimise les requêtes inline."""
        return super().get_queryset(request).select_related('id_site', 'id_site__id_type_site')
    
    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',)
        }


class CorOgSiteInline(admin.TabularInline):
    """Inline amélioré pour les relations organisme-site."""
    model = CorOgSite
    extra = 0
    fields = ('uuid_og', 'principal')
    autocomplete_fields = ['uuid_og']
    verbose_name = "Organisme gestionnaire"
    verbose_name_plural = "Organismes gestionnaires"
    
    def get_queryset(self, request):
        """Optimise les requêtes inline."""
        return super().get_queryset(request).select_related('uuid_og')
    
    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',)
        }
        
class SiteInlineForOrganisme(admin.TabularInline):
    """Inline pour afficher les sites d'un organisme."""
    model = CorOgSite
    extra = 0
    fields = ('id_site',)
    autocomplete_fields = ['id_site']
    verbose_name = "Site géré"
    verbose_name_plural = "Sites gérés"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('id_site')
        
class UsersInlineForOrganisme(admin.TabularInline):
    """Inline pour afficher les utilisateurs d'un organisme."""
    model = Role
    fk_name = 'id_organisme'
    extra = 0
    fields = ('email', 'nom_role', 'prenom_role', 'role_level', 'active')
    readonly_fields = ('email', 'nom_role', 'prenom_role')
    verbose_name = "Utilisateur"
    verbose_name_plural = "Utilisateurs de l'organisme"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PlansInlineForSite(admin.TabularInline):
    """Inline pour afficher les plans de gestion associés à un site."""
    model = CorSitePg
    extra = 0
    fields = ('plan_link', 'plan_statut', 'plan_periode', 'rang', 'commentaire')
    readonly_fields = ('plan_link', 'plan_statut', 'plan_periode')
    verbose_name = "Plan de gestion"
    verbose_name_plural = "Plans de gestion associés"

    def plan_link(self, obj):
        """Lien vers le plan de gestion."""
        if obj.plan_de_gestion:
            url = reverse('admin:plans_plangestion_change', args=[obj.plan_de_gestion.id_pg])
            return format_html('<a href="{}">{}</a>', url, obj.plan_de_gestion.nom)
        return "-"
    plan_link.short_description = "Plan de gestion"

    def plan_statut(self, obj):
        """Statut du plan avec couleur."""
        if obj.plan_de_gestion:
            colors = {'draft': 'orange', 'valide': 'green', 'archive': 'gray'}
            color = colors.get(obj.plan_de_gestion.statut, 'black')
            return mark_safe(f'<span style="color: {color};">{obj.plan_de_gestion.get_statut_display()}</span>')
        return "-"
    plan_statut.short_description = "Statut"

    def plan_periode(self, obj):
        """Période du plan."""
        if obj.plan_de_gestion:
            return obj.plan_de_gestion.get_periode_gestion()
        return "-"
    plan_periode.short_description = "Période"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('plan_de_gestion')

    def has_add_permission(self, request, obj=None):
        return False


class PlansReferentInlineForRole(admin.TabularInline):
    """Inline pour afficher les plans où l'utilisateur est référent."""
    model = PlanGestion.referents.through
    extra = 0
    fields = ('plan_link', 'plan_statut', 'plan_periode', 'plan_sites')
    readonly_fields = ('plan_link', 'plan_statut', 'plan_periode', 'plan_sites')
    verbose_name = "Plan de gestion (référent)"
    verbose_name_plural = "Plans de gestion (en tant que référent)"

    def plan_link(self, obj):
        """Lien vers le plan de gestion."""
        url = reverse('admin:plans_plangestion_change', args=[obj.plangestion.id_pg])
        return format_html('<a href="{}">{}</a>', url, obj.plangestion.nom)
    plan_link.short_description = "Plan de gestion"

    def plan_statut(self, obj):
        """Statut du plan avec couleur."""
        colors = {'draft': 'orange', 'valide': 'green', 'archive': 'gray'}
        color = colors.get(obj.plangestion.statut, 'black')
        return mark_safe(f'<span style="color: {color};">{obj.plangestion.get_statut_display()}</span>')
    plan_statut.short_description = "Statut"

    def plan_periode(self, obj):
        """Période du plan."""
        return obj.plangestion.get_periode_gestion()
    plan_periode.short_description = "Période"

    def plan_sites(self, obj):
        """Sites du plan."""
        sites = obj.plangestion.get_sites()
        if sites:
            return ", ".join([s.nom_site[:30] for s in sites[:3]])
        return "-"
    plan_sites.short_description = "Sites"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def make_active(modeladmin, request, queryset):
    """Action pour activer les utilisateurs sélectionnés."""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request,
        f"{updated} utilisateur(s) activé(s) avec succès."
    )
make_active.short_description = "Activer les utilisateurs sélectionnés"

def make_inactive(modeladmin, request, queryset):
    """Action pour désactiver les utilisateurs sélectionnés."""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request,
        f"{updated} utilisateur(s) désactivé(s) avec succès."
    )
make_inactive.short_description = "Désactiver les utilisateurs sélectionnés (soft delete)"

def hard_delete_users(modeladmin, request, queryset):
    """Action pour supprimer définitivement les utilisateurs (DANGER!)."""
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Seuls les super-administrateurs peuvent supprimer définitivement des utilisateurs.",
            level='ERROR'
        )
        return
    
    count = queryset.count()
    queryset.delete()
    modeladmin.message_user(
        request,
        f"{count} utilisateur(s) supprimé(s) DÉFINITIVEMENT.",
        level='WARNING'
    )
hard_delete_users.short_description = "⚠️ SUPPRIMER DÉFINITIVEMENT (Super-admin seulement)"

def export_users_csv(modeladmin, request, queryset):
    """Exporter les utilisateurs sélectionnés en CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="utilisateurs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Email', 'Nom', 'Prénom', 'Rôle', 'Organisme', 'Actif', 
        'Staff', 'Sites assignés', 'Date création', 'Dernière connexion'
    ])
    
    for user in queryset.select_related('id_organisme').prefetch_related('corrolesite_set__id_site'):
        sites = ', '.join([cor.id_site.nom_site for cor in user.corrolesite_set.all()])
        writer.writerow([
            user.id_role,
            user.email,
            user.nom_role or '',
            user.prenom_role or '',
            user.get_role_level_display(),
            user.id_organisme.nom_organisme if user.id_organisme else '',
            'Oui' if user.is_active else 'Non',
            'Oui' if user.is_staff else 'Non',
            sites,
            user.date_insert.strftime('%d/%m/%Y %H:%M') if user.date_insert else '',
            user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else 'Jamais',
        ])
    
    return response
export_users_csv.short_description = "Exporter en CSV"

@admin.register(Role)
class RoleAdmin(BaseUserAdmin):
    """Administration des utilisateurs avec actions avancées."""
    
    form = RoleChangeForm
    add_form = RoleCreationForm
    
    def has_delete_permission(self, request, obj=None):
        """Désactive le bouton 'Supprimer' standard de Django."""
        return False
    
    list_display = (
        'email', 'nom_complet', 'role_display', 'organisme_display', 
        'active_status', 'sites_count', 'date_insert'
    )
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'role_level', 'groupe', 
        'id_organisme', 'date_insert', 'last_login'
    )
    search_fields = ('email', 'nom_role', 'prenom_role', 'id_organisme__nom_organisme')
    ordering = ('email',)
    filter_horizontal = ()
    actions = [make_active, make_inactive, export_users_csv, hard_delete_users]
    list_per_page = 25
    
    def nom_complet(self, obj):
        """Affiche le nom complet de l'utilisateur."""
        return f"{obj.nom_role or ''} {obj.prenom_role or ''}" or "N/A"
    nom_complet.short_description = "Nom complet"
    nom_complet.admin_order_field = 'nom_role'
    
    def organisme_display(self, obj):
        """Affiche l'organisme avec lien."""
        if obj.id_organisme:
            url = reverse('admin:users_biborganismes_change', args=[obj.id_organisme.id_organisme])
            return format_html('<a href="{}">{}</a>', url, obj.id_organisme.nom_organisme)
        return "Aucun"
    organisme_display.short_description = "Organisme"
    organisme_display.admin_order_field = 'id_organisme__nom_organisme'
    
    def active_status(self, obj):
        """Statut actif avec icône colorée."""
        if obj.is_active:
            return mark_safe('<span style="color: green;">✓ Actif</span>')
        return mark_safe('<span style="color: red;">✗ Inactif</span>')
    active_status.short_description = "Statut"
    active_status.admin_order_field = 'is_active'
    
    def role_display(self, obj):
        """Affiche le rôle métier avec icône et couleur."""
        role_colors = {
            'super_admin': 'red',
            'admin_og': 'orange', 
            'referent': 'blue',
            'utilisateur': 'green'
        }
        role_icons = {
            'super_admin': '👑',
            'admin_og': '🔧',
            'referent': '👤',
            'utilisateur': '👥'
        }
        
        color = role_colors.get(obj.role_level, 'black')
        icon = role_icons.get(obj.role_level, '❓')
        role_label = obj.get_role_level_display()
        
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{icon} {role_label}</span>')
    role_display.short_description = "Rôle"
    role_display.admin_order_field = 'role_level'
    
    def sites_count(self, obj):
        """Nombre de sites assignés."""
        count = obj.corrolesite_set.count()
        if count > 0:
            return mark_safe(f'<span style="color: green;">{count} site(s)</span>')
        return "0"
    sites_count.short_description = "Sites"
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related."""
        return super().get_queryset(request).select_related(
            'id_organisme'
        ).prefetch_related('corrolesite_set')
    
    def get_search_results(self, request, queryset, search_term):
        """Améliore la recherche avec l'organisme."""
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        try:
            # Recherche aussi par ID si c'est un nombre
            if search_term.isdigit():
                queryset |= self.model.objects.filter(id_role=int(search_term))
        except (ValueError, TypeError):
            pass
        return queryset, may_have_duplicates
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {
            'fields': ('nom_role', 'prenom_role', 'desc_role', 'identifiant')
        }),
        ('Organisation', {
            'fields': ('id_organisme', 'groupe')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'role_level', 'groups', 'user_permissions'),
        }),
        ('Métadonnées', {
            'fields': ('remarques', 'champs_addi'),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom_role', 'prenom_role', 'role_level', 'password1', 'password2'),
        }),
    )
    
    inlines = [CorRoleSiteInline, PlansReferentInlineForRole]

    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',)
        }


def export_organismes_csv(modeladmin, request, queryset):
    """Exporter les organismes sélectionnés en CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="organismes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Nom', 'Ville', 'Email', 'Téléphone', 'Organisme parent', 
        'Utilisateurs', 'Sites gérés', 'Date création'
    ])
    
    for org in queryset.select_related('id_parent').prefetch_related('role_set', 'corogsite_set'):
        writer.writerow([
            org.id_organisme,
            org.nom_organisme,
            org.ville_organisme or '',
            org.email_organisme or '',
            org.tel_organisme or '',
            org.id_parent.nom_organisme if org.id_parent else '',
            org.role_set.count(),
            org.corogsite_set.count(),
            org.meta_create_date.strftime('%d/%m/%Y %H:%M') if org.meta_create_date else '',
        ])
    
    return response
export_organismes_csv.short_description = "Exporter en CSV"

def hard_delete_organismes(modeladmin, request, queryset):
    """Action pour supprimer définitivement les organismes (DANGER!)."""
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Seuls les super-administrateurs peuvent supprimer définitivement des organismes.",
            level='ERROR'
        )
        return
    
    count = queryset.count()
    queryset.delete()
    modeladmin.message_user(
        request,
        f"{count} organisme(s) supprimé(s) DÉFINITIVEMENT.",
        level='WARNING'
    )
hard_delete_organismes.short_description = "⚠️ SUPPRIMER DÉFINITIVEMENT (Super-admin seulement)"

@admin.register(BibOrganismes)
class BibOrganismesAdmin(admin.ModelAdmin):
    """Administration des organismes avec fonctionnalités avancées."""

    def has_delete_permission(self, request, obj=None):
        """Désactive le bouton 'Supprimer' standard de Django."""
        return False

    list_display = (
        'nom_organisme', 'ville_organisme', 'contact_info',
        'parent_display', 'users_count', 'sites_count', 'plans_count', 'meta_create_date'
    )
    list_filter = (
        'ville_organisme', 'id_parent', 'meta_create_date',
        ('email_organisme', admin.EmptyFieldListFilter),
        ('tel_organisme', admin.EmptyFieldListFilter)
    )
    search_fields = (
        'nom_organisme', 'email_organisme', 'ville_organisme', 
        'adresse_organisme', 'id_parent__nom_organisme'
    )
    readonly_fields = ('uuid_organisme', 'meta_create_date', 'meta_update_date', 'plans_lies')
    actions = [export_organismes_csv, hard_delete_organismes]
    list_per_page = 25
    
    def contact_info(self, obj):
        """Affiche les informations de contact."""
        info = []
        if obj.email_organisme:
            info.append(f"📧 {obj.email_organisme}")
        if obj.tel_organisme:
            info.append(f"📞 {obj.tel_organisme}")
        return mark_safe('<br>'.join(info)) if info else "Aucun contact"
    contact_info.short_description = "Contact"
    
    def parent_display(self, obj):
        """Affiche l'organisme parent avec lien."""
        if obj.id_parent:
            url = reverse('admin:users_biborganismes_change', args=[obj.id_parent.id_organisme])
            return format_html('<a href="{}">{}</a>', url, obj.id_parent.nom_organisme)
        return mark_safe('<em>Organisme parent</em>')
    parent_display.short_description = "Parent"
    parent_display.admin_order_field = 'id_parent__nom_organisme'
    
    def users_count(self, obj):
        """Nombre d'utilisateurs de l'organisme."""
        count = obj.role_set.count()
        if count > 0:
            return mark_safe(f'<span style="color: blue;">{count} utilisateur(s)</span>')
        return "0"
    users_count.short_description = "Utilisateurs"
    
    def sites_count(self, obj):
        """Nombre de sites gérés."""
        count = obj.corogsite_set.count()
        if count > 0:
            return mark_safe(f'<span style="color: green;">{count} site(s)</span>')
        return "0"
    sites_count.short_description = "Sites"

    def plans_count(self, obj):
        """Nombre de plans de gestion liés aux sites de l'organisme."""
        # Récupérer les IDs des sites de l'organisme
        site_ids = obj.corogsite_set.values_list('id_site', flat=True)
        # Compter les plans uniques liés à ces sites
        count = PlanGestion.objects.filter(sites__site__in=site_ids).distinct().count()
        if count > 0:
            return mark_safe(f'<span style="color: purple;">{count} plan(s)</span>')
        return "0"
    plans_count.short_description = "Plans"

    def plans_lies(self, obj):
        """Affiche les plans de gestion liés aux sites de l'organisme."""
        # Récupérer les IDs des sites de l'organisme
        site_ids = obj.corogsite_set.values_list('id_site', flat=True)
        # Récupérer les plans uniques liés à ces sites
        plans = PlanGestion.objects.filter(sites__site__in=site_ids).distinct().select_related(
            'id_evaluation', 'id_redacteur_type'
        )[:10]

        if not plans:
            return "Aucun plan de gestion"

        links = []
        for plan in plans:
            url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
            statut_colors = {'draft': 'orange', 'valide': 'green', 'archive': 'gray'}
            color = statut_colors.get(plan.statut, 'black')
            links.append(format_html(
                '<a href="{}" style="color: {};">{}</a> <small>({} - {})</small>',
                url, color, plan.nom, plan.get_statut_display(), plan.get_periode_gestion()
            ))

        result = '<br>'.join(links)
        total = PlanGestion.objects.filter(sites__site__in=site_ids).distinct().count()
        if total > 10:
            result += f'<br><em>... et {total - 10} autres plan(s)</em>'

        return mark_safe(result)
    plans_lies.short_description = "Plans de gestion liés"

    def get_queryset(self, request):
        """Optimise les requêtes."""
        return super().get_queryset(request).select_related(
            'id_parent'
        ).prefetch_related('role_set', 'corogsite_set')
    
    def get_search_results(self, request, queryset, search_term):
        """Améliore la recherche des organismes."""
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        try:
            if search_term.isdigit():
                queryset |= self.model.objects.filter(id_organisme=int(search_term))
        except (ValueError, TypeError):
            pass
        return queryset, may_have_duplicates
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom_organisme', 'id_parent', 'uuid_organisme')
        }),
        ('Contact', {
            'fields': (
                'adresse_organisme', 'cp_organisme', 'ville_organisme',
                'tel_organisme', 'fax_organisme', 'email_organisme'
            )
        }),
        ('Web', {
            'fields': ('url_organisme', 'url_logo')
        }),
        ('Plans de gestion', {
            'fields': ('plans_lies',),
            'description': 'Plans de gestion liés aux sites gérés par cet organisme'
        }),
        ('Données additionnelles', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('meta_create_date', 'meta_update_date'),
            'classes': ('collapse',)
        }),
    )

    inlines = [SiteInlineForOrganisme, UsersInlineForOrganisme]


def activate_sites(modeladmin, request, queryset):
    """Action pour activer les sites sélectionnés."""
    updated = queryset.update(active=True)
    modeladmin.message_user(
        request,
        f"{updated} site(s) activé(s) avec succès."
    )
activate_sites.short_description = "Activer les sites sélectionnés"

def deactivate_sites(modeladmin, request, queryset):
    """Action pour désactiver les sites sélectionnés."""
    updated = queryset.update(active=False)
    modeladmin.message_user(
        request,
        f"{updated} site(s) désactivé(s) avec succès."
    )
deactivate_sites.short_description = "Désactiver les sites sélectionnés (soft delete)"

def hard_delete_sites(modeladmin, request, queryset):
    """Action pour supprimer définitivement les sites (DANGER!)."""
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Seuls les super-administrateurs peuvent supprimer définitivement des sites.",
            level='ERROR'
        )
        return
    
    count = queryset.count()
    queryset.delete()
    modeladmin.message_user(
        request,
        f"{count} site(s) supprimé(s) DÉFINITIVEMENT.",
        level='WARNING'
    )
hard_delete_sites.short_description = "⚠️ SUPPRIMER DÉFINITIVEMENT (Super-admin seulement)"

def export_sites_csv(modeladmin, request, queryset):
    """Exporter les sites sélectionnés en CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sites_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Nom', 'ID Local', 'Type', 'Surface (ha)', 'Marin', 'Outre-mer', 
        'Actif', 'Date création', 'Organismes', 'Référents'
    ])
    
    for site in queryset.select_related('id_type_site').prefetch_related('corogsite_set__uuid_og', 'corrolesite_set__id_role'):
        organismes = ', '.join([cor.uuid_og.nom_organisme for cor in site.corogsite_set.all()])
        referents = ', '.join([f"{cor.id_role.nom_role} {cor.id_role.prenom_role}" for cor in site.corrolesite_set.filter(referent=True)])
        
        writer.writerow([
            site.id_site,
            site.nom_site,
            site.id_local or '',
            site.id_type_site.label if site.id_type_site else '',
            site.surf_off or '',
            'Oui' if site.marin else 'Non',
            'Oui' if site.outre_mer else 'Non',
            'Oui' if site.active else 'Non',
            site.date_crea.strftime('%d/%m/%Y') if site.date_crea else '',
            organismes,
            referents,
        ])
    
    return response
export_sites_csv.short_description = "Exporter en CSV"

@admin.register(Site)
class SiteAdmin(gis_admin.GISModelAdmin):
    """Administration des sites avec support géospatial et fonctionnalités avancées."""
    
    def has_delete_permission(self, request, obj=None):
        """Désactive le bouton 'Supprimer' standard de Django."""
        return False
    
    list_display = (
        'nom_site', 'id_local', 'type_site_display', 'surface_display',
        'caractéristiques', 'status_display', 'organismes_count', 'date_crea'
    )
    list_filter = (
        'id_type_site', 'marin', 'outre_mer', 'active', 
        ('date_crea', admin.DateFieldListFilter),
        ('surf_off', admin.EmptyFieldListFilter)
    )
    search_fields = (
        'nom_site', 'id_local', 'id_inpn', 
        'organismes_gestionnaires__nom_organisme',
        'users_assigned__nom_role', 'users_assigned__email'
    )
    readonly_fields = ('id_site',)
    actions = [activate_sites, deactivate_sites, export_sites_csv, hard_delete_sites]
    list_per_page = 25
    
    def type_site_display(self, obj):
        """Affiche le type de site avec couleur."""
        if obj.id_type_site:
            color = {
                'RNN': 'green',
                'RNR': 'blue',
                'PNR': 'orange',
                'ENS': 'purple',
                'APB': 'teal'
            }.get(obj.id_type_site.cd_nomenclature, 'black')
            label = obj.id_type_site.label or obj.id_type_site.cd_nomenclature or str(obj.id_type_site)
            return mark_safe(f'<span style="color: {color}; font-weight: bold;">{label}</span>')
        return "Non defini"
    type_site_display.short_description = "Type"
    type_site_display.admin_order_field = 'id_type_site__cd_nomenclature'
    
    def surface_display(self, obj):
        """Affiche la surface formatée."""
        if obj.surf_off:
            if obj.surf_off >= 1000:
                return f"{obj.surf_off:,.0f} ha"
            else:
                return f"{obj.surf_off:.1f} ha"
        return "N/A"
    surface_display.short_description = "Surface"
    surface_display.admin_order_field = 'surf_off'
    
    def caractéristiques(self, obj):
        """Affiche les caractéristiques du site."""
        chars = []
        if obj.marin:
            chars.append('🌊 Marin')
        if obj.outre_mer:
            chars.append('🏝️ Outre-mer')
        return mark_safe(' '.join(chars)) if chars else "Terrestre"
    caractéristiques.short_description = "Caractéristiques"
    
    def status_display(self, obj):
        """Statut du site avec icône."""
        if obj.active:
            return mark_safe('<span style="color: green;">✓ Actif</span>')
        return mark_safe('<span style="color: red;">✗ Inactif</span>')
    status_display.short_description = "Statut"
    status_display.admin_order_field = 'active'
    
    def organismes_count(self, obj):
        """Nombre d'organismes gestionnaires."""
        count = obj.corogsite_set.count()
        if count > 0:
            return mark_safe(f'<span style="color: blue;">{count} organisme(s)</span>')
        return "0"
    organismes_count.short_description = "Organismes"
    
    def get_queryset(self, request):
        """Optimise les requêtes."""
        return super().get_queryset(request).select_related(
            'id_type_site'
        ).prefetch_related('corogsite_set', 'corrolesite_set')
    
    def get_search_results(self, request, queryset, search_term):
        """Améliore la recherche des sites."""
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        try:
            if search_term.isdigit():
                queryset |= self.model.objects.filter(id_site=int(search_term))
        except (ValueError, TypeError):
            pass
        return queryset, may_have_duplicates
    
    fieldsets = (
        ('Identifiants', {
            'fields': ('id_site', 'id_local', 'id_inpn', 'nom_site', 'jonction_nom')
        }),
        ('Classification', {
            'fields': ('id_type_site', 'date_crea', 'surf_off')
        }),
        ('Caractéristiques', {
            'fields': ('marin', 'outre_mer', 'active')
        }),
        ('Géographie', {
            'fields': ('geom', 'geom_pt'),
            'classes': ('collapse',)
        }),
        ('Modifications', {
            'fields': ('modif_adm', 'modif_geo'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CorRoleSiteInline, CorOgSiteInline, PlansInlineForSite]

    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',)
        }

    # Configuration de la carte
    default_zoom = 6
    default_lon = 2.0  # Longitude centre France
    default_lat = 46.0  # Latitude centre France


def validate_referents(modeladmin, request, queryset):
    """Action pour valider les référents sélectionnés."""
    updated = queryset.filter(referent=True).update(referent_valid=True)
    modeladmin.message_user(
        request,
        f"{updated} référent(s) validé(s) avec succès."
    )
validate_referents.short_description = "Valider les référents sélectionnés"

@admin.register(CorRoleSite)
class CorRoleSiteAdmin(admin.ModelAdmin):
    """Administration des relations utilisateur-site avec actions avancées."""
    
    list_display = (
        'user_display', 'site_display', 'role_status', 
        'referent_status', 'conservateur_display'
    )
    list_filter = (
        'referent', 'referent_valid', 'conservateur',
        'id_role__role_level', 'id_role__is_active',
        'id_site__active', 'id_site__id_type_site'
    )
    search_fields = (
        'id_role__email', 'id_role__nom_role', 'id_role__prenom_role',
        'id_site__nom_site', 'id_site__id_local'
    )
    autocomplete_fields = ['id_role', 'id_site']
    actions = [validate_referents]
    list_per_page = 25
    
    def user_display(self, obj):
        """Affiche l'utilisateur avec lien."""
        url = reverse('admin:users_role_change', args=[obj.id_role.id_role])
        return format_html(
            '<a href="{}">{} ({})</a>', 
            url, obj.id_role.email, obj.id_role.get_role_level_display()
        )
    user_display.short_description = "Utilisateur"
    user_display.admin_order_field = 'id_role__email'
    
    def site_display(self, obj):
        """Affiche le site avec lien."""
        url = reverse('admin:users_site_change', args=[obj.id_site.id_site])
        return format_html('<a href="{}">{}</a>', url, obj.id_site.nom_site)
    site_display.short_description = "Site"
    site_display.admin_order_field = 'id_site__nom_site'
    
    def role_status(self, obj):
        """Statut du rôle avec icônes."""
        status = []
        if obj.referent:
            color = 'green' if obj.referent_valid else 'orange'
            status.append(f'<span style="color: {color};">👤 Référent</span>')
        if obj.conservateur:
            status.append('<span style="color: blue;">🔒 Conservateur</span>')
        return mark_safe(' '.join(status)) if status else "Utilisateur"
    role_status.short_description = "Rôle sur site"
    
    def referent_status(self, obj):
        """Statut de validation du référent."""
        if obj.referent:
            if obj.referent_valid:
                return mark_safe('<span style="color: green;">✓ Validé</span>')
            else:
                return mark_safe('<span style="color: orange;">⏳ En attente</span>')
        return "N/A"
    referent_status.short_description = "Validation"
    referent_status.admin_order_field = 'referent_valid'
    
    def conservateur_display(self, obj):
        """Affiche si c'est un conservateur."""
        if obj.conservateur:
            return mark_safe('<span style="color: blue;">✓ Conservateur</span>')
        return "Non"
    conservateur_display.short_description = "Conservateur"
    conservateur_display.admin_order_field = 'conservateur'


def make_principal(modeladmin, request, queryset):
    """Action pour définir comme gestionnaire principal."""
    updated = queryset.update(principal=True)
    modeladmin.message_user(
        request,
        f"{updated} relation(s) définie(s) comme principale(s)."
    )
make_principal.short_description = "Définir comme gestionnaire principal"

@admin.register(CorOgSite)
class CorOgSiteAdmin(admin.ModelAdmin):
    """Administration des relations organisme-site avec améliorations."""
    
    list_display = (
        'organisme_display', 'site_display', 'principal_status'
    )
    list_filter = (
        'principal', 'uuid_og__ville_organisme',
        'id_site__active', 'id_site__id_type_site'
    )
    search_fields = (
        'uuid_og__nom_organisme', 'uuid_og__ville_organisme',
        'id_site__nom_site', 'id_site__id_local'
    )
    autocomplete_fields = ['id_site']
    actions = [make_principal]
    list_per_page = 25
    
    def organisme_display(self, obj):
        """Affiche l'organisme avec lien."""
        url = reverse('admin:users_biborganismes_change', args=[obj.uuid_og.id_organisme])
        return format_html(
            '<a href="{}">{}</a><br><small style="color: gray;">{}</small>', 
            url, obj.uuid_og.nom_organisme, obj.uuid_og.ville_organisme or ''
        )
    organisme_display.short_description = "Organisme"
    organisme_display.admin_order_field = 'uuid_og__nom_organisme'
    
    def site_display(self, obj):
        """Affiche le site avec lien."""
        url = reverse('admin:users_site_change', args=[obj.id_site.id_site])
        type_site = obj.id_site.id_type_site.cd_nomenclature if obj.id_site.id_type_site else ''
        return format_html(
            '<a href="{}">{}</a><br><small style="color: gray;">{}</small>', 
            url, obj.id_site.nom_site, type_site
        )
    site_display.short_description = "Site"
    site_display.admin_order_field = 'id_site__nom_site'
    
    def principal_status(self, obj):
        """Statut de gestionnaire principal."""
        if obj.principal:
            return mark_safe('<span style="color: green; font-weight: bold;">★ Principal</span>')
        return "Secondaire"
    principal_status.short_description = "Statut"
    principal_status.admin_order_field = 'principal'