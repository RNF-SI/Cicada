"""
Views pour les modeles du core.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.users.permissions import IsSuperAdmin, IsAdminOrganisme
from apps.notifications.models import ValidationRequest, Notification
from apps.users.models import CorRoleSite, CorOgSite

from .models import Module, ErrorLog, ActivityLog, Nomenclature, SiteConfiguration
from .serializers import (
    ModuleSerializer,
    ModuleListSerializer,
    ModuleCreateUpdateSerializer,
    ErrorLogListSerializer,
    ErrorLogDetailSerializer,
    ErrorLogStatsSerializer,
    ActivityLogListSerializer,
    ActivityLogDetailSerializer,
    ActivityLogStatsSerializer,
    NomenclatureSerializer,
    SiteConfigurationSerializer,
    SiteConfigurationUpdateSerializer,
)

# Mapping des types frontend -> mnémonique backend TypeNomenclature
NOMENCLATURE_TYPE_MAPPING = {
    'TYPE_SITE': 'Espace naturel',
    'TYPE_EVALUATION': 'Evaluation PG',
    'TYPE_REDACTEUR': 'Rédacteur type',
    'TYPE_DOCUMENT_PLAN': 'Type document plan',
}


# =============================================================================
# Nomenclature ViewSet
# =============================================================================

class NomenclatureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API en lecture seule pour les nomenclatures.
    Filtrage par type via ?type=TYPE_SITE, ?type=TYPE_EVALUATION, etc.
    Paramètres optionnels :
    - ?prefix=CS  →  filtre les nomenclatures dont cd_nomenclature commence par le préfixe
    """
    serializer_class = NomenclatureSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Nomenclature.objects.filter(actif=True).select_related('id_type')
        type_param = self.request.query_params.get('type')
        if type_param:
            mnemonique = NOMENCLATURE_TYPE_MAPPING.get(type_param, type_param)
            qs = qs.filter(id_type__mnemonique=mnemonique)
        # Filtre optionnel par préfixe de code
        prefix = self.request.query_params.get('prefix')
        if prefix:
            qs = qs.filter(cd_nomenclature__startswith=prefix)
        return qs.order_by('hierarchy', 'label')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        type_param = request.query_params.get('type')
        if type_param == 'TYPE_ACTION':
            from .action_type_groups import get_action_group
            for item in response.data:
                item['group_label'] = get_action_group(
                    item.get('cd_nomenclature', '')
                )
        elif type_param == 'TYPE_PRESSION':
            from .pressure_type_groups import get_pressure_group
            for item in response.data:
                item['group_label'] = get_pressure_group(
                    item.get('cd_nomenclature', '')
                )
        return response


# =============================================================================
# SiteConfiguration View
# =============================================================================

