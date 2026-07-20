"""
Vues API REST pour les Suivis/Inventaires (standalone).
"""
from django.db.models import Q

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models_operations import SuiviInventaire
from .models import PlanGestion
from apps.users.permissions import IsReferent
from apps.users.pagination import UsersPagination
from .permissions import CanModifyOnlyDraftPlan
from .serializers_suivis import (
    SuiviInventaireListSerializer,
    SuiviInventaireDetailSerializer,
    SuiviInventaireCreateSerializer,
)
from .filters_suivis import SuiviInventaireFilter


class SuiviInventaireViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Suivis/Inventaires (standalone).

    Endpoints:
    - GET /api/inventaires/suivis/ - Liste
    - GET /api/inventaires/suivis/{id}/ - Détail
    - POST /api/inventaires/suivis/ - Créer
    - PATCH /api/inventaires/suivis/{id}/ - Modifier
    - DELETE /api/inventaires/suivis/{id}/ - Supprimer
    """

    queryset = SuiviInventaire.objects.select_related(
        'id_statut', 'id_type_action',
        'id_pg', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('operations', 'protocoles')

    permission_classes = [permissions.IsAuthenticated, CanModifyOnlyDraftPlan]
    pagination_class = UsersPagination

    def get_plan_for_payload(self, data):
        """Pour le check draft à la création."""
        plan_id = data.get('id_pg')
        if not plan_id:
            return None
        try:
            return PlanGestion.objects.only('statut').get(pk=plan_id)
        except PlanGestion.DoesNotExist:
            return None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SuiviInventaireFilter
    search_fields = ['intitule', 'commentaires']
    ordering_fields = ['intitule', 'date_lancement_suivi', 'date_ajout']
    ordering = ['-date_ajout']

    def get_serializer_class(self):
        if self.action == 'list':
            return SuiviInventaireListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SuiviInventaireCreateSerializer
        return SuiviInventaireDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            # Admin organisme sees suivis created by users in their org
            # and suivis linked to plans on their org's sites
            return queryset.filter(
                Q(id_utilisateur_ajout__id_organisme=user.id_organisme) |
                Q(id_pg__sites__site__corogsite__uuid_og=user.id_organisme)
            ).distinct()

        # Regular users see their own suivis + suivis linked to their sites/plans
        return queryset.filter(
            Q(id_utilisateur_ajout=user) |
            Q(id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_pg__referents=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)
