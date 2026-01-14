"""
Views pour les notifications et validations.
"""
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from apps.users.permissions import IsSuperAdmin, IsAdminOrganisme, IsReferent

from .models import Notification, ValidationRequest, PendingUser
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    ValidationRequestSerializer,
    ValidationRequestListSerializer,
    ValidationApproveSerializer,
    ValidationRejectSerializer,
    PublicRegistrationSerializer,
    SiteAccessRequestSerializer,
    PlanAccessRequestSerializer,
    AdminDeactivationRequestSerializer,
    ModuleAccessRequestSerializer,
    GrantModuleAccessSerializer,
)
from .services import NotificationService, ValidationService


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des notifications.

    Endpoints:
    - GET /api/notifications/ - Liste des notifications de l'utilisateur
    - GET /api/notifications/{id}/ - Detail d'une notification
    - DELETE /api/notifications/{id}/ - Supprimer une notification
    - GET /api/notifications/unread/ - Notifications non lues
    - GET /api/notifications/count/ - Compteur non lues
    - POST /api/notifications/{id}/mark_read/ - Marquer comme lue
    - POST /api/notifications/mark_all_read/ - Tout marquer comme lu
    - GET /api/notifications/poll/ - Endpoint de polling
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'delete', 'post']

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    def get_queryset(self):
        """Retourne uniquement les notifications de l'utilisateur connecte."""
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related(
            'related_user',
            'related_site',
            'related_plan',
            'related_organisme',
            'related_validation'
        )

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Liste des notifications non lues."""
        queryset = self.get_queryset().filter(read=False)
        serializer = NotificationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Compteur de notifications non lues."""
        count = self.get_queryset().filter(read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marque une notification comme lue."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marque toutes les notifications comme lues."""
        self.get_queryset().filter(read=False).update(
            read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def poll(self, request):
        """
        Endpoint de polling pour les mises a jour.
        Utiliser ?since=<timestamp> pour n'obtenir que les nouvelles.
        """
        since_param = request.query_params.get('since')
        queryset = self.get_queryset()

        if since_param:
            try:
                since = timezone.datetime.fromisoformat(since_param)
                queryset = queryset.filter(created_at__gt=since)
            except ValueError:
                pass

        unread_count = self.get_queryset().filter(read=False).count()

        # Compteur de validations en attente
        pending_validations = 0
        if request.user.is_referent():
            pending_validations = ValidationService.get_pending_requests_for_user(
                request.user
            ).count()

        notifications = NotificationListSerializer(
            queryset[:10],
            many=True
        ).data

        return Response({
            'notifications': notifications,
            'unread_count': unread_count,
            'pending_validations': pending_validations,
            'has_updates': queryset.exists(),
            'timestamp': timezone.now().isoformat(),
        })


class ValidationRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des demandes de validation.

    Endpoints:
    - GET /api/validations/ - Liste des demandes
    - GET /api/validations/{id}/ - Detail d'une demande
    - GET /api/validations/pending_count/ - Compteur en attente
    - GET /api/validations/my_requests/ - Mes demandes
    - POST /api/validations/{id}/approve/ - Approuver
    - POST /api/validations/{id}/reject/ - Rejeter
    - POST /api/validations/{id}/cancel/ - Annuler
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']

    def get_serializer_class(self):
        if self.action == 'list':
            return ValidationRequestListSerializer
        if self.action == 'approve':
            return ValidationApproveSerializer
        if self.action == 'reject':
            return ValidationRejectSerializer
        return ValidationRequestSerializer

    def get_queryset(self):
        """Filtre les demandes selon le role de l'utilisateur."""
        user = self.request.user

        # Debug logging
        logger.debug(f"[VALIDATIONS] get_queryset for user: {user.email} (role_level={user.role_level}, is_super_admin={user.is_super_admin()})")

        # Utiliser la nouvelle methode qui retourne toutes les demandes visibles
        # (en attente + traitees par l'utilisateur + liees a son organisme)
        queryset = ValidationService.get_all_requests_for_user(user)

        # Ajouter les demandes faites par l'utilisateur lui-meme
        user_requests = ValidationRequest.objects.filter(requester=user)
        combined_ids = set(queryset.values_list('id', flat=True)) | set(user_requests.values_list('id', flat=True))

        logger.debug(f"[VALIDATIONS] Returning {len(combined_ids)} requests for user {user.email}")

        return ValidationRequest.objects.filter(id__in=combined_ids).select_related(
            'requester',
            'target_site',
            'target_plan',
            'target_user',
            'requested_organisme',
            'validator'
        ).order_by('-created_at')

    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['approve', 'reject']:
            return [IsReferent()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """Liste avec filtres."""
        queryset = self.get_queryset()

        # Filtre par statut
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filtre par type
        type_filter = request.query_params.get('request_type')
        if type_filter:
            queryset = queryset.filter(request_type=type_filter)

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_count(self, request):
        """Compteur de demandes en attente pour l'utilisateur."""
        count = ValidationService.get_pending_requests_for_user(
            request.user
        ).count()
        return Response({'pending_count': count})

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Liste des demandes faites par l'utilisateur."""
        queryset = ValidationRequest.objects.filter(
            requester=request.user
        ).order_by('-created_at')

        serializer = ValidationRequestListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approuve une demande de validation."""
        # Utiliser une transaction avec select_for_update pour eviter les race conditions
        try:
            with transaction.atomic():
                # Verrouiller la ligne pour eviter les approbations concurrentes
                validation_request = ValidationRequest.objects.select_for_update().get(pk=pk)

                # Verifier que l'utilisateur peut valider
                if not validation_request.can_be_validated_by(request.user):
                    return Response(
                        {'error': 'Vous n\'avez pas les droits pour valider cette demande.'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Verifier que la demande est en attente (apres le verrou)
                if not validation_request.is_pending():
                    # Retourner un message plus informatif
                    validator_name = ""
                    if validation_request.validator:
                        v = validation_request.validator
                        validator_name = f"{v.prenom_role or ''} {v.nom_role or ''}".strip() or v.email
                    return Response(
                        {'error': f'Cette demande a deja ete traitee par {validator_name}.'},
                        status=status.HTTP_409_CONFLICT
                    )

                serializer = ValidationApproveSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                comment = serializer.validated_data.get('comment')

                # Traiter selon le type
                if validation_request.request_type == 'user_registration':
                    ValidationService.approve_registration(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'site_access':
                    ValidationService.approve_site_access(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'plan_access':
                    ValidationService.approve_plan_access(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'site_org_link':
                    ValidationService.approve_site_org_link(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'referent_validation':
                    ValidationService.approve_referent_validation(
                        validation_request,
                        request.user,
                        comment
                    )
                else:
                    # Approbation generique
                    validation_request.approve(request.user, comment)
                    NotificationService.notify_validation_result(validation_request, approved=True)

        except ValidationRequest.DoesNotExist:
            return Response(
                {'error': 'Demande de validation non trouvee.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'status': 'approved',
            'message': 'La demande a ete approuvee.'
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejette une demande de validation."""
        # Utiliser une transaction avec select_for_update pour eviter les race conditions
        try:
            with transaction.atomic():
                # Verrouiller la ligne pour eviter les traitements concurrents
                validation_request = ValidationRequest.objects.select_for_update().get(pk=pk)

                # Verifier que l'utilisateur peut valider
                if not validation_request.can_be_validated_by(request.user):
                    return Response(
                        {'error': 'Vous n\'avez pas les droits pour rejeter cette demande.'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Verifier que la demande est en attente (apres le verrou)
                if not validation_request.is_pending():
                    # Retourner un message plus informatif
                    validator_name = ""
                    if validation_request.validator:
                        v = validation_request.validator
                        validator_name = f"{v.prenom_role or ''} {v.nom_role or ''}".strip() or v.email
                    return Response(
                        {'error': f'Cette demande a deja ete traitee par {validator_name}.'},
                        status=status.HTTP_409_CONFLICT
                    )

                serializer = ValidationRejectSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                comment = serializer.validated_data['comment']

                ValidationService.reject_request(validation_request, request.user, comment)

        except ValidationRequest.DoesNotExist:
            return Response(
                {'error': 'Demande de validation non trouvee.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'status': 'rejected',
            'message': 'La demande a ete rejetee.'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule une demande (par le demandeur)."""
        validation_request = self.get_object()

        # Verifier que c'est le demandeur
        if validation_request.requester != request.user:
            return Response(
                {'error': 'Vous ne pouvez annuler que vos propres demandes.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verifier que la demande est en attente
        if not validation_request.is_pending():
            return Response(
                {'error': 'Cette demande a deja ete traitee.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        validation_request.cancel()

        return Response({
            'status': 'cancelled',
            'message': 'La demande a ete annulee.'
        })

    @action(detail=False, methods=['post'])
    def request_module_access(self, request):
        """
        POST /api/validations/request_module_access/
        Demande l'acces a un module.
        """
        serializer = ModuleAccessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        module_code = serializer.validated_data['module_code']
        justification = serializer.validated_data.get('justification', '')

        # Verifier qu'une demande n'existe pas deja pour ce module
        existing = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='module_access',
            target_module=module_code,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande pour ce module est deja en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'utilisateur n'a pas deja acces
        already_approved = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='module_access',
            target_module=module_code,
            status='approved'
        ).exists()

        if already_approved:
            return Response(
                {'error': 'Vous avez deja acces a ce module.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer la demande
        validation_request = ValidationRequest.objects.create(
            request_type='module_access',
            status='pending',
            requester=request.user,
            target_module=module_code,
            justification=justification,
        )

        # Notifier les super_admins
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande d\'acces au module a ete soumise.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def grant_module_access(self, request):
        """
        POST /api/validations/grant_module_access/
        Octroie l'acces a un module directement (super_admin uniquement).
        """
        # Verifier que c'est un super_admin
        if not request.user.is_super_admin():
            return Response(
                {'error': 'Seul un super administrateur peut octroyer des acces.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = GrantModuleAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        module_code = serializer.validated_data['module_code']

        from apps.users.models import Role
        target_user = Role.objects.get(id_role=user_id)

        # Verifier que l'utilisateur n'a pas deja acces
        already_approved = ValidationRequest.objects.filter(
            requester=target_user,
            request_type='module_access',
            target_module=module_code,
            status='approved'
        ).exists()

        if already_approved:
            return Response(
                {'error': 'Cet utilisateur a deja acces a ce module.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Annuler toute demande en attente pour ce module/utilisateur
        ValidationRequest.objects.filter(
            requester=target_user,
            request_type='module_access',
            target_module=module_code,
            status='pending'
        ).update(status='cancelled')

        # Creer une demande directement approuvee
        validation_request = ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=target_user,
            target_module=module_code,
            justification='Acces octroye par administrateur',
            validator=request.user,
            validated_at=timezone.now(),
        )

        # Notifier l'utilisateur
        NotificationService.create_notification(
            recipient=target_user,
            notification_type='validation_approved',
            title='Acces module accorde',
            message=f'Vous avez obtenu l\'acces au module {module_code}.',
            related_validation=validation_request,
        )

        return Response({
            'status': 'granted',
            'message': f'Acces au module {module_code} octroye.',
        })

    @action(detail=False, methods=['post'])
    def revoke_module_access(self, request):
        """
        POST /api/validations/revoke_module_access/
        Revoque l'acces a un module (super_admin uniquement).
        """
        # Verifier que c'est un super_admin
        if not request.user.is_super_admin():
            return Response(
                {'error': 'Seul un super administrateur peut revoquer des acces.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = GrantModuleAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        module_code = serializer.validated_data['module_code']

        from apps.users.models import Role
        target_user = Role.objects.get(id_role=user_id)

        # Trouver et rejeter la demande approuvee
        approved_requests = ValidationRequest.objects.filter(
            requester=target_user,
            request_type='module_access',
            target_module=module_code,
            status='approved'
        )

        if not approved_requests.exists():
            return Response(
                {'error': 'Cet utilisateur n\'a pas acces a ce module.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mettre a jour le statut en "rejected" pour indiquer la revocation
        approved_requests.update(
            status='rejected',
            validator=request.user,
            validation_comment='Acces revoque par administrateur',
            validated_at=timezone.now()
        )

        # Notifier l'utilisateur
        NotificationService.create_notification(
            recipient=target_user,
            notification_type='validation_rejected',
            title='Acces module revoque',
            message=f'Votre acces au module {module_code} a ete revoque.',
        )

        return Response({
            'status': 'revoked',
            'message': f'Acces au module {module_code} revoque.',
        })

    @action(detail=False, methods=['get'])
    def my_module_access(self, request):
        """
        GET /api/validations/my_module_access/
        Retourne la liste des modules auxquels l'utilisateur a acces.
        """
        approved_modules = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='module_access',
            status='approved'
        ).values_list('target_module', flat=True)

        return Response({
            'modules': list(approved_modules)
        })


class PublicRegistrationView:
    """
    Vue pour l'inscription publique.
    Cette vue est separee car elle n'est pas dans un ViewSet standard.
    Elle sera ajoutee aux URLs de l'app authentication.
    """

    @staticmethod
    def register(request):
        """
        POST /api/auth/register/
        Inscription publique d'un nouvel utilisateur.
        """
        from rest_framework.decorators import api_view, permission_classes
        from rest_framework.permissions import AllowAny

        serializer = PublicRegistrationSerializer(
            data=request.data,
            context={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            }
        )
        serializer.is_valid(raise_exception=True)
        pending_user = serializer.save()

        return Response({
            'message': 'Votre demande d\'inscription a ete soumise. '
                      'Vous recevrez un email lorsqu\'elle sera validee.',
            'validation_request_id': pending_user.validation_request.id,
        }, status=status.HTTP_201_CREATED)


# Vue fonction pour l'inscription publique
from rest_framework.decorators import api_view, permission_classes


@api_view(['POST'])
@permission_classes([AllowAny])
def public_registration_view(request):
    """Endpoint d'inscription publique."""
    serializer = PublicRegistrationSerializer(
        data=request.data,
        context={
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
        }
    )
    serializer.is_valid(raise_exception=True)
    pending_user = serializer.save()

    return Response({
        'message': 'Votre demande d\'inscription a ete soumise. '
                  'Vous recevrez un email lorsqu\'elle sera validee.',
        'validation_request_id': pending_user.validation_request.id,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_registration_status_view(request):
    """
    GET /api/auth/registration-status/?email=xxx
    Verifie le statut d'une inscription en attente.
    """
    email = request.query_params.get('email')
    if not email:
        return Response(
            {'error': 'Email requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        pending_user = PendingUser.objects.get(email__iexact=email)
        return Response({
            'status': 'pending',
            'message': 'Votre demande est en attente de validation.',
            'created_at': pending_user.created_at.isoformat(),
        })
    except PendingUser.DoesNotExist:
        # Verifier si l'utilisateur existe deja
        from apps.users.models import Role
        if Role.objects.filter(email__iexact=email).exists():
            return Response({
                'status': 'registered',
                'message': 'Ce compte existe deja. Vous pouvez vous connecter.',
            })

        return Response({
            'status': 'not_found',
            'message': 'Aucune demande trouvee pour cette adresse email.',
        })