class SiteConfigurationView(APIView):
    """
    Vue pour la configuration globale du site.

    Endpoints:
    - GET /api/settings/ - Retourne la configuration (public, pas d'auth)
    - PATCH /api/settings/ - Met a jour l'image (super_admin uniquement)
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        """
        GET: Pas d'authentification requise
        PATCH/PUT: Super admin uniquement
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsSuperAdmin()]

    def get(self, request):
        """
        GET /api/settings/
        Retourne la configuration du site (public).
        """
        config = SiteConfiguration.get_instance()
        serializer = SiteConfigurationSerializer(config, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        """
        PATCH /api/settings/
        Met a jour la configuration (super_admin only).
        Supporte l'upload d'image via multipart/form-data.
        """
        config = SiteConfiguration.get_instance()

        # Gestion de la suppression d'image (reset to default)
        if request.data.get('homepage_image') == '' or request.data.get('reset_image') == 'true':
            # Supprimer l'image actuelle si elle existe
            if config.homepage_image:
                config.homepage_image.delete(save=False)
            config.homepage_image = None
            config.updated_by = request.user
            config.save()
            serializer = SiteConfigurationSerializer(config, context={'request': request})
            return Response(serializer.data)

        # #448 — Suppression du logo de la structure (reset)
        if request.data.get('structure_logo') == '' or request.data.get('reset_logo') == 'true':
            if config.structure_logo:
                config.structure_logo.delete(save=False)
            config.structure_logo = None
            config.updated_by = request.user
            config.save()
            serializer = SiteConfigurationSerializer(config, context={'request': request})
            return Response(serializer.data)

        # Use update serializer for write operations
        update_serializer = SiteConfigurationUpdateSerializer(
            config,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        update_serializer.is_valid(raise_exception=True)
        config = update_serializer.save(updated_by=request.user)

        # Return data with read serializer (relative URLs)
        return Response(SiteConfigurationSerializer(config, context={'request': request}).data)


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


# =============================================================================
# ActivityLog ViewSet
# =============================================================================

class ActivityLogFilter(filters.FilterSet):
    """Filtres pour les logs d'activite."""

    entity_type = filters.ChoiceFilter(choices=ActivityLog.ENTITY_TYPES)
    action = filters.ChoiceFilter(choices=ActivityLog.ACTION_TYPES)
    visibility = filters.ChoiceFilter(choices=ActivityLog.VISIBILITY_LEVELS)
    site_id = filters.NumberFilter(field_name='related_site__id_site')
    plan_id = filters.NumberFilter(field_name='related_plan__id_pg')
    organisme_id = filters.NumberFilter(field_name='related_organisme__id_organisme')
    user_id = filters.NumberFilter(field_name='related_user__id_role')
    actor_id = filters.NumberFilter(field_name='actor__id_role')
    date_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = ActivityLog
        fields = ['entity_type', 'action', 'visibility']

    def filter_search(self, queryset, name, value):
        """Recherche dans la description et le nom de l'entite."""
        return queryset.filter(
            Q(description__icontains=value) |
            Q(entity_name__icontains=value) |
            Q(actor_name__icontains=value)
        )


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la consultation de l'historique d'activite.

    Filtrage automatique selon le role de l'utilisateur:
    - super_admin: Tout (y compris system et rgpd)
    - admin_og: Activite de son organisme (public + admin)
    - referent: Activite de ses sites/plans (public uniquement)
    - utilisateur: Ses notifications uniquement

    Endpoints:
    - GET /api/activity/ - Liste paginee avec filtres (filtree par role)
    - GET /api/activity/{id}/ - Detail d'une activite
    - GET /api/activity/my_sites/ - Activite sur mes sites
    - GET /api/activity/my_plans/ - Activite sur mes plans
    - GET /api/activity/stats/ - Statistiques
    - GET /api/activity/tabs_counts/ - Compteurs pour les onglets
    """

    queryset = ActivityLog.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_class = ActivityLogFilter
    ordering_fields = ['created_at', 'entity_type', 'action']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityLogDetailSerializer
        return ActivityLogListSerializer

    def get_queryset(self):
        """
        Filtre les activites selon le role de l'utilisateur.
        """
        user = self.request.user
        queryset = ActivityLog.objects.select_related(
            'actor', 'related_site', 'related_plan', 'related_organisme', 'related_user'
        )

        # Super admin voit tout
        if user.is_super_admin():
            return queryset

        # Rédacteur principal voit tout
        if user.is_redacteur_principal():
            return queryset

        # Admin organisme voit public + admin de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(visibility='public') |
                Q(visibility='admin', related_organisme=user.id_organisme)
            )

        # Utilisateur standard : seulement les activites publiques liees a ses sites/plans
        user_site_ids = CorRoleSite.objects.filter(
            id_role=user
        ).values_list('id_site_id', flat=True)

        user_plan_ids = user.plans_referents.values_list('id_pg', flat=True)

        return queryset.filter(
            visibility='public'
        ).filter(
            Q(related_site_id__in=user_site_ids) |
            Q(related_plan_id__in=user_plan_ids) |
            Q(related_user=user) |
            Q(actor=user)
        )

    @action(detail=False, methods=['get'])
    def my_sites(self, request):
        """
        GET /api/activity/my_sites/
        Activite sur les sites de l'utilisateur.
        """
        user = request.user

        # Recuperer les sites de l'utilisateur
        if user.is_super_admin() or user.is_redacteur_principal():
            queryset = self.get_queryset().filter(entity_type='site')
        elif user.is_admin_organisme() and user.id_organisme:
            # Sites de l'organisme
            org_site_ids = CorOgSite.objects.filter(
                uuid_og=user.id_organisme
            ).values_list('id_site_id', flat=True)
            queryset = self.get_queryset().filter(
                entity_type='site',
                related_site_id__in=org_site_ids
            )
        else:
            user_site_ids = CorRoleSite.objects.filter(
                id_role=user
            ).values_list('id_site_id', flat=True)
            queryset = self.get_queryset().filter(
                entity_type='site',
                related_site_id__in=user_site_ids
            )

        # Appliquer les filtres
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_plans(self, request):
        """
        GET /api/activity/my_plans/
        Activite sur les plans de l'utilisateur.
        """
        user = request.user

        if user.is_super_admin() or user.is_redacteur_principal():
            queryset = self.get_queryset().filter(entity_type='plan')
        elif user.is_admin_organisme() and user.id_organisme:
            # Plans lies aux sites de l'organisme
            org_site_ids = CorOgSite.objects.filter(
                uuid_og=user.id_organisme
            ).values_list('id_site_id', flat=True)
            from apps.plans.models import CorSitePg
            org_plan_ids = CorSitePg.objects.filter(
                site_id__in=org_site_ids
            ).values_list('plan_de_gestion_id', flat=True)
            queryset = self.get_queryset().filter(
                entity_type='plan',
                related_plan_id__in=org_plan_ids
            )
        else:
            user_plan_ids = user.plans_referents.values_list('id_pg', flat=True)
            queryset = self.get_queryset().filter(
                entity_type='plan',
                related_plan_id__in=user_plan_ids
            )

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_rights(self, request):
        """
        GET /api/activity/my_rights/
        Activites ou l'utilisateur est le sujet (ses droits ont change).
        """
        user = request.user

        rights_actions = [
            'add_member', 'remove_member', 'add_referent', 'remove_referent',
            'activate', 'deactivate', 'access_granted', 'access_revoked',
            'validation_approved', 'validation_rejected',
        ]

        queryset = ActivityLog.objects.filter(
            related_user=user,
            action__in=rights_actions
        ).select_related(
            'actor', 'related_site', 'related_plan', 'related_organisme'
        ).order_by('-created_at')

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=['get'])
    def rgpd(self, request):
        """
        GET /api/activity/rgpd/
        Activite RGPD (super_admin only).
        """
        if not request.user.is_super_admin():
            return Response(
                {'detail': 'Acces reserve aux super administrateurs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = ActivityLog.objects.filter(
            action__in=['rgpd_request', 'rgpd_cancelled', 'rgpd_anonymized']
        ).select_related('actor', 'related_user')

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def system(self, request):
        """
        GET /api/activity/system/
        Activite systeme (super_admin only).
        """
        if not request.user.is_super_admin():
            return Response(
                {'detail': 'Acces reserve aux super administrateurs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = ActivityLog.objects.filter(
            visibility='system'
        ).select_related('actor', 'related_site', 'related_plan', 'related_organisme')

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def validations(self, request):
        """
        GET /api/activity/validations/
        Activite liee aux validations (admin_og+).
        """
        user = request.user
        if not user.is_admin_organisme():
            return Response(
                {'detail': 'Acces reserve aux administrateurs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = self.get_queryset().filter(
            entity_type='validation'
        )

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/activity/stats/
        Statistiques sur l'activite visible par l'utilisateur.
        """
        queryset = self.get_queryset()

        # Par type d'entite
        by_type = dict(
            queryset
            .values('entity_type')
            .annotate(count=Count('id'))
            .values_list('entity_type', 'count')
        )

        # Par action
        by_action = dict(
            queryset
            .values('action')
            .annotate(count=Count('id'))
            .values_list('action', 'count')
        )

        # Par jour (30 derniers jours)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        by_day = list(
            queryset
            .filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
            .values('date', 'count')
        )

        for item in by_day:
            item['date'] = item['date'].isoformat()

        return Response({
            'total': queryset.count(),
            'by_type': by_type,
            'by_action': by_action,
            'by_day': by_day,
        })

    @action(detail=False, methods=['get'])
    def tabs_counts(self, request):
        """
        GET /api/activity/tabs_counts/
        Compteurs pour les onglets de la page activite.
        """
        user = request.user
        base_queryset = self.get_queryset()

        # Compteur general
        all_count = base_queryset.count()

        # Sites
        if user.is_super_admin() or user.is_redacteur_principal():
            sites_count = base_queryset.filter(entity_type='site').count()
            plans_count = base_queryset.filter(entity_type='plan').count()
        elif user.is_admin_organisme() and user.id_organisme:
            org_site_ids = CorOgSite.objects.filter(
                uuid_og=user.id_organisme
            ).values_list('id_site_id', flat=True)
            sites_count = base_queryset.filter(
                entity_type='site',
                related_site_id__in=org_site_ids
            ).count()
            from apps.plans.models import CorSitePg
            org_plan_ids = CorSitePg.objects.filter(
                site_id__in=org_site_ids
            ).values_list('plan_de_gestion_id', flat=True)
            plans_count = base_queryset.filter(
                entity_type='plan',
                related_plan_id__in=org_plan_ids
            ).count()
        else:
            user_site_ids = CorRoleSite.objects.filter(
                id_role=user
            ).values_list('id_site_id', flat=True)
            sites_count = base_queryset.filter(
                entity_type='site',
                related_site_id__in=user_site_ids
            ).count()
            user_plan_ids = user.plans_referents.values_list('id_pg', flat=True)
            plans_count = base_queryset.filter(
                entity_type='plan',
                related_plan_id__in=user_plan_ids
            ).count()

        # Notifications (non lues)
        notifications_count = Notification.objects.filter(
            recipient=user,
            read=False
        ).count()

        # Mes droits (activites concernant les droits de l'utilisateur)
        rights_actions = [
            'add_member', 'remove_member', 'add_referent', 'remove_referent',
            'activate', 'deactivate', 'access_granted', 'access_revoked',
            'validation_approved', 'validation_rejected',
        ]
        my_rights_count = ActivityLog.objects.filter(
            related_user=user,
            action__in=rights_actions
        ).count()

        result = {
            'all': all_count,
            'my_sites': sites_count,
            'my_plans': plans_count,
            'my_rights': my_rights_count,
            'notifications': notifications_count,
        }

        # Validations (admin_og+)
        if user.is_admin_organisme():
            validations_count = base_queryset.filter(entity_type='validation').count()
            result['validations'] = validations_count

        # System et RGPD (super_admin)
        if user.is_super_admin():
            system_count = ActivityLog.objects.filter(visibility='system').count()
            rgpd_count = ActivityLog.objects.filter(
                action__in=['rgpd_request', 'rgpd_cancelled', 'rgpd_anonymized']
            ).count()
            result['system'] = system_count
            result['rgpd'] = rgpd_count

        return Response(result)


def _orphans_has_global_access(user):
    """Acces global (tous organismes) aux orphelins : super_admin ou redacteur principal."""
    return user.is_super_admin() or user.is_redacteur_principal()


def _orphaned_sites_queryset(user):
    """
    Sites actifs sans aucun utilisateur associe.
    Scope : acces global -> tous ; admin_og -> sites de son organisme.
    """
    from apps.users.models import Site, CorRoleSite, CorOgSite

    sites_with_users = CorRoleSite.objects.values_list('id_site', flat=True)
    qs = (
        Site.objects.filter(active=True)
        .exclude(id_site__in=sites_with_users)
        .order_by('nom_site')
    )

    if _orphans_has_global_access(user):
        return qs

    # admin_og : restreint a son organisme
    if user.id_organisme_id:
        site_ids = CorOgSite.objects.filter(
            uuid_og=user.id_organisme
        ).values_list('id_site', flat=True)
        return qs.filter(id_site__in=site_ids)

    return qs.none()


def _orphaned_plans_queryset(user):
    """
    Plans de gestion sans aucun site associe.
    Un plan orphelin n'ayant plus de site n'est rattachable a aucun organisme :
    reserve a l'acces global (super_admin / redacteur principal).
    """
    from apps.plans.models import PlanGestion, CorSitePg

    if not _orphans_has_global_access(user):
        return PlanGestion.objects.none()

    # Sur CorSitePg, la FK vers le plan est `plan_de_gestion` (col. plan_de_gestion_id).
    plans_with_sites = CorSitePg.objects.values_list('plan_de_gestion', flat=True)
    return (
        PlanGestion.objects.exclude(id_pg__in=plans_with_sites)
        .order_by('nom')
    )


class AdminOrphansView(APIView):
    """
    Sites et plans orphelins (etat persistant, consultable a la demande).

    Remplace l'ancien audit hebdomadaire par email : l'etat orphelin n'est pas un
    evenement recurrent mais un etat que les admins consultent quand ils le souhaitent.

    GET /api/admin/orphans/ ->
        {
          "sites": [{ "id_site", "nom_site", "slug", "organismes": [...] }],
          "plans": [{ "id_pg", "nom", "slug" }],
          "sites_count": int,
          "plans_count": int
        }

    Scope par role :
    - super_admin / redacteur principal : tous les sites + tous les plans orphelins
    - admin_og : sites orphelins de son organisme uniquement (pas de plans orphelins)
    """
    permission_classes = [IsAdminOrganisme]

    def get(self, request):
        from apps.users.models import CorOgSite

        user = request.user

        sites = list(_orphaned_sites_queryset(user))
        plans = list(_orphaned_plans_queryset(user))

        # Organismes gestionnaires par site (pour affichage)
        site_ids = [s.id_site for s in sites]
        orgs_by_site = {}
        if site_ids:
            for cor in CorOgSite.objects.filter(
                id_site__in=site_ids
            ).select_related('uuid_og'):
                orgs_by_site.setdefault(cor.id_site_id, []).append(
                    cor.uuid_og.nom_organisme
                )

        sites_data = [
            {
                'id_site': s.id_site,
                'nom_site': s.nom_site,
                'slug': s.slug,
                'organismes': orgs_by_site.get(s.id_site, []),
            }
            for s in sites
        ]
        plans_data = [
            {
                'id_pg': p.id_pg,
                'nom': p.nom,
                'slug': p.slug,
            }
            for p in plans
        ]

        return Response({
            'sites': sites_data,
            'plans': plans_data,
            'sites_count': len(sites_data),
            'plans_count': len(plans_data),
        })


class AdminOrphansCountsView(APIView):
    """
    Compteurs legers des orphelins (pour le badge de navigation admin).

    GET /api/admin/orphans/counts/ -> { "sites_count", "plans_count", "total" }
    """
    permission_classes = [IsAdminOrganisme]

    def get(self, request):
        user = request.user
        sites_count = _orphaned_sites_queryset(user).count()
        plans_count = _orphaned_plans_queryset(user).count()
        return Response({
            'sites_count': sites_count,
            'plans_count': plans_count,
            'total': sites_count + plans_count,
        })


# =============================================================================
# Logs applicatifs (#456) — consultation par le super_admin
# =============================================================================

# Fichiers de logs autorisés à la consultation (cf. config LOGGING).
_ALLOWED_LOG_FILES = {'django.log', 'error.log', 'audit.log'}
_MAX_LOG_LINES = 1000


def _resolve_log_file(filename):
    """Résout un nom de fichier de log de façon sûre (anti-traversée de chemin).

    N'autorise que les fichiers connus (et leurs variantes de rotation
    `name.log.N`), situés directement dans LOG_DIR.
    Retourne le chemin absolu ou None si invalide/inexistant.
    """
    import os
    from django.conf import settings
    if not filename or '/' in filename or '\\' in filename or filename.startswith('.'):
        return None
    base = filename.split('.log')[0] + '.log'
    if base not in _ALLOWED_LOG_FILES:
        return None
    log_dir = os.path.realpath(settings.LOG_DIR)
    path = os.path.realpath(os.path.join(log_dir, filename))
    # Le chemin résolu doit rester dans LOG_DIR et le fichier doit exister.
    if os.path.commonpath([log_dir, path]) != log_dir or not os.path.isfile(path):
        return None
    return path


class AdminLogsView(APIView):
    """
    Consultation des fichiers de logs applicatifs (super_admin uniquement).

    - GET /api/admin/logs/                         → liste des fichiers disponibles
    - GET /api/admin/logs/?file=error.log&lines=300&level=ERROR
                                                   → N dernières lignes (filtre niveau optionnel)
    - GET /api/admin/logs/?file=error.log&download=1 → téléchargement du fichier
    """

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        import os
        from django.conf import settings
        from django.http import FileResponse

        filename = request.query_params.get('file')

        # Sans `file` : lister les fichiers de logs disponibles.
        if not filename:
            log_dir = settings.LOG_DIR
            files = []
            try:
                for name in sorted(os.listdir(log_dir)):
                    base = name.split('.log')[0] + '.log'
                    if base in _ALLOWED_LOG_FILES and os.path.isfile(os.path.join(log_dir, name)):
                        size = os.path.getsize(os.path.join(log_dir, name))
                        files.append({'name': name, 'size': size})
            except FileNotFoundError:
                pass
            return Response({'log_dir': log_dir, 'files': files})

        path = _resolve_log_file(filename)
        if not path:
            return Response({'error': 'Fichier de log introuvable ou non autorisé.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Téléchargement du fichier brut.
        if request.query_params.get('download') in ('1', 'true', 'yes'):
            return FileResponse(open(path, 'rb'), as_attachment=True, filename=os.path.basename(path))

        # Lecture des N dernières lignes (+ filtre par niveau optionnel).
        try:
            lines_param = int(request.query_params.get('lines', 300))
        except (TypeError, ValueError):
            lines_param = 300
        n = max(1, min(lines_param, _MAX_LOG_LINES))

        level = (request.query_params.get('level') or '').strip().upper()
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.read().splitlines()
        except OSError:
            return Response({'error': "Impossible de lire le fichier de log."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if level:
            all_lines = [ln for ln in all_lines if level in ln.upper()]

        tail = all_lines[-n:]
        return Response({
            'file': os.path.basename(path),
            'lines': tail,
            'returned': len(tail),
            'total': len(all_lines),
            'truncated': len(all_lines) > len(tail),
        })
