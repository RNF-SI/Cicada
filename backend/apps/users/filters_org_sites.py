"""
Filtres Django Filter pour les API Organismes et Sites.
"""
import django_filters
from django.db.models import Q

from .models import BibOrganismes, Site


class OrganismeFilter(django_filters.FilterSet):
    """Filtres pour les organismes."""
    
    # Recherche globale
    search = django_filters.CharFilter(method='search_filter', label='Recherche globale')
    
    # Filtres par nom
    nom = django_filters.CharFilter(field_name='nom_organisme', lookup_expr='icontains')
    nom_exact = django_filters.CharFilter(field_name='nom_organisme', lookup_expr='exact')
    
    # Filtres géographiques
    ville = django_filters.CharFilter(field_name='ville_organisme', lookup_expr='icontains')
    cp = django_filters.CharFilter(field_name='cp_organisme', lookup_expr='exact')
    
    # Filtres par contact
    email = django_filters.CharFilter(field_name='email_organisme', lookup_expr='icontains')
    has_email = django_filters.BooleanFilter(method='filter_has_email')
    has_phone = django_filters.BooleanFilter(method='filter_has_phone')
    has_website = django_filters.BooleanFilter(method='filter_has_website')
    
    # Filtres hiérarchiques
    is_parent = django_filters.BooleanFilter(method='filter_is_parent')
    has_parent = django_filters.BooleanFilter(method='filter_has_parent')
    parent_id = django_filters.NumberFilter(field_name='id_parent__id_organisme')
    
    # Filtres par statut
    active = django_filters.BooleanFilter(field_name='active')
    
    # Filtres par relations
    has_sites = django_filters.BooleanFilter(method='filter_has_sites')
    has_users = django_filters.BooleanFilter(method='filter_has_users')
    
    # Tri
    ordering = django_filters.OrderingFilter(
        fields=(
            ('nom_organisme', 'nom'),
            ('ville_organisme', 'ville'),
            ('id_organisme', 'id'),
        ),
        field_labels={
            'nom': 'Nom',
            'ville': 'Ville',
            'id': 'Identifiant',
        }
    )
    
    class Meta:
        model = BibOrganismes
        fields = [
            'search', 'nom', 'nom_exact', 'ville', 'cp',
            'email', 'has_email', 'has_phone', 'has_website',
            'is_parent', 'has_parent', 'parent_id',
            'active', 'has_sites', 'has_users'
        ]
    
    def search_filter(self, queryset, name, value):
        """Recherche globale dans plusieurs champs."""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(nom_organisme__icontains=value) |
            Q(ville_organisme__icontains=value) |
            Q(email_organisme__icontains=value) |
            Q(adresse_organisme__icontains=value) |
            Q(id_parent__nom_organisme__icontains=value)
        ).distinct()
    
    def filter_has_email(self, queryset, name, value):
        """Filtre les organismes avec/sans email."""
        if value:
            return queryset.filter(email_organisme__isnull=False).exclude(email_organisme='')
        else:
            return queryset.filter(Q(email_organisme__isnull=True) | Q(email_organisme=''))
    
    def filter_has_phone(self, queryset, name, value):
        """Filtre les organismes avec/sans téléphone."""
        if value:
            return queryset.filter(tel_organisme__isnull=False).exclude(tel_organisme='')
        else:
            return queryset.filter(Q(tel_organisme__isnull=True) | Q(tel_organisme=''))
    
    def filter_has_website(self, queryset, name, value):
        """Filtre les organismes avec/sans site web."""
        if value:
            return queryset.filter(url_organisme__isnull=False).exclude(url_organisme='')
        else:
            return queryset.filter(Q(url_organisme__isnull=True) | Q(url_organisme=''))
    
    def filter_is_parent(self, queryset, name, value):
        """Filtre les organismes parents/enfants."""
        if value:
            return queryset.filter(id_parent__isnull=True)
        else:
            return queryset.filter(id_parent__isnull=False)
    
    def filter_has_parent(self, queryset, name, value):
        """Filtre les organismes ayant/n'ayant pas de parent."""
        if value:
            return queryset.filter(id_parent__isnull=False)
        else:
            return queryset.filter(id_parent__isnull=True)
    
    def filter_has_sites(self, queryset, name, value):
        """Filtre les organismes gérant/ne gérant pas de sites."""
        from .models import CorOgSite
        
        if value:
            org_ids_with_sites = CorOgSite.objects.values_list('uuid_og__id_organisme', flat=True).distinct()
            return queryset.filter(id_organisme__in=org_ids_with_sites)
        else:
            org_ids_with_sites = CorOgSite.objects.values_list('uuid_og__id_organisme', flat=True).distinct()
            return queryset.exclude(id_organisme__in=org_ids_with_sites)
    
    def filter_has_users(self, queryset, name, value):
        """Filtre les organismes ayant/n'ayant pas d'utilisateurs."""
        from .models import Role
        
        if value:
            org_ids_with_users = Role.objects.filter(
                id_organisme__isnull=False
            ).values_list('id_organisme__id_organisme', flat=True).distinct()
            return queryset.filter(id_organisme__in=org_ids_with_users)
        else:
            org_ids_with_users = Role.objects.filter(
                id_organisme__isnull=False
            ).values_list('id_organisme__id_organisme', flat=True).distinct()
            return queryset.exclude(id_organisme__in=org_ids_with_users)


