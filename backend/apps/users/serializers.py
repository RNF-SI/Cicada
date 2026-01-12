"""
Serializers pour l'API REST des utilisateurs.
"""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from apps.plans.models import PlanGestion


class BibOrganismesSerializer(serializers.ModelSerializer):
    """
    Serializer pour les organismes (lecture seule dans le contexte users).
    """

    class Meta:
        model = BibOrganismes
        fields = [
            'id_organisme', 'uuid_organisme', 'nom_organisme', 'ville_organisme',
            'email_organisme', 'tel_organisme', 'url_organisme'
        ]
        read_only_fields = ['id_organisme', 'uuid_organisme']


class SiteBasicSerializer(serializers.ModelSerializer):
    """
    Serializer basique pour les sites (pour les relations).
    """
    
    class Meta:
        model = Site
        fields = ['id_site', 'nom_site', 'surf_off', 'active']
        read_only_fields = ['id_site']


class CorRoleSiteSerializer(serializers.ModelSerializer):
    """
    Serializer pour les relations utilisateur-site.
    """
    site = SiteBasicSerializer(source='id_site', read_only=True)
    site_id = serializers.IntegerField(source='id_site.id_site', write_only=True)
    
    class Meta:
        model = CorRoleSite
        fields = [
            'id_site', 'site_id', 'site', 'referent', 
            'referent_valid', 'conservateur'
        ]


class RoleBasicSerializer(serializers.ModelSerializer):
    """
    Serializer basique pour les utilisateurs (pour les relations).
    """
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Role
        fields = ['id_role', 'email', 'nom_complet', 'role_level']
        read_only_fields = ['id_role']


class PlanReferentSerializer(serializers.ModelSerializer):
    """
    Serializer pour les plans de gestion dont l'utilisateur est referent.
    """
    class Meta:
        model = PlanGestion
        fields = ['id_pg', 'nom', 'statut', 'annee_debut', 'annee_fin']
        read_only_fields = ['id_pg']


class RoleListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des utilisateurs (vue allégée).
    """
    organisme = BibOrganismesSerializer(source='id_organisme', read_only=True)
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)
    sites_lies = CorRoleSiteSerializer(
        source='corrolesite_set',
        many=True,
        read_only=True
    )
    plans_referent = PlanReferentSerializer(
        source='plans_referents',
        many=True,
        read_only=True
    )

    class Meta:
        model = Role
        fields = [
            'id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet',
            'role_level', 'organisme', 'active', 'is_staff', 'date_insert',
            'sites_lies', 'plans_referent', 'last_login'
        ]
        read_only_fields = ['id_role', 'date_insert', 'last_login']


class RoleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour un utilisateur.
    """
    organisme = BibOrganismesSerializer(source='id_organisme', read_only=True)
    uuid_organisme = serializers.SlugRelatedField(
        source='id_organisme',
        slug_field='uuid_organisme',
        queryset=BibOrganismes.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)
    sites_lies = CorRoleSiteSerializer(
        source='corrolesite_set',
        many=True,
        read_only=True
    )
    plans_referent = PlanReferentSerializer(
        source='plans_referents',
        many=True,
        read_only=True
    )

    # Permissions info
    permissions_info = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet',
            'role_level', 'organisme', 'uuid_organisme', 'desc_role',
            'identifiant', 'remarques', 'active', 'is_staff', 'is_superuser',
            'sites_lies', 'plans_referent', 'permissions_info', 'date_insert', 'date_update',
            'last_login'
        ]
        read_only_fields = [
            'id_role', 'date_insert', 'date_update', 'last_login'
        ]
    
    def get_permissions_info(self, obj):
        """Retourne les informations de permissions de l'utilisateur."""
        return {
            'is_super_admin': obj.is_super_admin(),
            'is_admin_organisme': obj.is_admin_organisme(),
            'is_referent': obj.is_referent(),
            'groups': [group.name for group in obj.groups.all()],
        }


class RoleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'utilisateurs.
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=Role.objects.all())]
    )
    uuid_organisme = serializers.SlugRelatedField(
        source='id_organisme',
        slug_field='uuid_organisme',
        queryset=BibOrganismes.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Role
        fields = [
            'email', 'nom_role', 'prenom_role', 'role_level',
            'uuid_organisme', 'desc_role', 'identifiant', 'remarques',
            'password', 'password_confirm', 'active', 'is_staff'
        ]

    def validate(self, attrs):
        """Validation personnalisée."""
        # Vérifier que les mots de passe correspondent
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas.'
            })

        # Validation métier : Super admin ne peut pas être dans un organisme
        if attrs.get('role_level') == 'super_admin' and attrs.get('id_organisme'):
            raise serializers.ValidationError({
                'uuid_organisme': 'Un Super Administrateur ne peut pas appartenir à un organisme.'
            })

        # Validation métier : Admin organisme doit avoir un organisme
        if attrs.get('role_level') == 'admin_og' and not attrs.get('id_organisme'):
            raise serializers.ValidationError({
                'uuid_organisme': 'Un Administrateur d\'organisme doit appartenir à un organisme.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Création d'un utilisateur avec mot de passe hashé."""
        # Retirer les champs non-modèle
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        
        # Créer l'utilisateur
        user = Role.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Attribution automatique du groupe selon le role_level
        from django.contrib.auth.models import Group
        role_group_mapping = {
            'super_admin': 'Super Administrateurs',
            'admin_og': 'Administrateurs Organisme',
            'referent': 'Référents',
            'utilisateur': 'Utilisateurs',
        }
        
        group_name = role_group_mapping.get(user.role_level)
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
            except Group.DoesNotExist:
                pass
        
        return user


class RoleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la modification d'utilisateurs.
    """
    uuid_organisme = serializers.SlugRelatedField(
        source='id_organisme',
        slug_field='uuid_organisme',
        queryset=BibOrganismes.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Role
        fields = [
            'nom_role', 'prenom_role', 'role_level', 'uuid_organisme',
            'desc_role', 'identifiant', 'remarques', 'active', 'is_staff'
        ]

    def validate(self, attrs):
        """Validation pour la modification."""
        instance = self.instance

        # Validation métier selon les nouvelles valeurs
        new_role_level = attrs.get('role_level', instance.role_level)
        new_organisme = attrs.get('id_organisme', instance.id_organisme)

        # Super admin ne peut pas être dans un organisme
        if new_role_level == 'super_admin' and new_organisme:
            raise serializers.ValidationError({
                'uuid_organisme': 'Un Super Administrateur ne peut pas appartenir à un organisme.'
            })

        # Admin organisme doit avoir un organisme
        if new_role_level == 'admin_og' and not new_organisme:
            raise serializers.ValidationError({
                'uuid_organisme': 'Un Administrateur d\'organisme doit appartenir à un organisme.'
            })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Mise à jour avec gestion des groupes."""
        # Sauvegarder l'ancien role_level
        old_role_level = instance.role_level
        
        # Mise à jour standard
        instance = super().update(instance, validated_data)
        
        # Mettre à jour les groupes si le role_level a changé
        new_role_level = validated_data.get('role_level')
        if new_role_level and new_role_level != old_role_level:
            from django.contrib.auth.models import Group
            
            role_group_mapping = {
                'super_admin': 'Super Administrateurs',
                'admin_og': 'Administrateurs Organisme', 
                'referent': 'Référents',
                'utilisateur': 'Utilisateurs',
            }
            
            # Retirer des anciens groupes
            instance.groups.clear()
            
            # Ajouter au nouveau groupe
            group_name = role_group_mapping.get(new_role_level)
            if group_name:
                try:
                    group = Group.objects.get(name=group_name)
                    instance.groups.add(group)
                except Group.DoesNotExist:
                    pass
        
        return instance


class RolePasswordChangeSerializer(serializers.Serializer):
    """
    Serializer pour changer le mot de passe d'un utilisateur.
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Vérifier que les mots de passe correspondent."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs
    
    def save(self, **kwargs):
        """Mettre à jour le mot de passe."""
        user = self.context['user']
        user.set_password(self.validated_data['password'])
        user.save()
        return user


class SiteAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer pour assigner/désassigner des sites à un utilisateur.
    """
    site_id = serializers.IntegerField(source='id_site.id_site')
    site_nom = serializers.CharField(source='id_site.nom_site', read_only=True)
    
    class Meta:
        model = CorRoleSite
        fields = [
            'site_id', 'site_nom', 'referent', 
            'referent_valid', 'conservateur'
        ]
    
    def validate_site_id(self, value):
        """Vérifier que le site existe."""
        try:
            Site.objects.get(id_site=value)
            return value
        except Site.DoesNotExist:
            raise serializers.ValidationError("Site non trouvé.")
    
    def create(self, validated_data):
        """Créer une assignation de site."""
        site_data = validated_data.pop('id_site')
        site = Site.objects.get(id_site=site_data['id_site'])
        
        # L'utilisateur est fourni par la vue
        user = self.context['user']
        
        # Créer ou mettre à jour la relation
        cor_role_site, created = CorRoleSite.objects.update_or_create(
            id_role=user,
            id_site=site,
            defaults=validated_data
        )
        
        return cor_role_site