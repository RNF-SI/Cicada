"""
Serializers pour l'API REST Plans de Gestion.
"""
from rest_framework import serializers
from django.contrib.gis.serializers.geojson import Serializer as GeoJSONSerializer
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

from .models import PlanGestion, CorSitePg, CorPgFichier, CorRolePlan
from apps.users.serializers import RoleBasicSerializer, SiteBasicSerializer


class CorSitePgSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Site-Plan de Gestion."""

    site = SiteBasicSerializer(read_only=True)
    site_id = serializers.IntegerField(write_only=True, source='site.id_site')

    class Meta:
        model = CorSitePg
        fields = [
            'id', 'site', 'site_id', 'rang', 'commentaire',
            'date_association'
        ]
        read_only_fields = ['id', 'date_association']


class CorPgFichierSerializer(serializers.ModelSerializer):
    """Serializer pour les fichiers de Plans de Gestion."""

    fichier = serializers.FileField(write_only=True, required=False)
    file_size_human = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    is_document = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CorPgFichier
        fields = [
            'id', 'nom_fichier', 'chemin_fichier', 'fichier', 'url',
            'type_fichier', 'titre', 'description', 'auteur', 'public',
            'ordre_affichage', 'taille_fichier', 'file_size_human', 'extension',
            'is_image', 'is_document', 'date_upload', 'date_document'
        ]
        read_only_fields = [
            'id', 'chemin_fichier', 'taille_fichier', 'extension',
            'date_upload'
        ]

    def get_file_size_human(self, obj):
        """Retourne la taille du fichier en format lisible."""
        if obj.taille_fichier:
            size = obj.taille_fichier
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        return None

    def get_is_image(self, obj):
        """Vérifie si le fichier est une image."""
        if obj.extension:
            return obj.extension.lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return False

    def get_is_document(self, obj):
        """Vérifie si le fichier est un document."""
        if obj.extension:
            return obj.extension.lower() in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods']
        return False
    
    def get_url(self, obj):
        """URL de téléchargement du fichier."""
        if obj.chemin_fichier:
            return f"/media/plans/{obj.plan_de_gestion.id_pg}/{obj.nom_fichier}"
        return None
    
    def create(self, validated_data):
        """Créer un fichier avec upload."""
        fichier = validated_data.pop('fichier', None)
        instance = super().create(validated_data)
        
        if fichier:
            instance.handle_file_upload(fichier)
        
        return instance


class PlanSiteListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les sites dans la liste des plans."""
    id_site = serializers.IntegerField(source='site.id_site')
    nom_site = serializers.CharField(source='site.nom_site')
    slug = serializers.SlugField(source='site.slug', read_only=True)
    type_site_label = serializers.SerializerMethodField()

    class Meta:
        model = CorSitePg
        fields = ['id_site', 'nom_site', 'slug', 'type_site_label', 'rang']

    def get_type_site_label(self, obj):
        """Récupérer le label du type de site depuis la nomenclature."""
        if obj.site and obj.site.id_type_site:
            return obj.site.id_type_site.label
        return None


class PlanReferentListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les référents dans la liste des plans."""
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = None  # Will be set to Role
        fields = ['id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet']


# Set the model after import to avoid circular imports
from apps.users.models import Role
PlanReferentListSerializer.Meta.model = Role


class CorRolePlanSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Utilisateur-Plan de Gestion (membres et référents)."""

    id_role = serializers.IntegerField(source='id_role.id_role', read_only=True)
    email = serializers.EmailField(source='id_role.email', read_only=True)
    nom_role = serializers.CharField(source='id_role.nom_role', read_only=True)
    prenom_role = serializers.CharField(source='id_role.prenom_role', read_only=True)
    nom_complet = serializers.CharField(source='id_role.get_full_name', read_only=True)

    class Meta:
        model = CorRolePlan
        fields = [
            'id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet',
            'referent', 'date_association', 'commentaire'
        ]


class PlanGestionListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des Plans de Gestion."""

    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    nb_sites = serializers.IntegerField(source='sites.count', read_only=True)
    nb_fichiers = serializers.IntegerField(source='fichiers.count', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    evaluation_display = serializers.CharField(source='id_evaluation.label', read_only=True)
    redacteur_type_display = serializers.CharField(source='id_redacteur_type.label', read_only=True)

    # Include sites and referents details for admin display
    sites = PlanSiteListSerializer(many=True, read_only=True)
    referents = PlanReferentListSerializer(many=True, read_only=True)
    membres = CorRolePlanSerializer(many=True, read_only=True)

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'id_cdr', 'rang', 'annee_debut', 'annee_fin', 'periode_gestion',
            'surface', 'gestion_partagee', 'ct88', 'risque_incendie', 'statut', 'statut_display', 'version',
            'date_validation_cspn', 'id_docgestion_fcen',
            'evaluation_display', 'redacteur_type_display', 'redacteur_nom',
            'redacteurs', 'relecteurs',
            'nb_sites', 'nb_fichiers', 'sites', 'referents', 'membres', 'date_ajout', 'date_maj'
        ]


class PlanGestionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les Plans de Gestion."""

    # Relations - use simplified serializers for frontend compatibility
    sites = PlanSiteListSerializer(many=True, read_only=True)
    fichiers = CorPgFichierSerializer(many=True, read_only=True)
    referents = PlanReferentListSerializer(many=True, read_only=True)
    membres = CorRolePlanSerializer(many=True, read_only=True)

    # Champs calculés
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    is_multi_sites = serializers.BooleanField(read_only=True)
    organismes_gestionnaires = serializers.SerializerMethodField()
    sites_list = serializers.SerializerMethodField()

    # Champs display
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    evaluation_display = serializers.CharField(source='id_evaluation.label', read_only=True)
    redacteur_type_display = serializers.CharField(source='id_redacteur_type.label', read_only=True)

    # Utilisateurs
    utilisateur_ajout = RoleBasicSerializer(source='id_utilisateur_ajout', read_only=True)
    utilisateur_maj = RoleBasicSerializer(source='id_utilisateur_maj', read_only=True)

    # IDs pour création/modification
    evaluation_id = serializers.IntegerField(source='id_evaluation.id_nomenclature', write_only=True, required=False, allow_null=True)
    redacteur_type_id = serializers.IntegerField(source='id_redacteur_type.id_nomenclature', write_only=True, required=False, allow_null=True)
    sites_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    def get_organismes_gestionnaires(self, obj):
        """Retourne la liste des noms des organismes gestionnaires."""
        organismes = []
        for site in obj.get_sites():
            for cor_og_site in site.corogsite_set.select_related('uuid_og'):
                if cor_og_site.uuid_og:
                    organismes.append({
                        'id_organisme': cor_og_site.uuid_og.id_organisme,
                        'nom_organisme': cor_og_site.uuid_og.nom_organisme
                    })
        # Remove duplicates by id
        seen = set()
        unique = []
        for org in organismes:
            if org['id_organisme'] not in seen:
                seen.add(org['id_organisme'])
                unique.append(org)
        return unique

    def get_sites_list(self, obj):
        """Retourne la liste simplifiée des sites."""
        return [
            {'id_site': site.id_site, 'nom_site': site.nom_site}
            for site in obj.get_sites()
        ]

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'id_cdr', 'rang',
            'annee_debut', 'annee_fin', 'periode_gestion',
            'surface', 'gestion_partagee', 'ct88', 'risque_incendie',
            'date_validation_cspn', 'id_docgestion_fcen',
            'evaluation_id', 'evaluation_display', 'redacteur_type_id', 'redacteur_type_display',
            'redacteur_nom', 'redacteurs', 'relecteurs',
            'commentaire', 'statut', 'statut_display', 'version',
            'geometrie', 'is_multi_sites', 'organismes_gestionnaires', 'sites_list',
            'sites', 'fichiers', 'referents', 'membres', 'sites_ids', 'referents_ids',
            'utilisateur_ajout', 'utilisateur_maj',
            'date_ajout', 'date_maj'
        ]
        read_only_fields = [
            'id_pg', 'slug', 'date_ajout', 'date_maj'
        ]
    
    def create(self, validated_data):
        """Créer un plan avec ses relations."""
        sites_ids = validated_data.pop('sites_ids', [])
        referents_ids = validated_data.pop('referents_ids', [])

        # Résoudre les IDs des nomenclatures
        if 'id_evaluation' in validated_data:
            from apps.core.models import Nomenclature
            eval_id = validated_data['id_evaluation']['id_nomenclature']
            validated_data['id_evaluation'] = Nomenclature.objects.get(id_nomenclature=eval_id)

        if 'id_redacteur_type' in validated_data:
            from apps.core.models import Nomenclature
            red_id = validated_data['id_redacteur_type']['id_nomenclature']
            validated_data['id_redacteur_type'] = Nomenclature.objects.get(id_nomenclature=red_id)

        plan = super().create(validated_data)

        # Ajouter les sites
        if sites_ids:
            from apps.users.models import Site
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )

        # Ajouter les référents
        if referents_ids:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)

        return plan

    def update(self, instance, validated_data):
        """Mettre à jour un plan avec ses relations."""
        sites_ids = validated_data.pop('sites_ids', None)
        referents_ids = validated_data.pop('referents_ids', None)

        # Résoudre les IDs des nomenclatures
        if 'id_evaluation' in validated_data:
            from apps.core.models import Nomenclature
            eval_id = validated_data['id_evaluation']['id_nomenclature']
            validated_data['id_evaluation'] = Nomenclature.objects.get(id_nomenclature=eval_id)

        if 'id_redacteur_type' in validated_data:
            from apps.core.models import Nomenclature
            red_id = validated_data['id_redacteur_type']['id_nomenclature']
            validated_data['id_redacteur_type'] = Nomenclature.objects.get(id_nomenclature=red_id)

        plan = super().update(instance, validated_data)

        # Mettre à jour les sites si fournis
        if sites_ids is not None:
            from apps.users.models import Site
            # Supprimer les anciennes associations
            CorSitePg.objects.filter(plan_de_gestion=plan).delete()
            # Créer les nouvelles associations
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )

        # Mettre à jour les référents si fournis
        if referents_ids is not None:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)

        return plan


