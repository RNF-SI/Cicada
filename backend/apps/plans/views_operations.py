"""
Vues API REST pour les Opérations (Actions).
"""
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models_operations import Operation, OperationAnnee, FinanceOperation
from .models_indicateurs import Indicateur
from apps.users.permissions import IsReferent
from .serializers_operations import (
    OperationSerializer, OperationListSerializer, OperationCreateSerializer,
)
from .filters_operations import OperationFilter


class OperationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Opérations (Actions).

    Endpoints:
    - GET /api/plans/operations/ - Liste
    - GET /api/plans/operations/{id}/ - Détail
    - POST /api/plans/operations/ - Créer
    - PATCH /api/plans/operations/{id}/ - Modifier
    - DELETE /api/plans/operations/{id}/ - Supprimer
    - GET /api/plans/operations/by-indicateur/{indicateur_id}/ - Par indicateur
    """

    queryset = Operation.objects.select_related(
        'id_priorite', 'id_type_action', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'indicateurs', 'sites', 'metriques',
        Prefetch('operation_annees', queryset=OperationAnnee.objects.select_related('id_operateur')),
        Prefetch('finances', queryset=FinanceOperation.objects.select_related('id_categorie')),
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OperationFilter
    search_fields = ['libelle', 'description', 'code_operation']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'annee_min']
    ordering = ['libelle']

    def get_serializer_class(self):
        if self.action == 'list':
            return OperationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OperationCreateSerializer
        return OperationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                indicateurs__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(indicateurs__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(indicateurs__id_ne__id_olt__id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(
            indicateurs__id_ne__id_olt__id_enjeu__id_pg__statut='valide'
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-indicateur/(?P<indicateur_id>\d+)')
    def by_indicateur(self, request, indicateur_id=None):
        """
        Récupérer les opérations d'un indicateur.

        GET /api/plans/operations/by-indicateur/{indicateur_id}/
        """
        indicateur = get_object_or_404(Indicateur, id_indicateur=indicateur_id)
        operations = self.get_queryset().filter(indicateurs=indicateur)
        return Response({
            'indicateur_id': int(indicateur_id),
            'indicateur_nom': indicateur.nom_indicateur,
            'operations': OperationSerializer(operations, many=True).data,
            'total': operations.count()
        })
