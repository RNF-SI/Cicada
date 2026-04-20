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
    AdminPromotionRequestSerializer,
    AdminDemotionRequestSerializer,
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
        # Retourner le compteur reel pour synchronisation frontend
        unread_count = self.get_queryset().filter(read=False).count()
        return Response({'status': 'ok', 'unread_count': unread_count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marque toutes les notifications comme lues."""
        updated_count = self.get_queryset().filter(read=False).update(
            read=True,
            read_at=timezone.now()
        )
        # Retourner le compteur reel apres mise a jour (devrait etre 0)
        unread_count = self.get_queryset().filter(read=False).count()
        return Response({
            'status': 'ok',
            'updated_count': updated_count,
            'unread_count': unread_count
        })

    @action(detail=False, methods=['get'])
    def poll(self, request):
        """
        Endpoint de polling pour les mises a jour.
        Utiliser ?since=<timestamp> pour detecter les nouvelles notifications.
        Retourne toujours les 10 dernieres notifications (non filtrees par since).
        """
        since_param = request.query_params.get('since')
        base_queryset = self.get_queryset()

        # Calculer has_updates base sur since
        has_updates = True
        if since_param:
            try:
                since = timezone.datetime.fromisoformat(since_param)
                has_updates = base_queryset.filter(created_at__gt=since).exists()
            except ValueError:
                pass

        unread_count = base_queryset.filter(read=False).count()

        # Compteur de validations en attente
        pending_validations = 0
        if request.user.is_referent():
            pending_validations = ValidationService.get_pending_requests_for_user(
                request.user
            ).count()

        # Toujours retourner les 10 dernieres notifications (pas filtrees par since)
        notifications = NotificationListSerializer(
            base_queryset[:10],
            many=True
        ).data

        return Response({
            'notifications': notifications,
            'unread_count': unread_count,
            'pending_validations': pending_validations,
            'has_updates': has_updates,
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

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Retourne la liste des types de demandes et des statuts disponibles.

        Permet au frontend de rester synchronisé avec le backend sans hardcoder les valeurs.

        Response:
            {
                "request_types": [
                    {"value": "user_registration", "label": "Inscription utilisateur"},
                    ...
                ],
                "statuses": [
                    {"value": "pending", "label": "En attente"},
                    ...
                ]
            }
        """
        request_types = [
            {'value': value, 'label': str(label)}
            for value, label in ValidationRequest.REQUEST_TYPES
        ]
        statuses = [
            {'value': value, 'label': str(label)}
            for value, label in ValidationRequest.STATUS_CHOICES
        ]
        return Response({
            'request_types': request_types,
            'statuses': statuses
        })

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

                # Bloquer site_access si site_org_link en attente
                if validation_request.request_type == 'site_access':
                    pending_org_link = ValidationRequest.objects.filter(
                        requester=validation_request.requester,
                        target_site=validation_request.target_site,
                        request_type='site_org_link',
                        status='pending'
                    ).exists()
                    if pending_org_link:
                        return Response(
                            {'error': "Une demande de lien organisme-site est en attente pour ce site. "
                                      "Veuillez l'approuver en premier."},
                            status=status.HTTP_409_CONFLICT
                        )

                serializer = ValidationApproveSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                comment = serializer.validated_data.get('comment')
                approve_as_referent = serializer.validated_data.get('approve_as_referent')
                organisme_id_override = serializer.validated_data.get('organisme_id_override')

                # Traiter selon le type
                if validation_request.request_type == 'user_registration':
                    organisme_override = None
                    if organisme_id_override:
                        from apps.users.models import BibOrganismes
                        try:
                            organisme_override = BibOrganismes.objects.get(
                                id_organisme=organisme_id_override
                            )
                        except BibOrganismes.DoesNotExist:
                            return Response(
                                {'error': "Organisme d'override introuvable."},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    ValidationService.approve_registration(
                        validation_request,
                        request.user,
                        comment,
                        organisme_override=organisme_override,
                    )
                elif validation_request.request_type == 'site_access':
                    ValidationService.approve_site_access(
                        validation_request,
                        request.user,
                        comment,
                        override_referent=approve_as_referent
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
                elif validation_request.request_type == 'site_org_unlink':
                    ValidationService.approve_site_org_unlink(
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
                elif validation_request.request_type == 'invite_org_to_site':
                    ValidationService.approve_invite_org_to_site(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'invite_user_to_site':
                    ValidationService.approve_invite_user_to_site(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'site_creation':
                    ValidationService.approve_site_creation(
                        validation_request,
                        request.user,
                        comment,
                        override_referent=approve_as_referent
                    )
                elif validation_request.request_type == 'plan_site_link':
                    ValidationService.approve_plan_site_link(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'admin_deactivation':
                    ValidationService.approve_admin_deactivation(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'admin_promotion':
                    ValidationService.approve_admin_promotion(
                        validation_request,
                        request.user,
                        comment
                    )
                elif validation_request.request_type == 'admin_demotion':
                    ValidationService.approve_admin_demotion(
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
    def request_plan_access(self, request):
        """
        POST /api/validations/request_plan_access/
        Demande l'acces a un plan de gestion.
        """
        serializer = PlanAccessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = request.data.get('plan_id')
        justification = serializer.validated_data.get('justification', '')

        # Verifier que plan_id est fourni
        if not plan_id:
            return Response(
                {'error': 'L\'identifiant du plan est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.plans.models import PlanGestion

        # Recuperer le plan
        try:
            plan = PlanGestion.objects.get(id_pg=plan_id)
        except PlanGestion.DoesNotExist:
            return Response(
                {'error': 'Plan de gestion introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que l'utilisateur n'est pas deja referent
        if plan.referents.filter(id_role=request.user.id_role).exists():
            return Response(
                {'error': 'Vous avez deja acces a ce plan de gestion.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'utilisateur n'est pas deja membre direct (CorRolePlan)
        from apps.plans.models import CorRolePlan
        if CorRolePlan.objects.filter(id_role=request.user, plan_de_gestion=plan).exists():
            return Response(
                {'error': 'Vous avez deja acces a ce plan de gestion.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='plan_access',
            target_plan=plan,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande d\'acces a ce plan est deja en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer la demande
        request_as_referent = request.data.get('request_as_referent', False)
        validation_request = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=request.user,
            target_plan=plan,
            justification=justification,
            request_as_referent=request_as_referent,
        )

        # Notifier les validateurs (referents du plan + admin_og des sites)
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande d\'acces au plan de gestion a ete soumise.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def request_plan_site_link(self, request):
        """
        POST /api/validations/request_plan_site_link/
        Demande a lier un site a un plan de gestion.
        """
        serializer = PlanAccessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = request.data.get('plan_id')
        site_id = request.data.get('site_id')
        justification = serializer.validated_data.get('justification', '')

        if not plan_id or not site_id:
            return Response(
                {'error': 'plan_id et site_id sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.plans.models import PlanGestion, CorSitePg
        from apps.users.models import Site

        try:
            plan = PlanGestion.objects.get(id_pg=plan_id)
        except PlanGestion.DoesNotExist:
            return Response(
                {'error': 'Plan de gestion introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            site = Site.objects.get(id_site=site_id)
        except Site.DoesNotExist:
            return Response(
                {'error': 'Site introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que le site n'est pas deja lie
        if CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists():
            return Response(
                {'error': 'Ce site est deja lie a ce plan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            request_type='plan_site_link',
            target_plan=plan,
            target_site=site,
            status='pending'
        ).exists()
        if existing:
            return Response(
                {'error': 'Une demande de lien est deja en attente pour ce site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'utilisateur a un lien avec le plan ou le site
        user = request.user
        from apps.plans.models import CorRolePlan
        from apps.users.models import CorRoleSite
        is_plan_referent = plan.referents.filter(pk=user.pk).exists()
        is_plan_member = CorRolePlan.objects.filter(id_role=user, plan_de_gestion=plan).exists()
        is_site_referent = user.can_manage_site(site)
        is_site_member = CorRoleSite.objects.filter(id_role=user, id_site=site).exists()

        if not (user.is_admin_organisme() or is_plan_referent or is_plan_member or is_site_referent or is_site_member):
            return Response(
                {'error': "Vous n'avez pas les droits pour effectuer cette action."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Liaison directe si super_admin, ou admin_og qui gere le site,
        # ou referent du plan ET du site
        can_link_directly = (
            user.is_super_admin() or
            user.is_redacteur_principal() or
            (user.is_admin_organisme() and is_site_referent) or
            (is_plan_referent and is_site_referent)
        )

        if can_link_directly:
            CorSitePg.objects.get_or_create(
                site=site,
                plan_de_gestion=plan,
                defaults={'rang': 0}
            )

            # Notifier les referents du plan (sauf l'utilisateur courant)
            for referent in plan.referents.filter(active=True).exclude(pk=user.pk):
                NotificationService.create_notification(
                    recipient=referent,
                    notification_type='info',
                    title=f"Site lié au plan {plan.nom}",
                    message=f"Le site {site.nom_site} a été lié au plan de gestion {plan.nom}.",
                    priority='medium',
                    related_plan=plan,
                    related_site=site,
                    action_url=f"/plans/{plan.slug or plan.id_pg}",
                )

            return Response({
                'message': 'Site lie au plan avec succes.',
                'direct': True,
            }, status=status.HTTP_201_CREATED)

        # Sinon, creer une demande de validation
        validation_request = ValidationRequest.objects.create(
            request_type='plan_site_link',
            status='pending',
            requester=request.user,
            target_plan=plan,
            target_site=site,
            justification=justification,
        )

        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande de lien plan-site a ete soumise et est en attente de validation.',
            'direct': False,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def request_admin_deactivation(self, request):
        """
        POST /api/validations/request_admin_deactivation/
        Demande la desactivation d'un admin_og par un autre admin_og.
        Seuls les super_admin peuvent valider cette demande.
        """
        serializer = AdminDeactivationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = request.data.get('target_user_id')
        justification = serializer.validated_data['justification']

        # Verifier que target_user_id est fourni
        if not target_user_id:
            return Response(
                {'error': 'L\'identifiant de l\'utilisateur cible est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.users.models import Role

        # Recuperer l'utilisateur cible
        try:
            target_user = Role.objects.get(id_role=target_user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur cible introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que le demandeur est admin_og ou super_admin
        if not (request.user.is_super_admin() or request.user.role_level == 'admin_og'):
            return Response(
                {'error': 'Seuls les administrateurs peuvent demander la desactivation d\'un autre administrateur.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verifier que la cible est admin_og
        if target_user.role_level != 'admin_og':
            return Response(
                {'error': 'Seule la desactivation d\'un admin_og peut etre demandee via ce processus.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pour admin_og, verifier que la cible est du meme organisme
        if request.user.role_level == 'admin_og':
            if target_user.id_organisme != request.user.id_organisme:
                return Response(
                    {'error': 'Vous ne pouvez demander la desactivation que d\'un administrateur de votre organisme.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            request_type='admin_deactivation',
            target_user=target_user,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande de desactivation pour cet administrateur est deja en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer la demande
        validation_request = ValidationRequest.objects.create(
            request_type='admin_deactivation',
            status='pending',
            requester=request.user,
            target_user=target_user,
            requested_organisme=target_user.id_organisme,
            justification=justification,
        )

        # Notifier les super_admins
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande de desactivation a ete soumise aux super administrateurs.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def request_admin_promotion(self, request):
        """
        POST /api/validations/request_admin_promotion/
        Demande la promotion d'un utilisateur en admin_og.
        Seuls les super_admin peuvent valider cette demande.
        """
        serializer = AdminPromotionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = request.data.get('target_user_id')
        justification = serializer.validated_data['justification']

        if not target_user_id:
            return Response(
                {'error': 'L\'identifiant de l\'utilisateur cible est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.users.models import Role

        try:
            target_user = Role.objects.get(id_role=target_user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur cible introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que le demandeur est admin_og ou super_admin
        if not (request.user.is_super_admin() or request.user.role_level == 'admin_og'):
            return Response(
                {'error': 'Seuls les administrateurs peuvent demander la promotion d\'un utilisateur.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verifier que la cible est un utilisateur simple (pas deja admin)
        if target_user.role_level != 'utilisateur':
            return Response(
                {'error': 'Seul un utilisateur simple peut etre promu admin_og.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pour admin_og, verifier que la cible est du meme organisme
        if request.user.role_level == 'admin_og':
            if target_user.id_organisme != request.user.id_organisme:
                return Response(
                    {'error': 'Vous ne pouvez promouvoir que des utilisateurs de votre organisme.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            request_type='admin_promotion',
            target_user=target_user,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande de promotion pour cet utilisateur est deja en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer la demande
        validation_request = ValidationRequest.objects.create(
            request_type='admin_promotion',
            status='pending',
            requester=request.user,
            target_user=target_user,
            requested_organisme=target_user.id_organisme,
            justification=justification,
        )

        # Notifier les super_admins
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande de promotion a ete soumise aux super administrateurs.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def request_admin_demotion(self, request):
        """
        POST /api/validations/request_admin_demotion/
        Demande la retrogradation d'un admin_og en utilisateur simple.
        Seuls les super_admin peuvent valider cette demande.
        """
        serializer = AdminDemotionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = request.data.get('target_user_id')
        justification = serializer.validated_data['justification']

        if not target_user_id:
            return Response(
                {'error': 'L\'identifiant de l\'utilisateur cible est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.users.models import Role

        try:
            target_user = Role.objects.get(id_role=target_user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur cible introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que le demandeur est admin_og ou super_admin
        if not (request.user.is_super_admin() or request.user.role_level == 'admin_og'):
            return Response(
                {'error': 'Seuls les administrateurs peuvent demander la retrogradation d\'un admin_og.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verifier que la cible est admin_og
        if target_user.role_level != 'admin_og':
            return Response(
                {'error': 'Seule la retrogradation d\'un admin_og peut etre demandee.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pour admin_og, verifier que la cible est du meme organisme
        if request.user.role_level == 'admin_og':
            if target_user.id_organisme != request.user.id_organisme:
                return Response(
                    {'error': 'Vous ne pouvez demander la retrogradation que d\'un administrateur de votre organisme.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            request_type='admin_demotion',
            target_user=target_user,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande de retrogradation pour cet administrateur est deja en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer la demande
        validation_request = ValidationRequest.objects.create(
            request_type='admin_demotion',
            status='pending',
            requester=request.user,
            target_user=target_user,
            requested_organisme=target_user.id_organisme,
            justification=justification,
        )

        # Notifier les super_admins
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': 'Votre demande de retrogradation a ete soumise aux super administrateurs.',
        }, status=status.HTTP_201_CREATED)

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
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from apps.authentication.throttles import AuthRateThrottle


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
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
