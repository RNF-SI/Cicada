"""
Serializers pour l'API REST Indicateurs, Métriques et Mesures.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models_indicateurs import (
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
    Metrique, MetriqueScoreBlock, Mesure,
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

class MetriqueScoreBlockSerializer(serializers.ModelSerializer):
    """
    Bloc de scoring complémentaire d'une métrique numérique (#247).

    Même structure qu'un bloc principal (5 paliers, sens de variation,
    inclusivités, bornes extrêmes). Combiné aux blocs précédents via
    `logical_op` (OR par défaut).
    """

    class Meta:
        model = MetriqueScoreBlock
        fields = [
            'id_score_block',
            'position',
            'logical_op',
            'group_open',
            'group_close',
            'sens_variation',
            'score_1_inf', 'score_1_sup',
            'score_2_inf', 'score_2_sup',
            'score_3_inf', 'score_3_sup',
            'score_4_inf', 'score_4_sup',
            'score_5_inf', 'score_5_sup',
            'score_1_sup_inclusive',
            'score_2_sup_inclusive',
            'score_3_sup_inclusive',
            'score_4_sup_inclusive',
            'has_borne_score1',
            'has_borne_score5',
            'inactive_levels',
        ]
        read_only_fields = ['id_score_block']


class MetriqueSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Métrique avec mesures et opérations imbriquées."""
    mesures = MesureSerializer(many=True, read_only=True)
    nb_mesures = serializers.SerializerMethodField()
    operations = serializers.SerializerMethodField()
    nb_operations = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_metrique_label = serializers.CharField(source='type_metrique.label', read_only=True)
    type_metrique_mnemonique = serializers.CharField(source='type_metrique.mnemonique', read_only=True)
    score_blocks = MetriqueScoreBlockSerializer(many=True, read_only=True)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description', 'ordre',
            'type_metrique', 'type_metrique_label', 'type_metrique_mnemonique',
            'unite', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_val', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_val', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_val', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_val', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_val', 'score_5_label',
            # Direction et inclusivité des bornes
            'sens_variation',
            'score_1_sup_inclusive', 'score_2_sup_inclusive',
            'score_3_sup_inclusive', 'score_4_sup_inclusive',
            'has_borne_score1', 'has_borne_score5',
            'inactive_levels',
            'group_open', 'group_close',
            # Blocs complémentaires (#247) — même structure que le bloc principal
            'score_blocks',
            # Relations
            'mesures', 'nb_mesures',
            'operations', 'nb_operations',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_metrique', 'date_ajout', 'date_maj']

    def get_nb_mesures(self, obj):
        # Use prefetched data if available (avoids COUNT query)
        if hasattr(obj, '_prefetched_objects_cache') and 'mesures' in obj._prefetched_objects_cache:
            return len(obj.mesures.all())
        return obj.mesures.count()

    def get_operations(self, obj):
        from .serializers_operations import OperationNestedSerializer
        # Nested serializer: operation_annees + finances, sans les lookups coûteux (enjeu_slug/oo_id)
        return OperationNestedSerializer(obj.operations.all(), many=True).data

    def get_nb_operations(self, obj):
        # Use prefetched data if available (avoids COUNT query)
        if hasattr(obj, '_prefetched_objects_cache') and 'operations' in obj._prefetched_objects_cache:
            return len(obj.operations.all())
        return obj.operations.count()


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

    # #247 — Blocs de scoring complémentaires (même structure que le bloc principal,
    # combinés en ET/OU). Le client envoie la liste complète à chaque update.
    score_blocks = MetriqueScoreBlockSerializer(many=True, required=False)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description', 'ordre',
            'type_metrique', 'unite', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_val', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_val', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_val', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_val', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_val', 'score_5_label',
            # Direction et inclusivité des bornes
            'sens_variation',
            'score_1_sup_inclusive', 'score_2_sup_inclusive',
            'score_3_sup_inclusive', 'score_4_sup_inclusive',
            'has_borne_score1', 'has_borne_score5',
            'inactive_levels',
            'group_open', 'group_close',
            # Blocs complémentaires
            'score_blocks',
        ]
        read_only_fields = ['id_metrique']

    def create(self, validated_data):
        blocks = validated_data.pop('score_blocks', [])
        metrique = super().create(validated_data)
        for block in blocks:
            MetriqueScoreBlock.objects.create(id_metrique=metrique, **block)
        return metrique

    def update(self, instance, validated_data):
        # Stratégie simple : on remplace l'ensemble des blocs à chaque update.
        # Le client doit envoyer la liste complète des blocs complémentaires
        # à conserver. Évite la complexité d'un diff partiel.
        blocks = validated_data.pop('score_blocks', None)
        instance = super().update(instance, validated_data)
        if blocks is not None:
            instance.score_blocks.all().delete()
            for block in blocks:
                MetriqueScoreBlock.objects.create(id_metrique=instance, **block)
        return instance

    def validate(self, attrs):
        """Validate interval consistency for NUMERIQUE metrics."""
        type_met = attrs.get('type_metrique', getattr(self.instance, 'type_metrique', None) if self.instance else None)

        # Only validate for NUMERIQUE type
        is_numerique = True
        if type_met and hasattr(type_met, 'mnemonique'):
            is_numerique = type_met.mnemonique == 'NUMERIQUE'
        elif type_met and hasattr(type_met, 'pk'):
            from apps.core.models import Nomenclature
            try:
                is_numerique = Nomenclature.objects.get(pk=type_met.pk).mnemonique == 'NUMERIQUE'
            except Nomenclature.DoesNotExist:
                is_numerique = False

        if not is_numerique:
            return attrs

        sens = attrs.get(
            'sens_variation',
            getattr(self.instance, 'sens_variation', 'CROISSANT') if self.instance else 'CROISSANT'
        )

        # Niveaux désactivés : sautés par les validateurs de bornes / continuité.
        inactive = attrs.get(
            'inactive_levels',
            getattr(self.instance, 'inactive_levels', None) if self.instance else None
        ) or []
        try:
            inactive_set = {int(x) for x in inactive}
        except (TypeError, ValueError):
            inactive_set = set()

        # Validate inf < sup for each level (always true regardless of direction)
        for level in range(1, 6):
            if level in inactive_set:
                continue
            inf_val = attrs.get(f'score_{level}_inf')
            sup_val = attrs.get(f'score_{level}_sup')
            if inf_val is not None and sup_val is not None and inf_val >= sup_val:
                raise serializers.ValidationError({
                    f'score_{level}_sup': _("La borne sup doit être strictement supérieure à la borne inf.")
                })

        # Validate continuity between adjacent levels — en sautant les niveaux
        # inactifs (un niveau marqué « non utilisé » casse volontairement la
        # continuité avec ses voisins).
        # Ascending: score_N_sup == score_(N+1)_inf (boundary = upper end of N)
        # Descending: score_N_inf == score_(N+1)_sup (boundary = lower end of N)
        for n in range(1, 5):
            if n in inactive_set or (n + 1) in inactive_set:
                continue
            if sens == 'DECROISSANT':
                val_n = attrs.get(f'score_{n}_inf')
                val_next = attrs.get(f'score_{n + 1}_sup')
            else:
                val_n = attrs.get(f'score_{n}_sup')
                val_next = attrs.get(f'score_{n + 1}_inf')

            if val_n is not None and val_next is not None and val_n != val_next:
                raise serializers.ValidationError(
                    _("Les bornes entre les scores %(n)s et %(next)s doivent être égales pour assurer la continuité.")
                    % {'n': n, 'next': n + 1}
                )

        return attrs


