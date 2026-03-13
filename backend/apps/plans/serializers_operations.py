"""
Serializers pour l'API REST Opérations (Actions).
"""
from rest_framework import serializers

from .models_operations import (
    Protocole, SuiviInventaire,
    Operation, CorOperationIndicateur, CorOperationSite, CorOperationMetrique,
    OperationAnnee, FinanceOperation
)


# =============================================================================
# Serializers pour les entités nested
# =============================================================================

class OperationAnneeSerializer(serializers.ModelSerializer):
    """Serializer pour la programmation annuelle d'une opération."""
    operateur_label = serializers.CharField(source='id_operateur.label', read_only=True)

    class Meta:
        model = OperationAnnee
        fields = [
            'id_operation_annee', 'annee', 'periodicite',
            'budget', 'etp', 'id_operateur', 'operateur_label',
            'periodicite_mensuelle', 'geom'
        ]
        read_only_fields = ['id_operation_annee']


class FinanceOperationSerializer(serializers.ModelSerializer):
    """Serializer pour une source de financement d'opération."""
    categorie_label = serializers.CharField(source='id_categorie.label', read_only=True)

    class Meta:
        model = FinanceOperation
        fields = [
            'id_finance_operation', 'libelle',
            'id_categorie', 'categorie_label'
        ]
        read_only_fields = ['id_finance_operation']


class ProtocoleSerializer(serializers.ModelSerializer):
    """Serializer pour un protocole."""

    class Meta:
        model = Protocole
        fields = [
            'id_protocole',
            'protocole_dans_campanule', 'protocole_campanule_nom',
            'cd_protocole_campanule', 'nb_etp_cycle',
            'nom_protocole', 'mode_validation',
            'respect_protocole', 'justification_non_respect', 'differences_protocole',
            'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_protocole', 'date_ajout', 'date_maj']


class SuiviInventaireSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (lecture)."""
    protocole = ProtocoleSerializer(source='id_protocole', read_only=True)

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'cibles_principales', 'taxon_taxref',
            'annee_lancement_suivi',
            # Protocole (nested)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
            # Audit
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']


class SuiviInventaireWriteSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (écriture, accepte protocole nested)."""
    protocole = ProtocoleSerializer(required=False, allow_null=True)

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'cibles_principales', 'taxon_taxref',
            'annee_lancement_suivi',
            # Protocole (nested writable)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
        ]
        read_only_fields = ['id_suivi_inventaire']


# =============================================================================
# Serializer détaillé
# =============================================================================

class OperationSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Opération."""
    priorite_label = serializers.CharField(source='id_priorite.label', read_only=True)
    type_action_label = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    indicateur_ids = serializers.SerializerMethodField()
    nb_indicateurs = serializers.SerializerMethodField()
    site_ids = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
    metrique_ids = serializers.SerializerMethodField()
    nb_metriques = serializers.SerializerMethodField()
    operation_annees = OperationAnneeSerializer(many=True, read_only=True)
    finances = FinanceOperationSerializer(many=True, read_only=True)
    suivi_inventaire = SuiviInventaireSerializer(source='id_suivi', read_only=True)

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle',
            'id_priorite', 'priorite_label',
            'id_type_action', 'type_action_label',
            'id_referentiel_operations', 'code_operation',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'id_suivi', 'suivi_inventaire',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'geom',
            'indicateur_ids', 'nb_indicateurs',
            'site_ids', 'nb_sites',
            'metrique_ids', 'nb_metriques',
            'operation_annees', 'finances',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_indicateur_ids(self, obj):
        return list(obj.indicateurs.values_list('id_indicateur', flat=True))

    def get_nb_indicateurs(self, obj):
        return obj.indicateurs.count()

    def get_site_ids(self, obj):
        return list(obj.sites.values_list('id_site', flat=True))

    def get_nb_sites(self, obj):
        return obj.sites.count()

    def get_metrique_ids(self, obj):
        return list(obj.metriques.values_list('id_metrique', flat=True))

    def get_nb_metriques(self, obj):
        return obj.metriques.count()


# =============================================================================
# Serializer léger (pour listes et imbrication dans IndicateurSerializer)
# =============================================================================

class OperationListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Opérations."""
    priorite_label = serializers.CharField(source='id_priorite.label', read_only=True)
    type_action_label = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    nb_indicateurs = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
    nb_metriques = serializers.SerializerMethodField()
    nb_operation_annees = serializers.SerializerMethodField()
    nb_finances = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle',
            'id_priorite', 'priorite_label',
            'id_type_action', 'type_action_label',
            'id_referentiel_operations', 'code_operation',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'id_suivi',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'nb_indicateurs', 'nb_sites', 'nb_metriques',
            'nb_operation_annees', 'nb_finances',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_nb_indicateurs(self, obj):
        return obj.indicateurs.count()

    def get_nb_sites(self, obj):
        return obj.sites.count()

    def get_nb_metriques(self, obj):
        return obj.metriques.count()

    def get_nb_operation_annees(self, obj):
        return obj.operation_annees.count()

    def get_nb_finances(self, obj):
        return obj.finances.count()