class PlanGestionGeoJSONSerializer(serializers.ModelSerializer):
    """Serializer GeoJSON pour les Plans de Gestion."""
    
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    nb_sites = serializers.IntegerField(source='sites.count', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = PlanGestion
        geo_field = 'geometrie'
        fields = [
            'id_pg', 'nom', 'slug', 'periode_gestion', 'gestion_partagee',
            'statut', 'statut_display', 'nb_sites'
        ]


class PlanGestionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création simplifiée de Plans de Gestion."""

    sites_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=True, min_length=1)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'id_cdr', 'rang', 'annee_debut', 'annee_fin',
            'surface', 'gestion_partagee', 'ct88', 'risque_incendie',
            'date_validation_cspn', 'id_docgestion_fcen',
            'id_evaluation', 'id_redacteur_type', 'redacteur_nom',
            'redacteurs', 'relecteurs',
            'commentaire', 'statut', 'version', 'geometrie',
            'sites_ids', 'referents_ids'
        ]
        read_only_fields = ['id_pg', 'slug']
        extra_kwargs = {
            'nom': {'required': True},
            'rang': {'required': True},
            'annee_debut': {'required': True},
            'annee_fin': {'required': True},
        }
    
    def create(self, validated_data):
        """Créer un plan avec sites et référents."""
        sites_ids = validated_data.pop('sites_ids', [])
        referents_ids = validated_data.pop('referents_ids', [])
        
        # Créer le plan
        plan = super().create(validated_data)
        
        # Associer les sites
        if sites_ids:
            from apps.users.models import Site
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )
        
        # Associer les référents
        if referents_ids:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)
        
        return plan