"""
ViewSets pour l'API REST des utilisateurs.
"""
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth.models import Group

from .models import Role, BibOrganismes, Site, CorRoleSite
from .serializers import (
    RoleListSerializer, RoleDetailSerializer, RoleCreateSerializer,
    RoleUpdateSerializer, RolePasswordChangeSerializer, SiteAssignmentSerializer
)
from .permissions import (
    IsSuperAdmin, IsAdminOrganisme, IsReferent,
    CanManageOrganisme, IsOwnerOrReadOnly
)
from .filters import RoleFilter


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des utilisateurs via API REST.
    
    Endpoints:
    - GET /api/users/ : Liste paginée des utilisateurs
    - GET /api/users/{id}/ : Détail d'un utilisateur  
    - POST /api/users/ : Créer un utilisateur
    - PUT/PATCH /api/users/{id}/ : Modifier un utilisateur
    - DELETE /api/users/{id}/ : Supprimer un utilisateur
    - POST /api/users/{id}/change-password/ : Changer mot de passe
    - POST /api/users/{id}/sites/ : Assigner un site
    - DELETE /api/users/{id}/sites/{site_id}/ : Désassigner un site
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_class = RoleFilter
    search_fields = ['email', 'nom_role', 'prenom_role', 'identifiant']
    ordering_fields = ['email', 'nom_role', 'prenom_role', 'date_insert', 'role_level']
    ordering = ['-date_insert']
    
    def get_queryset(self):
        """
        Filtrage des utilisateurs selon les permissions.
        """
        user = self.request.user
        
        # Super admin voit tous les utilisateurs
        if user.is_super_admin():
            return Role.objects.select_related('id_organisme').prefetch_related('groups')

        # Rédacteur principal voit tous les utilisateurs
        if user.is_redacteur_principal():
            return Role.objects.select_related('id_organisme').prefetch_related('groups')

        # Admin organisme voit les utilisateurs de son organisme
        elif user.is_admin_organisme() and user.id_organisme:
            return Role.objects.filter(
                Q(id_organisme=user.id_organisme) | Q(id_role=user.id_role)
            ).select_related('id_organisme').prefetch_related('groups')
        
        # Référent et utilisateur voient seulement leur profil
        else:
            return Role.objects.filter(id_role=user.id_role).select_related('id_organisme')
    
    def get_serializer_class(self):
        """
        Choix du serializer selon l'action.
        """
        if self.action == 'list':
            return RoleListSerializer
        elif self.action == 'create':
            return RoleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RoleUpdateSerializer
        elif self.action == 'change_password':
            return RolePasswordChangeSerializer
        elif self.action in ['assign_site', 'unassign_site']:
            return SiteAssignmentSerializer
        else:
            return RoleDetailSerializer
    
    def get_permissions(self):
        """
        Permissions selon l'action.
        """
        # Check if action has its own permission_classes defined via @action decorator
        if hasattr(self, 'action') and self.action:
            action_func = getattr(self, self.action, None)
            if action_func and hasattr(action_func, 'kwargs'):
                action_permission_classes = action_func.kwargs.get('permission_classes')
                if action_permission_classes:
                    return [permission() for permission in action_permission_classes]

        if self.action == 'create':
            # Seuls Admin Organisme+ peuvent créer des utilisateurs
            permission_classes = [IsAdminOrganisme]
        elif self.action in ['update', 'partial_update']:
            # Utilisateur peut modifier son profil OU Admin Organisme+ peut modifier dans son scope
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'destroy':
            # Seuls Admin Organisme+ peuvent supprimer
            permission_classes = [IsAdminOrganisme]
        elif self.action in ['assign_site', 'unassign_site']:
            # Seuls Admin Organisme+ peuvent assigner des sites
            permission_classes = [IsAdminOrganisme]
        elif self.action == 'change_password':
            # Utilisateur peut changer son mot de passe OU Admin peut changer celui de ses users
            permission_classes = [IsOwnerOrReadOnly]
        else:
            # Actions de lecture : authentifié suffit (filtrage via get_queryset)
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Logique lors de la création d'un utilisateur.
        """
        user = self.request.user
        
        # Validation des permissions de création
        new_user_organisme = serializer.validated_data.get('id_organisme')
        new_user_role_level = serializer.validated_data.get('role_level', 'utilisateur')
        
        # Seul super_admin peut attribuer redacteur_principal ou super_admin
        if new_user_role_level in ('super_admin', 'redacteur_principal') and not user.is_super_admin():
            raise serializers.ValidationError({
                'role_level': 'Seul un Super Administrateur peut attribuer ce rôle.'
            })

        # Admin organisme ne peut créer que dans son organisme
        if user.is_admin_organisme() and not user.is_super_admin():
            if new_user_organisme != user.id_organisme:
                raise serializers.ValidationError({
                    'organisme_id': 'Vous ne pouvez créer des utilisateurs que dans votre organisme.'
                })
        
        # Sauvegarder l'utilisateur
        serializer.save()
    
    def perform_update(self, serializer):
        """
        Logique lors de la modification d'un utilisateur.
        """
        user = self.request.user
        target_user = self.get_object()
        
        # Validation des permissions de modification
        if not user.is_super_admin():
            # Utilisateur peut modifier son profil (sauf role_level et organisme)
            if user == target_user:
                # Empêcher auto-modification du role_level et organisme
                if 'role_level' in serializer.validated_data:
                    serializer.validated_data.pop('role_level')
                if 'id_organisme' in serializer.validated_data:
                    serializer.validated_data.pop('id_organisme')
            
            # Admin organisme peut modifier dans son organisme
            elif user.is_admin_organisme():
                if target_user.id_organisme != user.id_organisme:
                    raise PermissionError('Vous ne pouvez modifier que les utilisateurs de votre organisme.')
                
                # Ne peut pas créer de Super Admin ni Rédacteur Principal
                if serializer.validated_data.get('role_level') in ('super_admin', 'redacteur_principal'):
                    raise PermissionError('Vous ne pouvez pas attribuer ce rôle.')
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Logique lors de la suppression (désactivation) d'un utilisateur.
        """
        user = self.request.user
        
        # Empêcher l'auto-suppression
        if user == instance:
            raise PermissionError('Vous ne pouvez pas supprimer votre propre compte.')
        
        # Super admin ne peut pas être supprimé par un admin organisme
        if instance.is_super_admin() and not user.is_super_admin():
            raise PermissionError('Vous ne pouvez pas supprimer un Super Administrateur.')
        
        # Validation organisme pour admin organisme
        if user.is_admin_organisme() and not user.is_super_admin():
            if instance.id_organisme != user.id_organisme:
                raise PermissionError('Vous ne pouvez supprimer que les utilisateurs de votre organisme.')
        
        # Désactivation au lieu de suppression physique
        instance.active = False
        instance.save()
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Changer le mot de passe d'un utilisateur.
        POST /api/users/{id}/change-password/
        """
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'user': user})
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Mot de passe modifié avec succès'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='set-redacteur-principal',
            permission_classes=[IsSuperAdmin])
    def set_redacteur_principal(self, request, pk=None):
        """
        Promouvoir un utilisateur en Rédacteur Principal.
        POST /api/users/{id}/set-redacteur-principal/
        Réservé au super_admin.
        """
        target_user = self.get_object()

        if target_user.role_level == 'redacteur_principal':
            return Response(
                {'error': 'Cet utilisateur est déjà Rédacteur Principal.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target_user.is_super_admin():
            return Response(
                {'error': 'Impossible de rétrograder un Super Administrateur.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_role = target_user.role_level
        target_user.role_level = 'redacteur_principal'
        target_user.is_staff = True
        target_user.save(update_fields=['role_level', 'is_staff'])

        # Mettre à jour le groupe Django
        from django.contrib.auth.models import Group
        target_user.groups.clear()
        try:
            group = Group.objects.get(name='Rédacteurs Principaux')
            target_user.groups.add(group)
        except Group.DoesNotExist:
            pass

        # Log d'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            actor=request.user,
            action='status_change',
            entity_type='user',
            entity_id=target_user.pk,
            entity_name=target_user.get_full_name(),
            description=f'Promu Rédacteur Principal (était {old_role})',
            related_user=target_user,
        )

        return Response({
            'message': f'{target_user.get_full_name()} est maintenant Rédacteur Principal.',
            'user': RoleDetailSerializer(target_user, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'], url_path='remove-redacteur-principal',
            permission_classes=[IsSuperAdmin])
    def remove_redacteur_principal(self, request, pk=None):
        """
        Retirer le rôle de Rédacteur Principal (retour à utilisateur).
        POST /api/users/{id}/remove-redacteur-principal/
        Réservé au super_admin.
        """
        target_user = self.get_object()

        if target_user.role_level != 'redacteur_principal':
            return Response(
                {'error': "Cet utilisateur n'est pas Rédacteur Principal."},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_user.role_level = 'utilisateur'
        target_user.save(update_fields=['role_level'])

        # Mettre à jour le groupe Django
        from django.contrib.auth.models import Group
        target_user.groups.clear()
        try:
            group = Group.objects.get(name='Utilisateurs')
            target_user.groups.add(group)
        except Group.DoesNotExist:
            pass

        # Log d'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            actor=request.user,
            action='status_change',
            entity_type='user',
            entity_id=target_user.pk,
            entity_name=target_user.get_full_name(),
            description='Rétrogradé de Rédacteur Principal à Utilisateur',
            related_user=target_user,
        )

        return Response({
            'message': f"{target_user.get_full_name()} n'est plus Rédacteur Principal.",
            'user': RoleDetailSerializer(target_user, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'])
    def assign_site(self, request, pk=None):
        """
        Assigner un site à un utilisateur.
        POST /api/users/{id}/sites/
        """
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'user': user})
        
        if serializer.is_valid():
            # Validation des permissions
            requesting_user = request.user
            site_id = serializer.validated_data['id_site']['id_site']
            site = Site.objects.get(id_site=site_id)
            
            # Vérifier que l'admin peut assigner ce site
            if not requesting_user.is_super_admin():
                if not requesting_user.can_manage_site(site):
                    return Response(
                        {'error': 'Vous ne pouvez pas assigner ce site'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='sites/(?P<site_id>[^/.]+)')
    def unassign_site(self, request, pk=None, site_id=None):
        """
        Désassigner un site d'un utilisateur.
        DELETE /api/users/{id}/sites/{site_id}/
        """
        user = self.get_object()
        
        try:
            site = Site.objects.get(id_site=site_id)
            cor_role_site = CorRoleSite.objects.get(id_role=user, id_site=site)
            
            # Validation des permissions
            requesting_user = request.user
            if not requesting_user.is_super_admin():
                if not requesting_user.can_manage_site(site):
                    return Response(
                        {'error': 'Vous ne pouvez pas désassigner ce site'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            cor_role_site.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Site.DoesNotExist:
            return Response(
                {'error': 'Site non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CorRoleSite.DoesNotExist:
            return Response(
                {'error': 'Assignation non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Obtenir ses propres informations utilisateur.
        GET /api/users/me/
        """
        serializer = RoleDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques sur les utilisateurs (pour admin).
        GET /api/users/stats/
        """
        if not request.user.is_admin_organisme():
            return Response(
                {'error': 'Permissions insuffisantes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Filtrer selon les permissions
        queryset = self.get_queryset()
        
        stats = {
            'total_users': queryset.count(),
            'active_users': queryset.filter(active=True).count(),
            'inactive_users': queryset.filter(active=False).count(),
            'by_role_level': {}
        }
        
        # Statistiques par niveau de rôle
        for choice_code, choice_label in Role.ROLE_CHOICES:
            count = queryset.filter(role_level=choice_code).count()
            stats['by_role_level'][choice_code] = {
                'label': choice_label,
                'count': count
            }
        
        # Statistiques par organisme (si super admin)
        if request.user.is_super_admin():
            organismes_stats = []
            for org in BibOrganismes.objects.all():
                org_users = queryset.filter(id_organisme=org)
                if org_users.exists():
                    organismes_stats.append({
                        'organisme': org.nom_organisme,
                        'total': org_users.count(),
                        'active': org_users.filter(active=True).count()
                    })
            stats['by_organisme'] = organismes_stats

        return Response(stats)

    @action(detail=False, methods=['post'])
    def request_deletion(self, request):
        """
        Demander la suppression de son propre compte (RGPD).
        POST /api/users/request_deletion/

        Le compte reste actif. Un super_admin traitera manuellement la demande
        (desactivation ou anonymisation).
        """
        user = request.user

        # Les super_admin ne peuvent pas demander la suppression de leur compte
        if user.is_super_admin():
            return Response(
                {'error': 'Les super administrateurs ne peuvent pas demander la suppression de leur compte.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verifier que le compte n'est pas deja en cours de suppression
        if user.deletion_requested_at:
            return Response(
                {'error': 'Une demande de suppression est deja en cours pour ce compte.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le compte n'est pas anonymise
        if user.is_anonymized:
            return Response(
                {'error': 'Ce compte a deja ete supprime.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enregistrer la demande (sans desactiver le compte)
        from django.utils import timezone
        user.deletion_requested_at = timezone.now()
        user.save(update_fields=['deletion_requested_at'])

        # Enregistrer l'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            entity_type='user',
            entity_id=user.id_role,
            entity_name=str(user),
            action='rgpd_request',
            actor=user,
            description=f"L'utilisateur {user} a demande la suppression de son compte (RGPD).",
            visibility='admin'
        )

        # Notifier les personnes concernées
        from apps.notifications.services import NotificationService

        # Collecter tous les destinataires uniques (hors l'utilisateur lui-même)
        recipients = set()

        # 1. Super admins
        super_admins = Role.objects.filter(
            role_level='super_admin',
            active=True
        ).exclude(id_role=user.id_role)
        recipients.update(super_admins)

        # 2. Admin(s) de l'organisme de l'utilisateur
        if user.id_organisme:
            org_admins = Role.objects.filter(
                id_organisme=user.id_organisme,
                role_level='admin_og',
                active=True
            ).exclude(id_role=user.id_role)
            recipients.update(org_admins)

        # 3. Référents des sites où l'utilisateur est membre
        user_sites = CorRoleSite.objects.filter(id_role=user).values_list('id_site', flat=True)
        if user_sites:
            site_referents = Role.objects.filter(
                corrolesite__id_site__in=user_sites,
                corrolesite__referent=True,
                corrolesite__referent_valid=True,
                active=True
            ).exclude(id_role=user.id_role).distinct()
            recipients.update(site_referents)

        # 4. Référents des plans de gestion où l'utilisateur est référent
        user_plans = user.plans_referents.all()
        if user_plans.exists():
            for plan in user_plans:
                plan_referents = plan.referents.filter(
                    active=True
                ).exclude(id_role=user.id_role)
                recipients.update(plan_referents)

        # Envoyer les notifications
        for recipient in recipients:
            NotificationService.create_notification(
                recipient=recipient,
                notification_type='system_alert',
                title="Demande de suppression de compte (RGPD)",
                message=f"L'utilisateur {user} a demande la suppression de son compte. "
                        f"Cette demande doit etre traitee par un super administrateur.",
                priority='medium',
                related_user=user
            )

        return Response({
            'status': 'requested',
            'message': 'Votre demande de suppression a ete enregistree. '
                      'Un administrateur traitera votre demande dans les meilleurs delais.'
        })

    @action(detail=False, methods=['post'])
    def cancel_deletion(self, request):
        """
        Annuler une demande de suppression de compte (RGPD).
        POST /api/users/cancel_deletion/

        Permet a l'utilisateur d'annuler sa propre demande.
        """
        user = request.user

        # Verifier qu'une demande est en cours
        if not user.deletion_requested_at:
            return Response(
                {'error': 'Aucune demande de suppression en cours.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le compte n'est pas deja anonymise
        if user.is_anonymized:
            return Response(
                {'error': 'Ce compte a deja ete supprime et ne peut pas etre restaure.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Annuler la demande
        user.deletion_requested_at = None
        user.save(update_fields=['deletion_requested_at'])

        # Enregistrer l'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            entity_type='user',
            entity_id=user.id_role,
            entity_name=str(user),
            action='rgpd_cancelled',
            actor=user,
            description=f"L'utilisateur {user} a annule sa demande de suppression RGPD.",
            visibility='admin'
        )

        return Response({
            'status': 'cancelled',
            'message': 'Votre demande de suppression a ete annulee.'
        })

    # ==================== RGPD Admin Endpoints ====================

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdmin])
    def rgpd_requests(self, request):
        """
        Liste des demandes de suppression RGPD en cours.
        GET /api/users/users/rgpd_requests/
        Accessible uniquement aux super_admins.
        """
        from .serializers import RgpdRequestSerializer

        users = Role.objects.filter(
            deletion_requested_at__isnull=False,
            is_anonymized=False
        ).select_related('id_organisme').order_by('-deletion_requested_at')

        # Pagination
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = RgpdRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RgpdRequestSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def deactivate_rgpd(self, request, pk=None):
        """
        Desactiver un compte suite a une demande RGPD.
        POST /api/users/users/{id}/deactivate_rgpd/
        Accessible uniquement aux super_admins et si AUTH_PROVIDER == 'local'.
        """
        from django.conf import settings

        # Verifier que l'auth est locale
        if getattr(settings, 'AUTH_PROVIDER', 'local') != 'local':
            return Response(
                {'error': "La gestion des comptes est deleguee a Keycloak."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = self.get_object()

        # Verifier qu'une demande RGPD est en cours
        if not user.deletion_requested_at:
            return Response(
                {'error': "Aucune demande RGPD en cours pour cet utilisateur."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le compte n'est pas deja anonymise
        if user.is_anonymized:
            return Response(
                {'error': "Ce compte est deja anonymise."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Desactiver le compte et effacer la demande (traitee)
        user.active = False
        user.deletion_requested_at = None
        user.save(update_fields=['active', 'deletion_requested_at'])

        # Enregistrer l'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            entity_type='user',
            entity_id=user.id_role,
            entity_name=str(user),
            action='deactivate',
            actor=request.user,
            description=f"Le compte de {user} a ete desactive suite a une demande RGPD par {request.user}.",
            visibility='admin'
        )

        # Notifier l'utilisateur
        from apps.notifications.services import NotificationService
        NotificationService.create_notification(
            recipient=user,
            notification_type='account_deactivated',
            title="Compte desactive (RGPD)",
            message="Votre compte a ete desactive suite a votre demande de suppression. "
                    "Vos donnees personnelles n'ont pas encore ete supprimees.",
            priority='high'
        )

        return Response({
            'status': 'deactivated',
            'message': f"Le compte de {user} a ete desactive."
        })

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def anonymize_rgpd(self, request, pk=None):
        """
        Anonymiser un compte suite a une demande RGPD.
        POST /api/users/users/{id}/anonymize_rgpd/
        Accessible uniquement aux super_admins et si AUTH_PROVIDER == 'local'.
        """
        from django.conf import settings

        # Verifier que l'auth est locale
        if getattr(settings, 'AUTH_PROVIDER', 'local') != 'local':
            return Response(
                {'error': "La gestion des comptes est deleguee a Keycloak."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = self.get_object()

        # Verifier qu'une demande RGPD est en cours
        if not user.deletion_requested_at:
            return Response(
                {'error': "Aucune demande RGPD en cours pour cet utilisateur."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le compte n'est pas deja anonymise
        if user.is_anonymized:
            return Response(
                {'error': "Ce compte est deja anonymise."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sauvegarder le nom pour le log
        user_name = str(user)
        user_id = user.id_role

        # Anonymiser le compte
        user.anonymize()

        # Enregistrer l'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            entity_type='user',
            entity_id=user_id,
            entity_name=user_name,
            action='rgpd_anonymized',
            actor=request.user,
            description=f"Le compte de {user_name} a ete anonymise suite a une demande RGPD par {request.user}.",
            visibility='system'
        )

        return Response({
            'status': 'anonymized',
            'message': f"Le compte a ete anonymise."
        })

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def reject_rgpd(self, request, pk=None):
        """
        Rejeter/annuler une demande RGPD.
        POST /api/users/users/{id}/reject_rgpd/
        Accessible uniquement aux super_admins.
        """
        user = self.get_object()

        # Verifier qu'une demande RGPD est en cours
        if not user.deletion_requested_at:
            return Response(
                {'error': "Aucune demande RGPD en cours pour cet utilisateur."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le compte n'est pas deja anonymise
        if user.is_anonymized:
            return Response(
                {'error': "Ce compte est deja anonymise."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Annuler la demande
        user.deletion_requested_at = None
        user.save(update_fields=['deletion_requested_at'])

        # Enregistrer l'activité
        from apps.core.services import ActivityService
        ActivityService.log_activity(
            entity_type='user',
            entity_id=user.id_role,
            entity_name=str(user),
            action='rgpd_cancelled',
            actor=request.user,
            description=f"La demande RGPD de {user} a ete rejetee par {request.user}.",
            visibility='admin'
        )

        # Notifier l'utilisateur
        from apps.notifications.services import NotificationService
        NotificationService.create_notification(
            recipient=user,
            notification_type='system_alert',
            title="Demande de suppression rejetee",
            message="Votre demande de suppression de compte a ete rejetee par un administrateur. "
                    "Votre compte reste actif.",
            priority='medium'
        )

        return Response({
            'status': 'rejected',
            'message': f"La demande RGPD de {user} a ete rejetee."
        })

    @action(detail=False, methods=['get'])
    def auth_provider(self, request):
        """
        Retourne le provider d'authentification configure.
        GET /api/users/users/auth_provider/
        """
        from django.conf import settings
        return Response({
            'provider': getattr(settings, 'AUTH_PROVIDER', 'local')
        })