# =============================================================================
# Serializer de création/modification
# =============================================================================

class OperationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Opération."""
    indicateur_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    site_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    metrique_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    operation_annees = OperationAnneeSerializer(many=True, required=False, default=[])
    finances = FinanceOperationSerializer(many=True, required=False, default=[])
    suivi_inventaire = SuiviInventaireWriteSerializer(required=False, allow_null=True)

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle',
            'id_priorite', 'id_type_action',
            'id_referentiel_operations', 'code_operation',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'suivi_inventaire',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'geom',
            'indicateur_ids', 'site_ids', 'metrique_ids',
            'operation_annees', 'finances'
        ]
        read_only_fields = ['id_operation']

    def _create_operation_annees(self, operation, annees_data):
        """Create OperationAnnee objects in bulk."""
        if not annees_data:
            return
        OperationAnnee.objects.bulk_create([
            OperationAnnee(id_operation=operation, **annee)
            for annee in annees_data
        ])

    def _create_finances(self, operation, finances_data):
        """Create FinanceOperation objects in bulk."""
        if not finances_data:
            return
        FinanceOperation.objects.bulk_create([
            FinanceOperation(id_operation=operation, **finance)
            for finance in finances_data
        ])

    def create(self, validated_data):
        indicateur_ids = validated_data.pop('indicateur_ids', [])
        site_ids = validated_data.pop('site_ids', [])
        metrique_ids = validated_data.pop('metrique_ids', [])
        annees_data = validated_data.pop('operation_annees', [])
        finances_data = validated_data.pop('finances', [])
        suivi_data = validated_data.pop('suivi_inventaire', None)

        # Create SuiviInventaire if provided
        if suivi_data:
            user = validated_data.get('id_utilisateur_ajout')
            protocole_data = suivi_data.pop('protocole', None)

            # Create Protocole if provided
            protocole = None
            if protocole_data:
                protocole = Protocole.objects.create(
                    id_utilisateur_ajout=user,
                    **protocole_data
                )

            suivi = SuiviInventaire.objects.create(
                id_utilisateur_ajout=user,
                id_protocole=protocole,
                **suivi_data
            )
            validated_data['id_suivi'] = suivi

        operation = Operation.objects.create(**validated_data)

        # M2M indicateurs
        if indicateur_ids:
            from .models_indicateurs import Indicateur
            indicateurs = Indicateur.objects.filter(id_indicateur__in=indicateur_ids)
            for ind in indicateurs:
                CorOperationIndicateur.objects.create(
                    id_operation=operation,
                    id_indicateur=ind
                )

        # M2M sites
        if site_ids:
            from apps.users.models import Site
            sites = Site.objects.filter(id_site__in=site_ids)
            for site in sites:
                CorOperationSite.objects.create(
                    id_operation=operation,
                    id_site=site
                )

        # M2M metriques
        if metrique_ids:
            from .models_indicateurs import Metrique
            metriques = Metrique.objects.filter(id_metrique__in=metrique_ids)
            for met in metriques:
                CorOperationMetrique.objects.create(
                    id_operation=operation,
                    id_metrique=met
                )

        # Nested: operation_annees and finances
        self._create_operation_annees(operation, annees_data)
        self._create_finances(operation, finances_data)

        return operation

    def update(self, instance, validated_data):
        indicateur_ids = validated_data.pop('indicateur_ids', None)
        site_ids = validated_data.pop('site_ids', None)
        metrique_ids = validated_data.pop('metrique_ids', None)
        annees_data = validated_data.pop('operation_annees', None)
        finances_data = validated_data.pop('finances', None)
        suivi_data = validated_data.pop('suivi_inventaire', None)

        # Handle nested suivi_inventaire
        if suivi_data is not None:
            user = validated_data.get('id_utilisateur_maj') or instance.id_utilisateur_ajout
            protocole_data = suivi_data.pop('protocole', None)

            if instance.id_suivi:
                # Handle protocole nested in suivi
                if protocole_data is not None:
                    if instance.id_suivi.id_protocole:
                        # Update existing Protocole
                        for attr, value in protocole_data.items():
                            setattr(instance.id_suivi.id_protocole, attr, value)
                        instance.id_suivi.id_protocole.id_utilisateur_maj = user
                        instance.id_suivi.id_protocole.save()
                    else:
                        # Create new Protocole
                        protocole = Protocole.objects.create(
                            id_utilisateur_ajout=user,
                            **protocole_data
                        )
                        instance.id_suivi.id_protocole = protocole

                # Update existing SuiviInventaire
                for attr, value in suivi_data.items():
                    setattr(instance.id_suivi, attr, value)
                instance.id_suivi.id_utilisateur_maj = user
                instance.id_suivi.save()
            else:
                # Create new Protocole if provided
                protocole = None
                if protocole_data:
                    protocole = Protocole.objects.create(
                        id_utilisateur_ajout=user,
                        **protocole_data
                    )

                # Create new SuiviInventaire
                suivi = SuiviInventaire.objects.create(
                    id_utilisateur_ajout=user,
                    id_protocole=protocole,
                    **suivi_data
                )
                validated_data['id_suivi'] = suivi

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace M2M indicateurs
        if indicateur_ids is not None:
            CorOperationIndicateur.objects.filter(id_operation=instance).delete()
            from .models_indicateurs import Indicateur
            indicateurs = Indicateur.objects.filter(id_indicateur__in=indicateur_ids)
            for ind in indicateurs:
                CorOperationIndicateur.objects.create(
                    id_operation=instance,
                    id_indicateur=ind
                )

        # Replace M2M sites
        if site_ids is not None:
            CorOperationSite.objects.filter(id_operation=instance).delete()
            from apps.users.models import Site
            sites = Site.objects.filter(id_site__in=site_ids)
            for site in sites:
                CorOperationSite.objects.create(
                    id_operation=instance,
                    id_site=site
                )

        # Replace M2M metriques
        if metrique_ids is not None:
            CorOperationMetrique.objects.filter(id_operation=instance).delete()
            from .models_indicateurs import Metrique
            metriques = Metrique.objects.filter(id_metrique__in=metrique_ids)
            for met in metriques:
                CorOperationMetrique.objects.create(
                    id_operation=instance,
                    id_metrique=met
                )

        # Replace nested operation_annees (delete + recreate)
        if annees_data is not None:
            OperationAnnee.objects.filter(id_operation=instance).delete()
            self._create_operation_annees(instance, annees_data)

        # Replace nested finances (delete + recreate)
        if finances_data is not None:
            FinanceOperation.objects.filter(id_operation=instance).delete()
            self._create_finances(instance, finances_data)

        return instance
