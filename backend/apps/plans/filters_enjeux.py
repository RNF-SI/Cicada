"""
Filtres pour l'API REST Enjeux, FCR et Responsabilités.
"""
import django_filters
from django.db.models import Q

from .models_enjeux import Enjeu, Responsabilite


class EnjeuFilter(django_filters.FilterSet):
    """Filtre pour les Enjeux et FCR."""

    # Filtres par plan
    id_pg = django_filters.NumberFilter(field_name='id_pg__id_pg')
    plan_nom = django_filters.CharFilter(field_name='id_pg__nom', lookup_expr='icontains')

    # Filtres par catégorie (Enjeu ou FCR)
    categorie = django_filters.CharFilter(field_name='id_categorie__mnemonique')
    is_enjeu = django_filters.BooleanFilter(method='filter_is_enjeu')
    is_fcr = django_filters.BooleanFilter(method='filter_is_fcr')

    # Filtres par priorité (Enjeu)
    rang = django_filters.NumberFilter()
    rang_min = django_filters.NumberFilter(field_name='rang', lookup_expr='gte')
    rang_max = django_filters.NumberFilter(field_name='rang', lookup_expr='lte')

    # Filtres par catégorie écologique (Enjeu)
    categorie_ecologique = django_filters.BooleanFilter()

    # Filtres par type d'enjeu
    habitat = django_filters.BooleanFilter()
    espece = django_filters.BooleanFilter()
    processus = django_filters.BooleanFilter()
    has_type = django_filters.BooleanFilter(method='filter_has_type')

    # Filtres par catégorie FCR
    categorie_fcr = django_filters.CharFilter(field_name='id_categorie_fcr__mnemonique')

    # Filtres par importance
    importance = django_filters.CharFilter(field_name='id_importance__mnemonique')

    # Filtres par relations taxonomiques
    has_taxons = django_filters.BooleanFilter(method='filter_has_taxons')
    has_habitats = django_filters.BooleanFilter(method='filter_has_habitats')

    # Filtres par dates
    date_ajout_min = django_filters.DateFilter(field_name='date_ajout', lookup_expr='gte')
    date_ajout_max = django_filters.DateFilter(field_name='date_ajout', lookup_expr='lte')

    # Recherche textuelle
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Enjeu
        fields = [
            'id_pg', 'plan_nom',
            'categorie', 'is_enjeu', 'is_fcr',
            'rang', 'rang_min', 'rang_max',
            'categorie_ecologique', 'habitat', 'espece', 'processus',
            'categorie_fcr', 'importance',
            'has_taxons', 'has_habitats',
            'date_ajout_min', 'date_ajout_max',
            'search'
        ]

    def filter_is_enjeu(self, queryset, name, value):
        """Filtrer pour ne garder que les Enjeux."""
        if value:
            return queryset.filter(id_categorie__mnemonique='ENJEU')
        return queryset.exclude(id_categorie__mnemonique='ENJEU')

    def filter_is_fcr(self, queryset, name, value):
        """Filtrer pour ne garder que les FCR."""
        if value:
            return queryset.filter(id_categorie__mnemonique='FCR')
        return queryset.exclude(id_categorie__mnemonique='FCR')

    def filter_has_type(self, queryset, name, value):
        """Filtrer les enjeux qui ont au moins un type coché."""
        if value:
            return queryset.filter(
                Q(habitat=True) | Q(espece=True) | Q(processus=True) |
                Q(patrimoine_geologique=True) | Q(fonctionnalite_ecosysteme=True) | Q(autre_ecologique=True) |
                Q(valeur_paysagere=True) | Q(patrimoine_culturel=True) | Q(developpement_durable=True) |
                Q(usages=True) | Q(valeur_ajoutee=True) | Q(autre_socioeco=True)
            )
        return queryset.filter(
            habitat=False, espece=False, processus=False,
            patrimoine_geologique=False, fonctionnalite_ecosysteme=False, autre_ecologique=False,
            valeur_paysagere=False, patrimoine_culturel=False, developpement_durable=False,
            usages=False, valeur_ajoutee=False, autre_socioeco=False
        )

    def filter_has_taxons(self, queryset, name, value):
        """Filtrer les enjeux qui ont des taxons associés."""
        if value:
            return queryset.filter(taxons__isnull=False).distinct()
        return queryset.filter(taxons__isnull=True)

    def filter_has_habitats(self, queryset, name, value):
        """Filtrer les enjeux qui ont des habitats associés."""
        if value:
            return queryset.filter(habitats__isnull=False).distinct()
        return queryset.filter(habitats__isnull=True)

    def filter_search(self, queryset, name, value):
        """Recherche textuelle dans plusieurs champs."""
        if value:
            return queryset.filter(
                Q(libelle__icontains=value) |
                Q(intitule_court__icontains=value) |
                Q(description__icontains=value) |
                Q(etat_enjeu__icontains=value)
            )
        return queryset


class ResponsabiliteFilter(django_filters.FilterSet):
    """Filtre pour les Responsabilités."""

    # Filtres par site
    id_site = django_filters.NumberFilter(field_name='id_site__id_site')
    site_nom = django_filters.CharFilter(field_name='id_site__nom_site', lookup_expr='icontains')

    # Filtres par type et niveau
    type_responsabilite = django_filters.CharFilter(
        field_name='id_type_responsabilite__mnemonique'
    )
    niveau_responsabilite = django_filters.CharFilter(
        field_name='id_niveau_responsabilite__mnemonique'
    )

    # Filtres par relations
    has_taxons = django_filters.BooleanFilter(method='filter_has_taxons')
    has_habitats = django_filters.BooleanFilter(method='filter_has_habitats')
    has_enjeux = django_filters.BooleanFilter(method='filter_has_enjeux')

    # Filtres par dates
    date_ajout_min = django_filters.DateFilter(field_name='date_ajout', lookup_expr='gte')
    date_ajout_max = django_filters.DateFilter(field_name='date_ajout', lookup_expr='lte')

    # Recherche textuelle
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Responsabilite
        fields = [
            'id_site', 'site_nom',
            'type_responsabilite', 'niveau_responsabilite',
            'has_taxons', 'has_habitats', 'has_enjeux',
            'date_ajout_min', 'date_ajout_max',
            'search'
        ]

    def filter_has_taxons(self, queryset, name, value):
        """Filtrer les responsabilités qui ont des taxons associés."""
        if value:
            return queryset.filter(taxons__isnull=False).distinct()
        return queryset.filter(taxons__isnull=True)

    def filter_has_habitats(self, queryset, name, value):
        """Filtrer les responsabilités qui ont des habitats associés."""
        if value:
            return queryset.filter(habitats__isnull=False).distinct()
        return queryset.filter(habitats__isnull=True)

    def filter_has_enjeux(self, queryset, name, value):
        """Filtrer les responsabilités qui ont des enjeux liés."""
        if value:
            return queryset.filter(enjeux_lies__isnull=False).distinct()
        return queryset.filter(enjeux_lies__isnull=True)

    def filter_search(self, queryset, name, value):
        """Recherche textuelle dans plusieurs champs."""
        if value:
            return queryset.filter(
                Q(description__icontains=value) |
                Q(id_site__nom_site__icontains=value)
            )
        return queryset
