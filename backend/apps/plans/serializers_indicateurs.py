"""
Serializers pour l'API REST Indicateurs, Métriques et Mesures.
"""
from rest_framework import serializers

from .models_indicateurs import (
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
    Metrique, Mesure,
)


# =============================================================================
# Serializers pour les tables de corrélation
# =============================================================================

class CorIndicateurTaxonSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Taxon."""

    class Meta:
        model = CorIndicateurTaxon
        fields = ['id', 'id_indicateur', 'cd_nom', 'nom_complet', 'nom_vern']
        read_only_fields = ['id']


class CorIndicateurHabitatSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Habitat."""

    class Meta:
        model = CorIndicateurHabitat
        fields = ['id', 'id_indicateur', 'cd_hab', 'lb_hab_fr']
        read_only_fields = ['id']


class CorIndicateurGeologieSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Géologie."""

    class Meta:
        model = CorIndicateurGeologie
        fields = ['id', 'id_indicateur', 'id_inpg', 'nom']
        read_only_fields = ['id']


# =============================================================================
# Serializers pour les Mesures
# =============================================================================

class MesureSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'une Mesure."""
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Mesure
        fields = [
            'id_mesure', 'id_metrique',
            'valeur', 'date_mesure', 'commentaire',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_mesure', 'date_ajout', 'date_maj']


class MesureCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Mesure."""

    class Meta:
        model = Mesure
        fields = [
            'id_mesure', 'id_metrique',
            'valeur', 'date_mesure', 'commentaire'
        ]
        read_only_fields = ['id_mesure']


# =============================================================================
# Serializers pour les Métriques
# =============================================================================

class MetriqueSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Métrique avec mesures imbriquées."""
    mesures = MesureSerializer(many=True, read_only=True)
    nb_mesures = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_metrique_label = serializers.CharField(source='type_metrique.label', read_only=True)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description',
            'type_metrique', 'type_metrique_label',
            'unite', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_label',
            # Relations
            'mesures', 'nb_mesures',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_metrique', 'date_ajout', 'date_maj']

    def get_nb_mesures(self, obj):
        return obj.mesures.count()


class MetriqueListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Métriques."""
    nb_mesures = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_metrique_label = serializers.CharField(source='type_metrique.label', read_only=True)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description',
            'type_metrique', 'type_metrique_label',
            'unite', 'ponderation',
            'nb_mesures',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_metrique', 'date_ajout', 'date_maj']

    def get_nb_mesures(self, obj):
        return obj.mesures.count()


class MetriqueCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Métrique."""

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description',
            'type_metrique', 'unite', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_label',
        ]
        read_only_fields = ['id_metrique']


# =============================================================================
# Serializers pour les Indicateurs
# =============================================================================

class IndicateurSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Indicateur avec métriques et corrélations imbriquées."""
    metriques = MetriqueSerializer(many=True, read_only=True)
    taxons = CorIndicateurTaxonSerializer(many=True, read_only=True)
    habitats = CorIndicateurHabitatSerializer(many=True, read_only=True)
    geologies = CorIndicateurGeologieSerializer(many=True, read_only=True)
    nb_metriques = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_indicateur_label = serializers.CharField(source='type_indicateur.label', read_only=True)

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne',
            'nom_indicateur', 'description',
            'type_indicateur', 'type_indicateur_label',
            'est_standardise',
            # Relations
            'metriques', 'nb_metriques',
            'taxons', 'habitats', 'geologies',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_indicateur', 'date_ajout', 'date_maj']

    def get_nb_metriques(self, obj):
        return obj.metriques.count()


class IndicateurListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Indicateurs."""
    nb_metriques = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_indicateur_label = serializers.CharField(source='type_indicateur.label', read_only=True)

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne',
            'nom_indicateur', 'description',
            'type_indicateur', 'type_indicateur_label',
            'est_standardise',
            'nb_metriques',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_indicateur', 'date_ajout', 'date_maj']

    def get_nb_metriques(self, obj):
        return obj.metriques.count()


class IndicateurCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Indicateur."""

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne',
            'nom_indicateur', 'description',
            'type_indicateur', 'est_standardise'
        ]
        read_only_fields = ['id_indicateur']
