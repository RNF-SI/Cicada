"""
Serializers pour les notifications et validations.
"""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.users.serializers import RoleBasicSerializer, SiteBasicSerializer

from .models import Notification, ValidationRequest, PendingUser


class OrganismeBasicSerializer(serializers.Serializer):
    """Serializer basique pour les organismes (inline)."""
    id = serializers.IntegerField(source='id_organisme')
    nom_organisme = serializers.CharField()


class PlanGestionBasicSerializer(serializers.Serializer):
    """Serializer basique pour les plans de gestion (inline)."""
    id = serializers.IntegerField(source='id_pg')
    nom = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications."""

    related_user = RoleBasicSerializer(read_only=True)
    related_site = SiteBasicSerializer(read_only=True)
    related_plan = PlanGestionBasicSerializer(read_only=True)
    related_organisme = OrganismeBasicSerializer(read_only=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'priority',
            'priority_display',
            'related_user',
            'related_site',
            'related_plan',
            'related_organisme',
            'related_validation',
            'action_url',
            'read',
            'read_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'priority',
            'related_user',
            'related_site',
            'related_plan',
            'related_organisme',
            'related_validation',
            'action_url',
            'created_at',
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer simplifie pour les listes de notifications."""

    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'priority',
            'action_url',
            'read',
            'created_at',
        ]


