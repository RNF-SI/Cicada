"""
Vues API REST pour les Opérations (Actions).
"""
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from collections import defaultdict

from .models_operations import Operation, CorOperationMetrique, OperationAnnee, OperationAnneeOrganisme, FinanceOperation
from .models_indicateurs import Indicateur, Metrique
from .models import PlanGestion, CorRolePlan
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
        'id_priorite', 'id_type_action', 'id_utilisateur_ajout', 'id_utilisateur_maj',
    ).prefetch_related(
        Prefetch('metriques', queryset=Metrique.objects.select_related(
            'id_indicateur',
            'id_indicateur__id_ne__id_olt__id_enjeu',
            'id_indicateur__id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu',
        )),
        'sites',
        Prefetch('operation_annees', queryset=OperationAnnee.objects.prefetch_related(
            Prefetch('organismes', queryset=OperationAnneeOrganisme.objects.select_related('id_organisme'))
        )),
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

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide')
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
        operations = self.get_queryset().filter(metriques__id_indicateur=indicateur).distinct()
        return Response({
            'indicateur_id': int(indicateur_id),
            'indicateur_nom': indicateur.nom_indicateur,
            'operations': OperationSerializer(operations, many=True).data,
            'total': operations.count()
        })

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """
        Récupérer les opérations d'un plan, groupées par type d'action.

        GET /api/plans/operations/by-plan/{plan_id}/
        """
        plan = get_object_or_404(PlanGestion, id_pg=plan_id)
        operations = self.get_queryset().filter(
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
            Q(metriques__id_indicateur__id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu__id_pg=plan)
        ).distinct()

        grouped = defaultdict(list)
        for op in operations:
            key = op.id_type_action.label if op.id_type_action else 'Autre'
            grouped[key].append(OperationListSerializer(op).data)

        groups = [
            {'type_action': key, 'operations': ops, 'count': len(ops)}
            for key, ops in sorted(grouped.items())
        ]

        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'groups': groups,
            'total': operations.count()
        })

    @action(detail=True, methods=['post'], url_path='add-metrique')
    def add_metrique(self, request, pk=None):
        """
        Ajouter une métrique à une opération (lien M2M, idempotent).

        POST /api/plans/operations/{id}/add-metrique/
        Body: { "metrique_id": 123 }
        """
        operation = self.get_object()
        metrique_id = request.data.get('metrique_id')
        if not metrique_id:
            return Response(
                {'detail': 'metrique_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        metrique = get_object_or_404(Metrique, id_metrique=metrique_id)
        _, created = CorOperationMetrique.objects.get_or_create(
            id_operation=operation, id_metrique=metrique
        )
        # Clear prefetch cache so serializer sees the updated M2M
        operation = Operation.objects.get(pk=operation.pk)
        return Response(
            OperationSerializer(operation).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='remove-metrique')
    def remove_metrique(self, request, pk=None):
        """
        Retirer une métrique d'une opération (lien M2M, idempotent).

        POST /api/plans/operations/{id}/remove-metrique/
        Body: { "metrique_id": 123 }
        """
        operation = self.get_object()
        metrique_id = request.data.get('metrique_id')
        if not metrique_id:
            return Response(
                {'detail': 'metrique_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        CorOperationMetrique.objects.filter(
            id_operation=operation, id_metrique_id=metrique_id
        ).delete()
        # Clear prefetch cache so serializer sees the updated M2M
        operation = Operation.objects.get(pk=operation.pk)
        return Response(OperationSerializer(operation).data)
