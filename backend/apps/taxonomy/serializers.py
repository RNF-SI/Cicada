"""Serializers pour l'API TaxRef."""

from rest_framework import serializers

from .models import Taxref, VMTaxrefListForAutocomplete, TMetaTaxref


class TaxrefListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes de taxons."""

    class Meta:
        model = Taxref
        fields = [
            'cd_nom', 'cd_ref', 'lb_nom', 'nom_complet', 'nom_valide',
            'nom_vern', 'regne', 'group2_inpn', 'id_rang', 'famille',
        ]


class TaxrefDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un taxon."""

    class Meta:
        model = Taxref
        fields = '__all__'


class TaxrefAutocompleteSerializer(serializers.ModelSerializer):
    """Serializer pour l'autocomplete des taxons."""

    class Meta:
        model = VMTaxrefListForAutocomplete
        fields = [
            'cd_nom', 'cd_ref', 'search_name', 'nom_valide',
            'nom_vern', 'lb_nom', 'regne', 'group2_inpn', 'id_rang',
        ]


class TaxrefVersionSerializer(serializers.ModelSerializer):
    """Serializer pour la version du référentiel."""

    class Meta:
        model = TMetaTaxref
        fields = ['referential_name', 'version', 'update_date']