class ValidationRequestSerializer(serializers.ModelSerializer):
    """Serializer complet pour les demandes de validation."""

    requester = RoleBasicSerializer(read_only=True)
    target_site = SiteBasicSerializer(read_only=True)
    target_plan = PlanGestionBasicSerializer(read_only=True)
    target_user = RoleBasicSerializer(read_only=True)
    requested_organisme = OrganismeBasicSerializer(read_only=True)
    validator = RoleBasicSerializer(read_only=True)
    request_type_display = serializers.CharField(
        source='get_request_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    pending_user_info = serializers.SerializerMethodField()
    can_validate = serializers.SerializerMethodField()
    blocked_by_org_link = serializers.SerializerMethodField()

    class Meta:
        model = ValidationRequest
        fields = [
            'id',
            'request_type',
            'request_type_display',
            'status',
            'status_display',
            'requester',
            'target_site',
            'target_plan',
            'target_user',
            'requested_organisme',
            'requested_role_level',
            'justification',
            'validator',
            'validation_comment',
            'validated_at',
            'pending_user_info',
            'can_validate',
            'blocked_by_org_link',
            'request_as_referent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_pending_user_info(self, obj):
        """Retourne les infos du PendingUser pour les inscriptions."""
        if obj.request_type == 'user_registration':
            # Pour les inscriptions en attente ou rejetees, PendingUser existe
            if hasattr(obj, 'pending_user'):
                pending = obj.pending_user
                return {
                    'email': pending.email,
                    'nom_role': pending.nom_role,
                    'prenom_role': pending.prenom_role,
                    'nom_complet': pending.get_full_name(),
                    'justification': pending.justification,
                    'created_at': pending.created_at.isoformat() if pending.created_at else None,
                }
            # Pour les inscriptions approuvees, PendingUser est supprime
            # mais on peut recuperer les infos via requester (le Role cree)
            elif obj.requester:
                return {
                    'email': obj.requester.email,
                    'nom_role': obj.requester.nom_role,
                    'prenom_role': obj.requester.prenom_role,
                    'nom_complet': str(obj.requester),
                    'justification': obj.justification,
                    'created_at': obj.created_at.isoformat() if obj.created_at else None,
                }
        return None

    def get_can_validate(self, obj):
        """Indique si l'utilisateur courant peut valider cette demande."""
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.can_be_validated_by(request.user)
        return False

    def get_blocked_by_org_link(self, obj):
        """Indique si cette demande site_access est bloquee par un site_org_link en attente."""
        if obj.request_type != 'site_access' or obj.status != 'pending':
            return False
        return ValidationRequest.objects.filter(
            requester=obj.requester,
            target_site=obj.target_site,
            request_type='site_org_link',
            status='pending'
        ).exists()


class ValidationRequestListSerializer(serializers.ModelSerializer):
    """Serializer simplifie pour les listes."""

    requester_id = serializers.IntegerField(source='requester.id_role', read_only=True, allow_null=True)
    requester_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    target_site_id = serializers.IntegerField(source='target_site.id_site', read_only=True, allow_null=True)
    target_plan_id = serializers.IntegerField(source='target_plan.id_pg', read_only=True, allow_null=True)
    validator_name = serializers.SerializerMethodField()
    validator_comment = serializers.CharField(source='validation_comment', read_only=True)
    request_type_display = serializers.CharField(
        source='get_request_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    blocked_by_org_link = serializers.SerializerMethodField()

    class Meta:
        model = ValidationRequest
        fields = [
            'id',
            'request_type',
            'request_type_display',
            'status',
            'status_display',
            'requester_id',
            'requester_name',
            'target_name',
            'target_site_id',
            'target_plan_id',
            'justification',
            'validator_name',
            'validator_comment',
            'validated_at',
            'created_at',
            'request_as_referent',
            'blocked_by_org_link',
        ]

    def get_requester_name(self, obj):
        """Nom du demandeur."""
        # Pour les demandes avec un requester (y compris inscriptions approuvees)
        if obj.requester:
            return str(obj.requester)
        # Pour les inscriptions en attente ou rejetees, le PendingUser est conserve
        if obj.request_type == 'user_registration' and hasattr(obj, 'pending_user'):
            return obj.pending_user.get_full_name()
        return "Inconnu"

    def get_target_name(self, obj):
        """Nom de la cible (site, plan, utilisateur, module)."""
        if obj.target_site:
            return f"Site: {obj.target_site.nom_site}"
        if obj.target_plan:
            return f"Plan: {obj.target_plan.nom}"
        if obj.target_user:
            return f"Utilisateur: {obj.target_user}"
        if obj.target_module:
            # Recuperer le nom du module depuis la base de donnees
            from apps.core.models import Module
            try:
                module = Module.objects.get(code=obj.target_module)
                return module.name
            except Module.DoesNotExist:
                return obj.target_module
        if obj.requested_organisme:
            return f"Organisme: {obj.requested_organisme.nom_organisme}"
        return None

    def get_validator_name(self, obj):
        """Nom du validateur (si traite)."""
        if obj.validator:
            return str(obj.validator)
        return None

    def get_blocked_by_org_link(self, obj):
        """Indique si cette demande site_access est bloquee par un site_org_link en attente."""
        if obj.request_type != 'site_access' or obj.status != 'pending':
            return False
        return ValidationRequest.objects.filter(
            requester=obj.requester,
            target_site=obj.target_site,
            request_type='site_org_link',
            status='pending'
        ).exists()


class ValidationApproveSerializer(serializers.Serializer):
    """Serializer pour l'approbation d'une demande."""

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text=_("Commentaire optionnel")
    )
    approve_as_referent = serializers.BooleanField(
        required=False,
        default=None,
        allow_null=True,
        help_text=_("Si defini, surcharge le choix du demandeur pour le statut referent")
    )


class ValidationRejectSerializer(serializers.Serializer):
    """Serializer pour le rejet d'une demande."""

    comment = serializers.CharField(
        required=True,
        max_length=1000,
        help_text=_("Motif du rejet (obligatoire)")
    )


class PublicRegistrationSerializer(serializers.Serializer):
    """Serializer pour l'inscription publique."""

    email = serializers.EmailField(
        help_text=_("Adresse email (sera utilisée pour la connexion)")
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text=_("Mot de passe (minimum 8 caractères)")
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text=_("Confirmation du mot de passe")
    )
    nom_role = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text=_("Nom de famille")
    )
    prenom_role = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text=_("Prénom")
    )
    requested_organisme_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_("ID de l'organisme demandé")
    )
    justification = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text=_("Motif de la demande d'inscription")
    )

    def validate_email(self, value):
        """Verifie que l'email n'est pas deja utilise."""
        from apps.users.models import Role

        email_lower = value.lower()

        # Verifier dans Role
        if Role.objects.filter(email__iexact=email_lower).exists():
            raise serializers.ValidationError(
                _("Cette adresse email est déjà utilisée.")
            )

        # Verifier dans PendingUser
        if PendingUser.objects.filter(email__iexact=email_lower).exists():
            raise serializers.ValidationError(
                _("Une demande d'inscription avec cette adresse est déjà en attente.")
            )

        return email_lower

    def validate(self, data):
        """Validation globale."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _("Les mots de passe ne correspondent pas.")
            })

        # Verifier que l'organisme existe si fourni
        if data.get('requested_organisme_id'):
            from apps.users.models import BibOrganismes
            try:
                BibOrganismes.objects.get(id_organisme=data['requested_organisme_id'])
            except BibOrganismes.DoesNotExist:
                raise serializers.ValidationError({
                    'requested_organisme_id': _("Organisme non trouvé.")
                })

        return data

    def create(self, validated_data):
        """Cree PendingUser et ValidationRequest."""
        from django.contrib.auth.hashers import make_password
        from apps.users.models import BibOrganismes

        # Recuperer l'organisme si fourni
        organisme = None
        if validated_data.get('requested_organisme_id'):
            organisme = BibOrganismes.objects.get(
                id_organisme=validated_data['requested_organisme_id']
            )

        # Creer la ValidationRequest
        validation_request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requester=None,  # Pas encore de compte
            requested_organisme=organisme,
            justification=validated_data.get('justification', ''),
        )

        # Creer le PendingUser
        pending_user = PendingUser.objects.create(
            email=validated_data['email'],
            password_hash=make_password(validated_data['password']),
            nom_role=validated_data.get('nom_role', ''),
            prenom_role=validated_data.get('prenom_role', ''),
            requested_organisme=organisme,
            justification=validated_data.get('justification', ''),
            validation_request=validation_request,
            ip_address=self.context.get('ip_address'),
            user_agent=self.context.get('user_agent'),
        )

        # Notifier les validateurs
        from .services import NotificationService
        NotificationService.notify_validators(validation_request)

        # Envoyer un email de confirmation au demandeur
        try:
            from .tasks import send_registration_pending_email
            full_name = f"{pending_user.prenom_role} {pending_user.nom_role}".strip() or pending_user.email
            send_registration_pending_email.delay(pending_user.email, nom_complet=full_name)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not send registration pending email: {e}")

        return pending_user


class SiteAccessRequestSerializer(serializers.Serializer):
    """Serializer pour demander l'acces a un site."""

    justification = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text=_("Motif de la demande")
    )