class SiteFilter(django_filters.FilterSet):
    """Filtres pour les sites."""
    
    # Recherche globale
    search = django_filters.CharFilter(method='search_filter', label='Recherche globale')
    
    # Filtres par nom et identifiants
    nom = django_filters.CharFilter(field_name='nom_site', lookup_expr='icontains')
    nom_exact = django_filters.CharFilter(field_name='nom_site', lookup_expr='exact')
    id_local = django_filters.CharFilter(field_name='id_local', lookup_expr='icontains')
    id_inpn = django_filters.CharFilter(field_name='id_inpn', lookup_expr='icontains')
    
    # Filtres par type
    type_site = django_filters.NumberFilter(field_name='id_type_site__id_nomenclature')
    type_site_label = django_filters.CharFilter(method='filter_type_site_label')
    
    # Filtres par surface
    surf_min = django_filters.NumberFilter(field_name='surf_off', lookup_expr='gte')
    surf_max = django_filters.NumberFilter(field_name='surf_off', lookup_expr='lte')
    surf_range = django_filters.RangeFilter(field_name='surf_off')
    
    # Filtres par dates
    created_after = django_filters.DateFilter(field_name='date_crea', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='date_crea', lookup_expr='lte')
    created_year = django_filters.NumberFilter(field_name='date_crea__year')
    
    # Modifications
    modif_adm_after = django_filters.DateFilter(field_name='modif_adm', lookup_expr='gte')
    modif_geo_after = django_filters.DateFilter(field_name='modif_geo', lookup_expr='gte')
    
    # Filtres booléens
    active = django_filters.BooleanFilter(field_name='active')
    marin = django_filters.BooleanFilter(field_name='marin')
    outre_mer = django_filters.BooleanFilter(field_name='outre_mer')
    
    # Filtres géospatiaux
    has_geometry = django_filters.BooleanFilter(method='filter_has_geometry')
    has_point = django_filters.BooleanFilter(method='filter_has_point')
    
    # Filtres par relations
    organisme = django_filters.NumberFilter(method='filter_by_organisme')
    organisme_nom = django_filters.CharFilter(method='filter_by_organisme_nom')
    has_organismes = django_filters.BooleanFilter(method='filter_has_organismes')
    
    user = django_filters.NumberFilter(method='filter_by_user')
    user_email = django_filters.CharFilter(method='filter_by_user_email')
    has_users = django_filters.BooleanFilter(method='filter_has_users')
    has_referent = django_filters.BooleanFilter(method='filter_has_referent')
    
    # Tri
    ordering = django_filters.OrderingFilter(
        fields=(
            ('nom_site', 'nom'),
            ('surf_off', 'surface'),
            ('date_crea', 'date_creation'),
            ('id_site', 'id'),
        ),
        field_labels={
            'nom': 'Nom',
            'surface': 'Surface',
            'date_creation': 'Date de création',
            'id': 'Identifiant',
        }
    )
    
    class Meta:
        model = Site
        fields = [
            'search', 'nom', 'nom_exact', 'id_local', 'id_inpn',
            'type_site', 'type_site_label',
            'surf_min', 'surf_max', 'surf_range',
            'created_after', 'created_before', 'created_year',
            'modif_adm_after', 'modif_geo_after',
            'active', 'marin', 'outre_mer',
            'has_geometry', 'has_point',
            'organisme', 'organisme_nom', 'has_organismes',
            'user', 'user_email', 'has_users', 'has_referent'
        ]
    
    def search_filter(self, queryset, name, value):
        """Recherche globale dans plusieurs champs."""
        if not value:
            return queryset

        return queryset.filter(
            Q(nom_site__icontains=value) |
            Q(id_local__icontains=value) |
            Q(id_inpn__icontains=value) |
            Q(jonction_nom__icontains=value) |
            Q(id_type_site__label__icontains=value)
        ).distinct()

    def filter_type_site_label(self, queryset, name, value):
        """
        Filtre par type de site en acceptant soit le code court (mnémonique,
        ex: 'RNN') soit le libellé complet (ex: 'Réserve Naturelle Nationale').
        Les sélecteurs du frontend envoient le code court, mais on reste
        compatible avec les appels passant le libellé complet.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(id_type_site__mnemonique__iexact=value) |
            Q(id_type_site__label__icontains=value)
        )
    
    def filter_has_geometry(self, queryset, name, value):
        """Filtre les sites avec/sans géométrie."""
        if value:
            return queryset.filter(geom__isnull=False)
        else:
            return queryset.filter(geom__isnull=True)
    
    def filter_has_point(self, queryset, name, value):
        """Filtre les sites avec/sans point de référence."""
        if value:
            return queryset.filter(geom_pt__isnull=False)
        else:
            return queryset.filter(geom_pt__isnull=True)
    
    def filter_by_organisme(self, queryset, name, value):
        """Filtre par organisme gestionnaire."""
        from .models import CorOgSite
        
        site_ids = CorOgSite.objects.filter(
            uuid_og__id_organisme=value
        ).values_list('id_site__id_site', flat=True)
        
        return queryset.filter(id_site__in=site_ids)
    
    def filter_by_organisme_nom(self, queryset, name, value):
        """Filtre par nom d'organisme gestionnaire."""
        from .models import CorOgSite
        
        site_ids = CorOgSite.objects.filter(
            uuid_og__nom_organisme__icontains=value
        ).values_list('id_site__id_site', flat=True)
        
        return queryset.filter(id_site__in=site_ids)
    
    def filter_has_organismes(self, queryset, name, value):
        """Filtre les sites ayant/n'ayant pas d'organismes gestionnaires."""
        from .models import CorOgSite
        
        if value:
            site_ids_with_orgs = CorOgSite.objects.values_list('id_site__id_site', flat=True).distinct()
            return queryset.filter(id_site__in=site_ids_with_orgs)
        else:
            site_ids_with_orgs = CorOgSite.objects.values_list('id_site__id_site', flat=True).distinct()
            return queryset.exclude(id_site__in=site_ids_with_orgs)
    
    def filter_by_user(self, queryset, name, value):
        """Filtre par utilisateur assigné."""
        from .models import CorRoleSite
        
        site_ids = CorRoleSite.objects.filter(
            id_role__id_role=value
        ).values_list('id_site__id_site', flat=True)
        
        return queryset.filter(id_site__in=site_ids)
    
    def filter_by_user_email(self, queryset, name, value):
        """Filtre par email d'utilisateur assigné."""
        from .models import CorRoleSite
        
        site_ids = CorRoleSite.objects.filter(
            id_role__email__icontains=value
        ).values_list('id_site__id_site', flat=True)
        
        return queryset.filter(id_site__in=site_ids)
    
    def filter_has_users(self, queryset, name, value):
        """Filtre les sites ayant/n'ayant pas d'utilisateurs assignés."""
        from .models import CorRoleSite
        
        if value:
            site_ids_with_users = CorRoleSite.objects.values_list('id_site__id_site', flat=True).distinct()
            return queryset.filter(id_site__in=site_ids_with_users)
        else:
            site_ids_with_users = CorRoleSite.objects.values_list('id_site__id_site', flat=True).distinct()
            return queryset.exclude(id_site__in=site_ids_with_users)
    
    def filter_has_referent(self, queryset, name, value):
        """Filtre les sites ayant/n'ayant pas de référent."""
        from .models import CorRoleSite
        
        if value:
            site_ids_with_referent = CorRoleSite.objects.filter(
                referent=True, referent_valid=True
            ).values_list('id_site__id_site', flat=True).distinct()
            return queryset.filter(id_site__in=site_ids_with_referent)
        else:
            site_ids_with_referent = CorRoleSite.objects.filter(
                referent=True, referent_valid=True
            ).values_list('id_site__id_site', flat=True).distinct()
            return queryset.exclude(id_site__in=site_ids_with_referent)