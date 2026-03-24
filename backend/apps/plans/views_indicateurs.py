"""
Vues API REST pour les Indicateurs, Métriques et Mesures.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models_indicateurs import Indicateur, Metrique, Mesure
from .models_enjeux import NiveauExigence, ResultatAttendu
from .models import CorRolePlan
from apps.users.permissions import IsReferent
from .serializers_indicateurs import (
    IndicateurSerializer, IndicateurListSerializer, IndicateurCreateSerializer,
    MetriqueSerializer, MetriqueListSerializer, MetriqueCreateSerializer,
    MesureSerializer, MesureCreateSerializer,
)
from .filters_indicateurs import IndicateurFilter, MetriqueFilter, MesureFilter


class IndicateurViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Indicateurs.

    Endpoints:
    - GET /api/plans/indicateurs/ - Liste
    - GET /api/plans/indicateurs/{id}/ - Détail
    - POST /api/plans/indicateurs/ - Créer
    - PATCH /api/plans/indicateurs/{id}/ - Modifier
    - DELETE /api/plans/indicateurs/{id}/ - Supprimer
    - GET /api/plans/indicateurs/by-ne/{ne_id}/ - Par niveau d'exigence
    """

    queryset = Indicateur.objects.select_related(
        'id_ne', 'id_resultat_attendu', 'type_indicateur',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'metriques', 'metriques__type_metrique', 'metriques__id_utilisateur_ajout',
        'metriques__mesures', 'metriques__mesures__id_utilisateur_ajout',
        'taxons', 'habitats', 'geologies',
        'metriques__operations', 'metriques__operations__id_priorite', 'metriques__operations__id_utilisateur_ajout'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = IndicateurFilter
    search_fields = ['nom_indicateur', 'description']
    ordering_fields = ['nom_indicateur', 'date_ajout', 'date_maj']
    ordering = ['nom_indicateur']

    def get_serializer_class(self):
        if self.action == 'list':
            return IndicateurListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return IndicateurCreateSerializer
        return IndicateurSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme)
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_ne__id_olt__id_enjeu__id_pg__statut='valide') |
            Q(id_resultat_attendu__id_oo__id_pression__id_facteur_influence__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-ne/(?P<ne_id>\d+)')
    def by_ne(self, request, ne_id=None):
        """
        Récupérer les indicateurs d'un niveau d'exigence.

        GET /api/plans/indicateurs/by-ne/{ne_id}/
        """
        ne = get_object_or_404(NiveauExigence, id_ne=ne_id)
        indicateurs = self.get_queryset().filter(id_ne=ne)
        return Response({
            'ne_id': int(ne_id),
            'ne_libelle': ne.libelle,
            'indicateurs': IndicateurSerializer(indicateurs, many=True).data,
            'total': indicateurs.count()
        })

    @action(detail=False, methods=['get'], url_path=r'by-ra/(?P<ra_id>\d+)')
    def by_resultat_attendu(self, request, ra_id=None):
        """
        Récupérer les indicateurs d'un résultat attendu.

        GET /api/plans/indicateurs/by-ra/{ra_id}/
        """
        ra = get_object_or_404(ResultatAttendu, id_ra=ra_id)
        indicateurs = self.get_queryset().filter(id_resultat_attendu=ra)
        return Response({
            'ra_id': int(ra_id),
            'ra_libelle': ra.libelle,
            'indicateurs': IndicateurSerializer(indicateurs, many=True).data,
            'total': indicateurs.count()
        })


class MetriqueViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Métriques.

    Endpoints:
    - GET /api/plans/metriques/ - Liste
    - GET /api/plans/metriques/{id}/ - Détail
    - POST /api/plans/metriques/ - Créer
    - PATCH /api/plans/metriques/{id}/ - Modifier
    - DELETE /api/plans/metriques/{id}/ - Supprimer
    - GET /api/plans/metriques/by-indicateur/{indicateur_id}/ - Par indicateur
    """

    queryset = Metrique.objects.select_related(
        'id_indicateur', 'type_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('mesures', 'mesures__id_utilisateur_ajout')

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MetriqueFilter
    search_fields = ['nom_metrique', 'description']
    ordering_fields = ['nom_metrique', 'date_ajout', 'date_maj']
    ordering = ['nom_metrique']

    def get_serializer_class(self):
        if self.action == 'list':
            return MetriqueListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MetriqueCreateSerializer
        return MetriqueSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-indicateur/(?P<indicateur_id>\d+)')
    def by_indicateur(self, request, indicateur_id=None):
        """
        Récupérer les métriques d'un indicateur.

        GET /api/plans/metriques/by-indicateur/{indicateur_id}/
        """
        indicateur = get_object_or_404(Indicateur, id_indicateur=indicateur_id)
        metriques = self.get_queryset().filter(id_indicateur=indicateur)
        return Response({
            'indicateur_id': int(indicateur_id),
            'indicateur_nom': indicateur.nom_indicateur,
            'metriques': MetriqueSerializer(metriques, many=True).data,
            'total': metriques.count()
        })


class MesureViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Mesures.

    Endpoints:
    - GET /api/plans/mesures/ - Liste
    - GET /api/plans/mesures/{id}/ - Détail
    - POST /api/plans/mesures/ - Créer
    - PATCH /api/plans/mesures/{id}/ - Modifier
    - DELETE /api/plans/mesures/{id}/ - Supprimer
    - GET /api/plans/mesures/by-metrique/{metrique_id}/ - Par métrique
    """

    queryset = Mesure.objects.select_related(
        'id_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MesureFilter
    search_fields = ['valeur', 'commentaire']
    ordering_fields = ['date_mesure', 'date_ajout', 'date_maj']
    ordering = ['-date_mesure', '-date_ajout']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MesureCreateSerializer
        return MesureSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-metrique/(?P<metrique_id>\d+)')
    def by_metrique(self, request, metrique_id=None):
        """
        Récupérer les mesures d'une métrique.

        GET /api/plans/mesures/by-metrique/{metrique_id}/
        """
        metrique = get_object_or_404(Metrique, id_metrique=metrique_id)
        mesures = self.get_queryset().filter(id_metrique=metrique)
        return Response({
            'metrique_id': int(metrique_id),
            'metrique_nom': metrique.nom_metrique,
            'mesures': MesureSerializer(mesures, many=True).data,
            'total': mesures.count()
        })
