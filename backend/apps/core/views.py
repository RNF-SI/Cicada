"""
Views pour les modeles du core.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsSuperAdmin
from apps.notifications.models import ValidationRequest

from .models import Module
from .serializers import (
    ModuleSerializer,
    ModuleListSerializer,
    ModuleCreateUpdateSerializer,
)


class ModuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des modules applicatifs.

    Endpoints:
    - GET /api/modules/ - Liste des modules actifs (public pour utilisateurs connectes)
    - GET /api/modules/{id}/ - Detail d'un module
    - POST /api/modules/ - Creer un module (super_admin)
    - PUT /api/modules/{id}/ - Modifier un module (super_admin)
    - DELETE /api/modules/{id}/ - Supprimer un module (super_admin)
    - GET /api/modules/all/ - Tous les modules y compris inactifs (super_admin)
    - GET /api/modules/requiring_access/ - Modules necessitant un acces
    - GET /api/modules/my_accessible/ - Modules accessibles par l'utilisateur connecte
    """

    queryset = Module.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ModuleListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ModuleCreateUpdateSerializer
        return ModuleSerializer

    def get_queryset(self):
        """
        Par defaut, retourne uniquement les modules actifs.
        Les super_admins peuvent voir tous les modules via l'action 'all'.
        """
        return Module.objects.filter(is_active=True)

    def get_permissions(self):
        """
        Permissions selon l'action:
        - list, retrieve, requiring_access, my_accessible: IsAuthenticated
        - create, update, partial_update, destroy, all: IsSuperAdmin
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'all']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def all(self, request):
        """
        GET /api/modules/all/
        Retourne tous les modules y compris inactifs (super_admin only).
        """
        queryset = Module.objects.all()
        serializer = ModuleSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def requiring_access(self, request):
        """
        GET /api/modules/requiring_access/
        Retourne les modules qui necessitent une demande d'acces.
        """
        queryset = self.get_queryset().filter(requires_access=True)
        serializer = ModuleListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_accessible(self, request):
        """
        GET /api/modules/my_accessible/
        Retourne les modules accessibles par l'utilisateur connecte.
        Inclut:
        - Tous les modules qui ne necessitent pas d'acces
        - Les modules avec acces approuve pour l'utilisateur
        """
        user = request.user

        # Modules ne necessitant pas d'acces
        public_modules = self.get_queryset().filter(requires_access=False)

        # Codes des modules avec acces approuve
        approved_module_codes = ValidationRequest.objects.filter(
            requester=user,
            request_type='module_access',
            status='approved'
        ).values_list('target_module', flat=True)

        # Modules avec acces approuve
        approved_modules = self.get_queryset().filter(
            requires_access=True,
            code__in=approved_module_codes
        )

        # Combiner les deux querysets
        all_accessible = public_modules | approved_modules
        all_accessible = all_accessible.distinct().order_by('display_order', 'name')

        serializer = ModuleListSerializer(all_accessible, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def access_status(self, request, pk=None):
        """
        GET /api/modules/{id}/access_status/
        Retourne le statut d'acces de l'utilisateur pour ce module.
        """
        module = self.get_object()
        user = request.user

        if not module.requires_access:
            return Response({
                'module_code': module.code,
                'requires_access': False,
                'has_access': True,
                'status': 'granted',
                'message': 'Ce module ne necessite pas d\'acces specifique.'
            })

        # Chercher une demande d'acces
        access_request = ValidationRequest.objects.filter(
            requester=user,
            request_type='module_access',
            target_module=module.code
        ).order_by('-created_at').first()

        if not access_request:
            return Response({
                'module_code': module.code,
                'requires_access': True,
                'has_access': False,
                'status': 'none',
                'message': 'Vous n\'avez pas encore demande l\'acces a ce module.'
            })

        status_messages = {
            'pending': 'Votre demande est en attente de validation.',
            'approved': 'Vous avez acces a ce module.',
            'rejected': 'Votre demande a ete rejetee.',
            'cancelled': 'Votre demande a ete annulee.',
            'expired': 'Votre demande a expire.',
        }

        return Response({
            'module_code': module.code,
            'requires_access': True,
            'has_access': access_request.status == 'approved',
            'status': access_request.status,
            'request_id': access_request.id,
            'message': status_messages.get(access_request.status, ''),
            'created_at': access_request.created_at.isoformat(),
            'validated_at': access_request.validated_at.isoformat() if access_request.validated_at else None,
        })
