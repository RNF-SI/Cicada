"""
Vues API REST pour les Enjeux, FCR et Responsabilités.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    EtatActuel, ObjectifLongTerme, NiveauExigence,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie
)
from .models import PlanGestion
from apps.users.models import Site
from .serializers_enjeux import (
    EnjeuListSerializer, EnjeuDetailSerializer, EnjeuCreateSerializer,
    FacteurInfluenceSerializer, FacteurInfluenceListSerializer, FacteurInfluenceCreateSerializer,
    PressionSerializer, PressionCreateSerializer,
    EtatActuelSerializer, EtatActuelListSerializer, EtatActuelCreateSerializer,
    ObjectifLongTermeSerializer, ObjectifLongTermeListSerializer, ObjectifLongTermeCreateSerializer,
    NiveauExigenceSerializer, NiveauExigenceCreateSerializer,
    ResponsabiliteListSerializer, ResponsabiliteDetailSerializer, ResponsabiliteCreateSerializer,
    CorEnjeuTaxonSerializer, CorEnjeuHabitatSerializer
)
from apps.users.permissions import IsReferent, IsSuperAdmin, IsAdminOrganisme
from .filters_enjeux import EnjeuFilter, ResponsabiliteFilter


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

    queryset = Enjeu.objects.select_related(
        'id_pg', 'id_categorie', 'id_categorie_fcr', 'id_importance',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'taxons', 'habitats', 'geologies',
        'facteurs_influence', 'facteurs_influence__pressions',
        'facteurs_influence__id_utilisateur_ajout',
        'facteurs_influence__pressions__id_utilisateur_ajout',
        'objectifs_long_terme', 'objectifs_long_terme__id_utilisateur_ajout',
        'objectifs_long_terme__etat_actuel',
        'objectifs_long_terme__etat_actuel__id_utilisateur_ajout',
        'objectifs_long_terme__niveaux_exigence',
        'objectifs_long_terme__niveaux_exigence__id_utilisateur_ajout',
        'objectifs_long_terme__niveaux_exigence__indicateurs',
        'objectifs_long_terme__niveaux_exigence__indicateurs__type_indicateur',
        'objectifs_long_terme__niveaux_exigence__indicateurs__metriques',
        'objectifs_long_terme__niveaux_exigence__indicateurs__metriques__type_metrique',
        'objectifs_long_terme__niveaux_exigence__indicateurs__id_utilisateur_ajout',
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EnjeuFilter
    search_fields = ['libelle', 'intitule_court', 'description', 'etat_enjeu']
    ordering_fields = ['rang', 'libelle', 'date_ajout', 'date_maj']
    ordering = ['rang', 'libelle']

    def get_serializer_class(self):
        """Choisir le serializer selon l'action."""
        if self.action == 'list':
            return EnjeuListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EnjeuCreateSerializer
        return EnjeuDetailSerializer

    def get_queryset(self):
        """Filtrer selon les permissions utilisateur."""
        user = self.request.user
        queryset = self.queryset

        # Super admin : voir tous les enjeux
        if user.is_super_admin():
            return queryset

        # Admin organisme : voir les enjeux des plans de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        # Référent : voir les enjeux des plans dont il est référent
        if user.is_referent():
            return queryset.filter(
                Q(id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_pg__referents=user)
            ).distinct()

        # Utilisateur : voir les enjeux des plans validés
        return queryset.filter(id_pg__statut='valide')

    def perform_create(self, serializer):
        """Définir l'utilisateur créateur."""
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        """Définir l'utilisateur modificateur."""
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-plan/(?P<plan_id>\d+)')
    def by_plan(self, request, plan_id=None):
        """
        Récupérer les enjeux et FCR d'un plan spécifique.

        GET /api/plans/enjeux/by-plan/{plan_id}/
        """
        # Vérifier que le plan existe et que l'utilisateur y a accès
        plan = get_object_or_404(PlanGestion, id_pg=plan_id)

        # Vérifier les permissions
        if not request.user.is_super_admin():
            if request.user.is_admin_organisme() and request.user.id_organisme:
                if not plan.sites.filter(site__corogsite__uuid_og=request.user.id_organisme).exists():
                    return Response(
                        {'error': 'Vous n\'avez pas accès à ce plan'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif not plan.referents.filter(id_role=request.user.id_role).exists():
                if plan.statut != 'valide':
                    return Response(
                        {'error': 'Vous n\'avez pas accès à ce plan'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        enjeux = self.get_queryset().filter(id_pg=plan)

        # Séparer enjeux et FCR
        enjeux_list = enjeux.filter(id_categorie__mnemonique='ENJEU').order_by('rang', 'libelle')
        fcr_list = enjeux.filter(id_categorie__mnemonique='FCR').order_by('libelle')

        return Response({
            'plan_id': int(plan_id),
            'plan_nom': plan.nom,
            'enjeux': EnjeuDetailSerializer(enjeux_list, many=True).data,
            'fcr': EnjeuDetailSerializer(fcr_list, many=True).data,
            'total_enjeux': enjeux_list.count(),
            'total_fcr': fcr_list.count()
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
        if not request.user.is_super_admin():
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
        'id_enjeu', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('pressions', 'pressions__id_utilisateur_ajout')

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj']
    ordering = ['libelle']

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

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(id_enjeu__id_pg__statut='valide')

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-enjeu/(?P<enjeu_id>\d+)')
    def by_enjeu(self, request, enjeu_id=None):
        """
        Récupérer les facteurs d'influence d'un enjeu.

        GET /api/plans/facteurs-influence/by-enjeu/{enjeu_id}/
        """
        enjeu = get_object_or_404(Enjeu, id_enjeu=enjeu_id)
        facteurs = self.get_queryset().filter(id_enjeu=enjeu)
        return Response({
            'enjeu_id': int(enjeu_id),
            'enjeu_libelle': enjeu.libelle,
            'facteurs_influence': FacteurInfluenceSerializer(facteurs, many=True).data,
            'total': facteurs.count()
        })


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
        'id_facteur_influence', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj']
    ordering = ['libelle']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PressionCreateSerializer
        return PressionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_facteur_influence__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(id_facteur_influence__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_facteur_influence__id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(id_facteur_influence__id_enjeu__id_pg__statut='valide')

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

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


class EtatActuelViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les États Actuels.

    Endpoints:
    - GET /api/plans/etats-actuels/ - Liste
    - GET /api/plans/etats-actuels/{id}/ - Détail
    - POST /api/plans/etats-actuels/ - Créer
    - PATCH /api/plans/etats-actuels/{id}/ - Modifier
    - DELETE /api/plans/etats-actuels/{id}/ - Supprimer
    - GET /api/plans/etats-actuels/by-enjeu/{enjeu_id}/ - Par enjeu
    """

    queryset = EtatActuel.objects.select_related(
        'id_olt', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj']
    ordering = ['libelle']

    def get_serializer_class(self):
        if self.action == 'list':
            return EtatActuelListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EtatActuelCreateSerializer
        return EtatActuelSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_olt__id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(id_olt__id_enjeu__id_pg__statut='valide')

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-olt/(?P<olt_id>\d+)')
    def by_olt(self, request, olt_id=None):
        """
        Récupérer l'état actuel d'un OLT.

        GET /api/plans/etats-actuels/by-olt/{olt_id}/
        """
        olt = get_object_or_404(ObjectifLongTerme, id_olt=olt_id)
        etats = self.get_queryset().filter(id_olt=olt)
        return Response({
            'olt_id': int(olt_id),
            'olt_libelle': olt.libelle,
            'etats_actuels': EtatActuelSerializer(etats, many=True).data,
            'total': etats.count()
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
    - GET /api/plans/objectifs-long-terme/by-etat/{etat_id}/ - Par état actuel
    """

    queryset = ObjectifLongTerme.objects.select_related(
        'id_enjeu', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'etat_actuel', 'etat_actuel__id_utilisateur_ajout',
        'niveaux_exigence', 'niveaux_exigence__id_utilisateur_ajout'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj']
    ordering = ['libelle']

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

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(id_enjeu__id_pg__statut='valide')

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

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

    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['libelle', 'description']
    ordering_fields = ['libelle', 'date_ajout', 'date_maj']
    ordering = ['libelle']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return NiveauExigenceCreateSerializer
        return NiveauExigenceSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        if user.is_referent():
            return queryset.filter(
                Q(id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
                Q(id_olt__id_enjeu__id_pg__referents=user)
            ).distinct()

        return queryset.filter(id_olt__id_enjeu__id_pg__statut='valide')

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

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


# Import models for stats action
from django.db import models
