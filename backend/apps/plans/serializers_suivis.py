"""
Serializers pour l'API REST Suivis/Inventaires (standalone).
"""
from rest_framework import serializers

from .models_operations import Protocole, SuiviInventaire
from .serializers_operations import ProtocoleSerializer


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
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def get_nb_operations(self, obj):
        return obj.operations.count()


# =============================================================================
# Serializer détaillé
# =============================================================================

class SuiviInventaireDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un suivi/inventaire."""
    protocole = ProtocoleSerializer(source='id_protocole', read_only=True)
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
            'cible_secondaire', 'habitat_ref',
            'id_statut', 'statut_label',
            'actif',
            'annee_fin_suivi',
            'frequence_nombre', 'frequence_unite', 'frequence_unite_precision',
            'commentaires',
            # Original fields
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
            # Protocole (nested)
            'protocole',
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
            'cible_secondaire', 'habitat_ref',
            'id_statut',
            'actif',
            'annee_fin_suivi',
            'frequence_nombre', 'frequence_unite', 'frequence_unite_precision',
            'commentaires',
            # Original fields
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
            # Protocole (nested writable)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
        ]
        read_only_fields = ['id_suivi_inventaire']
        extra_kwargs = {
            'id_type_action': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        protocole_data = validated_data.pop('protocole', None)
        user = validated_data.get('id_utilisateur_ajout')

        # Create Protocole if provided
        protocole = None
        if protocole_data:
            protocole = Protocole.objects.create(
                id_utilisateur_ajout=user,
                **protocole_data
            )

        suivi = SuiviInventaire.objects.create(
            id_protocole=protocole,
            **validated_data
        )
        return suivi

    def update(self, instance, validated_data):
        protocole_data = validated_data.pop('protocole', None)
        user = validated_data.get('id_utilisateur_maj') or instance.id_utilisateur_ajout

        # Handle nested protocole
        if protocole_data is not None:
            if instance.id_protocole:
                # Update existing Protocole
                for attr, value in protocole_data.items():
                    setattr(instance.id_protocole, attr, value)
                instance.id_protocole.id_utilisateur_maj = user
                instance.id_protocole.save()
            else:
                # Create new Protocole
                protocole = Protocole.objects.create(
                    id_utilisateur_ajout=user,
                    **protocole_data
                )
                instance.id_protocole = protocole

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
