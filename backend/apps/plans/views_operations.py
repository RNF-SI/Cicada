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

from .models_operations import (
    Operation, CorOperationMetrique, OperationAnnee, OperationAnneeOrganisme,
    FinanceOperation, RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
    OperationRealisationGlobale,
)
from .models_indicateurs import Indicateur, Metrique
from .models import PlanGestion, CorRolePlan
from apps.core.models import Nomenclature
from apps.users.permissions import IsReferent
from .permissions import CanModifyOnlyDraftPlan
from .reorder import do_reorder
from .serializers_operations import (
    OperationSerializer, OperationListSerializer, OperationCreateSerializer,
    RealisationOperationAnneeSerializer, RealisationOperationAnneeOrganismeSerializer,
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
            'id_indicateur__id_resultat_attendu__id_oo',
        )),
        'sites',
        Prefetch('operation_annees', queryset=OperationAnnee.objects.select_related(
            'realisation', 'realisation__id_niveau_realisation',
        ).prefetch_related(
            Prefetch(
                'organismes',
                queryset=OperationAnneeOrganisme.objects.select_related(
                    'id_organisme', 'realisation',
                ),
            ),
        )),
        Prefetch('finances', queryset=FinanceOperation.objects.select_related('id_categorie')),
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OperationFilter
    search_fields = ['libelle', 'description', 'code_operation']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'annee_min', 'id_operation']
    ordering = ['id_operation']

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

        # Une opération peut être rattachée au plan via :
        # - une de ses métriques (chaîne metriques→indicateur→ne→olt→enjeu→pg)
        # - son suivi/inventaire (id_suivi→SuiviInventaire.id_pg)
        # On inclut les deux chemins pour qu'une opération créée avec un suivi
        # mais sans métrique reste visible à son créateur. Le créateur d'une
        # opération orpheline (sans plan résolu) la voit toujours.
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                # #367 — action rattachée directement à un indicateur (sans métrique)
                Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_suivi__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_utilisateur_ajout=user)
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide') |
            # #367 — action rattachée directement à un indicateur (sans métrique)
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide') |
            Q(id_suivi__id_pg__in=user_plan_ids) |
            Q(id_suivi__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_suivi__id_pg__statut='valide') |
            Q(id_utilisateur_ajout=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    def get_plan_for_payload(self, data):
        """
        Pour le check draft à la création (#248) : remonte au plan via le
        suivi (id_suivi → SuiviInventaire.id_pg) ou via une métrique
        (metrique_ids[0] → Indicateur → … → plan).
        """
        suivi_id = data.get('id_suivi')
        if suivi_id:
            from .models_operations import SuiviInventaire
            try:
                return SuiviInventaire.objects.only('id_pg').get(pk=suivi_id).id_pg
            except SuiviInventaire.DoesNotExist:
                return None
        metrique_ids = data.get('metrique_ids') or []
        if metrique_ids:
            try:
                metrique = Metrique.objects.select_related(
                    'id_indicateur__id_ne__id_olt__id_enjeu__id_pg',
                    'id_indicateur__id_resultat_attendu__id_oo',
                ).get(pk=metrique_ids[0])
            except Metrique.DoesNotExist:
                return None
            return metrique.get_plan_de_gestion()
        # #367 — action rattachée directement à un indicateur (sans métrique)
        indicateur_id = data.get('id_indicateur')
        if indicateur_id:
            try:
                return Indicateur.objects.select_related(
                    'id_ne__id_olt__id_enjeu__id_pg',
                    'id_resultat_attendu__id_oo',
                ).get(pk=indicateur_id).get_plan_de_gestion()
            except Indicateur.DoesNotExist:
                return None
        return None

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les opérations d'une métrique (#249/#261).

        L'ordre porte sur les opérations rattachées à une métrique via la M2M
        `CorOperationMetrique`. Le payload doit indiquer la métrique parent.

        Payload: { "parent_id": <id_metrique>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(
            self,
            request,
            parent_filter=lambda pid, _req: Q(metriques=pid),
        )

    @action(detail=False, methods=['get'], url_path=r'by-indicateur/(?P<indicateur_id>\d+)')
    def by_indicateur(self, request, indicateur_id=None):
        """
        Récupérer les opérations d'un indicateur.

        GET /api/plans/operations/by-indicateur/{indicateur_id}/
        """
        indicateur = get_object_or_404(Indicateur, id_indicateur=indicateur_id)
        operations = self.get_queryset().filter(
            # via une métrique de l'indicateur, ou rattachée directement (#367)
            Q(metriques__id_indicateur=indicateur) | Q(id_indicateur=indicateur)
        ).distinct()
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
            Q(metriques__id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg=plan) |
            # #367 — actions rattachées directement à un indicateur (sans métrique)
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
            Q(id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg=plan)
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

    @action(detail=True, methods=['post'], url_path='create-indicator')
    def create_indicator(self, request, pk=None):
        """
        Crée un nouvel indicateur de réponse + sa métrique, rattaché au même
        NE/RA qu'une métrique déjà liée à l'opération, et lie le tout à l'op.

        POST /api/plans/operations/{id}/create-indicator/
        Body: {
            "nom_indicateur": str (required),
            "nom_metrique": str (optional, vide par défaut),
            "type_metrique_id": int (optional),
            "valeur_cible": str (optional, écrit dans Metrique.etat_reference)
        }
        """
        operation = self.get_object()

        nom_indicateur = (request.data.get('nom_indicateur') or '').strip()
        if not nom_indicateur:
            return Response(
                {'detail': "nom_indicateur est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Trouver le parent NE/RA depuis la 1ère métrique de l'opération.
        first_met = (
            operation.metriques
            .select_related('id_indicateur__id_ne', 'id_indicateur__id_resultat_attendu')
            .first()
        )
        if first_met:
            parent_ind = first_met.id_indicateur
        elif operation.id_indicateur_id:
            # #367 — action rattachée directement à un indicateur (sans métrique) :
            # on en hérite le parent NE/RA pour y rattacher l'indicateur de réponse.
            parent_ind = operation.id_indicateur
        else:
            return Response(
                {'detail': "L'opération doit être rattachée à au moins une métrique ou à un "
                           "indicateur pour créer un nouvel indicateur de réponse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupère le type indicateur "réponse" si possible, sinon réutilise celui du parent.
        from apps.core.models import Nomenclature
        type_ind_reponse = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_INDICATEUR', mnemonique='REPONSE',
        ).first()

        new_ind = Indicateur.objects.create(
            nom_indicateur=nom_indicateur,
            id_ne=parent_ind.id_ne,
            id_resultat_attendu=parent_ind.id_resultat_attendu,
            type_indicateur=type_ind_reponse or parent_ind.type_indicateur,
            id_utilisateur_ajout=request.user,
        )

        type_met_id = request.data.get('type_metrique_id')
        # #398 — ne PAS retomber sur `nom_indicateur` : un indicateur de réponse
        # créé sans métrique nommée doit rester « sans métrique » (sinon le nom
        # de l'indicateur s'affiche à tort comme une métrique sous l'action).
        new_met = Metrique.objects.create(
            id_indicateur=new_ind,
            nom_metrique=(request.data.get('nom_metrique') or '').strip(),
            type_metrique_id=type_met_id if type_met_id else None,
            etat_reference=request.data.get('valeur_cible') or '',
            id_utilisateur_ajout=request.user,
        )

        CorOperationMetrique.objects.create(
            id_operation=operation, id_metrique=new_met,
        )

        return Response({
            'id_metrique': new_met.id_metrique,
            'id_indicateur': new_ind.id_indicateur,
            'nom_indicateur': new_ind.nom_indicateur,
            'nom_metrique': new_met.nom_metrique,
            'etat_reference': new_met.etat_reference,
            'type_metrique': new_met.type_metrique_id,
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# Suivi de réalisation des opérations (Phase 1)
# =============================================================================


def _scope_realisation_queryset(queryset, user, op_path):
    """
    Scope un queryset de réalisations selon le rôle de l'utilisateur,
    en passant par la chaîne `op_path` qui mène jusqu'à l'Operation.
    Ex: 'id_operation_annee__id_operation' pour RealisationOperationAnnee.
    """
    if user.is_super_admin() or user.is_redacteur_principal():
        return queryset

    base_metrique_chain = f'{op_path}__metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg'
    base_suivi_chain = f'{op_path}__id_suivi__id_pg'

    if user.is_admin_organisme() and user.id_organisme:
        return queryset.filter(
            Q(**{f'{base_metrique_chain}__sites__site__corogsite__uuid_og': user.id_organisme}) |
            Q(**{f'{base_suivi_chain}__sites__site__corogsite__uuid_og': user.id_organisme}) |
            Q(**{f'{op_path}__id_utilisateur_ajout': user})
        ).distinct()

    user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list(
        'plan_de_gestion_id', flat=True
    )
    return queryset.filter(
        Q(**{f'{base_metrique_chain}__in': user_plan_ids}) |
        Q(**{f'{base_metrique_chain}__sites__site__corrolesite__id_role': user}) |
        Q(**{f'{base_metrique_chain}__statut': 'valide'}) |
        Q(**{f'{base_suivi_chain}__in': user_plan_ids}) |
        Q(**{f'{base_suivi_chain}__sites__site__corrolesite__id_role': user}) |
        Q(**{f'{base_suivi_chain}__statut': 'valide'}) |
        Q(**{f'{op_path}__id_utilisateur_ajout': user})
    ).distinct()


def _can_manage_operation_global(user, operation):
    """
    #355 — Droit de surcharger le niveau de réalisation GLOBAL d'une action.
    Réservé aux gestionnaires du plan (cf. canManageLifecycle côté front) :
    super_admin / rédacteur principal, admin de l'organisme du plan, ou
    référent du plan.
    """
    if user.is_super_admin() or user.is_redacteur_principal():
        return True
    plan = operation.get_plan_de_gestion()
    if plan is None:
        return False
    if user.is_admin_organisme() and user.id_organisme:
        return plan.sites.filter(
            site__corogsite__uuid_og=user.id_organisme
        ).exists()
    return plan.referents.filter(pk=user.pk).exists()


class RealisationOperationAnneeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la réalisation annuelle d'une opération (suivi).

    Endpoints:
    - GET    /api/plans/realisations/                       Liste (filtrable)
    - GET    /api/plans/realisations/{id}/                  Détail
    - POST   /api/plans/realisations/                       Créer
    - PATCH  /api/plans/realisations/{id}/                  Modifier
    - DELETE /api/plans/realisations/{id}/                  Supprimer
    - POST   /api/plans/realisations/upsert/                Upsert par id_operation_annee
    - GET    /api/plans/realisations/by-operation/{id}/     Réalisations d'une opération
    - GET    /api/plans/realisations/by-plan/{id}/          Réalisations d'un plan
    """

    queryset = RealisationOperationAnnee.objects.select_related(
        'id_niveau_realisation', 'id_operation_annee', 'id_operation_annee__id_operation',
    )
    serializer_class = RealisationOperationAnneeSerializer
    # Pas de CanModifyOnlyDraftPlan : les suivis sont éditables après validation du plan.
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['id_operation_annee__annee', 'date_maj']
    ordering = ['id_operation_annee__annee']
    filterset_fields = {
        'id_operation_annee': ['exact'],
        'id_operation_annee__id_operation': ['exact'],
        'id_operation_annee__annee': ['exact', 'gte', 'lte'],
        'id_niveau_realisation': ['exact'],
        'id_niveau_realisation__mnemonique': ['exact'],
    }

    def get_queryset(self):
        return _scope_realisation_queryset(
            self.queryset, self.request.user, 'id_operation_annee__id_operation'
        )

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """
        Crée ou met à jour la réalisation pour un id_operation_annee donné.

        POST /api/plans/realisations/upsert/
        Body: { "id_operation_annee": 123, "id_niveau_realisation": 1502, ... }

        #418 — Si l'année n'était pas programmée (pas d'OperationAnnee), on
        accepte aussi { "id_operation": 12, "annee": 2025, ... } : l'année est
        créée à la volée (periodicite=False) pour permettre la saisie du suivi
        d'une action « réalisée non prévue ».
        """
        id_op_annee = request.data.get('id_operation_annee')
        created_oa = False
        if id_op_annee:
            operation_annee = get_object_or_404(OperationAnnee, pk=id_op_annee)
        else:
            id_operation = request.data.get('id_operation')
            annee = request.data.get('annee')
            if not id_operation or annee in (None, ''):
                return Response(
                    {'detail': 'id_operation_annee, ou (id_operation + annee), est requis.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            operation = get_object_or_404(Operation, pk=id_operation)
            operation_annee, created_oa = OperationAnnee.objects.get_or_create(
                id_operation=operation, annee=int(annee),
                defaults={'periodicite': False},
            )
        # Garde-fou : l'utilisateur doit voir l'opération parente via le scoping standard.
        accessible_ops = _scope_realisation_queryset(
            OperationAnnee.objects.filter(pk=operation_annee.pk),
            request.user, 'id_operation',
        )
        if not accessible_ops.exists():
            if created_oa:
                operation_annee.delete()
            return Response(
                {'detail': "Vous n'avez pas accès à cette opération."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance, _ = RealisationOperationAnnee.objects.get_or_create(
            id_operation_annee=operation_annee
        )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(id_utilisateur_maj=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _global_payload(operation):
        """État effectif du niveau de réalisation global d'une opération (#355)."""
        return {
            'id_operation': operation.id_operation,
            'niveau_realisation_global_mnemonique': operation.get_niveau_realisation_global(),
            'niveau_realisation_global_label': operation.get_niveau_realisation_global_label(),
            'niveau_realisation_global_manuel': operation.is_niveau_realisation_global_manuel(),
            'niveau_realisation_global_commentaire': operation.get_niveau_realisation_global_commentaire(),
        }

    @action(detail=False, methods=['get', 'post', 'delete'],
            url_path=r'global-realisation/(?P<operation_id>\d+)')
    def global_realisation(self, request, operation_id=None):
        """
        #355 — Niveau de réalisation GLOBAL (sur la période) d'une action.

        GET    /api/plans/realisations/global-realisation/{operation_id}/
          → état effectif (calcul auto ou surcharge).
        POST   …  body { id_niveau_realisation, commentaire_override? }
          → pose/met à jour la surcharge manuelle.
        DELETE …  → retire la surcharge (retour au calcul automatique).

        Écritures réservées aux gestionnaires du plan. Non verrouillé brouillon
        (donnée de suivi, éditable après validation).
        """
        operation = get_object_or_404(Operation, pk=operation_id)

        if request.method == 'GET':
            return Response(self._global_payload(operation))

        if not _can_manage_operation_global(request.user, operation):
            return Response(
                {'detail': "Action réservée aux gestionnaires du plan."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'DELETE':
            OperationRealisationGlobale.objects.filter(id_operation=operation).delete()
            fresh = get_object_or_404(Operation, pk=operation_id)
            return Response(self._global_payload(fresh))

        # POST — poser/mettre à jour la surcharge (niveau et/ou commentaire).
        # #356 — Le commentaire est indépendant du forçage : on peut enregistrer
        # un commentaire seul (niveau null), ce qui n'active PAS le mode manuel.
        niveau_id = request.data.get('id_niveau_realisation')
        commentaire = request.data.get('commentaire_override')
        if not niveau_id and commentaire is None:
            return Response(
                {'detail': 'id_niveau_realisation ou commentaire_override est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        niveau = None
        if niveau_id:
            niveau = get_object_or_404(
                Nomenclature, pk=niveau_id,
                id_type__mnemonique='NIVEAU_REALISATION',
            )
        OperationRealisationGlobale.objects.update_or_create(
            id_operation=operation,
            defaults={
                'id_niveau_realisation': niveau,
                'commentaire_override': commentaire or '',
                'id_utilisateur_maj': request.user,
            },
        )
        fresh = get_object_or_404(Operation, pk=operation_id)
        return Response(self._global_payload(fresh))

    @action(detail=False, methods=['get'], url_path=r'by-operation/(?P<operation_id>\d+)')
    def by_operation(self, request, operation_id=None):
        """Liste les réalisations d'une opération (toutes années)."""
        operation = get_object_or_404(Operation, pk=operation_id)
        realisations = self.get_queryset().filter(
            id_operation_annee__id_operation=operation
        )
        return Response({
            'operation_id': int(operation_id),
            'realisations': self.get_serializer(realisations, many=True).data,
            'total': realisations.count(),
        })

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """Liste les réalisations d'un plan (toutes opérations × années)."""
        plan = get_object_or_404(PlanGestion, pk=plan_id)
        realisations = self.get_queryset().filter(
            Q(id_operation_annee__id_operation__metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
            Q(id_operation_annee__id_operation__id_suivi__id_pg=plan)
        ).distinct()
        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'realisations': self.get_serializer(realisations, many=True).data,
            'total': realisations.count(),
        })

    @action(detail=False, methods=['get'], url_path=r'bilan-indicateurs/(?P<plan_id>\d+)')
    def bilan_indicateurs(self, request, plan_id=None):
        """
        Agrégations pour l'onglet Indicateurs du Bilan (Phase 4 - Figma #4043).

        Retourne :
          - total_indicateurs / indicateurs_evalues (avec au moins 1 mesure)
          - taux_evaluation (pour le camembert "taux de réalisation")
          - score_distribution : counts par score 1-5 + sans donnée
          - by_enjeu : moyenne des scores par enjeu (pour le radar)
        """
        from collections import defaultdict
        from .models_indicateurs import Indicateur
        from .models import PlanGestion as _Plan

        plan = get_object_or_404(_Plan, pk=plan_id)

        def _compute_score(value, m):
            """Retourne 1-5 selon la grille de scores de la métrique, ou 0 si hors plage.
            #423 — délègue à _value_to_score (virgule décimale, bornes ouvertes ET
            inclusivité des bornes gérées au même endroit)."""
            from .views_indicateurs import _value_to_score
            return _value_to_score(value, m) or 0

        indicators_qs = Indicateur.objects.filter(
            id_ne__id_olt__id_enjeu__id_pg=plan,
        ).select_related(
            'id_ne__id_olt__id_enjeu',
        ).prefetch_related('metriques__mesures').distinct()

        total = 0
        evalues = 0
        score_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
        score_labels = {
            1: 'Très mauvais', 2: 'Mauvais', 3: 'Moyen', 4: 'Bon', 5: 'Très bon', 0: 'Sans donnée',
        }
        by_enjeu_scores = defaultdict(list)
        by_enjeu_meta = {}

        for ind in indicators_qs:
            total += 1
            ind_scores = []
            for m in ind.metriques.all():
                last = m.mesures.order_by('-date_mesure', '-date_ajout').first()
                if not last:
                    continue
                score = _compute_score(last.valeur, m)
                if score > 0:
                    ind_scores.append(score)
            if ind_scores:
                avg = round(sum(ind_scores) / len(ind_scores))
                score_dist[avg] += 1
                evalues += 1
                if ind.id_ne and ind.id_ne.id_olt and ind.id_ne.id_olt.id_enjeu:
                    enjeu = ind.id_ne.id_olt.id_enjeu
                    by_enjeu_scores[enjeu.id_enjeu].append(avg)
                    by_enjeu_meta[enjeu.id_enjeu] = enjeu.libelle
            else:
                score_dist[0] += 1

        radar = [
            {
                'enjeu_id': eid,
                'libelle': by_enjeu_meta[eid],
                'moyenne': round(sum(scores) / len(scores), 2),
                'count': len(scores),
            }
            for eid, scores in by_enjeu_scores.items()
        ]
        radar.sort(key=lambda x: x['libelle'])

        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'total_indicateurs': total,
            'indicateurs_evalues': evalues,
            'taux_evaluation_pct': round(evalues / total * 100, 1) if total else 0,
            'score_distribution': [
                {'score': k, 'label': score_labels[k], 'count': v}
                for k, v in sorted(score_dist.items())
            ],
            'by_enjeu': radar,
        })

    @action(detail=False, methods=['get'], url_path=r'bilan/(?P<plan_id>\d+)')
    def bilan(self, request, plan_id=None):
        """
        Agrégations pour la page Bilan de gestion (Phase 4).

        Retourne :
          - counts par catégorie d'action (CATEGORIE_ACTION_RESERVE) × niveau réalisation
          - counts par enjeu × niveau réalisation
          - totaux globaux par niveau (alimente le camembert)
          - totaux budget : { fonctionnement, investissement, total } × { previsionnel, realise }
          - totaux RH (ETP) : { previsionnel, realise }

        Granularité de comptage : par (operation, année) — soit une ligne RealisationOperationAnnee.
        Le scoping suit le get_queryset standard (référent / admin_og / super_admin / rédacteur principal).
        """
        from decimal import Decimal
        from collections import defaultdict

        plan = get_object_or_404(PlanGestion, pk=plan_id)

        # Filtres optionnels
        enjeu_id = request.query_params.get('enjeu_id')
        organisme_id = request.query_params.get('organisme_id')
        # Année : vue « annuel » du bilan. Sans ce filtre, le bilan agrégeait
        # toutes les années → une action « Terminée » en 2026 apparaissait
        # « Terminée » pour 2027, 2028… (#101). On scope alors les comptages à
        # l'année demandée (chaque RealisationOperationAnnee est déjà par année).
        annee = request.query_params.get('annee')
        # #355 — Vue « globale » (sans année) : le comptage des niveaux de
        # réalisation se fait UNE fois par opération via son statut global
        # (surcharge sinon calcul sur les années programmées), au lieu de
        # compter chaque ligne annuelle. Corrige « 1 année Terminée = action
        # Terminée au global ». La vue annuelle (?annee=) reste par année.
        is_global_view = not annee

        # 1) RealisationOperationAnnee scopées au plan, avec relations utiles préchargées.
        realisations_qs = self.get_queryset().filter(
            Q(id_operation_annee__id_operation__metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
            Q(id_operation_annee__id_operation__id_suivi__id_pg=plan)
        ).select_related(
            'id_operation_annee',
            'id_operation_annee__id_operation',
            'id_operation_annee__id_operation__id_categorie_action_reserve',
            'id_operation_annee__id_operation__id_type_action',
            'id_niveau_realisation',
        ).prefetch_related(
            'id_operation_annee__organismes',
            'id_operation_annee__organismes__realisation',
            'id_operation_annee__id_operation__metriques__id_indicateur__id_ne__id_olt__id_enjeu',
        ).distinct()

        if enjeu_id:
            realisations_qs = realisations_qs.filter(
                id_operation_annee__id_operation__metriques__id_indicateur__id_ne__id_olt__id_enjeu_id=enjeu_id
            ).distinct()

        if annee:
            try:
                realisations_qs = realisations_qs.filter(id_operation_annee__annee=int(annee))
            except (TypeError, ValueError):
                pass

        # Helper : initialise un compteur par niveau de réalisation
        def _empty_counts():
            return {
                'non_demarre': 0, 'en_cours': 0, 'partiel': 0,
                'termine': 0, 'abandonne': 0, 'reporte': 0,
                'inconnu': 0, 'total': 0,
            }

        # 2) Boucle d'agrégation
        by_categorie = defaultdict(_empty_counts)  # { (code, label): counts }
        categorie_meta = {}  # code -> label
        by_enjeu = defaultdict(_empty_counts)      # { enjeu_id: counts }
        enjeu_meta = {}                            # enjeu_id -> libelle
        taux_global = _empty_counts()

        budget_previsionnel_fonct = Decimal('0')
        budget_previsionnel_invest = Decimal('0')
        budget_realise_fonct = Decimal('0')
        budget_realise_invest = Decimal('0')
        etp_previsionnel = Decimal('0')
        etp_realise_total = Decimal('0')

        # Set des operation_annees vues pour ne pas double-compter les budgets prévisionnels.
        seen_op_annees = set()
        # #355 — opérations vues (pour le comptage global après la boucle).
        seen_op_ids = set()

        niveau_map = {
            'NON_DEMARRE': 'non_demarre', 'EN_COURS': 'en_cours',
            'PARTIEL': 'partiel', 'TERMINE': 'termine',
            'ABANDONNE': 'abandonne', 'REPORTE': 'reporte',
        }

        for r in realisations_qs:
            oa = r.id_operation_annee
            op = oa.id_operation
            seen_op_ids.add(op.id_operation)

            # --- Comptage niveau (vue ANNUELLE uniquement) ---
            # En vue globale, le comptage est fait une fois par opération après
            # la boucle via le statut global (#355).
            if not is_global_view:
                mnemonique = (
                    r.id_niveau_realisation.mnemonique
                    if r.id_niveau_realisation else None
                )
                key = niveau_map.get(mnemonique, 'inconnu')

                # Catégorie d'action (préfixe CT88 si dispo, sinon TYPE_ACTION)
                cat = op.id_categorie_action_reserve or op.id_type_action
                cat_code = (cat.cd_nomenclature or cat.mnemonique or 'AUTRE') if cat else 'AUTRE'
                cat_label = (cat.label if cat else 'Autre')
                categorie_meta[cat_code] = cat_label
                by_categorie[cat_code][key] += 1
                by_categorie[cat_code]['total'] += 1

                # Enjeux : une op peut être rattachée à plusieurs métriques → plusieurs enjeux.
                # On compte une fois par enjeu rattaché.
                enjeux_set = set()
                for m in op.metriques.all():
                    try:
                        enjeu = m.id_indicateur.id_ne.id_olt.id_enjeu
                        if enjeu is None:
                            continue
                        enjeux_set.add(enjeu.id_enjeu)
                        enjeu_meta[enjeu.id_enjeu] = enjeu.libelle
                    except Exception:
                        continue
                for eid in enjeux_set:
                    by_enjeu[eid][key] += 1
                    by_enjeu[eid]['total'] += 1

                taux_global[key] += 1
                taux_global['total'] += 1

            # --- Budgets / ETP ---
            mode = op.ventilation_mode

            # Prévisionnel : on ne le compte qu'une fois par OperationAnnee
            if oa.id_operation_annee not in seen_op_annees:
                seen_op_annees.add(oa.id_operation_annee)
                if mode == 'none':
                    budget_previsionnel_fonct += (oa.budget or 0)
                elif mode == 'by_type':
                    budget_previsionnel_fonct += (oa.budget_fonctionnement or 0)
                    budget_previsionnel_invest += (oa.budget_investissement or 0)
                else:  # by_org / by_org_type
                    for oao in oa.organismes.all():
                        budget_previsionnel_fonct += (oao.budget_fonctionnement or 0)
                        budget_previsionnel_invest += (oao.budget_investissement or 0)
                etp_previsionnel += (oa.etp or 0)

            # Réalisé
            if mode in ('none',):
                budget_realise_fonct += (r.budget_realise or 0)
            elif mode == 'by_type':
                budget_realise_fonct += (r.budget_fonctionnement_realise or 0)
                budget_realise_invest += (r.budget_investissement_realise or 0)
            else:  # by_org / by_org_type
                for oao in oa.organismes.all():
                    real_oao = getattr(oao, 'realisation', None)
                    if real_oao:
                        budget_realise_fonct += (real_oao.budget_fonctionnement_realise or 0)
                        budget_realise_invest += (real_oao.budget_investissement_realise or 0)
            # ETP réalisé : par année (champ etp_realise) sauf si ventilation par org
            if mode in ('none', 'by_type'):
                etp_realise_total += (r.etp_realise or 0)
            else:
                for oao in oa.organismes.all():
                    real_oao = getattr(oao, 'realisation', None)
                    if real_oao:
                        etp_realise_total += (real_oao.etp_realise or 0)

        # #355 — Vue globale : comptage du niveau UNE fois par opération via son
        # statut global (surcharge sinon calcul sur les années programmées).
        if is_global_view and seen_op_ids:
            ops_global = Operation.objects.filter(
                id_operation__in=seen_op_ids
            ).select_related(
                'id_categorie_action_reserve', 'id_type_action',
                'realisation_globale', 'realisation_globale__id_niveau_realisation',
            ).prefetch_related(
                Prefetch(
                    'operation_annees',
                    queryset=OperationAnnee.objects.select_related(
                        'realisation', 'realisation__id_niveau_realisation',
                    ),
                ),
                'metriques__id_indicateur__id_ne__id_olt__id_enjeu',
            )
            for op in ops_global:
                key = niveau_map.get(op.get_niveau_realisation_global(), 'inconnu')

                cat = op.id_categorie_action_reserve or op.id_type_action
                cat_code = (cat.cd_nomenclature or cat.mnemonique or 'AUTRE') if cat else 'AUTRE'
                categorie_meta[cat_code] = (cat.label if cat else 'Autre')
                by_categorie[cat_code][key] += 1
                by_categorie[cat_code]['total'] += 1

                enjeux_set = set()
                for m in op.metriques.all():
                    try:
                        enjeu = m.id_indicateur.id_ne.id_olt.id_enjeu
                        if enjeu is None:
                            continue
                        enjeux_set.add(enjeu.id_enjeu)
                        enjeu_meta[enjeu.id_enjeu] = enjeu.libelle
                    except Exception:
                        continue
                for eid in enjeux_set:
                    by_enjeu[eid][key] += 1
                    by_enjeu[eid]['total'] += 1

                taux_global[key] += 1
                taux_global['total'] += 1

        # 3) Mise en forme
        by_categorie_list = sorted(
            [
                {'code': code, 'label': categorie_meta[code], **counts}
                for code, counts in by_categorie.items()
            ],
            key=lambda x: x['code'],
        )
        by_enjeu_list = sorted(
            [
                {'enjeu_id': eid, 'libelle': enjeu_meta[eid], **counts}
                for eid, counts in by_enjeu.items()
            ],
            key=lambda x: x['libelle'],
        )

        budget_total_prev = budget_previsionnel_fonct + budget_previsionnel_invest
        budget_total_real = budget_realise_fonct + budget_realise_invest

        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'annee_min': plan.annee_debut,
            'annee_max': plan.annee_fin,
            'taux_realisation': taux_global,
            'by_categorie_action': by_categorie_list,
            'by_enjeu': by_enjeu_list,
            'budget': {
                'fonctionnement': {
                    'previsionnel': float(budget_previsionnel_fonct),
                    'realise': float(budget_realise_fonct),
                },
                'investissement': {
                    'previsionnel': float(budget_previsionnel_invest),
                    'realise': float(budget_realise_invest),
                },
                'total': {
                    'previsionnel': float(budget_total_prev),
                    'realise': float(budget_total_real),
                },
            },
            'rh': {
                'previsionnel': float(etp_previsionnel),
                'realise': float(etp_realise_total),
            },
        })


class RealisationOperationAnneeOrganismeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la ventilation par organisme du suivi de réalisation.

    Endpoints:
    - GET    /api/plans/realisations-organismes/             Liste
    - GET    /api/plans/realisations-organismes/{id}/        Détail
    - POST   /api/plans/realisations-organismes/             Créer
    - PATCH  /api/plans/realisations-organismes/{id}/        Modifier
    - DELETE /api/plans/realisations-organismes/{id}/        Supprimer
    - POST   /api/plans/realisations-organismes/upsert/      Upsert par id_operation_annee_organisme
    """

    queryset = RealisationOperationAnneeOrganisme.objects.select_related(
        'id_operation_annee_organisme',
        'id_operation_annee_organisme__id_operation_annee__id_operation',
    )
    serializer_class = RealisationOperationAnneeOrganismeSerializer
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'id_operation_annee_organisme': ['exact'],
        'id_operation_annee_organisme__id_operation_annee': ['exact'],
        'id_operation_annee_organisme__id_operation_annee__id_operation': ['exact'],
        'id_operation_annee_organisme__id_organisme': ['exact'],
    }
    ordering = ['id_operation_annee_organisme__id_operation_annee__annee']

    def get_queryset(self):
        return _scope_realisation_queryset(
            self.queryset, self.request.user,
            'id_operation_annee_organisme__id_operation_annee__id_operation',
        )

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """
        Crée ou met à jour la réalisation pour un id_operation_annee_organisme donné.

        POST /api/plans/realisations-organismes/upsert/
        Body: { "id_operation_annee_organisme": 123, "budget_fonctionnement_realise": 800, ... }
        """
        id_oao = request.data.get('id_operation_annee_organisme')
        if not id_oao:
            return Response(
                {'detail': 'id_operation_annee_organisme est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        oao = get_object_or_404(OperationAnneeOrganisme, pk=id_oao)
        accessible = _scope_realisation_queryset(
            OperationAnneeOrganisme.objects.filter(pk=oao.pk),
            request.user, 'id_operation_annee__id_operation',
        )
        if not accessible.exists():
            return Response(
                {'detail': "Vous n'avez pas accès à cette opération."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance, _ = RealisationOperationAnneeOrganisme.objects.get_or_create(
            id_operation_annee_organisme=oao
        )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
