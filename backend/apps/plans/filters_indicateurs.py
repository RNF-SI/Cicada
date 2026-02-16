"""
Filtres pour les Indicateurs, Métriques et Mesures.
"""
import django_filters

from .models_indicateurs import Indicateur, Metrique, Mesure


class IndicateurFilter(django_filters.FilterSet):
    """Filtres pour les Indicateurs."""

    id_ne = django_filters.NumberFilter(field_name='id_ne')
    type_indicateur = django_filters.NumberFilter(field_name='type_indicateur')
    est_standardise = django_filters.BooleanFilter(field_name='est_standardise')

    class Meta:
        model = Indicateur
        fields = ['id_ne', 'type_indicateur', 'est_standardise']


class MetriqueFilter(django_filters.FilterSet):
    """Filtres pour les Métriques."""

    id_indicateur = django_filters.NumberFilter(field_name='id_indicateur')
    type_metrique = django_filters.NumberFilter(field_name='type_metrique')

    class Meta:
        model = Metrique
        fields = ['id_indicateur', 'type_metrique']


class MesureFilter(django_filters.FilterSet):
    """Filtres pour les Mesures."""

    id_metrique = django_filters.NumberFilter(field_name='id_metrique')
    date_mesure_min = django_filters.DateFilter(field_name='date_mesure', lookup_expr='gte')
    date_mesure_max = django_filters.DateFilter(field_name='date_mesure', lookup_expr='lte')

    class Meta:
        model = Mesure
        fields = ['id_metrique']