class PlanAccessRequestSerializer(serializers.Serializer):
    """Serializer pour demander l'acces a un plan."""

    justification = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text=_("Motif de la demande")
    )


class AdminDeactivationRequestSerializer(serializers.Serializer):
    """Serializer pour demander la desactivation d'un admin_og."""

    justification = serializers.CharField(
        required=True,
        max_length=2000,
        help_text=_("Motif de la demande (obligatoire)")
    )


class AdminPromotionRequestSerializer(serializers.Serializer):
    """Serializer pour demander la promotion d'un utilisateur en admin_og."""

    justification = serializers.CharField(
        required=True,
        max_length=2000,
        help_text=_("Motif de la demande (obligatoire)")
    )


class AdminDemotionRequestSerializer(serializers.Serializer):
    """Serializer pour demander la retrogradation d'un admin_og en utilisateur."""

    justification = serializers.CharField(
        required=True,
        max_length=2000,
        help_text=_("Motif de la demande (obligatoire)")
    )


class ModuleAccessRequestSerializer(serializers.Serializer):
    """Serializer pour demander l'acces a un module."""

    module_code = serializers.CharField(
        required=True,
        max_length=50,
        help_text=_("Code du module (ex: zonages)")
    )
    justification = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text=_("Motif de la demande")
    )

    def validate_module_code(self, value):
        """Verifie que le code module existe et necessite un acces."""
        from apps.core.models import Module

        try:
            module = Module.objects.get(code=value, is_active=True)
        except Module.DoesNotExist:
            # Liste des modules valides pour le message d'erreur
            valid_codes = list(Module.objects.filter(
                is_active=True, requires_access=True
            ).values_list('code', flat=True))
            raise serializers.ValidationError(
                _("Code module invalide. Modules disponibles: %(modules)s") % {
                    'modules': ', '.join(valid_codes) if valid_codes else 'aucun'
                }
            )

        if not module.requires_access:
            raise serializers.ValidationError(
                _("Ce module ne necessite pas de demande d'acces.")
            )

        return value


class GrantModuleAccessSerializer(serializers.Serializer):
    """Serializer pour octroyer l'acces a un module (admin)."""

    user_id = serializers.IntegerField(
        required=True,
        help_text=_("ID de l'utilisateur")
    )
    module_code = serializers.CharField(
        required=True,
        max_length=50,
        help_text=_("Code du module")
    )

    def validate_module_code(self, value):
        """Verifie que le code module existe et necessite un acces."""
        from apps.core.models import Module

        try:
            module = Module.objects.get(code=value, is_active=True)
        except Module.DoesNotExist:
            raise serializers.ValidationError(_("Code module invalide."))

        if not module.requires_access:
            raise serializers.ValidationError(
                _("Ce module ne necessite pas de gestion d'acces.")
            )

        return value

    def validate_user_id(self, value):
        """Verifie que l'utilisateur existe."""
        from apps.users.models import Role
        try:
            Role.objects.get(id_role=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError(_("Utilisateur non trouve."))
        return value