# =============================================================================
# Serializers pour les Indicateurs
# =============================================================================

class IndicateurSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Indicateur avec métriques et corrélations imbriquées.
    Les opérations sont désormais imbriquées sous chaque métrique (Métrique → Opérations)."""
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
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
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
    nb_operations = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_indicateur_label = serializers.CharField(source='type_indicateur.label', read_only=True)

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
            'nom_indicateur', 'description',
            'type_indicateur', 'type_indicateur_label',
            'est_standardise',
            'nb_metriques', 'nb_operations',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_indicateur', 'date_ajout', 'date_maj']

    def get_nb_metriques(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'metriques' in obj._prefetched_objects_cache:
            return len(obj.metriques.all())
        return obj.metriques.count()

    def get_nb_operations(self, obj):
        # Use prefetched data if available to avoid N+1
        if hasattr(obj, '_prefetched_objects_cache') and 'metriques' in obj._prefetched_objects_cache:
            seen = set()
            for met in obj.metriques.all():
                if hasattr(met, '_prefetched_objects_cache') and 'operations' in met._prefetched_objects_cache:
                    for op in met.operations.all():
                        seen.add(op.id_operation)
            return len(seen)
        from .models_operations import Operation
        return Operation.objects.filter(metriques__id_indicateur=obj).distinct().count()


class IndicateurCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Indicateur."""

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
            'nom_indicateur', 'description',
            'type_indicateur', 'est_standardise'
        ]
        read_only_fields = ['id_indicateur']

    def validate(self, attrs):
        id_ne = attrs.get('id_ne', getattr(self.instance, 'id_ne', None) if self.instance else None)
        id_ra = attrs.get('id_resultat_attendu', getattr(self.instance, 'id_resultat_attendu', None) if self.instance else None)

        if not id_ne and not id_ra:
            raise serializers.ValidationError(
                "Un indicateur doit être rattaché à un niveau d'exigence ou un résultat attendu."
            )
        if id_ne and id_ra:
            raise serializers.ValidationError(
                "Un indicateur ne peut être rattaché qu'à un seul parent."
            )
        return attrs
