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
        
        # Admin organisme ne peut créer que dans son organisme
        if user.is_admin_organisme() and not user.is_super_admin():
            if new_user_organisme != user.id_organisme:
                raise serializers.ValidationError({
                    'organisme_id': 'Vous ne pouvez créer des utilisateurs que dans votre organisme.'
                })
            
            # Admin organisme ne peut pas créer de Super Admin
            if new_user_role_level == 'super_admin':
                raise serializers.ValidationError({
                    'role_level': 'Vous ne pouvez pas créer de Super Administrateur.'
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
                
                # Ne peut pas créer de Super Admin
                if serializer.validated_data.get('role_level') == 'super_admin':
                    raise PermissionError('Vous ne pouvez pas promouvoir un utilisateur en Super Admin.')
        
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

        Le compte sera desactive immediatement et anonymise apres 30 jours.
        """
        user = request.user

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

        # Demander la suppression
        user.request_deletion()

        # Notifier les administrateurs
        from apps.notifications.services import NotificationService
        for admin in Role.objects.filter(
            role_level='super_admin',
            active=True
        ).exclude(id_role=user.id_role):
            NotificationService.create_notification(
                recipient=admin,
                notification_type='system_alert',
                title="Demande de suppression de compte (RGPD)",
                message=f"L'utilisateur {user} a demande la suppression de son compte. "
                        f"Le compte sera anonymise dans 30 jours.",
                priority='low',
                related_user=user
            )

        return Response({
            'status': 'requested',
            'message': 'Votre demande de suppression a ete enregistree. '
                      'Votre compte sera desactive immediatement et vos donnees '
                      'seront anonymisees apres 30 jours.'
        })

    @action(detail=False, methods=['post'])
    def cancel_deletion(self, request):
        """
        Annuler une demande de suppression de compte (RGPD).
        POST /api/users/cancel_deletion/

        Permet d'annuler la demande pendant le delai de grace de 30 jours.
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
        user.active = True
        user.save(update_fields=['deletion_requested_at', 'active'])

        return Response({
            'status': 'cancelled',
            'message': 'Votre demande de suppression a ete annulee. '
                      'Votre compte est de nouveau actif.'
        })