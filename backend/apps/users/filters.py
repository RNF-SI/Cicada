"""
Filtres personnalisés pour l'API des utilisateurs.
"""
import django_filters
from django.db.models import Q
from .models import Role, BibOrganismes


class RoleFilter(django_filters.FilterSet):
    """
    Filtres pour les utilisateurs.
    """
    
    # Filtres simples
    email = django_filters.CharFilter(lookup_expr='icontains')
    nom = django_filters.CharFilter(field_name='nom_role', lookup_expr='icontains')
    prenom = django_filters.CharFilter(field_name='prenom_role', lookup_expr='icontains')
    role_level = django_filters.ChoiceFilter(choices=Role.ROLE_CHOICES)
    active = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    
    # Filtres par organisme
    organisme = django_filters.ModelChoiceFilter(
        field_name='id_organisme',
        queryset=BibOrganismes.objects.all(),
        empty_label="Aucun organisme"
    )
    organisme_nom = django_filters.CharFilter(
        field_name='id_organisme__nom_organisme',
        lookup_expr='icontains'
    )
    
    # Filtres par dates
    created_after = django_filters.DateFilter(
        field_name='date_insert',
        lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='date_insert',
        lookup_expr='lte'
    )
    last_login_after = django_filters.DateTimeFilter(
        field_name='last_login',
        lookup_expr='gte'
    )
    
    # Filtre de recherche globale
    search = django_filters.CharFilter(method='search_filter')
    
    # Filtres booléens composés
    has_organisme = django_filters.BooleanFilter(method='filter_has_organisme')
    is_admin = django_filters.BooleanFilter(method='filter_is_admin')
    is_referent_any = django_filters.BooleanFilter(method='filter_is_referent')
    
    class Meta:
        model = Role
        fields = [
            'email', 'nom', 'prenom', 'role_level', 'active', 'is_staff',
            'organisme', 'organisme_nom', 'created_after', 'created_before',
            'last_login_after', 'search', 'has_organisme', 'is_admin', 'is_referent_any'
        ]
    
    def search_filter(self, queryset, name, value):
        """
        Recherche globale dans plusieurs champs.
        """
        return queryset.filter(
            Q(email__icontains=value) |
            Q(nom_role__icontains=value) |
            Q(prenom_role__icontains=value) |
            Q(identifiant__icontains=value) |
            Q(id_organisme__nom_organisme__icontains=value)
        )
    
    def filter_has_organisme(self, queryset, name, value):
        """
        Filtrer les utilisateurs avec ou sans organisme.
        """
        if value:
            return queryset.exclude(id_organisme__isnull=True)
        else:
            return queryset.filter(id_organisme__isnull=True)
    
    def filter_is_admin(self, queryset, name, value):
        """
        Filtrer les utilisateurs avec des permissions d'admin.
        """
        if value:
            return queryset.filter(
                Q(role_level='super_admin') |
                Q(role_level='redacteur_principal') |
                Q(role_level='admin_og') |
                Q(is_staff=True) |
                Q(is_superuser=True)
            )
        else:
            return queryset.exclude(
                Q(role_level='super_admin') |
                Q(role_level='redacteur_principal') |
                Q(role_level='admin_og') |
                Q(is_staff=True) |
                Q(is_superuser=True)
            )
    
    def filter_is_referent(self, queryset, name, value):
        """
        Filtrer les utilisateurs qui sont référents d'au moins un site.
        """
        if value:
            return queryset.filter(
                corrolesite__referent=True,
                corrolesite__referent_valid=True
            ).distinct()
        else:
            return queryset.exclude(
                corrolesite__referent=True,
                corrolesite__referent_valid=True
            ).distinct()


class RoleFilterAdmin(RoleFilter):
    """
    Filtres étendus pour les administrateurs.
    """
    
    # Filtres supplémentaires pour admin
    groups = django_filters.CharFilter(
        field_name='groups__name',
        lookup_expr='icontains'
    )
    has_sites = django_filters.BooleanFilter(method='filter_has_sites')
    sites_count = django_filters.NumberFilter(method='filter_sites_count')
    
    class Meta(RoleFilter.Meta):
        fields = RoleFilter.Meta.fields + ['groups', 'has_sites', 'sites_count']
    
    def filter_has_sites(self, queryset, name, value):
        """
        Filtrer les utilisateurs avec ou sans sites assignés.
        """
        if value:
            return queryset.filter(corrolesite__isnull=False).distinct()
        else:
            return queryset.filter(corrolesite__isnull=True).distinct()
    
    def filter_sites_count(self, queryset, name, value):
        """
        Filtrer par nombre de sites assignés.
        """
        from django.db.models import Count
        return queryset.annotate(
            sites_count=Count('corrolesite')
        ).filter(sites_count=value)