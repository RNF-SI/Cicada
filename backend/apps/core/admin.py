"""
Administration Django pour les modèles core (nomenclatures).
"""
from django.contrib import admin
from .models import TypeNomenclature, Nomenclature


class NomenclatureInline(admin.TabularInline):
    """Inline pour les nomenclatures d'un type."""
    model = Nomenclature
    extra = 0
    fields = ('mnemonique', 'label', 'actif')
    readonly_fields = ('hierarchy',)


@admin.register(TypeNomenclature)
class TypeNomenclatureAdmin(admin.ModelAdmin):
    """Administration des types de nomenclatures."""
    
    list_display = (
        'id_type', 'mnemonique', 'label', 'statut', 'source'
    )
    list_filter = ('statut', 'source')
    search_fields = ('mnemonique', 'label', 'definition')
    readonly_fields = ('date_ajout', 'date_maj')
    
    fieldsets = (
        ('Identification', {
            'fields': ('id_type', 'mnemonique', 'statut', 'source')
        }),
        ('Contenu', {
            'fields': ('label', 'definition')
        }),
        ('Métadonnées', {
            'fields': ('date_ajout', 'date_maj'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [NomenclatureInline]
    
    def has_add_permission(self, request):
        """Seuls les superusers peuvent ajouter des types."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Seuls les superusers peuvent modifier des types."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Seuls les superusers peuvent supprimer des types."""
        return request.user.is_superuser


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    """Administration des nomenclatures."""
    
    list_display = (
        'id_nomenclature', 'mnemonique', 'label', 'id_type', 'actif'
    )
    list_filter = ('id_type', 'actif', 'statut', 'source')
    search_fields = (
        'mnemonique', 'label', 'definition'
    )
    readonly_fields = ('hierarchy', 'date_ajout', 'date_maj')
    autocomplete_fields = ['id_type']
    
    fieldsets = (
        ('Identification', {
            'fields': ('id_type', 'mnemonique', 'actif')
        }),
        ('Contenu', {
            'fields': ('label', 'definition')
        }),
        ('Provenance', {
            'fields': ('source', 'statut'),
            'classes': ('collapse',)
        }),
        ('Hiérarchie', {
            'fields': ('hierarchy',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_ajout', 'date_maj'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related."""
        return super().get_queryset(request).select_related('id_type')
    
    def has_add_permission(self, request):
        """Seuls les superusers peuvent ajouter des nomenclatures."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Seuls les superusers peuvent modifier des nomenclatures."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Seuls les superusers peuvent supprimer des nomenclatures."""
        return request.user.is_superuser