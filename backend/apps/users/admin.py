"""
Administration Django pour les utilisateurs, organismes et sites.
"""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.gis import admin as gis_admin

from .models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite


class RoleCreationForm(forms.ModelForm):
    """Formulaire de création d'utilisateur."""
    
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmation mot de passe', widget=forms.PasswordInput)

    class Meta:
        model = Role
        fields = ('email', 'nom_role', 'prenom_role')

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
        fields = ('email', 'password', 'nom_role', 'prenom_role', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial["password"]


class CorRoleSiteInline(admin.TabularInline):
    """Inline pour les relations utilisateur-site."""
    model = CorRoleSite
    extra = 0
    fields = ('id_site', 'referent', 'referent_valid', 'conservateur')


class CorOgSiteInline(admin.TabularInline):
    """Inline pour les relations organisme-site."""
    model = CorOgSite
    extra = 0
    fields = ('uuid_og', 'principal')


@admin.register(Role)
class RoleAdmin(BaseUserAdmin):
    """Administration des utilisateurs."""
    
    form = RoleChangeForm
    add_form = RoleCreationForm
    
    list_display = (
        'email', 'nom_role', 'prenom_role', 'id_organisme', 
        'is_active', 'is_staff', 'date_insert'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groupe', 'id_organisme')
    search_fields = ('email', 'nom_role', 'prenom_role')
    ordering = ('email',)
    filter_horizontal = ()
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {
            'fields': ('nom_role', 'prenom_role', 'desc_role', 'identifiant')
        }),
        ('Organisation', {
            'fields': ('id_organisme', 'groupe')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
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
            'fields': ('email', 'nom_role', 'prenom_role', 'password1', 'password2'),
        }),
    )
    
    inlines = [CorRoleSiteInline]


@admin.register(BibOrganismes)
class BibOrganismesAdmin(admin.ModelAdmin):
    """Administration des organismes."""
    
    list_display = (
        'nom_organisme', 'ville_organisme', 'email_organisme',
        'id_parent', 'meta_create_date'
    )
    list_filter = ('ville_organisme', 'id_parent', 'meta_create_date')
    search_fields = ('nom_organisme', 'email_organisme', 'ville_organisme')
    readonly_fields = ('uuid_organisme', 'meta_create_date', 'meta_update_date')
    
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
        ('Données additionnelles', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('meta_create_date', 'meta_update_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Site)
class SiteAdmin(gis_admin.GISModelAdmin):
    """Administration des sites avec support géospatial."""
    
    list_display = (
        'nom_site', 'id_local', 'id_type_site', 'surf_off',
        'marin', 'outre_mer', 'active', 'date_crea'
    )
    list_filter = ('id_type_site', 'marin', 'outre_mer', 'active', 'date_crea')
    search_fields = ('nom_site', 'id_local', 'id_inpn')
    readonly_fields = ('id_site',)
    
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
    
    inlines = [CorRoleSiteInline, CorOgSiteInline]
    
    # Configuration de la carte
    default_zoom = 6
    default_lon = 2.0  # Longitude centre France
    default_lat = 46.0  # Latitude centre France


@admin.register(CorRoleSite)
class CorRoleSiteAdmin(admin.ModelAdmin):
    """Administration des relations utilisateur-site."""
    
    list_display = ('id_role', 'id_site', 'referent', 'referent_valid', 'conservateur')
    list_filter = ('referent', 'referent_valid', 'conservateur')
    search_fields = (
        'id_role__email', 'id_role__nom_role', 'id_role__prenom_role',
        'id_site__nom_site'
    )
    autocomplete_fields = ['id_role', 'id_site']


@admin.register(CorOgSite)
class CorOgSiteAdmin(admin.ModelAdmin):
    """Administration des relations organisme-site."""
    
    list_display = ('uuid_og', 'id_site', 'principal')
    list_filter = ('principal',)
    search_fields = (
        'uuid_og__nom_organisme',
        'id_site__nom_site'
    )
    autocomplete_fields = ['id_site']