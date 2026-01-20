"""
Views pour les modeles du core.
"""
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsSuperAdmin
from apps.notifications.models import ValidationRequest

from .models import Module, ErrorLog
from .serializers import (
    ModuleSerializer,
    ModuleListSerializer,
    ModuleCreateUpdateSerializer,
    ErrorLogListSerializer,
    ErrorLogDetailSerializer,
    ErrorLogStatsSerializer,
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


# =============================================================================
# ErrorLog ViewSet
# =============================================================================

class ErrorLogFilter(filters.FilterSet):
    """Filtres pour les logs d'erreur."""

    level = filters.ChoiceFilter(choices=ErrorLog.LEVEL_CHOICES)
    acknowledged = filters.BooleanFilter()
    date_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    exception_type = filters.CharFilter(lookup_expr='icontains')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = ErrorLog
        fields = ['level', 'acknowledged', 'exception_type']

    def filter_search(self, queryset, name, value):
        """Recherche dans le message et le correlation_id."""
        from django.db.models import Q
        return queryset.filter(
            Q(message__icontains=value) |
            Q(correlation_id__icontains=value) |
            Q(path__icontains=value)
        )


class ErrorLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la consultation des logs d'erreur.

    Accessible uniquement aux super_admin.

    Endpoints:
    - GET /api/admin/error-logs/ - Liste paginee avec filtres
    - GET /api/admin/error-logs/{id}/ - Detail d'un log
    - POST /api/admin/error-logs/{id}/acknowledge/ - Acquitter un log
    - POST /api/admin/error-logs/acknowledge_all/ - Acquitter tous les logs visibles
    - GET /api/admin/error-logs/stats/ - Statistiques
    - GET /api/admin/error-logs/unacknowledged_count/ - Nombre de logs non acquittes
    """

    queryset = ErrorLog.objects.all()
    permission_classes = [IsSuperAdmin]
    filterset_class = ErrorLogFilter
    search_fields = ['message', 'correlation_id', 'path']
    ordering_fields = ['created_at', 'level', 'acknowledged']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ErrorLogDetailSerializer
        return ErrorLogListSerializer

    def get_queryset(self):
        """Optimise les requetes avec select_related."""
        return ErrorLog.objects.select_related('user', 'acknowledged_by')

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        POST /api/admin/error-logs/{id}/acknowledge/
        Acquitte un log d'erreur.
        """
        error_log = self.get_object()

        if error_log.acknowledged:
            return Response(
                {'detail': 'Ce log a deja ete acquitte.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        error_log.acknowledge(request.user)

        return Response({
            'id': error_log.id,
            'acknowledged': True,
            'acknowledged_by': request.user.id_role,
            'acknowledged_at': error_log.acknowledged_at.isoformat(),
        })

    @action(detail=False, methods=['post'])
    def acknowledge_all(self, request):
        """
        POST /api/admin/error-logs/acknowledge_all/
        Acquitte tous les logs non acquittes correspondant aux filtres actuels.
        """
        # Appliquer les filtres
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(acknowledged=False)

        count = queryset.count()

        # Mise a jour en masse
        now = timezone.now()
        queryset.update(
            acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=now
        )

        return Response({
            'acknowledged_count': count,
            'acknowledged_by': request.user.id_role,
            'acknowledged_at': now.isoformat(),
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/admin/error-logs/stats/
        Retourne des statistiques sur les logs d'erreur.
        """
        # Statistiques globales
        total = ErrorLog.objects.count()
        unacknowledged = ErrorLog.objects.filter(acknowledged=False).count()

        # Par niveau
        by_level = dict(
            ErrorLog.objects
            .values('level')
            .annotate(count=Count('id'))
            .values_list('level', 'count')
        )

        # Par jour (7 derniers jours)
        seven_days_ago = timezone.now() - timedelta(days=7)
        by_day = list(
            ErrorLog.objects
            .filter(created_at__gte=seven_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
            .values('date', 'count')
        )

        # Convertir les dates en string
        for item in by_day:
            item['date'] = item['date'].isoformat()

        return Response({
            'total': total,
            'unacknowledged': unacknowledged,
            'by_level': by_level,
            'by_day': by_day,
        })

    @action(detail=False, methods=['get'])
    def unacknowledged_count(self, request):
        """
        GET /api/admin/error-logs/unacknowledged_count/
        Retourne le nombre de logs non acquittes (pour le badge).
        """
        count = ErrorLog.objects.filter(acknowledged=False).count()
        return Response({'count': count})
