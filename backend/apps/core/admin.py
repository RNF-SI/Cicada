"""
Administration Django pour les modèles core (nomenclatures).
"""
from django.contrib import admin
from .models import TypeNomenclature, Nomenclature


class NomenclatureInline(admin.TabularInline):
    """Inline pour les nomenclatures d'un type."""
    model = Nomenclature
    extra = 0
    fields = ('cd_nomenclature', 'label_fr', 'active')
    readonly_fields = ('hierarchy',)


@admin.register(TypeNomenclature)
class TypeNomenclatureAdmin(admin.ModelAdmin):
    """Administration des types de nomenclatures."""
    
    list_display = (
        'mnemonique', 'label_fr', 'statut', 'source', 'meta_create_date'
    )
    list_filter = ('statut', 'source', 'meta_create_date')
    search_fields = ('mnemonique', 'label_fr', 'label_default')
    readonly_fields = ('meta_create_date', 'meta_update_date')
    
    fieldsets = (
        ('Identification', {
            'fields': ('mnemonique', 'statut', 'source')
        }),
        ('Labels', {
            'fields': ('label_default', 'label_fr')
        }),
        ('Définitions', {
            'fields': ('definition_default', 'definition_fr'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('meta_create_date', 'meta_update_date'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [NomenclatureInline]


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    """Administration des nomenclatures."""
    
    list_display = (
        'cd_nomenclature', 'label_fr', 'id_type', 'id_broader', 'active'
    )
    list_filter = ('id_type', 'active', 'meta_create_date')
    search_fields = (
        'cd_nomenclature', 'label_fr', 'label_default', 'mnemonique'
    )
    readonly_fields = ('hierarchy', 'meta_create_date', 'meta_update_date')
    autocomplete_fields = ['id_type', 'id_broader']
    
    fieldsets = (
        ('Identification', {
            'fields': ('id_type', 'cd_nomenclature', 'mnemonique', 'active')
        }),
        ('Labels', {
            'fields': ('label_default', 'label_fr')
        }),
        ('Définitions', {
            'fields': ('definition_default', 'definition_fr'),
            'classes': ('collapse',)
        }),
        ('Hiérarchie', {
            'fields': ('id_broader', 'hierarchy'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('meta_create_date', 'meta_update_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related."""
        return super().get_queryset(request).select_related('id_type', 'id_broader')