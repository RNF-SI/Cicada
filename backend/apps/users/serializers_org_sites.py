"""
Serializers pour les API Organismes et Sites avec support GeoJSON.
"""
from rest_framework import serializers
try:
    from rest_framework_gis.serializers import GeoFeatureModelSerializer
    HAS_GIS_SUPPORT = True
except ImportError:
    # Fallback si rest_framework_gis n'est pas disponible
    GeoFeatureModelSerializer = serializers.ModelSerializer
    HAS_GIS_SUPPORT = False
    
from django.contrib.gis.geos import Point, MultiPolygon
from django.db import transaction

from .models import BibOrganismes, Site, CorRoleSite, CorOgSite, Role
from apps.core.models import Nomenclature


class OrganismeListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des organismes."""

    sites_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    parent_organisme = serializers.CharField(source='id_parent.nom_organisme', read_only=True)

    class Meta:
        model = BibOrganismes
        fields = [
            'id_organisme', 'uuid_organisme', 'nom_organisme',
            'adresse_organisme', 'cp_organisme', 'ville_organisme',
            'tel_organisme', 'email_organisme', 'url_organisme',
            'parent_organisme', 'id_parent',
            'sites_count', 'users_count'
        ]
    
    def get_sites_count(self, obj):
        """Nombre de sites gérés par l'organisme."""
        return CorOgSite.objects.filter(uuid_og=obj).count()
    
    def get_users_count(self, obj):
        """Nombre d'utilisateurs dans l'organisme."""
        return Role.objects.filter(id_organisme=obj, active=True).count()


class OrganismeDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un organisme."""
    
    parent_organisme = OrganismeListSerializer(source='id_parent', read_only=True)
    enfants_organismes = OrganismeListSerializer(source='children', many=True, read_only=True)
    sites_geres = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    statistiques = serializers.SerializerMethodField()
    
    class Meta:
        model = BibOrganismes
        fields = [
            'id_organisme', 'uuid_organisme', 'nom_organisme',
            'adresse_organisme', 'cp_organisme', 'ville_organisme',
            'tel_organisme', 'fax_organisme', 'email_organisme',
            'url_organisme', 'url_logo', 'parent_organisme',
            'enfants_organismes', 'sites_geres', 'users',
            'statistiques'
        ]
    
    def get_sites_geres(self, obj):
        """Sites gérés par l'organisme."""
        cor_sites = CorOgSite.objects.filter(uuid_og=obj).select_related('id_site')
        return [{
            'site': {
                'id_site': cor.id_site.id_site,
                'nom_site': cor.id_site.nom_site,
                'surf_off': cor.id_site.surf_off,
                'active': cor.id_site.active
            }
        } for cor in cor_sites]
    
    def get_users(self, obj):
        """Utilisateurs de l'organisme."""
        users = Role.objects.filter(id_organisme=obj, active=True)
        return [{
            'id_role': user.id_role,
            'nom_complet': f"{user.prenom_role} {user.nom_role}".strip(),
            'email': user.email,
            'role_level': user.role_level
        } for user in users]
    
    def get_statistiques(self, obj):
        """Statistiques de l'organisme."""
        total_users = Role.objects.filter(id_organisme=obj).count()
        active_users = Role.objects.filter(id_organisme=obj, active=True).count()
        total_sites = CorOgSite.objects.filter(uuid_og=obj).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_sites': total_sites
        }


class OrganismeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier un organisme."""
    
    parent_id = serializers.IntegerField(source='id_parent.id_organisme', required=False, allow_null=True)
    
    class Meta:
        model = BibOrganismes
        fields = [
            'nom_organisme', 'adresse_organisme', 'cp_organisme',
            'ville_organisme', 'tel_organisme', 'fax_organisme',
            'email_organisme', 'url_organisme', 'url_logo',
            'parent_id'
        ]
    
    def validate_parent_id(self, value):
        """Valide l'organisme parent."""
        if value is not None:
            try:
                BibOrganismes.objects.get(id_organisme=value)
            except BibOrganismes.DoesNotExist:
                raise serializers.ValidationError("Organisme parent introuvable.")
        return value
    
    def validate_nom_organisme(self, value):
        """Valide le nom de l'organisme."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom doit contenir au moins 3 caractères.")
        return value.strip()
    
    def create(self, validated_data):
        """Crée un nouvel organisme."""
        parent_data = validated_data.pop('id_parent', None)

        organisme = BibOrganismes.objects.create(**validated_data)

        if parent_data:
            # parent_data can be a BibOrganismes instance or a dict
            if isinstance(parent_data, BibOrganismes):
                organisme.id_parent = parent_data
            elif isinstance(parent_data, dict) and parent_data.get('id_organisme'):
                parent = BibOrganismes.objects.get(id_organisme=parent_data['id_organisme'])
                organisme.id_parent = parent
            organisme.save()

        return organisme

    def update(self, instance, validated_data):
        """Met à jour un organisme."""
        parent_data = validated_data.pop('id_parent', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if parent_data is not None:
            # parent_data can be a BibOrganismes instance or a dict
            if isinstance(parent_data, BibOrganismes):
                instance.id_parent = parent_data
            elif isinstance(parent_data, dict) and parent_data.get('id_organisme'):
                parent = BibOrganismes.objects.get(id_organisme=parent_data['id_organisme'])
                instance.id_parent = parent
            else:
                instance.id_parent = None

        instance.save()
        return instance


class SiteListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des sites."""
    
    type_site = serializers.CharField(source='id_type_site.label', read_only=True)
    organismes_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    
    # Point de référence en GeoJSON simple
    geom_pt_geojson = serializers.SerializerMethodField()
    
    class Meta:
        model = Site
        fields = [
            'id_site', 'id_local', 'id_inpn', 'nom_site',
            'surf_off', 'type_site', 'date_crea', 'marin',
            'outre_mer', 'active', 'geom_pt_geojson',
            'organismes_count', 'users_count'
        ]
    
    def get_geom_pt_geojson(self, obj):
        """Point de référence en GeoJSON."""
        if obj.geom_pt:
            return {
                'type': 'Point',
                'coordinates': [obj.geom_pt.x, obj.geom_pt.y]
            }
        return None
    
    def get_organismes_count(self, obj):
        """Nombre d'organismes gestionnaires."""
        return CorOgSite.objects.filter(id_site=obj).count()
    
    def get_users_count(self, obj):
        """Nombre d'utilisateurs assignés."""
        return CorRoleSite.objects.filter(id_site=obj).count()


class SiteGeoJSONSerializer(GeoFeatureModelSerializer):
    """Serializer GeoJSON complet pour un site avec géométries."""

    type_site = serializers.SerializerMethodField()
    organismes_gestionnaires = serializers.SerializerMethodField()
    users_assignes = serializers.SerializerMethodField()

    def get_type_site(self, obj):
        """Type de site with None handling."""
        return obj.id_type_site.label if obj.id_type_site else None
    
    class Meta:
        model = Site
        geo_field = 'geom'  # Champ géométrie principal
        fields = [
            'id_site', 'id_local', 'id_inpn', 'nom_site',
            'surf_off', 'type_site', 'date_crea', 'marin',
            'outre_mer', 'active', 'organismes_gestionnaires',
            'users_assignes', 'modif_adm', 'modif_geo'
        ]
    
    def get_organismes_gestionnaires(self, obj):
        """Organismes gestionnaires du site."""
        cor_orgs = CorOgSite.objects.filter(id_site=obj).select_related('uuid_og')
        return [{
            'organisme': {
                'id_organisme': cor.uuid_og.id_organisme,
                'nom_organisme': cor.uuid_og.nom_organisme
            }
        } for cor in cor_orgs]
    
    def get_users_assignes(self, obj):
        """Utilisateurs assignés au site."""
        cor_users = CorRoleSite.objects.filter(id_site=obj).select_related('id_role')
        return [{
            'user': {
                'id_role': cor.id_role.id_role,
                'nom_complet': f"{cor.id_role.prenom_role} {cor.id_role.nom_role}".strip(),
                'email': cor.id_role.email
            },
            'referent': cor.referent,
            'referent_valid': cor.referent_valid,
            'conservateur': cor.conservateur
        } for cor in cor_users]


class SiteDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un site sans GeoJSON complet."""
    
    type_site = serializers.SerializerMethodField()
    organismes_gestionnaires = serializers.SerializerMethodField()
    users_assignes = serializers.SerializerMethodField()
    
    # Géométries en format texte pour l'API standard
    geom_wkt = serializers.SerializerMethodField()
    geom_pt_wkt = serializers.SerializerMethodField()
    
    class Meta:
        model = Site
        fields = [
            'id_site', 'id_local', 'id_inpn', 'nom_site',
            'jonction_nom', 'surf_off', 'type_site', 'date_crea',
            'marin', 'outre_mer', 'active', 'modif_adm', 'modif_geo',
            'geom_wkt', 'geom_pt_wkt', 'organismes_gestionnaires',
            'users_assignes'
        ]
    
    def get_type_site(self, obj):
        """Type de site avec détails."""
        if obj.id_type_site:
            return {
                'id_nomenclature': obj.id_type_site.id_nomenclature,
                'label': obj.id_type_site.label,
                'cd_nomenclature': obj.id_type_site.cd_nomenclature
            }
        return None
    
    def get_geom_wkt(self, obj):
        """Géométrie principale en WKT."""
        return obj.geom.wkt if obj.geom else None
    
    def get_geom_pt_wkt(self, obj):
        """Point de référence en WKT."""
        return obj.geom_pt.wkt if obj.geom_pt else None
    
    def get_organismes_gestionnaires(self, obj):
        """Organismes gestionnaires du site."""
        cor_orgs = CorOgSite.objects.filter(id_site=obj).select_related('uuid_og')
        return [{
            'organisme': {
                'id_organisme': cor.uuid_og.id_organisme,
                'nom_organisme': cor.uuid_og.nom_organisme,
                'ville_organisme': cor.uuid_og.ville_organisme,
                'email_organisme': cor.uuid_og.email_organisme
            }
        } for cor in cor_orgs]
    
    def get_users_assignes(self, obj):
        """Utilisateurs assignés au site avec détails."""
        cor_users = CorRoleSite.objects.filter(id_site=obj).select_related('id_role')
        return [{
            'user': {
                'id_role': cor.id_role.id_role,
                'nom_complet': f"{cor.id_role.prenom_role} {cor.id_role.nom_role}".strip(),
                'email': cor.id_role.email,
                'role_level': cor.id_role.role_level,
                'organisme': cor.id_role.id_organisme.nom_organisme if cor.id_role.id_organisme else None
            },
            'referent': cor.referent,
            'referent_valid': cor.referent_valid,
            'conservateur': cor.conservateur
        } for cor in cor_users]


class SiteCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier un site avec support GeoJSON."""
    
    type_site_id = serializers.IntegerField(source='id_type_site.id_nomenclature', required=False, allow_null=True)
    
    # Support des géométries en GeoJSON ou WKT
    geom_geojson = serializers.JSONField(write_only=True, required=False, allow_null=True)
    geom_pt_geojson = serializers.JSONField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Site
        fields = [
            'id_local', 'id_inpn', 'nom_site', 'jonction_nom',
            'surf_off', 'type_site_id', 'date_crea', 'marin',
            'outre_mer', 'active', 'geom_geojson', 'geom_pt_geojson'
        ]
    
    def validate_type_site_id(self, value):
        """Valide le type de site."""
        if value is not None:
            try:
                Nomenclature.objects.get(id_nomenclature=value)
            except Nomenclature.DoesNotExist:
                raise serializers.ValidationError("Type de site introuvable.")
        return value
    
    def validate_nom_site(self, value):
        """Valide le nom du site."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom doit contenir au moins 3 caractères.")
        return value.strip()
    
    def validate_surf_off(self, value):
        """Valide la surface officielle."""
        if value is not None and value < 0:
            raise serializers.ValidationError("La surface ne peut pas être négative.")
        return value
    
    def validate_geom_geojson(self, value):
        """Valide la géométrie GeoJSON."""
        if value is not None:
            try:
                from django.contrib.gis.geos import GEOSGeometry
                geom = GEOSGeometry(str(value))
                if not isinstance(geom, MultiPolygon):
                    # Convertir en MultiPolygon si nécessaire
                    if hasattr(geom, 'geom_type') and geom.geom_type == 'Polygon':
                        geom = MultiPolygon(geom)
                    else:
                        raise serializers.ValidationError("La géométrie doit être un Polygon ou MultiPolygon.")
                return geom
            except Exception as e:
                raise serializers.ValidationError(f"GeoJSON invalide: {str(e)}")
        return value
    
    def validate_geom_pt_geojson(self, value):
        """Valide le point de référence GeoJSON."""
        if value is not None:
            try:
                from django.contrib.gis.geos import GEOSGeometry
                geom = GEOSGeometry(str(value))
                if not isinstance(geom, Point):
                    raise serializers.ValidationError("Le point de référence doit être un Point.")
                return geom
            except Exception as e:
                raise serializers.ValidationError(f"Point GeoJSON invalide: {str(e)}")
        return value
    
    def create(self, validated_data):
        """Crée un nouveau site."""
        type_site_data = validated_data.pop('id_type_site', None)
        geom_geojson = validated_data.pop('geom_geojson', None)
        geom_pt_geojson = validated_data.pop('geom_pt_geojson', None)
        
        with transaction.atomic():
            site = Site.objects.create(**validated_data)
            
            # Assigner le type de site
            if type_site_data and type_site_data.get('id_nomenclature'):
                type_site = Nomenclature.objects.get(id_nomenclature=type_site_data['id_nomenclature'])
                site.id_type_site = type_site
            
            # Assigner les géométries
            if geom_geojson:
                site.geom = geom_geojson
            if geom_pt_geojson:
                site.geom_pt = geom_pt_geojson
            
            site.save()
        
        return site
    
    def update(self, instance, validated_data):
        """Met à jour un site."""
        type_site_data = validated_data.pop('id_type_site', None)
        geom_geojson = validated_data.pop('geom_geojson', None)
        geom_pt_geojson = validated_data.pop('geom_pt_geojson', None)
        
        with transaction.atomic():
            # Mettre à jour les champs standard
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            # Mettre à jour le type de site
            if type_site_data is not None:
                if type_site_data.get('id_nomenclature'):
                    type_site = Nomenclature.objects.get(id_nomenclature=type_site_data['id_nomenclature'])
                    instance.id_type_site = type_site
                else:
                    instance.id_type_site = None
            
            # Mettre à jour les géométries
            if geom_geojson is not None:
                instance.geom = geom_geojson
            if geom_pt_geojson is not None:
                instance.geom_pt = geom_pt_geojson
            
            instance.save()
        
        return instance


# Serializers pour les relations

class OrganismeSiteAssignmentSerializer(serializers.Serializer):
    """Serializer pour assigner un site à un organisme."""
    
    site_id = serializers.IntegerField()
    
    def validate_site_id(self, value):
        """Valide l'existence du site."""
        try:
            Site.objects.get(id_site=value)
        except Site.DoesNotExist:
            raise serializers.ValidationError("Site introuvable.")
        return value


class BulkSiteAssignmentSerializer(serializers.Serializer):
    """Serializer pour assignation en masse de sites."""
    
    site_ids = serializers.ListField(child=serializers.IntegerField())
    
    def validate_site_ids(self, value):
        """Valide l'existence de tous les sites."""
        if not value:
            raise serializers.ValidationError("Au moins un site doit être spécifié.")
        
        existing_sites = Site.objects.filter(id_site__in=value).values_list('id_site', flat=True)
        missing_sites = set(value) - set(existing_sites)
        
        if missing_sites:
            raise serializers.ValidationError(f"Sites introuvables: {list(missing_sites)}")
        
        return value