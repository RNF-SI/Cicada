"""
Filtres pour les Opérations (Actions).
"""
import django_filters

from .models_operations import Operation


class OperationFilter(django_filters.FilterSet):
    """Filtres pour les Opérations."""

    id_indicateur = django_filters.NumberFilter(method='filter_by_indicateur')
    id_priorite = django_filters.NumberFilter(field_name='id_priorite')
    id_type_action = django_filters.NumberFilter(field_name='id_type_action')
    id_site = django_filters.NumberFilter(method='filter_by_site')
    annee_min = django_filters.NumberFilter(field_name='annee_min', lookup_expr='gte')
    annee_max = django_filters.NumberFilter(field_name='annee_max', lookup_expr='lte')

    class Meta:
        model = Operation
        fields = ['id_priorite', 'id_type_action']

    def filter_by_indicateur(self, queryset, name, value):
        return queryset.filter(id_metrique__id_indicateur__id_indicateur=value).distinct()

    def filter_by_site(self, queryset, name, value):
        return queryset.filter(sites__id_site=value).distinct()
