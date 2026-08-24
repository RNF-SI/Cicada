"""
Serializers pour l'API REST des utilisateurs.
"""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from apps.plans.models import PlanGestion


def _validate_identifiant_unique(identifiant, exclude_pk=None):
    """
    Vérifie qu'un identifiant de connexion est renseigné et libre.

    L'identifiant est obligatoire pour tout compte (#656). L'unicité est
    insensible à la casse et couvre aussi les demandes d'inscription en
    attente, qui deviendront des comptes à leur validation.
    """
    from apps.notifications.models import PendingUser

    identifiant = (identifiant or '').strip()
    if not identifiant:
        raise serializers.ValidationError(_("L'identifiant est obligatoire."))

    existants = Role.objects.filter(identifiant__iexact=identifiant)
    if exclude_pk is not None:
        existants = existants.exclude(pk=exclude_pk)
    if existants.exists():
        raise serializers.ValidationError(_("Cet identifiant est déjà utilisé."))

    if PendingUser.objects.filter(identifiant__iexact=identifiant).exists():
        raise serializers.ValidationError(
            _("Une demande d'inscription avec cet identifiant est déjà en attente.")
        )

    return identifiant


class BibOrganismesSerializer(serializers.ModelSerializer):
    """
    Serializer pour les organismes (lecture seule dans le contexte users).
    """
    type_organisme_code = serializers.CharField(
        source='id_type_organisme.cd_nomenclature', read_only=True, default=None
    )
    type_organisme_label = serializers.CharField(
        source='id_type_organisme.label', read_only=True, default=None
    )

    class Meta:
        model = BibOrganismes
        fields = [
            'id_organisme', 'uuid_organisme', 'nom_organisme', 'ville_organisme',
            'email_organisme', 'tel_organisme', 'url_organisme',
            'id_type_organisme', 'type_organisme_code', 'type_organisme_label'
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
            'id_role', 'email', 'identifiant', 'nom_role', 'prenom_role', 'nom_complet',
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
            'last_login',
            # RGPD fields
            'deletion_requested_at', 'is_anonymized', 'anonymized_at'
        ]
        read_only_fields = [
            'id_role', 'date_insert', 'date_update', 'last_login',
            'deletion_requested_at', 'is_anonymized', 'anonymized_at'
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
    identifiant = serializers.CharField(
        max_length=100,
        required=True,
        allow_blank=False,
        help_text=_("Identifiant de connexion (obligatoire)")
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

    def validate_identifiant(self, value):
        """L'identifiant est obligatoire et unique (#656)."""
        return _validate_identifiant_unique(value)

    def validate(self, attrs):
        """Validation personnalisée."""
        # Vérifier que les mots de passe correspondent
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': _('Les mots de passe ne correspondent pas.')
            })

        # Validation métier : Admin organisme doit avoir un organisme
        if attrs.get('role_level') == 'admin_og' and not attrs.get('id_organisme'):
            raise serializers.ValidationError({
                'uuid_organisme': _("Un Administrateur d'organisme doit appartenir à un organisme.")
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
            'redacteur_principal': 'Rédacteurs Principaux',
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

    def validate_identifiant(self, value):
        """Un identifiant déjà posé ne peut pas être vidé ni dupliqué (#656)."""
        exclude_pk = self.instance.pk if self.instance else None
        return _validate_identifiant_unique(value, exclude_pk=exclude_pk)

    def validate(self, attrs):
        """Validation pour la modification."""
        instance = self.instance

        # Validation métier selon les nouvelles valeurs
        new_role_level = attrs.get('role_level', instance.role_level)
        new_organisme = attrs.get('id_organisme', instance.id_organisme)

        # Admin organisme doit avoir un organisme
        if new_role_level == 'admin_og' and not new_organisme:
            raise serializers.ValidationError({
                'uuid_organisme': _("Un Administrateur d'organisme doit appartenir à un organisme.")
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
                'redacteur_principal': 'Rédacteurs Principaux',
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
                'password_confirm': _('Les mots de passe ne correspondent pas.')
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
            raise serializers.ValidationError(_("Site non trouvé."))

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


class RgpdRequestSerializer(serializers.ModelSerializer):
    """
    Serializer pour les demandes RGPD en attente de traitement.
    """
    organisme_name = serializers.CharField(
        source='id_organisme.nom_organisme',
        read_only=True,
        default=None
    )
    full_name = serializers.SerializerMethodField()
    days_since_request = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id_role', 'email', 'full_name', 'organisme_name',
            'deletion_requested_at', 'active', 'is_anonymized',
            'days_since_request'
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        """Retourne le nom complet de l'utilisateur."""
        return obj.get_full_name()

    def get_days_since_request(self, obj):
        """Retourne le nombre de jours depuis la demande."""
        if obj.deletion_requested_at:
            from django.utils import timezone
            delta = timezone.now() - obj.deletion_requested_at
            return delta.days
        return None