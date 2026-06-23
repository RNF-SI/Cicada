"""
Filtres pour les Suivis/Inventaires (standalone).
"""
import django_filters

from .models_operations import SuiviInventaire


class SuiviInventaireFilter(django_filters.FilterSet):
    """Filtres pour les Suivis/Inventaires."""

    actif = django_filters.BooleanFilter(field_name='actif')
    id_statut = django_filters.NumberFilter(field_name='id_statut')
    id_type_action = django_filters.NumberFilter(field_name='id_type_action')
    type_action_prefix = django_filters.CharFilter(
        method='filter_type_action_prefix',
        help_text="Filtre par préfixe du code d'action (ex: CS8 → CS8, CS8.1, CS8.2, ...)"
    )
    id_pg = django_filters.NumberFilter(field_name='id_pg')
    annee_min = django_filters.DateFilter(field_name='date_lancement_suivi', lookup_expr='gte')
    annee_max = django_filters.NumberFilter(field_name='annee_fin_suivi', lookup_expr='lte')
    # #358 — filtre par site (un suivi est rattaché aux sites via ses opérations).
    site = django_filters.NumberFilter(method='filter_site')

    class Meta:
        model = SuiviInventaire
        fields = ['actif', 'id_statut', 'id_type_action', 'id_pg']

    def filter_type_action_prefix(self, queryset, name, value):
        """Filtre les inventaires dont le type_action commence par le préfixe donné."""
        if not value:
            return queryset
        return queryset.filter(
            id_type_action__cd_nomenclature__startswith=value
        )

    def filter_site(self, queryset, name, value):
        """#358 — suivis rattachés à un site via leurs opérations (CorOperationSite)."""
        if not value:
            return queryset
        return queryset.filter(operations__sites=value).distinct()
