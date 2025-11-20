"""
Serializers pour l'API REST Plans de Gestion.
"""
from rest_framework import serializers
from django.contrib.gis.serializers.geojson import Serializer as GeoJSONSerializer
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

from .models import PlanGestion, CorSitePg, CorPgFichier
from apps.users.serializers import RoleBasicSerializer, SiteBasicSerializer


class CorSitePgSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Site-Plan de Gestion."""
    
    site = SiteBasicSerializer(read_only=True)
    site_id = serializers.IntegerField(write_only=True, source='site.id_site')
    
    class Meta:
        model = CorSitePg
        fields = [
            'id_cor_site_pg', 'site', 'site_id', 'rang', 'commentaire',
            'date_ajout', 'date_maj'
        ]
        read_only_fields = ['id_cor_site_pg', 'date_ajout', 'date_maj']


class CorPgFichierSerializer(serializers.ModelSerializer):
    """Serializer pour les fichiers de Plans de Gestion."""
    
    fichier = serializers.FileField(write_only=True, required=False)
    file_size_human = serializers.CharField(source='get_file_size_human', read_only=True)
    is_image = serializers.BooleanField(source='is_image', read_only=True)
    is_document = serializers.BooleanField(source='is_document', read_only=True)
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = CorPgFichier
        fields = [
            'id_fichier', 'nom_fichier', 'chemin_fichier', 'fichier', 'url',
            'type_fichier', 'titre', 'description', 'auteur', 'public',
            'ordre_affichage', 'taille_fichier', 'file_size_human', 'extension',
            'is_image', 'is_document', 'date_upload', 'date_maj'
        ]
        read_only_fields = [
            'id_fichier', 'chemin_fichier', 'taille_fichier', 'extension',
            'date_upload', 'date_maj'
        ]
    
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


class PlanGestionListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des Plans de Gestion."""
    
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    nb_sites = serializers.IntegerField(source='sites.count', read_only=True)
    nb_fichiers = serializers.IntegerField(source='fichiers.count', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    evaluation_display = serializers.CharField(source='id_evaluation.label_fr', read_only=True)
    redacteur_type_display = serializers.CharField(source='id_redacteur_type.label_fr', read_only=True)
    
    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'id_cdr', 'annee_debut', 'annee_fin', 'periode_gestion',
            'gestion_partagee', 'statut', 'statut_display', 'version',
            'evaluation_display', 'redacteur_type_display', 'redacteur_nom',
            'nb_sites', 'nb_fichiers', 'date_ajout', 'date_maj'
        ]


class PlanGestionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les Plans de Gestion."""
    
    # Relations
    sites = CorSitePgSerializer(many=True, read_only=True)
    fichiers = CorPgFichierSerializer(many=True, read_only=True)
    referents = RoleBasicSerializer(many=True, read_only=True)
    
    # Champs calculés
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    is_multi_sites = serializers.BooleanField(source='is_multi_sites', read_only=True)
    organismes_gestionnaires = serializers.ListField(source='get_organismes_gestionnaires', read_only=True)
    sites_list = serializers.ListField(source='get_sites', read_only=True)
    
    # Champs display
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    evaluation_display = serializers.CharField(source='id_evaluation.label_fr', read_only=True)
    redacteur_type_display = serializers.CharField(source='id_redacteur_type.label_fr', read_only=True)
    
    # Utilisateurs
    utilisateur_ajout = RoleBasicSerializer(source='id_utilisateur_ajout', read_only=True)
    utilisateur_maj = RoleBasicSerializer(source='id_utilisateur_maj', read_only=True)
    
    # IDs pour création/modification
    evaluation_id = serializers.IntegerField(source='id_evaluation.id_nomenclature', write_only=True)
    redacteur_type_id = serializers.IntegerField(source='id_redacteur_type.id_nomenclature', write_only=True)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'uuid', 'id_cdr',
            'annee_debut', 'annee_fin', 'periode_gestion',
            'gestion_partagee', 'autres_ep', 'ct88', 'risque_incendie',
            'evaluation_id', 'evaluation_display', 'redacteur_type_id', 'redacteur_type_display',
            'redacteur_nom', 'commentaire', 'statut', 'statut_display', 'version',
            'geometrie', 'is_multi_sites', 'organismes_gestionnaires', 'sites_list',
            'sites', 'fichiers', 'referents', 'referents_ids',
            'utilisateur_ajout', 'utilisateur_maj',
            'date_ajout', 'date_maj'
        ]
        read_only_fields = [
            'id_pg', 'uuid', 'date_ajout', 'date_maj'
        ]
    
    def create(self, validated_data):
        """Créer un plan avec ses relations."""
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
        
        # Ajouter les référents
        if referents_ids:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)
        
        return plan
    
    def update(self, instance, validated_data):
        """Mettre à jour un plan avec ses relations."""
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
            'id_pg', 'nom', 'periode_gestion', 'gestion_partagee',
            'statut', 'statut_display', 'nb_sites'
        ]


class PlanGestionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création simplifiée de Plans de Gestion."""
    
    sites_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = PlanGestion
        fields = [
            'nom', 'id_cdr', 'annee_debut', 'annee_fin',
            'gestion_partagee', 'autres_ep', 'ct88', 'risque_incendie',
            'id_evaluation', 'id_redacteur_type', 'redacteur_nom',
            'commentaire', 'statut', 'version', 'geometrie',
            'sites_ids', 'referents_ids'
        ]
    
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