"""
Filtres pour les Suivis/Inventaires (standalone).
"""
import django_filters

from .models_operations import SuiviInventaire


class SuiviInventaireFilter(django_filters.FilterSet):
    """Filtres pour les Suivis/Inventaires."""

    actif = django_filters.BooleanFilter(field_name='actif')
    id_statut = django_filters.NumberFilter(field_name='id_statut')
    id_type_suivi = django_filters.NumberFilter(field_name='id_type_suivi')
    id_pg = django_filters.NumberFilter(field_name='id_pg')
    annee_min = django_filters.DateFilter(field_name='date_lancement_suivi', lookup_expr='gte')
    annee_max = django_filters.NumberFilter(field_name='annee_fin_suivi', lookup_expr='lte')

    class Meta:
        model = SuiviInventaire
        fields = ['actif', 'id_statut', 'id_type_suivi', 'id_pg']
