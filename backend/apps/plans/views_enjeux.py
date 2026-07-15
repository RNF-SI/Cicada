"""
Vues API REST pour les Enjeux, FCR et Responsabilités.
"""
from django.db import transaction
from django.db.models import Q, Prefetch, Max
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie, CorEnjeuFichier,
    CorFacteurEnjeu,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie
)
from .models import PlanGestion, CorRolePlan
from apps.users.models import Site
from .serializers_enjeux import (
    EnjeuListSerializer, EnjeuDetailSerializer, EnjeuCreateSerializer,
    FacteurInfluenceSerializer, FacteurInfluenceListSerializer, FacteurInfluenceCreateSerializer,
    PressionSerializer, PressionCreateSerializer,
    ObjectifLongTermeSerializer, ObjectifLongTermeListSerializer, ObjectifLongTermeCreateSerializer,
    NiveauExigenceSerializer, NiveauExigenceCreateSerializer,
    ObjectifOperationnelSerializer, ObjectifOperationnelListSerializer, ObjectifOperationnelCreateSerializer,
    ResultatAttenduSerializer, ResultatAttenduCreateSerializer,
    ResponsabiliteListSerializer, ResponsabiliteDetailSerializer, ResponsabiliteCreateSerializer,
    CorEnjeuTaxonSerializer, CorEnjeuHabitatSerializer, CorEnjeuFichierSerializer
)
from apps.users.permissions import IsReferent, IsSuperAdmin, IsAdminOrganisme
from .permissions import CanModifyOnlyDraftPlan
from .filters_enjeux import EnjeuFilter, ResponsabiliteFilter
from .reorder import do_reorder


class EnjeuViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Enjeux et FCR.

    Fonctionnalités:
    - CRUD complet avec permissions
    - Filtres par plan, catégorie, priorité
    - Recherche textuelle
    - Actions pour ajouter/supprimer des taxons, habitats

    Endpoints:
    - GET /api/plans/enjeux/ - Liste des enjeux/FCR
    - GET /api/plans/enjeux/{id}/ - Détail d'un enjeu/FCR
    - POST /api/plans/enjeux/ - Créer un enjeu/FCR
    - PATCH /api/plans/enjeux/{id}/ - Modifier un enjeu/FCR
    - DELETE /api/plans/enjeux/{id}/ - Supprimer un enjeu/FCR
    - GET /api/plans/enjeux/by-plan/{plan_id}/ - Enjeux d'un plan
    - POST /api/plans/enjeux/{id}/add_taxon/ - Ajouter un taxon
    - DELETE /api/plans/enjeux/{id}/remove_taxon/{cd_nom}/ - Supprimer un taxon
    - POST /api/plans/enjeux/{id}/add_habitat/ - Ajouter un habitat
    - DELETE /api/plans/enjeux/{id}/remove_habitat/{cd_hab}/ - Supprimer un habitat
    """

    # #263 — Perf : le queryset de base est minimal (select_related sur
    # les FKs directs). Les prefetch profonds (FI/OO/OLT/NE/RA/Ind/Met/Op)
    # sont construits à la volée dans `_with_deep_prefetch()` pour éviter
    # le partage d'état mutable entre requêtes.
    queryset = Enjeu.objects.select_related(
        'id_pg', 'id_categorie', 'id_categorie_fcr', 'id_importance',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('taxons', 'habitats', 'geologies', 'objets_geologiques', 'fichiers')

    @classmethod
    def _build_deep_prefetches(cls):
        """Construit la liste de `Prefetch` profonds pour l'arborescence
        Enjeu → FI/Pression/OO/RA et Enjeu → OLT/NE → Indicateur/Métrique/Opération.

        Les FKs accédés par les serializers (createur, types, priorités…) sont
        passés en `select_related` sur la queryset interne du Prefetch, ce qui
        permet à chaque `obj.id_xxx` dans le serializer d'utiliser le cache
        sans déclencher de requête.
        """
        from django.db.models import Prefetch
        from .models_enjeux import (
            FacteurInfluence, Pression, ObjectifLongTerme, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
        )
        from .models_indicateurs import Indicateur, Metrique
        from .models_operations import Operation, OperationAnnee, OperationAnneeOrganisme, FinanceOperation

        op_annee_organisme_qs = OperationAnneeOrganisme.objects.select_related('id_organisme')
        finance_qs = FinanceOperation.objects.select_related('id_categorie')

        op_qs = Operation.objects.select_related(
            'id_priorite', 'id_type_action',
            'id_categorie_action_reserve', 'id_utilisateur_ajout',
            # #355 — surcharge manuelle du niveau global (reverse OneToOne)
            'realisation_globale', 'realisation_globale__id_niveau_realisation',
        ).prefetch_related(
            Prefetch('metriques', queryset=Metrique.objects.select_related('id_indicateur')),
            'sites',
            Prefetch(
                'operation_annees',
                # #355 — réalisation annuelle + niveau pour le calcul du statut global
                queryset=OperationAnnee.objects.select_related(
                    'realisation', 'realisation__id_niveau_realisation',
                ).prefetch_related(
                    Prefetch('organismes', queryset=op_annee_organisme_qs),
                ),
            ),
            Prefetch('finances', queryset=finance_qs),
        )

        metrique_qs = Metrique.objects.select_related(
            'type_metrique', 'id_indicateur', 'id_utilisateur_ajout',
        ).prefetch_related(
            'mesures', 'score_blocks',
            Prefetch('operations', queryset=op_qs),
        )

        indicateur_qs = Indicateur.objects.select_related(
            'type_indicateur', 'id_utilisateur_ajout',
            # #518 — surcharge manuelle de l'évaluation globale (#356), lue par
            # la colonne « Global » du tableau de bord (reverse OneToOne).
            'realisation_globale',
        ).exclude(
            # #477 — les indicateurs de RÉPONSE sont propres à une action (créés
            # via la fiche action, rattachés au même NE/RA pour le contexte) et ne
            # doivent JAMAIS apparaître comme des indicateurs autonomes dans
            # l'arborescence de l'enjeu ni dans le tableau de bord (où ils
            # s'affichaient à tort comme « Indicateur d'état/pression »). Ils
            # restent gérés à part via la fiche action et l'onglet « Réponse ».
            type_indicateur__mnemonique='REPONSE',
        ).prefetch_related(
            'taxons', 'habitats', 'geologies',
            # #518 — overrides manuels du score par année (tableau de bord)
            'annual_mesures',
            Prefetch('metriques', queryset=metrique_qs),
            # #367 — actions rattachées directement à l'indicateur (sans métrique)
            Prefetch('operations', queryset=op_qs),
        )

        ne_qs = NiveauExigence.objects.select_related('id_utilisateur_ajout').prefetch_related(
            Prefetch('indicateurs', queryset=indicateur_qs),
        )

        ra_qs = ResultatAttendu.objects.select_related('id_utilisateur_ajout').prefetch_related(
            Prefetch('indicateurs', queryset=indicateur_qs),
        )

        oo_qs = ObjectifOperationnel.objects.select_related('id_utilisateur_ajout').prefetch_related(
            Prefetch(
                'pressions',
                # #552 — précharge les enjeux du facteur pour calculer
                # ``shared_enjeu_ids`` (bandeau « élément lié ») sans N+1.
                queryset=Pression.objects.select_related('id_facteur_influence').prefetch_related(
                    'id_facteur_influence__enjeux',
                ),
            ),
            Prefetch('resultats_attendus', queryset=ra_qs),
        )

        pression_qs = Pression.objects.select_related(
            'id_type_pression', 'id_facteur_influence', 'id_utilisateur_ajout',
        ).prefetch_related(
            Prefetch('objectifs_operationnels', queryset=oo_qs),
        )

        # #552 — le facteur est désormais partagé (M2M enjeux) et son ordre est
        # propre à chaque enjeu : on précharge via les lignes de liaison
        # ``cor_facteurs`` (ordonnées par ordre), en portant le sous-arbre du
        # facteur ainsi que ses enjeux (pour ``enjeu_ids``).
        cor_facteurs_qs = CorFacteurEnjeu.objects.select_related(
            'id_facteur_influence', 'id_facteur_influence__id_utilisateur_ajout',
        ).prefetch_related(
            'id_facteur_influence__enjeux',
            Prefetch('id_facteur_influence__pressions', queryset=pression_qs),
        ).order_by('ordre', 'id')

        olt_qs = ObjectifLongTerme.objects.select_related('id_utilisateur_ajout').prefetch_related(
            Prefetch('niveaux_exigence', queryset=ne_qs),
        )

        return [
            Prefetch('cor_facteurs', queryset=cor_facteurs_qs),
            Prefetch('objectifs_long_terme', queryset=olt_qs),
            # #337 — OO rattachés directement à l'enjeu/FCR (sans pression)
            Prefetch('objectifs_operationnels_directs', queryset=oo_qs),
        ]

    @classmethod
    def _with_deep_prefetch(cls, qs):
        """Applique les prefetch profonds à un queryset Enjeu."""
        return qs.prefetch_related(*cls._build_deep_prefetches())

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EnjeuFilter
    search_fields = ['libelle', 'intitule_court', 'description', 'etat_enjeu']
    ordering_fields = ['rang', 'libelle', 'date_ajout', 'date_maj', 'id_enjeu']

    def get_plan_for_payload(self, data):
        """Pour le check draft à la création."""
        plan_id = data.get('id_pg')
        if not plan_id:
            return None
        try:
            return PlanGestion.objects.only('statut').get(pk=plan_id)
        except PlanGestion.DoesNotExist:
            return None
    ordering = ['id_enjeu']

    def get_serializer_class(self):
        """Choisir le serializer selon l'action."""
        if self.action == 'list':
            return EnjeuListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EnjeuCreateSerializer
        return EnjeuDetailSerializer

    def _user_plan_ids(self, user):
        """Retourne les IDs des plans accessibles via CorRolePlan (membre ou référent)."""
        return CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)

    def get_queryset(self):
        """Filtrer selon les permissions utilisateur."""
        user = self.request.user
        queryset = self.queryset

        # Super admin : voir tous les enjeux
        if user.is_super_admin():
            return queryset

        # Rédacteur principal : voir tous les enjeux
        if user.is_redacteur_principal():
            return queryset

        # Admin organisme : voir les enjeux des plans de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        # Membre ou référent d'un plan (via CorRolePlan) OU lié via site OU plans validés
        user_plan_ids = self._user_plan_ids(user)
        return queryset.filter(
            Q(id_pg__in=user_plan_ids) |
            Q(id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        """Définir l'utilisateur créateur."""
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        """Définir l'utilisateur modificateur."""
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les enjeux d'un plan (#249/#261).

        Payload: { "parent_id": <id_pg>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(self, request, parent_filter='id_pg')

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """
        Récupérer les enjeux et FCR d'un plan spécifique.

        GET /api/plans/enjeux/by-plan/{plan_id}/
        """
        # Vérifier que le plan existe et que l'utilisateur y a accès
        plan = get_object_or_404(PlanGestion, id_pg=plan_id)

        # Vérifier les permissions
        if not request.user.is_super_admin() and not request.user.is_redacteur_principal():
            if request.user.is_admin_organisme() and request.user.id_organisme:
                if not plan.sites.filter(site__corogsite__uuid_og=request.user.id_organisme).exists():
                    return Response(
                        {'error': 'Vous n\'avez pas accès à ce plan'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif not CorRolePlan.objects.filter(id_role=request.user, plan_de_gestion=plan).exists():
                # Ni membre ni référent du plan — vérifier accès site ou plan validé
                has_site_access = plan.sites.filter(site__corrolesite__id_role=request.user).exists()
                if not has_site_access and plan.statut != 'valide':
                    return Response(
                        {'error': 'Vous n\'avez pas accès à ce plan'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        # #263 — Applique les prefetch profonds (Prefetch avec select_related
        # sur les FK des serializers) uniquement à cette vue, pas à toutes les
        # autres actions du ViewSet (list/retrieve restent légères).
        enjeux = self._with_deep_prefetch(self.get_queryset().filter(id_pg=plan))

        # Séparer enjeux et FCR. Pas de `.filter()` chaîné après — chaque
        # `.filter()` recommencerait l'évaluation des prefetch. On évalue une
        # seule fois et on partitionne en Python.
        enjeux_all = list(enjeux.order_by('id_enjeu'))
        enjeux_list = [e for e in enjeux_all if e.id_categorie and e.id_categorie.mnemonique == 'ENJEU']
        fcr_list = [e for e in enjeux_all if e.id_categorie and e.id_categorie.mnemonique == 'FCR']

        # #228 / 2026-05-12 — Pré-calcul du code d'affichage de toutes les
        # actions du plan (préfixe 2 lettres + rang), passé via context aux
        # serializers d'opération nichés dans EnjeuDetailSerializer. Évite
        # de recalculer le mapping pour chaque opération individuellement.
        from .serializers_operations import compute_operation_codes_for_plan
        operation_codes = compute_operation_codes_for_plan(plan.pk)
        ctx = {**self.get_serializer_context(), 'operation_codes': operation_codes}

        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'plan_slug': plan.slug,
            'plan_statut': plan.statut,
            'enjeux': EnjeuDetailSerializer(enjeux_list, many=True, context=ctx).data,
            'fcr': EnjeuDetailSerializer(fcr_list, many=True, context=ctx).data,
            'total_enjeux': len(enjeux_list),
            'total_fcr': len(fcr_list),
        })

    @action(detail=True, methods=['post'])
    def add_taxon(self, request, pk=None):
        """
        Ajouter un taxon à un enjeu.

        POST /api/plans/enjeux/{id}/add_taxon/
        Body: {"cd_nom": 123, "nom_complet": "...", "nom_vern": "..."}
        """
        enjeu = self.get_object()
        cd_nom = request.data.get('cd_nom')

        if not cd_nom:
            return Response(
                {'error': 'cd_nom est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si le taxon existe déjà
        if enjeu.taxons.filter(cd_nom=cd_nom).exists():
            return Response(
                {'error': 'Ce taxon est déjà associé à cet enjeu'},
                status=status.HTTP_400_BAD_REQUEST
            )

        taxon = CorEnjeuTaxon.objects.create(
            id_enjeu=enjeu,
            cd_nom=cd_nom,
            nom_complet=request.data.get('nom_complet', ''),
            nom_vern=request.data.get('nom_vern', '')
        )

        return Response(
            CorEnjeuTaxonSerializer(taxon).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path=r'remove_taxon/(?P<cd_nom>\d+)')
    def remove_taxon(self, request, pk=None, cd_nom=None):
        """
        Supprimer un taxon d'un enjeu.

        DELETE /api/plans/enjeux/{id}/remove_taxon/{cd_nom}/
        """
        enjeu = self.get_object()
        deleted, _ = enjeu.taxons.filter(cd_nom=cd_nom).delete()

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Taxon non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['post'])
    def add_habitat(self, request, pk=None):
        """
        Ajouter un habitat à un enjeu.

        POST /api/plans/enjeux/{id}/add_habitat/
        Body: {"cd_hab": "1234", "lb_hab_fr": "..."}
        """
        enjeu = self.get_object()
        cd_hab = request.data.get('cd_hab')

        if not cd_hab:
            return Response(
                {'error': 'cd_hab est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if enjeu.habitats.filter(cd_hab=cd_hab).exists():
            return Response(
                {'error': 'Cet habitat est déjà associé à cet enjeu'},
                status=status.HTTP_400_BAD_REQUEST
            )

        habitat = CorEnjeuHabitat.objects.create(
            id_enjeu=enjeu,
            cd_hab=cd_hab,
            lb_hab_fr=request.data.get('lb_hab_fr', '')
        )

        return Response(
            CorEnjeuHabitatSerializer(habitat).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path=r'remove_habitat/(?P<cd_hab>[^/.]+)')
    def remove_habitat(self, request, pk=None, cd_hab=None):
        """
        Supprimer un habitat d'un enjeu.

        DELETE /api/plans/enjeux/{id}/remove_habitat/{cd_hab}/
        """
        enjeu = self.get_object()
        deleted, _ = enjeu.habitats.filter(cd_hab=cd_hab).delete()

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Habitat non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques globales sur les enjeux et FCR.

        GET /api/plans/enjeux/stats/
        """
        queryset = self.get_queryset()

        return Response({
            'total_enjeux': queryset.filter(id_categorie__mnemonique='ENJEU').count(),
            'total_fcr': queryset.filter(id_categorie__mnemonique='FCR').count(),
            'par_priorite': {
                'priorite_1': queryset.filter(rang=1).count(),
                'priorite_2': queryset.filter(rang=2).count(),
                'priorite_3': queryset.filter(rang=3).count()
            },
            'par_type': {
                'habitat': queryset.filter(habitat=True).count(),
                'espece': queryset.filter(espece=True).count(),
                'processus': queryset.filter(processus=True).count()
            }
        })


class ResponsabiliteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Responsabilités.

    Fonctionnalités:
    - CRUD complet avec permissions
    - Filtres par site, type, niveau
    - Recherche textuelle

    Endpoints:
    - GET /api/plans/responsabilites/ - Liste des responsabilités
    - GET /api/plans/responsabilites/{id}/ - Détail d'une responsabilité
    - POST /api/plans/responsabilites/ - Créer une responsabilité
    - PATCH /api/plans/responsabilites/{id}/ - Modifier une responsabilité
    - DELETE /api/plans/responsabilites/{id}/ - Supprimer une responsabilité
    - GET /api/plans/responsabilites/by-site/{site_id}/ - Responsabilités d'un site
    """

    queryset = Responsabilite.objects.select_related(
        'id_site', 'id_type_responsabilite', 'id_niveau_responsabilite',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('taxons', 'habitats', 'geologies', 'enjeux_lies')

    # Responsabilité est rattachée à un Site, pas à un Plan : pas de check draft.
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ResponsabiliteFilter
    search_fields = ['description', 'id_site__nom_site']
    ordering_fields = ['id_type_responsabilite', 'id_niveau_responsabilite', 'date_ajout']
    ordering = ['id_type_responsabilite', 'id_niveau_responsabilite']

    def get_serializer_class(self):
        """Choisir le serializer selon l'action."""
        if self.action == 'list':
            return ResponsabiliteListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ResponsabiliteCreateSerializer
        return ResponsabiliteDetailSerializer

    def get_queryset(self):
        """Filtrer selon les permissions utilisateur."""
        user = self.request.user
        queryset = self.queryset

        # Super admin : voir toutes les responsabilités
        if user.is_super_admin():
            return queryset

        # Rédacteur principal : voir toutes les responsabilités
        if user.is_redacteur_principal():
            return queryset

        # Admin organisme : voir les responsabilités des sites de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        # Référent : voir les responsabilités de ses sites
        if user.is_referent():
            return queryset.filter(
                id_site__corrolesite__id_role=user
            ).distinct()

        # Utilisateur standard : pas d'accès direct aux responsabilités
        return queryset.none()

    def perform_create(self, serializer):
        """Définir l'utilisateur créateur."""
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        """Définir l'utilisateur modificateur."""
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-site/(?P<site_id>\d+)')
    def by_site(self, request, site_id=None):
        """
        Récupérer les responsabilités d'un site spécifique.

        GET /api/plans/responsabilites/by-site/{site_id}/
        """
        site = get_object_or_404(Site, id_site=site_id)

        # Vérifier les permissions
        if not request.user.is_super_admin() and not request.user.is_redacteur_principal():
            if request.user.is_admin_organisme() and request.user.id_organisme:
                if not site.corogsite_set.filter(uuid_og=request.user.id_organisme).exists():
                    return Response(
                        {'error': 'Vous n\'avez pas accès à ce site'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif not request.user.can_manage_site(site):
                return Response(
                    {'error': 'Vous n\'avez pas accès à ce site'},
                    status=status.HTTP_403_FORBIDDEN
                )

        responsabilites = self.get_queryset().filter(id_site=site)

        return Response({
            'site_id': site_id,
            'site_nom': site.nom_site,
            'responsabilites': ResponsabiliteListSerializer(responsabilites, many=True).data,
            'total': responsabilites.count()
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques globales sur les responsabilités.

        GET /api/plans/responsabilites/stats/
        """
        queryset = self.get_queryset()

        # Compter par type
        par_type = {}
        for resp in queryset.values('id_type_responsabilite__label').annotate(
            count=models.Count('id_responsabilite')
        ):
            label = resp['id_type_responsabilite__label'] or 'Non défini'
            par_type[label] = resp['count']

        # Compter par niveau
        par_niveau = {}
        for resp in queryset.values('id_niveau_responsabilite__label').annotate(
            count=models.Count('id_responsabilite')
        ):
            label = resp['id_niveau_responsabilite__label'] or 'Non défini'
            par_niveau[label] = resp['count']

        return Response({
            'total': queryset.count(),
            'par_type': par_type,
            'par_niveau': par_niveau
        })


class FacteurInfluenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Facteurs d'Influence.

    Endpoints:
    - GET /api/plans/facteurs-influence/ - Liste
    - GET /api/plans/facteurs-influence/{id}/ - Détail
    - POST /api/plans/facteurs-influence/ - Créer
    - PATCH /api/plans/facteurs-influence/{id}/ - Modifier
    - DELETE /api/plans/facteurs-influence/{id}/ - Supprimer
    - GET /api/plans/facteurs-influence/by-enjeu/{enjeu_id}/ - Par enjeu
    """

    queryset = FacteurInfluence.objects.select_related(
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'enjeux',
        'pressions', 'pressions__id_utilisateur_ajout',
        'pressions__objectifs_operationnels', 'pressions__objectifs_operationnels__id_utilisateur_ajout',
        'pressions__objectifs_operationnels__resultats_attendus',
        'pressions__objectifs_operationnels__resultats_attendus__id_utilisateur_ajout',
        'pressions__objectifs_operationnels__resultats_attendus__indicateurs',
        'pressions__objectifs_operationnels__resultats_attendus__indicateurs__type_indicateur',
        'pressions__objectifs_operationnels__resultats_attendus__indicateurs__metriques',
        'pressions__objectifs_operationnels__resultats_attendus__indicateurs__metriques__type_metrique',
        'pressions__objectifs_operationnels__resultats_attendus__indicateurs__id_utilisateur_ajout',
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_facteur_influence']
    ordering = ['id_facteur_influence']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via l'enjeu parent (#552 : enjeu_id)."""
        enjeu_id = data.get('enjeu_id') or data.get('id_enjeu')
        if not enjeu_id:
            return None
        try:
            return Enjeu.objects.only('id_pg').get(pk=enjeu_id).get_plan_de_gestion()
        except Enjeu.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action == 'list':
            return FacteurInfluenceListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FacteurInfluenceCreateSerializer
        return FacteurInfluenceSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                enjeux__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(enjeux__id_pg__in=user_plan_ids) |
            Q(enjeux__id_pg__sites__site__corrolesite__id_role=user) |
            Q(enjeux__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @staticmethod
    def _assert_draft_or_403(plan):
        """#248/#552 — lève une 403 si le plan n'est pas éditable (hors brouillon)."""
        if plan is None or plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            return Response(
                {'detail': CanModifyOnlyDraftPlan.message},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les facteurs d'influence d'un enjeu (#249/#261).

        #552 — l'ordre est propre à l'enjeu (porté par CorFacteurEnjeu) : on
        écrit l'ordre sur la ligne de liaison, pas sur le facteur.

        Payload: { "parent_id": <id_enjeu>, "ordered_ids": [id1, id2, ...] }
        """
        def write_ordre(enjeu_id, facteur_id, pos):
            CorFacteurEnjeu.objects.filter(
                id_enjeu_id=enjeu_id, id_facteur_influence_id=facteur_id
            ).update(ordre=pos)

        return do_reorder(self, request, parent_filter='enjeux', ordre_writer=write_ordre)

    @action(detail=False, methods=['get'], url_path=r'by-enjeu/(?P<enjeu_id>\d+)')
    def by_enjeu(self, request, enjeu_id=None):
        """
        Récupérer les facteurs d'influence d'un enjeu (avec ordre propre à l'enjeu).

        GET /api/plans/facteurs-influence/by-enjeu/{enjeu_id}/
        """
        enjeu = get_object_or_404(Enjeu, id_enjeu=enjeu_id)
        # Ordonne via les lignes de liaison (ordre propre à l'enjeu) et injecte
        # l'ordre contextuel sur chaque facteur pour la sérialisation.
        accessible = set(self.get_queryset().values_list('pk', flat=True))
        cors = CorFacteurEnjeu.objects.filter(id_enjeu=enjeu).select_related(
            'id_facteur_influence'
        ).order_by('ordre', 'id')
        facteurs = []
        for cor in cors:
            if cor.id_facteur_influence_id not in accessible:
                continue
            fi = cor.id_facteur_influence
            fi._enjeu_ordre = cor.ordre
            facteurs.append(fi)
        return Response({
            'enjeu_id': int(enjeu_id),
            'enjeu_libelle': enjeu.libelle,
            'facteurs_influence': FacteurInfluenceSerializer(
                facteurs, many=True, context=self.get_serializer_context()
            ).data,
            'total': len(facteurs)
        })

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """
        #552 — Facteurs candidats au « lier » : tous les facteurs du plan
        (avec leurs enjeu_ids), pour proposer d'en rattacher un à un autre enjeu.

        GET /api/plans/facteurs-influence/by-plan/{plan_id}/
        """
        facteurs = self.get_queryset().filter(enjeux__id_pg=plan_id).distinct()
        return Response({
            'plan_id': int(plan_id),
            'facteurs_influence': FacteurInfluenceListSerializer(
                facteurs, many=True, context=self.get_serializer_context()
            ).data,
            'total': facteurs.count(),
        })

    @action(detail=True, methods=['post'], url_path='link')
    def link(self, request, pk=None):
        """
        #552 — Rattache (partage) ce facteur à un enjeu supplémentaire.

        POST /api/plans/facteurs-influence/{id}/link/  body: { "enjeu_id": <int> }
        Contraintes : même plan que le facteur, plan en brouillon.
        """
        facteur = self.get_object()
        enjeu_id = request.data.get('enjeu_id')
        if not enjeu_id:
            return Response({'detail': "enjeu_id requis."}, status=status.HTTP_400_BAD_REQUEST)
        enjeu = get_object_or_404(Enjeu, pk=enjeu_id)

        plan = facteur.get_plan_de_gestion()
        # Même plan uniquement.
        if plan is None or enjeu.id_pg_id != plan.pk:
            return Response(
                {'detail': "Un facteur ne peut être lié qu'à un enjeu du même plan de gestion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        blocked = self._assert_draft_or_403(plan)
        if blocked:
            return blocked

        max_ordre = CorFacteurEnjeu.objects.filter(id_enjeu=enjeu).aggregate(m=Max('ordre'))['m']
        CorFacteurEnjeu.objects.get_or_create(
            id_facteur_influence=facteur, id_enjeu=enjeu,
            defaults={'ordre': (max_ordre + 1) if max_ordre is not None else 0},
        )
        facteur.id_utilisateur_maj = request.user
        facteur.save(update_fields=['id_utilisateur_maj', 'date_maj'])
        return Response(
            FacteurInfluenceSerializer(facteur, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='unlink')
    def unlink(self, request, pk=None):
        """
        #552 — Détache ce facteur d'un enjeu. Si c'était le dernier enjeu lié,
        le facteur (et tout son sous-arbre) est supprimé.

        POST /api/plans/facteurs-influence/{id}/unlink/  body: { "enjeu_id": <int> }
        """
        facteur = self.get_object()
        enjeu_id = request.data.get('enjeu_id')
        if not enjeu_id:
            return Response({'detail': "enjeu_id requis."}, status=status.HTTP_400_BAD_REQUEST)

        plan = facteur.get_plan_de_gestion()
        blocked = self._assert_draft_or_403(plan)
        if blocked:
            return blocked

        with transaction.atomic():
            CorFacteurEnjeu.objects.filter(
                id_facteur_influence=facteur, id_enjeu_id=enjeu_id
            ).delete()
            if not facteur.enjeux.exists():
                facteur.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

        facteur.id_utilisateur_maj = request.user
        facteur.save(update_fields=['id_utilisateur_maj', 'date_maj'])
        return Response(
            FacteurInfluenceSerializer(facteur, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )


class PressionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Pressions.

    Endpoints:
    - GET /api/plans/pressions/ - Liste
    - GET /api/plans/pressions/{id}/ - Détail
    - POST /api/plans/pressions/ - Créer
    - PATCH /api/plans/pressions/{id}/ - Modifier
    - DELETE /api/plans/pressions/{id}/ - Supprimer
    - GET /api/plans/pressions/by-facteur/{facteur_id}/ - Par facteur
    """

    queryset = Pression.objects.select_related(
        'id_facteur_influence', 'id_utilisateur_ajout', 'id_utilisateur_maj',
        'id_type_pression'
    ).prefetch_related(
        'objectifs_operationnels', 'objectifs_operationnels__id_utilisateur_ajout',
        'objectifs_operationnels__pressions', 'objectifs_operationnels__pressions__id_facteur_influence',
        'objectifs_operationnels__resultats_attendus',
        'objectifs_operationnels__resultats_attendus__id_utilisateur_ajout',
        'objectifs_operationnels__resultats_attendus__indicateurs',
        'objectifs_operationnels__resultats_attendus__indicateurs__type_indicateur',
        'objectifs_operationnels__resultats_attendus__indicateurs__metriques',
        'objectifs_operationnels__resultats_attendus__indicateurs__metriques__type_metrique',
        'objectifs_operationnels__resultats_attendus__indicateurs__id_utilisateur_ajout',
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_pression']
    ordering = ['id_pression']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via le facteur d'influence parent."""
        fi_id = data.get('id_facteur_influence')
        if not fi_id:
            return None
        try:
            return FacteurInfluence.objects.get(pk=fi_id).get_plan_de_gestion()
        except FacteurInfluence.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PressionCreateSerializer
        return PressionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_facteur_influence__enjeux__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_facteur_influence__enjeux__id_pg__in=user_plan_ids) |
            Q(id_facteur_influence__enjeux__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_facteur_influence__enjeux__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les pressions d'un facteur d'influence (#249/#261).

        Payload: { "parent_id": <id_facteur_influence>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(self, request, parent_filter='id_facteur_influence')

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """
        Déplace une pression vers un autre facteur d'influence (#472).

        Payload : {"new_facteur_id": <int>, "position": <int>}

        Garde-fous :
        - Le facteur cible doit exister et être dans le même plan que l'ancien.
        - Le plan doit être en brouillon (verrou #248).
        - Renumérote les siblings dans le facteur cible.
        """
        pression = self.get_object()
        new_facteur_id = request.data.get('new_facteur_id')
        position = request.data.get('position', 0)

        if new_facteur_id is None:
            return Response(
                {"detail": "Payload invalide : 'new_facteur_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_facteur_id = int(new_facteur_id)
            position = int(position)
        except (TypeError, ValueError):
            return Response(
                {"detail": "'new_facteur_id' et 'position' doivent être des entiers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_facteur = FacteurInfluence.objects.get(pk=new_facteur_id)
        except FacteurInfluence.DoesNotExist:
            return Response(
                {"detail": "Facteur d'influence introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Garde : même plan que la source
        source_plan = pression.get_plan_de_gestion()
        target_plan = new_facteur.get_plan_de_gestion()
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

        with transaction.atomic():
            pression.id_facteur_influence = new_facteur
            pression.ordre = position
            pression.id_utilisateur_maj = request.user
            pression.save()

            # Renumérotation des siblings dans le facteur cible
            siblings = (
                Pression.objects
                .filter(id_facteur_influence=new_facteur)
                .exclude(pk=pression.pk)
                .order_by('ordre', 'id_pression')
            )
            for idx, sib in enumerate(siblings):
                new_pos = idx if idx < position else idx + 1
                if sib.ordre != new_pos:
                    sib.ordre = new_pos
                    sib.save(update_fields=['ordre'])

        serializer = PressionSerializer(pression)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path=r'by-facteur/(?P<facteur_id>\d+)')
    def by_facteur(self, request, facteur_id=None):
        """
        Récupérer les pressions d'un facteur d'influence.

        GET /api/plans/pressions/by-facteur/{facteur_id}/
        """
        facteur = get_object_or_404(FacteurInfluence, id_facteur_influence=facteur_id)
        pressions = self.get_queryset().filter(id_facteur_influence=facteur)
        return Response({
            'facteur_id': int(facteur_id),
            'facteur_libelle': facteur.libelle,
            'pressions': PressionSerializer(pressions, many=True).data,
            'total': pressions.count()
        })


class ObjectifLongTermeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Objectifs à Long Terme.

    Endpoints:
    - GET /api/plans/objectifs-long-terme/ - Liste
    - GET /api/plans/objectifs-long-terme/{id}/ - Détail
    - POST /api/plans/objectifs-long-terme/ - Créer
    - PATCH /api/plans/objectifs-long-terme/{id}/ - Modifier
    - DELETE /api/plans/objectifs-long-terme/{id}/ - Supprimer
    - GET /api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/ - Par enjeu
    """

    queryset = ObjectifLongTerme.objects.select_related(
        'id_enjeu', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'niveaux_exigence', 'niveaux_exigence__id_utilisateur_ajout'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_olt']
    ordering = ['id_olt']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via l'enjeu parent."""
        enjeu_id = data.get('id_enjeu')
        if not enjeu_id:
            return None
        try:
            return Enjeu.objects.only('id_pg').get(pk=enjeu_id).get_plan_de_gestion()
        except Enjeu.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action == 'list':
            return ObjectifLongTermeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ObjectifLongTermeCreateSerializer
        return ObjectifLongTermeSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les objectifs à long terme d'un enjeu (#249/#261).

        Payload: { "parent_id": <id_enjeu>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(self, request, parent_filter='id_enjeu')

    @action(detail=False, methods=['get'], url_path=r'by-enjeu/(?P<enjeu_id>\d+)')
    def by_enjeu(self, request, enjeu_id=None):
        """
        Récupérer les objectifs à long terme d'un enjeu.

        GET /api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/
        """
        enjeu = get_object_or_404(Enjeu, id_enjeu=enjeu_id)
        olts = self.get_queryset().filter(id_enjeu=enjeu)
        return Response({
            'enjeu_id': int(enjeu_id),
            'enjeu_libelle': enjeu.libelle,
            'objectifs_long_terme': ObjectifLongTermeSerializer(olts, many=True).data,
            'total': olts.count()
        })


class NiveauExigenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Niveaux d'Exigence.

    Endpoints:
    - GET /api/plans/niveaux-exigence/ - Liste
    - GET /api/plans/niveaux-exigence/{id}/ - Détail
    - POST /api/plans/niveaux-exigence/ - Créer
    - PATCH /api/plans/niveaux-exigence/{id}/ - Modifier
    - DELETE /api/plans/niveaux-exigence/{id}/ - Supprimer
    - GET /api/plans/niveaux-exigence/by-olt/{olt_id}/ - Par OLT
    """

    queryset = NiveauExigence.objects.select_related(
        'id_olt', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_ne']
    ordering = ['id_ne']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via l'OLT parent."""
        olt_id = data.get('id_olt')
        if not olt_id:
            return None
        try:
            return ObjectifLongTerme.objects.select_related('id_enjeu').get(pk=olt_id).get_plan_de_gestion()
        except ObjectifLongTerme.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return NiveauExigenceCreateSerializer
        return NiveauExigenceSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_olt__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les niveaux d'exigence d'un OLT (#249/#261).

        Payload: { "parent_id": <id_olt>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(self, request, parent_filter='id_olt')

    @action(detail=False, methods=['get'], url_path=r'by-olt/(?P<olt_id>\d+)')
    def by_olt(self, request, olt_id=None):
        """
        Récupérer les niveaux d'exigence d'un objectif à long terme.

        GET /api/plans/niveaux-exigence/by-olt/{olt_id}/
        """
        olt = get_object_or_404(ObjectifLongTerme, id_olt=olt_id)
        niveaux = self.get_queryset().filter(id_olt=olt)
        return Response({
            'olt_id': int(olt_id),
            'olt_libelle': olt.libelle,
            'niveaux_exigence': NiveauExigenceSerializer(niveaux, many=True).data,
            'total': niveaux.count()
        })


class ObjectifOperationnelViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Objectifs Opérationnels.

    Endpoints:
    - GET /api/plans/objectifs-operationnels/ - Liste
    - GET /api/plans/objectifs-operationnels/{id}/ - Détail
    - POST /api/plans/objectifs-operationnels/ - Créer
    - PATCH /api/plans/objectifs-operationnels/{id}/ - Modifier
    - DELETE /api/plans/objectifs-operationnels/{id}/ - Supprimer
    - GET /api/plans/objectifs-operationnels/by-pression/{pression_id}/ - Par pression
    """

    queryset = ObjectifOperationnel.objects.select_related(
        'id_utilisateur_ajout', 'id_utilisateur_maj', 'id_enjeu',
    ).prefetch_related(
        'pressions', 'pressions__id_facteur_influence',
        'pressions__id_facteur_influence__enjeux',
        'resultats_attendus', 'resultats_attendus__id_utilisateur_ajout',
        'resultats_attendus__indicateurs',
        'resultats_attendus__indicateurs__type_indicateur',
        'resultats_attendus__indicateurs__metriques',
        'resultats_attendus__indicateurs__metriques__type_metrique',
        'resultats_attendus__indicateurs__id_utilisateur_ajout',
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_oo']
    ordering = ['id_oo']

    def get_plan_for_payload(self, data):
        """#248 — check draft via la première pression rattachée (M2M),
        ou via l'enjeu rattaché directement (#337, cas FCR sans pression)."""
        pression_ids = data.get('pression_ids') or []
        if pression_ids:
            try:
                return Pression.objects.select_related(
                    'id_facteur_influence'
                ).get(pk=pression_ids[0]).get_plan_de_gestion()
            except Pression.DoesNotExist:
                return None
        enjeu_id = data.get('id_enjeu')
        if enjeu_id:
            try:
                return Enjeu.objects.only('id_pg').get(pk=enjeu_id).get_plan_de_gestion()
            except Enjeu.DoesNotExist:
                return None
        return None

    def get_serializer_class(self):
        if self.action == 'list':
            return ObjectifOperationnelListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ObjectifOperationnelCreateSerializer
        return ObjectifOperationnelSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        # #337 — un OO est rattaché soit via ses pressions, soit directement à
        # l'enjeu (FCR). Les deux chemins sont pris en compte pour le scoping.
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(pressions__id_facteur_influence__enjeux__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme)
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(pressions__id_facteur_influence__enjeux__id_pg__in=user_plan_ids) |
            Q(pressions__id_facteur_influence__enjeux__id_pg__sites__site__corrolesite__id_role=user) |
            Q(pressions__id_facteur_influence__enjeux__id_pg__statut='valide') |
            Q(id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les objectifs opérationnels d'un enjeu (#249/#261).

        Les OO sont rattachés à un enjeu soit transitivement via leurs pressions
        (Enjeu → FacteurInfluence → Pression ↔ OO M2M), soit directement via
        ``id_enjeu`` (#337, cas FCR).

        Payload: { "parent_id": <id_enjeu>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(
            self,
            request,
            parent_filter=lambda pid, _req: (
                Q(pressions__id_facteur_influence__enjeux=pid) |
                Q(id_enjeu=pid)
            ),
        )

    @action(detail=False, methods=['get'], url_path=r'by-pression/(?P<pression_id>\d+)')
    def by_pression(self, request, pression_id=None):
        """
        Récupérer les objectifs opérationnels d'une pression.

        GET /api/plans/objectifs-operationnels/by-pression/{pression_id}/
        """
        pression = get_object_or_404(Pression, id_pression=pression_id)
        oos = self.get_queryset().filter(pressions=pression)
        return Response({
            'pression_id': int(pression_id),
            'pression_libelle': pression.libelle,
            'objectifs_operationnels': ObjectifOperationnelSerializer(oos, many=True).data,
            'total': oos.count()
        })

    @staticmethod
    def _assert_draft_or_403(plan):
        """#248/#552 — 403 si le plan n'est pas éditable (hors brouillon)."""
        if plan is None or plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            return Response(
                {'detail': CanModifyOnlyDraftPlan.message},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """
        #552 — OO candidats au « lier » : tous les OO du plan (avec leurs
        pressions et shared_enjeu_ids), pour en rattacher un à une pression
        d'un autre enjeu.

        GET /api/plans/objectifs-operationnels/by-plan/{plan_id}/
        """
        oos = self.get_queryset().filter(
            Q(pressions__id_facteur_influence__enjeux__id_pg=plan_id) |
            Q(id_enjeu__id_pg=plan_id)
        ).distinct()
        return Response({
            'plan_id': int(plan_id),
            'objectifs_operationnels': ObjectifOperationnelListSerializer(
                oos, many=True, context=self.get_serializer_context()
            ).data,
            'total': oos.count(),
        })

    @action(detail=True, methods=['post'], url_path='link')
    def link(self, request, pk=None):
        """
        #552 — Rattache (partage) cet OO à une pression d'un autre enjeu. Tout
        le sous-arbre de l'OO suit (résultats attendus, indicateurs, suivi…).

        POST /api/plans/objectifs-operationnels/{id}/link/  body: { "pression_id": <int> }
        Contraintes : même plan que l'OO, plan en brouillon.
        """
        oo = self.get_object()
        pression_id = request.data.get('pression_id')
        if not pression_id:
            return Response({'detail': "pression_id requis."}, status=status.HTTP_400_BAD_REQUEST)
        pression = get_object_or_404(
            Pression.objects.select_related('id_facteur_influence'), pk=pression_id
        )

        oo_plan = oo.get_plan_de_gestion()
        pression_plan = pression.get_plan_de_gestion()
        if oo_plan is None or pression_plan is None or oo_plan.pk != pression_plan.pk:
            return Response(
                {'detail': "Un OO ne peut être lié qu'à une pression du même plan de gestion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        blocked = self._assert_draft_or_403(oo_plan)
        if blocked:
            return blocked

        oo.pressions.add(pression)
        oo.id_utilisateur_maj = request.user
        oo.save(update_fields=['id_utilisateur_maj', 'date_maj'])
        return Response(
            ObjectifOperationnelSerializer(
                self.get_queryset().get(pk=oo.pk), context=self.get_serializer_context()
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='unlink')
    def unlink(self, request, pk=None):
        """
        #552 — Détache cet OO d'une pression. S'il ne reste plus aucune pression
        ni rattachement direct (FCR), l'OO est supprimé.

        POST /api/plans/objectifs-operationnels/{id}/unlink/  body: { "pression_id": <int> }
        """
        oo = self.get_object()
        pression_id = request.data.get('pression_id')
        if not pression_id:
            return Response({'detail': "pression_id requis."}, status=status.HTTP_400_BAD_REQUEST)

        plan = oo.get_plan_de_gestion()
        blocked = self._assert_draft_or_403(plan)
        if blocked:
            return blocked

        with transaction.atomic():
            oo.pressions.remove(pression_id)
            if not oo.pressions.exists() and not oo.id_enjeu_id:
                oo.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

        oo.id_utilisateur_maj = request.user
        oo.save(update_fields=['id_utilisateur_maj', 'date_maj'])
        return Response(
            ObjectifOperationnelSerializer(
                self.get_queryset().get(pk=oo.pk), context=self.get_serializer_context()
            ).data,
            status=status.HTTP_200_OK,
        )


class ResultatAttenduViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Résultats Attendus.

    Endpoints:
    - GET /api/plans/resultats-attendus/ - Liste
    - GET /api/plans/resultats-attendus/{id}/ - Détail
    - POST /api/plans/resultats-attendus/ - Créer
    - PATCH /api/plans/resultats-attendus/{id}/ - Modifier
    - DELETE /api/plans/resultats-attendus/{id}/ - Supprimer
    - GET /api/plans/resultats-attendus/by-oo/{oo_id}/ - Par OO
    """

    queryset = ResultatAttendu.objects.select_related(
        'id_oo', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj', 'id_ra']
    ordering = ['id_ra']

    def get_plan_for_payload(self, data):
        """#248 — check draft via la première pression liée à l'OO parent."""
        oo_id = data.get('id_oo')
        if not oo_id:
            return None
        try:
            return ObjectifOperationnel.objects.get(pk=oo_id).get_plan_de_gestion()
        except ObjectifOperationnel.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ResultatAttenduCreateSerializer
        return ResultatAttenduSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_oo__pressions__id_facteur_influence__enjeux__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_oo__pressions__id_facteur_influence__enjeux__id_pg__in=user_plan_ids) |
            Q(id_oo__pressions__id_facteur_influence__enjeux__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_oo__pressions__id_facteur_influence__enjeux__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les résultats attendus d'un OO (#249/#261).

        Payload: { "parent_id": <id_oo>, "ordered_ids": [id1, id2, ...] }
        """
        return do_reorder(self, request, parent_filter='id_oo')

    @action(detail=False, methods=['get'], url_path=r'by-oo/(?P<oo_id>\d+)')
    def by_oo(self, request, oo_id=None):
        """
        Récupérer les résultats attendus d'un objectif opérationnel.

        GET /api/plans/resultats-attendus/by-oo/{oo_id}/
        """
        oo = get_object_or_404(ObjectifOperationnel, id_oo=oo_id)
        resultats = self.get_queryset().filter(id_oo=oo)
        return Response({
            'oo_id': int(oo_id),
            'oo_libelle': oo.libelle,
            'resultats_attendus': ResultatAttenduSerializer(resultats, many=True).data,
            'total': resultats.count()
        })


# Import models for stats action
from django.db import models


class CorEnjeuFichierViewSet(viewsets.ModelViewSet):
    """
    #237 — Documents (numériques + références papier) du patrimoine
    « Documents » d'un enjeu géologique.

    - Lecture (list/retrieve/download) : tout utilisateur authentifié, bornée
      par `get_queryset()` aux enjeux des plans accessibles.
    - Écriture (upload/papier/suppression) : référent du plan, sur brouillon
      uniquement (`CanModifyOnlyDraftPlan`).
    """

    queryset = CorEnjeuFichier.objects.all().select_related(
        'id_enjeu', 'id_enjeu__id_pg', 'id_utilisateur_upload'
    )
    serializer_class = CorEnjeuFichierSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['id_enjeu', 'support']
    ordering_fields = ['ordre_affichage', 'date_upload', 'nom_fichier']
    ordering = ['ordre_affichage', 'date_upload']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'download'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsReferent(), CanModifyOnlyDraftPlan()]

    def _accessible_enjeu_ids(self):
        """IDs des enjeux accessibles via le scope de l'EnjeuViewSet."""
        enjeu_viewset = EnjeuViewSet()
        enjeu_viewset.request = self.request
        enjeu_viewset.kwargs = {}
        return enjeu_viewset.get_queryset().values_list('id_enjeu', flat=True)

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin() or user.is_redacteur_principal():
            return self.queryset
        return self.queryset.filter(id_enjeu__in=self._accessible_enjeu_ids())

    def get_plan_for_payload(self, data):
        """Check draft à la création : remonte le plan depuis l'enjeu."""
        enjeu_id = data.get('id_enjeu')
        if not enjeu_id:
            return None
        try:
            return Enjeu.objects.select_related('id_pg').get(pk=enjeu_id).get_plan_de_gestion()
        except Enjeu.DoesNotExist:
            return None

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_upload=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Télécharger un document numérique : GET /api/plans/enjeux-fichiers/{id}/download/"""
        import os
        import mimetypes
        from django.conf import settings
        from django.http import HttpResponse

        fichier = self.get_object()
        # Scope d'accès (mêmes règles que get_queryset)
        if not self.get_queryset().filter(pk=fichier.pk).exists():
            return Response({'error': 'Permissions insuffisantes'}, status=status.HTTP_403_FORBIDDEN)

        if fichier.support != 'numerique' or not fichier.chemin_fichier:
            return HttpResponse('Document papier : aucun fichier à télécharger',
                                content_type='text/plain; charset=utf-8', status=404)

        chemin = fichier.chemin_fichier
        if not os.path.isabs(chemin):
            chemin = os.path.join(settings.MEDIA_ROOT, chemin)
        if not os.path.exists(chemin):
            return HttpResponse('Fichier non disponible sur le serveur',
                                content_type='text/plain; charset=utf-8', status=404)

        content_type, _ = mimetypes.guess_type(fichier.nom_fichier)
        content_type = content_type or 'application/octet-stream'
        with open(chemin, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type=content_type)
        ext = (fichier.extension or '').lower().lstrip('.')
        disposition = 'inline' if ext in ('pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp') else 'attachment'
        response['Content-Disposition'] = f'{disposition}; filename="{fichier.nom_fichier}"'
        response['Content-Length'] = len(content)
        return response
