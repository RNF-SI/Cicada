"""
Serializers pour l'API REST Suivis/Inventaires (standalone).
"""
from rest_framework import serializers

from .models_operations import SuiviInventaire
from .serializers_operations import (
    ProtocoleSerializer,
    pop_protocoles_data,
    sync_suivi_protocoles,
)


# =============================================================================
# Serializer léger (pour listes)
# =============================================================================

class SuiviInventaireListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des suivis/inventaires."""
    statut_label = serializers.CharField(source='id_statut.label', read_only=True, default=None)
    type_action_code = serializers.CharField(source='id_type_action.cd_nomenclature', read_only=True, default=None)
    type_action_label = serializers.CharField(source='id_type_action.label', read_only=True, default=None)
    nb_operations = serializers.SerializerMethodField()
    plan_nom = serializers.CharField(source='id_pg.nom', read_only=True, default=None)
    sites_list = serializers.SerializerMethodField()

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule',
            'date_lancement_suivi', 'annee_fin_suivi',
            'id_statut', 'statut_label',
            'id_type_action', 'type_action_code', 'type_action_label',
            'actif',
            'nb_operations',
            'id_pg', 'plan_nom',
            'sites_list',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def get_nb_operations(self, obj):
        return obj.operations.count()

    def get_sites_list(self, obj):
        """Retourne les noms des sites associés via les opérations liées."""
        sites = obj.operations.values_list('sites__nom_site', flat=True).distinct()
        return ', '.join(s for s in sites if s) or None


# =============================================================================
# Serializer détaillé
# =============================================================================

class SuiviInventaireDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un suivi/inventaire."""
    protocoles = ProtocoleSerializer(many=True, read_only=True)
    protocole = serializers.SerializerMethodField()
    statut_label = serializers.CharField(source='id_statut.label', read_only=True, default=None)
    type_action_code = serializers.CharField(source='id_type_action.cd_nomenclature', read_only=True, default=None)
    type_action_label = serializers.CharField(source='id_type_action.label', read_only=True, default=None)
    nb_operations = serializers.SerializerMethodField()
    plan_nom = serializers.CharField(source='id_pg.nom', read_only=True, default=None)
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    bancarisation_label = serializers.SerializerMethodField()
    outil_saisie_label = serializers.SerializerMethodField()

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            # Standalone fields
            'intitule', 'prix_indicatif',
            'id_type_action', 'type_action_code', 'type_action_label',
            'integre_plan_gestion',
            'suit_indicateur', 'type_indicateur',
            'id_pg', 'plan_nom',
            'cible_secondaire', 'habitat_ref', 'habitats',
            'id_statut', 'statut_label',
            'actif',
            'annee_fin_suivi',
            'frequence_nombre', 'frequence_unite', 'frequence_unite_precision',
            'commentaires',
            # Original fields
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
            # Protocoles (#252 — `protocole` = premier de la liste, déprécié)
            'protocoles', 'protocole',
            # Bancarisation
            'outil_bancarisation', 'bancarisation_label',
            'outil_saisie', 'outil_saisie_label',
            'transmission_donnee',
            # Computed
            'nb_operations',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def get_nb_operations(self, obj):
        return obj.operations.count()

    def get_protocole(self, obj):
        """Premier protocole, pour les clients antérieurs à #252."""
        premier = obj.protocoles.first()
        return ProtocoleSerializer(premier).data if premier else None

    def _resolve_nomenclature_label(self, mnemonique, type_mnemonique):
        """Resolve a nomenclature label from its mnemonique."""
        if not mnemonique:
            return None
        from apps.core.models import Nomenclature
        nom = Nomenclature.objects.filter(
            mnemonique=mnemonique,
            id_type__mnemonique=type_mnemonique
        ).first()
        return nom.label if nom else mnemonique

    def get_bancarisation_label(self, obj):
        return self._resolve_nomenclature_label(obj.outil_bancarisation, 'BANCARISATION_STOCKAGE')

    def get_outil_saisie_label(self, obj):
        return self._resolve_nomenclature_label(obj.outil_saisie, 'OUTIL_SAISIE')


# =============================================================================
# Serializer de création/modification
# =============================================================================

class SuiviInventaireCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un suivi/inventaire standalone."""
    protocoles = ProtocoleSerializer(many=True, required=False)
    protocole = ProtocoleSerializer(required=False, allow_null=True)

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            # Standalone fields
            'intitule', 'prix_indicatif',
            'id_type_action',
            'integre_plan_gestion',
            'suit_indicateur', 'type_indicateur',
            'id_pg',
            'cible_secondaire', 'habitat_ref', 'habitats',
            'id_statut',
            'actif',
            'annee_fin_suivi',
            'frequence_nombre', 'frequence_unite', 'frequence_unite_precision',
            'commentaires',
            # Original fields
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
            # Protocoles (nested writable) — `protocole` singulier déprécié (#252)
            'protocoles', 'protocole',
            # Bancarisation
            'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
        ]
        read_only_fields = ['id_suivi_inventaire']
        extra_kwargs = {
            'id_type_action': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        protocoles_data = pop_protocoles_data(validated_data)
        user = validated_data.get('id_utilisateur_ajout')

        suivi = SuiviInventaire.objects.create(**validated_data)
        sync_suivi_protocoles(suivi, protocoles_data, user)
        return suivi

    def update(self, instance, validated_data):
        protocoles_data = pop_protocoles_data(validated_data)
        user = validated_data.get('id_utilisateur_maj') or instance.id_utilisateur_ajout

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        sync_suivi_protocoles(instance, protocoles_data, user)
        return instance
