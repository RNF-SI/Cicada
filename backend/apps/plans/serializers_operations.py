"""
Serializers pour l'API REST Opérations (Actions).
"""
from rest_framework import serializers

from .models_operations import (
    Protocole, SuiviInventaire,
    Operation, CorOperationSite,
    OperationAnnee, OperationAnneeOrganisme, FinanceOperation
)


# =============================================================================
# Serializers pour les entités nested
# =============================================================================

class OperationAnneeOrganismeSerializer(serializers.ModelSerializer):
    """Serializer pour la ventilation budget/travail par organisme."""
    organisme_nom = serializers.CharField(source='id_organisme.nom_organisme', read_only=True)

    class Meta:
        model = OperationAnneeOrganisme
        fields = [
            'id_operation_annee_organisme',
            'id_organisme', 'organisme_nom',
            'budget_fonctionnement', 'budget_investissement', 'etp'
        ]
        read_only_fields = ['id_operation_annee_organisme']


class OperationAnneeSerializer(serializers.ModelSerializer):
    """Serializer pour la programmation annuelle d'une opération."""
    organismes = OperationAnneeOrganismeSerializer(many=True, read_only=True)

    class Meta:
        model = OperationAnnee
        fields = [
            'id_operation_annee', 'annee', 'periodicite',
            'budget', 'etp',
            'periodicite_mensuelle', 'geom', 'organismes'
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
            'periode_suivi', 'documentation_disponible', 'url_documentation',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_protocole', 'date_ajout', 'date_maj']


class SuiviInventaireSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (lecture)."""
    protocole = ProtocoleSerializer(source='id_protocole', read_only=True)
    bancarisation_label = serializers.SerializerMethodField()
    outil_saisie_label = serializers.SerializerMethodField()

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
            # Protocole (nested)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'bancarisation_label',
            'outil_saisie', 'outil_saisie_label',
            'transmission_donnee',
            # Audit
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def _resolve_nomenclature_label(self, mnemonique, type_mnemonique):
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


class SuiviInventaireWriteSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (écriture, accepte protocole nested)."""
    protocole = ProtocoleSerializer(required=False, allow_null=True)

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'taxon_taxref',
            'date_lancement_suivi',
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
    metrique_nom = serializers.CharField(source='id_metrique.nom_metrique', read_only=True, default=None)
    indicateur_id = serializers.SerializerMethodField()
    indicateur_nom = serializers.SerializerMethodField()
    site_ids = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
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
            'id_metrique', 'metrique_nom',
            'indicateur_id', 'indicateur_nom',
            'site_ids', 'nb_sites',
            'operation_annees', 'finances',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_indicateur_id(self, obj):
        if obj.id_metrique and obj.id_metrique.id_indicateur_id:
            return obj.id_metrique.id_indicateur_id
        return None

    def get_indicateur_nom(self, obj):
        if obj.id_metrique and obj.id_metrique.id_indicateur:
            return obj.id_metrique.id_indicateur.nom_indicateur
        return None

    def get_site_ids(self, obj):
        return list(obj.sites.values_list('id_site', flat=True))

    def get_nb_sites(self, obj):
        return obj.sites.count()


# =============================================================================
# Serializer léger (pour listes et imbrication dans IndicateurSerializer)
# =============================================================================

class OperationListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Opérations."""
    priorite_label = serializers.CharField(source='id_priorite.label', read_only=True)
    type_action_label = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    metrique_nom = serializers.CharField(source='id_metrique.nom_metrique', read_only=True, default=None)
    indicateur_id = serializers.SerializerMethodField()
    indicateur_nom = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
    nb_operation_annees = serializers.SerializerMethodField()
    nb_finances = serializers.SerializerMethodField()
    enjeu_slug = serializers.SerializerMethodField()
    oo_id = serializers.SerializerMethodField()

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
            'id_metrique', 'metrique_nom',
            'indicateur_id', 'indicateur_nom',
            'nb_sites',
            'nb_operation_annees', 'nb_finances',
            'enjeu_slug', 'oo_id',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_indicateur_id(self, obj):
        if obj.id_metrique and obj.id_metrique.id_indicateur_id:
            return obj.id_metrique.id_indicateur_id
        return None

    def get_indicateur_nom(self, obj):
        if obj.id_metrique and obj.id_metrique.id_indicateur:
            return obj.id_metrique.id_indicateur.nom_indicateur
        return None

    def get_nb_sites(self, obj):
        return obj.sites.count()

    def get_nb_operation_annees(self, obj):
        return obj.operation_annees.count()

    def get_nb_finances(self, obj):
        return obj.finances.count()

    def _get_enjeu_via_ne(self, indicateur):
        """Traverse NE path: Indicateur → NE → OLT → Enjeu."""
        try:
            ne = indicateur.id_ne
            if ne and ne.id_olt and ne.id_olt.id_enjeu:
                return ne.id_olt.id_enjeu
        except AttributeError:
            pass
        return None

    def _get_enjeu_and_oo_via_ra(self, indicateur):
        """Traverse RA path: Indicateur → RA → OO → Pression → FI → Enjeu."""
        try:
            ra = indicateur.id_resultat_attendu
            if ra and ra.id_oo and ra.id_oo.id_pression and ra.id_oo.id_pression.id_facteur_influence:
                fi = ra.id_oo.id_pression.id_facteur_influence
                if fi.id_enjeu:
                    return fi.id_enjeu, ra.id_oo.id_oo
        except AttributeError:
            pass
        return None, None

    def get_enjeu_slug(self, obj):
        if not obj.id_metrique or not obj.id_metrique.id_indicateur:
            return None
        indicateur = obj.id_metrique.id_indicateur
        # Try NE path first
        enjeu = self._get_enjeu_via_ne(indicateur)
        if enjeu:
            return enjeu.slug
        # Try RA path
        enjeu, _ = self._get_enjeu_and_oo_via_ra(indicateur)
        if enjeu:
            return enjeu.slug
        return None

    def get_oo_id(self, obj):
        if not obj.id_metrique or not obj.id_metrique.id_indicateur:
            return None
        indicateur = obj.id_metrique.id_indicateur
        _, oo_id = self._get_enjeu_and_oo_via_ra(indicateur)
        return oo_id


# =============================================================================
# Serializer de création/modification
# =============================================================================

class OperationAnneeOrganismeWriteSerializer(serializers.Serializer):
    """Write serializer for organisme budget data within an operation year."""
    id_organisme = serializers.IntegerField()
    budget_fonctionnement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    budget_investissement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    etp = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)


class OperationAnneeWriteSerializer(serializers.Serializer):
    """Write serializer for operation year with nested organismes."""
    annee = serializers.IntegerField()
    periodicite = serializers.BooleanField(default=False)
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    etp = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    periodicite_mensuelle = serializers.JSONField(default=dict, required=False)
    geom = serializers.JSONField(required=False, allow_null=True, default=None)
    organismes = OperationAnneeOrganismeWriteSerializer(many=True, required=False, default=[])


class OperationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Opération."""
    site_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    operation_annees = OperationAnneeWriteSerializer(many=True, required=False, default=[])
    finances = FinanceOperationSerializer(many=True, required=False, default=[])
    suivi_inventaire = SuiviInventaireWriteSerializer(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle',
            'id_priorite', 'id_type_action',
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
            'id_metrique', 'site_ids',
            'operation_annees', 'finances'
        ]
        read_only_fields = ['id_operation']
        extra_kwargs = {
            'id_suivi': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        """Use the read serializer for the response."""
        return OperationSerializer(instance, context=self.context).data

    def _create_operation_annees(self, operation, annees_data):
        """Create OperationAnnee objects with nested organismes."""
        if not annees_data:
            return
        for annee_data in annees_data:
            organismes_data = annee_data.pop('organismes', [])
            annee_obj = OperationAnnee.objects.create(id_operation=operation, **annee_data)
            if organismes_data:
                OperationAnneeOrganisme.objects.bulk_create([
                    OperationAnneeOrganisme(
                        id_operation_annee=annee_obj,
                        id_organisme_id=org['id_organisme'],
                        budget_fonctionnement=org.get('budget_fonctionnement'),
                        budget_investissement=org.get('budget_investissement'),
                        etp=org.get('etp'),
                    )
                    for org in organismes_data
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
        site_ids = validated_data.pop('site_ids', [])
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

        # M2M sites
        if site_ids:
            from apps.users.models import Site
            sites = Site.objects.filter(id_site__in=site_ids)
            for site in sites:
                CorOperationSite.objects.create(
                    id_operation=operation,
                    id_site=site
                )

        # Nested: operation_annees and finances
        self._create_operation_annees(operation, annees_data)
        self._create_finances(operation, finances_data)

        return operation

    def update(self, instance, validated_data):
        site_ids = validated_data.pop('site_ids', None)
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

        # Replace nested operation_annees (delete + recreate)
        if annees_data is not None:
            OperationAnnee.objects.filter(id_operation=instance).delete()
            self._create_operation_annees(instance, annees_data)

        # Replace nested finances (delete + recreate)
        if finances_data is not None:
            FinanceOperation.objects.filter(id_operation=instance).delete()
            self._create_finances(instance, finances_data)

        return instance
