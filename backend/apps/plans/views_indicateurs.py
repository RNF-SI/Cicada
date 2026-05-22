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

from django.db import transaction

from .models_indicateurs import (
    Indicateur, Metrique, Mesure,
    CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
)
from .models_enjeux import NiveauExigence, ResultatAttendu
from .models import CorRolePlan
from apps.users.permissions import IsReferent
from .permissions import CanModifyOnlyDraftPlan
from .reorder import do_reorder
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

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = IndicateurFilter
    search_fields = ['nom_indicateur', 'description']
    ordering_fields = ['nom_indicateur', 'date_ajout', 'date_maj', 'id_indicateur']
    ordering = ['id_indicateur']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via le parent (NE ou RA)."""
        ne_id = data.get('id_ne')
        if ne_id:
            try:
                return NiveauExigence.objects.select_related(
                    'id_olt__id_enjeu'
                ).get(pk=ne_id).get_plan_de_gestion()
            except NiveauExigence.DoesNotExist:
                return None
        ra_id = data.get('id_resultat_attendu')
        if ra_id:
            try:
                return ResultatAttendu.objects.get(pk=ra_id).get_plan_de_gestion()
            except ResultatAttendu.DoesNotExist:
                return None
        return None

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

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme)
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_ne__id_olt__id_enjeu__id_pg__statut='valide') |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les indicateurs d'un parent NE ou RA (#249/#261).

        Cas spécial : un indicateur a deux parents possibles (id_ne XOR
        id_resultat_attendu). Le payload doit donc inclure `parent_type`.

        Payload:
            {
                "parent_type": "ne" | "ra",
                "parent_id": <id_ne|id_ra>,
                "ordered_ids": [id1, id2, ...]
            }
        """
        parent_type = request.data.get('parent_type')
        if parent_type not in ('ne', 'ra'):
            return Response(
                {"detail": "Le champ 'parent_type' doit valoir 'ne' ou 'ra'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parent_field = 'id_ne' if parent_type == 'ne' else 'id_resultat_attendu'
        return do_reorder(self, request, parent_filter=parent_field)

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """
        Déplace un indicateur entre niveaux d'exigence (NE) ou résultats
        attendus (RA) — #261.

        Payload : {"new_parent_type": "ne"|"ra", "new_parent_id": <int>, "position": <int>}

        Garde-fous :
        - Le nouveau parent doit exister et être dans le même plan que l'ancien.
        - Le plan doit être en brouillon (verrou #248).
        - Renumérote les siblings dans le nouveau parent.
        """
        indicateur = self.get_object()
        new_parent_type = request.data.get('new_parent_type')
        new_parent_id = request.data.get('new_parent_id')
        position = request.data.get('position', 0)

        if new_parent_type not in ('ne', 'ra') or new_parent_id is None:
            return Response(
                {"detail": "Payload invalide : 'new_parent_type' ('ne'|'ra') et 'new_parent_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_parent_id = int(new_parent_id)
            position = int(position)
        except (TypeError, ValueError):
            return Response(
                {"detail": "'new_parent_id' et 'position' doivent être des entiers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if new_parent_type == 'ne':
                new_parent = NiveauExigence.objects.get(pk=new_parent_id)
            else:
                new_parent = ResultatAttendu.objects.get(pk=new_parent_id)
        except (NiveauExigence.DoesNotExist, ResultatAttendu.DoesNotExist):
            return Response(
                {"detail": "Parent introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Garde : même plan que la source
        source_plan = indicateur.get_plan_de_gestion()
        target_plan = new_parent.get_plan_de_gestion()
        if source_plan and target_plan and source_plan.pk != target_plan.pk:
            return Response(
                {"detail": "Déplacement entre plans interdit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verrou #248 — plan doit être en statut éditable (draft uniquement)
        if target_plan and target_plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            return Response(
                {"detail": "Modification interdite hors brouillon."},
                status=status.HTTP_403_FORBIDDEN,
            )

        filter_kwargs = (
            {'id_ne': new_parent.pk} if new_parent_type == 'ne'
            else {'id_resultat_attendu': new_parent.pk}
        )

        with transaction.atomic():
            if new_parent_type == 'ne':
                indicateur.id_ne = new_parent
                indicateur.id_resultat_attendu = None
            else:
                indicateur.id_ne = None
                indicateur.id_resultat_attendu = new_parent
            indicateur.ordre = position
            indicateur.save()

            # Renumérotation des siblings dans le nouveau parent
            siblings = (
                Indicateur.objects
                .filter(**filter_kwargs)
                .exclude(pk=indicateur.pk)
                .order_by('ordre', 'id_indicateur')
            )
            for idx, sib in enumerate(siblings):
                new_pos = idx if idx < position else idx + 1
                if sib.ordre != new_pos:
                    sib.ordre = new_pos
                    sib.save(update_fields=['ordre'])

        serializer = self.get_serializer(indicateur)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplique un indicateur (avec ses métriques et liens taxonomiques)
        sur un ou plusieurs niveaux d'exigence ou résultats attendus cibles
        (#262).

        POST /api/plans/indicateurs/{id}/duplicate/
        Body: { "ne_ids": [int], "ra_ids": [int] }

        Retourne la liste des IDs des indicateurs créés. Le clone porte le
        même nom (suffixe « (copie) ») et reprend la description, les
        métriques (avec leurs seuils de scores) et les liens taxon/
        habitat/géologie. Les mesures (données chiffrées dans le temps) ne
        sont **pas** copiées : elles restent associées à l'indicateur
        d'origine.
        """
        source = self.get_object()
        ne_ids = request.data.get('ne_ids') or []
        ra_ids = request.data.get('ra_ids') or []

        if not isinstance(ne_ids, list) or not isinstance(ra_ids, list):
            return Response(
                {'error': "ne_ids et ra_ids doivent être des listes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ne_ids and not ra_ids:
            return Response(
                {'error': "Au moins un niveau d'exigence ou résultat attendu cible est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Le get_queryset garantit déjà que la source est accessible à
        # l'utilisateur. Pour les cibles, on vérifie qu'elles appartiennent
        # à un plan en draft accessible (CanModifyOnlyDraftPlan ne couvre
        # pas explicitement ce cas — on contrôle ici).
        targets_ne = list(NiveauExigence.objects.filter(pk__in=ne_ids).select_related('id_olt__id_enjeu__id_pg'))
        targets_ra = list(ResultatAttendu.objects.filter(pk__in=ra_ids).select_related('id_oo'))

        for ne in targets_ne:
            plan = ne.get_plan_de_gestion()
            if plan is None or plan.statut != 'draft':
                return Response(
                    {'error': f"Le niveau d'exigence {ne.id_ne} n'est pas dans un plan en brouillon."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        for ra in targets_ra:
            plan = ra.get_plan_de_gestion()
            if plan is None or plan.statut != 'draft':
                return Response(
                    {'error': f"Le résultat attendu {ra.id_ra} n'est pas dans un plan en brouillon."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        with transaction.atomic():
            created = []
            for ne in targets_ne:
                created.append(self._clone_indicateur(source, id_ne=ne, id_resultat_attendu=None, user=request.user))
            for ra in targets_ra:
                created.append(self._clone_indicateur(source, id_ne=None, id_resultat_attendu=ra, user=request.user))

        return Response({
            'created_ids': [ind.id_indicateur for ind in created],
            'count': len(created),
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _clone_indicateur(source: Indicateur, id_ne, id_resultat_attendu, user) -> Indicateur:
        """
        Clone un indicateur sur un nouveau parent. Copie : champs simples,
        métriques (avec seuils de scores), liens taxonomiques. Ne copie
        PAS les mesures (données dans le temps qui restent rattachées
        à l'instance d'origine).
        """
        new_ind = Indicateur.objects.create(
            id_ne=id_ne,
            id_resultat_attendu=id_resultat_attendu,
            nom_indicateur=f"{source.nom_indicateur} (copie)",
            description=source.description,
            type_indicateur=source.type_indicateur,
            est_standardise=source.est_standardise,
            id_utilisateur_ajout=user,
        )
        # Cloner les métriques
        for met in source.metriques.all():
            Metrique.objects.create(
                id_indicateur=new_ind,
                nom_metrique=met.nom_metrique,
                description=met.description,
                type_metrique=met.type_metrique,
                unite=met.unite,
                ponderation=met.ponderation,
                etat_reference=met.etat_reference,
                score_1_inf=met.score_1_inf, score_1_sup=met.score_1_sup,
                score_2_inf=met.score_2_inf, score_2_sup=met.score_2_sup,
                score_3_inf=met.score_3_inf, score_3_sup=met.score_3_sup,
                score_4_inf=met.score_4_inf, score_4_sup=met.score_4_sup,
                score_5_inf=met.score_5_inf, score_5_sup=met.score_5_sup,
                id_utilisateur_ajout=user,
            )
        # Cloner les liens taxonomiques
        for cor in source.taxons.all():
            CorIndicateurTaxon.objects.create(
                id_indicateur=new_ind,
                cd_nom=cor.cd_nom,
                nom_complet=cor.nom_complet,
                nom_vern=cor.nom_vern,
            )
        for cor in source.habitats.all():
            CorIndicateurHabitat.objects.create(
                id_indicateur=new_ind,
                cd_hab=cor.cd_hab,
                lb_hab_fr=cor.lb_hab_fr,
            )
        for cor in source.geologies.all():
            CorIndicateurGeologie.objects.create(
                id_indicateur=new_ind,
                id_inpg=cor.id_inpg,
                nom=cor.nom,
            )
        return new_ind


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

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MetriqueFilter
    search_fields = ['nom_metrique', 'description']
    ordering_fields = ['nom_metrique', 'date_ajout', 'date_maj', 'id_metrique']
    ordering = ['id_metrique']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via l'indicateur parent."""
        indicateur_id = data.get('id_indicateur')
        if not indicateur_id:
            return None
        try:
            return Indicateur.objects.select_related(
                'id_ne__id_olt__id_enjeu', 'id_resultat_attendu'
            ).get(pk=indicateur_id).get_plan_de_gestion()
        except Indicateur.DoesNotExist:
            return None

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

        if user.is_redacteur_principal():
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

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MesureFilter
    search_fields = ['valeur', 'commentaire']
    ordering_fields = ['date_mesure', 'date_ajout', 'date_maj']
    ordering = ['-date_mesure', '-date_ajout']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via la métrique parent."""
        metrique_id = data.get('id_metrique')
        if not metrique_id:
            return None
        try:
            return Metrique.objects.select_related(
                'id_indicateur__id_ne__id_olt__id_enjeu',
                'id_indicateur__id_resultat_attendu',
            ).get(pk=metrique_id).get_plan_de_gestion()
        except Metrique.DoesNotExist:
            return None

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
