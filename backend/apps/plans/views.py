"""
Vues API REST pour les Plans de Gestion.
"""
import json as json_module
import os
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.storage import default_storage
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import PlanGestion, CorSitePg, CorPgFichier, CorRolePlan
from .serializers import (
    PlanGestionListSerializer, PlanGestionDetailSerializer,
    PlanGestionGeoJSONSerializer, PlanGestionCreateSerializer,
    PlanDuplicateOptionsSerializer,
    CorSitePgSerializer, CorPgFichierSerializer
)
from .services import PlanDuplicationService
from .filters import PlanGestionFilter, CorPgFichierFilter
from apps.users.permissions import (
    IsReferent, IsSuperAdmin, IsAdminOrganisme
)


class PlanGestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Plans de Gestion.

    Fonctionnalités:
    - CRUD complet avec permissions
    - Filtres avancés (statut, période, organisme, sites)
    - Recherche textuelle
    - Support GeoJSON
    - Gestion de fichiers
    - Assignation de sites et référents
    """

    def _can_manage_plan(self, user, plan):
        """Vérifie si l'utilisateur peut gérer ce plan (admin_og+ ou référent du plan)."""
        if user.is_admin_organisme():
            return True
        return plan.referents.filter(pk=user.pk).exists()

    queryset = PlanGestion.objects.all().select_related(
        'id_evaluation', 'id_redacteur_type',
        'id_utilisateur_ajout', 'id_utilisateur_maj',
        'plan_parent', 'id_type_document'
    ).prefetch_related('sites__site__id_type_site', 'fichiers', 'referents', 'children')

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsReferent()]
        return super().get_permissions()
    filterset_class = PlanGestionFilter
    search_fields = [
        'nom', 'commentaire', 'redacteur_nom', 'id_cdr'
    ]
    ordering_fields = [
        'nom', 'annee_debut', 'annee_fin', 'statut', 'date_ajout', 'date_maj'
    ]
    ordering = ['-date_maj']
    
    def get_serializer_class(self):
        """Choisir le serializer selon l'action."""
        if self.action == 'list':
            return PlanGestionListSerializer
        elif self.action == 'create':
            return PlanGestionCreateSerializer
        else:
            return PlanGestionDetailSerializer
    
    def get_queryset(self):
        """Filtrer selon les permissions utilisateur.

        Logique :
        - Super admin : tous les plans
        - Admin organisme : plans des sites de son organisme
        - Référent / Utilisateur : plans de ses sites assignés
          + plans dont il est référent/membre + plans de son organisme

        Query params:
        - scope=mine : exclut les plans de l'organisme auxquels l'utilisateur
          n'a pas accès directement (utilisé par la page de duplication)
        """
        from django.db.models import Q

        user = self.request.user
        queryset = self.queryset
        scope = self.request.query_params.get('scope')

        # Super admin : voir tous les plans
        if user.is_super_admin():
            return queryset

        # Admin organisme : voir les plans des sites de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        # Référent / Utilisateur : plans personnels + plans de l'organisme
        conditions = Q()

        # Plans des sites assignés à l'utilisateur
        conditions |= Q(sites__site__corrolesite__id_role=user)

        # Plans dont il est référent
        conditions |= Q(referents=user)

        # Plans dont il est membre direct (CorRolePlan)
        conditions |= Q(membres__id_role=user)

        # Plans de son organisme (pour pouvoir en demander l'accès)
        # Exclus si scope=mine (ex: page de duplication)
        if scope != 'mine' and user.id_organisme:
            conditions |= Q(sites__site__corogsite__uuid_og=user.id_organisme)

        return queryset.filter(conditions).distinct()
    
    def perform_create(self, serializer):
        """Définir l'utilisateur créateur."""
        serializer.save(id_utilisateur_ajout=self.request.user)
    
    def perform_update(self, serializer):
        """Définir l'utilisateur modificateur."""
        serializer.save(id_utilisateur_maj=self.request.user)
    
    @action(detail=False, methods=['get'], url_path=r'by-slug/(?P<slug>[-\w]+)')
    def by_slug(self, request, slug=None):
        """
        Récupérer un plan par son slug.

        GET /api/plans/plans/by-slug/{slug}/
        """
        plan = get_object_or_404(PlanGestion, slug=slug)

        # Vérifier les permissions via le queryset filtré
        if not self.get_queryset().filter(pk=plan.pk).exists():
            return Response(
                {'error': 'Vous n\'avez pas accès à ce plan'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def geojson_list(self, request):
        """
        Liste des plans au format GeoJSON FeatureCollection.

        GET /api/plans/geojson_list/
        """
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(geometrie__isnull=False)
        
        features = []
        for plan in queryset:
            serializer = PlanGestionGeoJSONSerializer(plan)
            feature = {
                'type': 'Feature',
                'geometry': json_module.loads(plan.geometrie.json) if plan.geometrie else None,
                'properties': serializer.data
            }
            features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return Response(geojson)
    
    @action(detail=True, methods=['get'])
    def geojson(self, request, pk=None):
        """
        Plan individuel au format GeoJSON Feature.
        
        GET /api/plans/{id}/geojson/
        """
        plan = self.get_object()
        
        if not plan.geometrie:
            return Response({'error': 'Ce plan n\'a pas de géométrie'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        serializer = PlanGestionGeoJSONSerializer(plan)
        feature = {
            'type': 'Feature',
            'geometry': json_module.loads(plan.geometrie.json),
            'properties': serializer.data
        }

        return Response(feature)
    
    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def assign_site(self, request, pk=None):
        """
        Assigner un site à un plan.

        POST /api/plans/{id}/assign_site/
        Body: {"site_id": 123, "rang": 1, "commentaire": "Site principal"}
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        site_id = request.data.get('site_id')
        rang = request.data.get('rang')
        commentaire = request.data.get('commentaire', '')
        
        if not site_id:
            return Response({'error': 'site_id requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.users.models import Site
            site = Site.objects.get(id_site=site_id)

            # Créer ou mettre à jour la relation
            cor_site_pg, created = CorSitePg.objects.update_or_create(
                plan_de_gestion=plan,
                site=site,
                defaults={
                    'rang': rang,
                    'commentaire': commentaire
                }
            )

            serializer = CorSitePgSerializer(cor_site_pg)

            return Response({
                'message': 'Site assigné avec succès' if created else 'Relation mise à jour',
                'relation': serializer.data
            })

        except Site.DoesNotExist:
            return Response({'error': 'Site non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['delete'],
            permission_classes=[permissions.IsAuthenticated])
    def remove_site(self, request, pk=None):
        """
        Retirer un site d'un plan.

        DELETE /api/plans/{id}/remove_site/?site_id=123
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        site_id = request.query_params.get('site_id')
        
        if not site_id:
            return Response({'error': 'site_id requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cor_site_pg = CorSitePg.objects.get(
                plan_de_gestion=plan,
                site__id_site=site_id
            )

            cor_site_pg.delete()

            return Response({'message': 'Site retiré du plan'})

        except CorSitePg.DoesNotExist:
            return Response({'error': 'Relation non trouvée'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def replace_site(self, request, pk=None):
        """
        Remplacer un site par un autre dans un plan.
        Utile pour réassigner un plan lié à un site rejeté/invalide.

        POST /api/plans/{id}/replace_site/
        Body: {"old_site_id": 123, "new_site_id": 456}
        """
        from apps.users.models import Site

        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        old_site_id = request.data.get('old_site_id')
        new_site_id = request.data.get('new_site_id')

        if not old_site_id or not new_site_id:
            return Response({'error': 'old_site_id et new_site_id sont requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Vérifier que le nouveau site existe
        try:
            new_site = Site.objects.get(id_site=new_site_id)
        except Site.DoesNotExist:
            return Response({'error': 'Nouveau site non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

        # Vérifier que l'ancien site est bien lié au plan
        try:
            old_cor = CorSitePg.objects.get(
                plan_de_gestion=plan,
                site__id_site=old_site_id
            )
        except CorSitePg.DoesNotExist:
            return Response({'error': 'Ancien site non lié à ce plan'},
                          status=status.HTTP_404_NOT_FOUND)

        # Vérifier que le nouveau site n'est pas déjà lié
        if CorSitePg.objects.filter(plan_de_gestion=plan, site=new_site).exists():
            # Le nouveau site est déjà lié, on supprime juste l'ancien
            old_cor.delete()
            return Response({
                'message': 'Ancien site retiré (le nouveau était déjà lié)',
                'plan_id': plan.id_pg
            })

        # Remplacer: mettre à jour l'association existante
        old_cor.site = new_site
        old_cor.save()

        # Mettre à jour le modificateur
        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=['id_utilisateur_maj', 'date_maj'])

        return Response({
            'message': f'Site remplacé avec succès',
            'plan_id': plan.id_pg,
            'old_site_id': old_site_id,
            'new_site_id': new_site_id,
            'new_site_name': new_site.nom_site
        })

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def assign_referent(self, request, pk=None):
        """
        Assigner un référent à un plan.

        POST /api/plans/{id}/assign_referent/
        Body: {"referent_id": 123}
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        referent_id = request.data.get('referent_id')

        if not referent_id:
            return Response({'error': 'referent_id requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.users.models import Role
            referent = Role.objects.get(id_role=referent_id)

            plan.referents.add(referent)

            # Sync CorRolePlan
            CorRolePlan.objects.update_or_create(
                id_role=referent,
                plan_de_gestion=plan,
                defaults={'referent': True}
            )

            return Response({'message': f'Référent {referent} assigné au plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'],
            permission_classes=[permissions.IsAuthenticated])
    def remove_referent(self, request, pk=None):
        """
        Retirer un référent d'un plan.

        DELETE /api/plans/{id}/remove_referent/?referent_id=123
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        referent_id = request.query_params.get('referent_id')

        if not referent_id:
            return Response({'error': 'referent_id requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.users.models import Role
            referent = Role.objects.get(id_role=referent_id)

            if referent not in plan.referents.all():
                return Response({'error': 'Ce référent n\'est pas assigné à ce plan'},
                              status=status.HTTP_400_BAD_REQUEST)

            plan.referents.remove(referent)

            # Sync CorRolePlan: downgrade to member (keep association)
            CorRolePlan.objects.filter(
                id_role=referent,
                plan_de_gestion=plan
            ).update(referent=False)

            return Response({'message': f'Référent {referent} retiré du plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def assign_member(self, request, pk=None):
        """
        Ajouter un membre (non-référent) à un plan.

        POST /api/plans/{id}/assign_member/
        Body: {"user_id": 123}
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'user_id requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.users.models import Role
            user = Role.objects.get(id_role=user_id)

            cor, created = CorRolePlan.objects.get_or_create(
                id_role=user,
                plan_de_gestion=plan,
                defaults={'referent': False}
            )
            if not created and cor.referent:
                return Response({'error': 'Cet utilisateur est déjà référent de ce plan'},
                              status=status.HTTP_400_BAD_REQUEST)
            if not created:
                return Response({'error': 'Cet utilisateur est déjà membre de ce plan'},
                              status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': f'Membre {user} ajouté au plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'],
            permission_classes=[permissions.IsAuthenticated])
    def remove_member(self, request, pk=None):
        """
        Retirer un membre d'un plan (supprime l'association complètement).

        DELETE /api/plans/{id}/remove_member/?user_id=123
        """
        plan = self.get_object()

        if not self._can_manage_plan(request.user, plan):
            return Response({'error': 'Vous devez être référent de ce plan ou administrateur.'},
                          status=status.HTTP_403_FORBIDDEN)
        user_id = request.query_params.get('user_id')

        if not user_id:
            return Response({'error': 'user_id requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.users.models import Role
            user = Role.objects.get(id_role=user_id)

            cor = CorRolePlan.objects.filter(
                id_role=user,
                plan_de_gestion=plan
            ).first()

            if not cor:
                return Response({'error': 'Cet utilisateur n\'est pas membre de ce plan'},
                              status=status.HTTP_400_BAD_REQUEST)

            # Also remove from M2M referents if present
            plan.referents.remove(user)
            cor.delete()

            return Response({'message': f'Membre {user} retiré du plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='mindmap')
    def mindmap(self, request, pk=None):
        """
        Arbre hiérarchique du plan pour la mind map.

        GET /api/plans/plans/{id}/mindmap/
        """
        plan = self.get_object()

        from .models_enjeux import (
            Enjeu, FacteurInfluence, Pression,
            ObjectifLongTerme, EtatActuel, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu
        )
        from .models_indicateurs import Indicateur, Metrique, Mesure
        from .models_operations import (
            Operation, OperationAnnee, FinanceOperation,
            SuiviInventaire, Protocole
        )

        def build_tree():
            root = {
                'name': plan.nom,
                'entityType': 'plan',
                'id': plan.id_pg,
                'children': []
            }

            # Fetch enjeux with deep prefetch
            enjeux = (
                Enjeu.objects
                .filter(id_pg=plan)
                .select_related('id_categorie')
                .prefetch_related(
                    'facteurs_influence__pressions',
                    'etats_actuels__objectifs_long_terme__niveaux_exigence__indicateurs__metriques__mesures',
                    'facteurs_influence__objectifs_operationnels__resultats_attendus__indicateurs__metriques__mesures',
                )
                .order_by('rang', 'libelle')
            )

            # Pre-build operation nodes keyed by indicateur ID
            # via Metrique → Operation (FK id_metrique on Operation)
            ind_to_ops = {}  # indicateur_id -> [op_node, ...]
            # Collect all indicateur IDs first
            all_indicateur_ids = set()
            for enjeu in enjeux:
                for ea in enjeu.etats_actuels.all():
                    for olt in ea.objectifs_long_terme.all():
                        for ne in olt.niveaux_exigence.all():
                            for ind in ne.indicateurs.all():
                                all_indicateur_ids.add(ind.id_indicateur)
                for facteur in enjeu.facteurs_influence.all():
                    for oo in facteur.objectifs_operationnels.all():
                        for ra in oo.resultats_attendus.all():
                            for ind in ra.indicateurs.all():
                                all_indicateur_ids.add(ind.id_indicateur)

            if all_indicateur_ids:
                # Find operations linked via metriques belonging to these indicateurs
                operations_qs = (
                    Operation.objects
                    .filter(id_metrique__id_indicateur__in=all_indicateur_ids)
                    .select_related('id_metrique')
                )
                for op in operations_qs:
                    ind_id = op.id_metrique.id_indicateur_id
                    op_node = {
                        'name': op.libelle,
                        'entityType': 'operation',
                        'id': op.id_operation,
                    }
                    ind_to_ops.setdefault(ind_id, []).append(op_node)

            def build_indicateur_node(ind):
                """Build an indicateur node with metriques, mesures AND operations."""
                ind_node = {
                    'name': ind.nom_indicateur,
                    'entityType': 'indicateur',
                    'id': ind.id_indicateur,
                    'children': []
                }
                for met in ind.metriques.all():
                    met_node = {
                        'name': met.nom_metrique,
                        'entityType': 'metrique',
                        'id': met.id_metrique,
                    }
                    ind_node['children'].append(met_node)
                # Append linked operations
                for op_node in ind_to_ops.get(ind.id_indicateur, []):
                    ind_node['children'].append(op_node)
                return ind_node

            for enjeu in enjeux:
                is_fcr = enjeu.id_categorie and enjeu.id_categorie.mnemonique == 'FCR'
                enjeu_node = {
                    'name': enjeu.intitule_court or enjeu.libelle,
                    'entityType': 'fcr' if is_fcr else 'enjeu',
                    'id': enjeu.id_enjeu,
                    'children': []
                }

                # Facteurs d'influence + pressions + OO
                for facteur in enjeu.facteurs_influence.all():
                    facteur_node = {
                        'name': facteur.libelle,
                        'entityType': 'facteur',
                        'id': facteur.id_facteur_influence,
                        'children': []
                    }
                    for pression in facteur.pressions.all():
                        facteur_node['children'].append({
                            'name': pression.libelle,
                            'entityType': 'pression',
                            'id': pression.id_pression
                        })
                    # OO branch (nested under facteur)
                    for oo in facteur.objectifs_operationnels.all():
                        oo_node = {
                            'name': oo.libelle,
                            'entityType': 'oo',
                            'id': oo.id_oo,
                            'children': []
                        }
                        for ra in oo.resultats_attendus.all():
                            ra_node = {
                                'name': ra.libelle,
                                'entityType': 'resultat_attendu',
                                'id': ra.id_ra,
                                'children': []
                            }
                            for ind in ra.indicateurs.all():
                                ra_node['children'].append(build_indicateur_node(ind))
                            oo_node['children'].append(ra_node)
                        facteur_node['children'].append(oo_node)
                    enjeu_node['children'].append(facteur_node)

                # EtatActuel -> OLT branch
                for ea in enjeu.etats_actuels.all():
                    ea_node = {
                        'name': ea.libelle,
                        'entityType': 'etat_actuel',
                        'id': ea.id_etat_actuel,
                        'children': []
                    }
                    for olt in ea.objectifs_long_terme.all():
                        olt_node = {
                            'name': olt.libelle,
                            'entityType': 'olt',
                            'id': olt.id_olt,
                            'children': []
                        }

                        # Niveaux d'exigence -> Indicateurs -> Metriques/Mesures + Operations
                        for ne in olt.niveaux_exigence.all():
                            ne_node = {
                                'name': ne.libelle,
                                'entityType': 'niveau_exigence',
                                'id': ne.id_ne,
                                'children': []
                            }
                            for ind in ne.indicateurs.all():
                                ne_node['children'].append(build_indicateur_node(ind))
                            olt_node['children'].append(ne_node)

                        ea_node['children'].append(olt_node)
                    enjeu_node['children'].append(ea_node)

                root['children'].append(enjeu_node)

            # Suivis / Inventaires linked to the plan
            suivis = (
                SuiviInventaire.objects
                .filter(id_pg=plan)
                .select_related('id_protocole')
            )
            if suivis.exists():
                suivis_group = {
                    'name': 'Suivis / Inventaires',
                    'entityType': 'suivi',
                    'children': []
                }
                for s in suivis:
                    s_node = {
                        'name': s.intitule or f"Suivi #{s.id_suivi_inventaire}",
                        'entityType': 'suivi',
                        'id': s.id_suivi_inventaire,
                        'children': []
                    }
                    if s.id_protocole:
                        s_node['children'].append({
                            'name': s.id_protocole.protocole_campanule_nom or s.id_protocole.nom_protocole or f"Protocole #{s.id_protocole.id_protocole}",
                            'entityType': 'protocole',
                            'id': s.id_protocole.id_protocole
                        })
                    suivis_group['children'].append(s_node)
                root['children'].append(suivis_group)

            return root

        tree = build_tree()
        return Response(tree)

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, pk=None):
        """
        Dupliquer un plan de gestion.

        POST /api/plans/plans/{id}/duplicate/
        Body: {
            "copy_sites": true,
            "copy_referents": true,
            "copy_fichiers": false,
            "copy_enjeux": true,
            "copy_sub_elements": true
        }
        """
        plan = self.get_object()

        # Seuls les plans validés peuvent servir de base
        if plan.statut != 'valide':
            return Response(
                {'error': 'Seuls les plans validés peuvent servir de base pour créer un nouveau plan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PlanDuplicateOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=plan,
            user=request.user,
            **serializer.validated_data,
        )

        result_serializer = PlanGestionDetailSerializer(new_plan)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='change-status',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def change_status(self, request, pk=None):
        """
        Changer le statut d'un plan de gestion.

        POST /api/plans/plans/{id}/change-status/
        Body: {"new_status": "valide"}

        Transitions autorisées (référent du plan, admin_og+):
        - draft → valide
        - valide → draft
        - valide → archive
        - archive → valide
        """
        plan = self.get_object()

        # Vérifier que l'utilisateur est référent de CE plan (ou admin_og+)
        user = request.user
        if not user.is_admin_organisme() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour modifier son statut.'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('new_status')

        if not new_status:
            return Response({'error': 'new_status requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = dict(PlanGestion.STATUT_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'error': f'Statut invalide. Choix: {", ".join(valid_statuses)}'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Vérifier les transitions autorisées
        current = plan.statut
        allowed_transitions = {
            'draft': ['valide'],
            'valide': ['archive', 'draft'],
            'archive': ['valide'],
        }

        if new_status not in allowed_transitions.get(current, []):
            return Response(
                {'error': f'Transition {current} → {new_status} non autorisée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = plan.statut
        plan.statut = new_status
        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=['statut', 'id_utilisateur_maj', 'date_maj'])

        # Log activity
        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='status_change',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description=f"Statut changé de {old_status} à {new_status}",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='create-evaluation',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def create_evaluation(self, request, pk=None):
        """
        Créer une évaluation mi-parcours à partir d'un plan validé.

        POST /api/plans/plans/{id}/create-evaluation/

        Le plan source doit être au statut 'valide'.
        Accessible aux référents du plan, admin_og+.
        Crée un nouveau plan enfant avec:
        - plan_parent = plan source
        - id_type_document = EVAL_MI_PARCOURS
        - statut = draft
        - version = plan.get_next_version()
        - Copie des sites et référents
        """
        plan = self.get_object()

        # Vérifier que l'utilisateur est référent de CE plan (ou admin_og+)
        user = request.user
        if not user.is_admin_organisme() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour créer une évaluation.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if plan.statut != 'valide':
            return Response(
                {'error': "Seul un plan validé peut donner lieu à une évaluation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer la nomenclature EVAL_MI_PARCOURS
        from apps.core.models import Nomenclature
        try:
            eval_type = Nomenclature.objects.get(mnemonique='EVAL_MI_PARCOURS')
        except Nomenclature.DoesNotExist:
            return Response(
                {'error': "Nomenclature EVAL_MI_PARCOURS non trouvée. Lancez 'python manage.py import_nomenclatures --force'."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Créer le nouveau plan
        new_plan = PlanGestion.objects.create(
            nom=f"Évaluation mi-parcours - {plan.nom}",
            plan_parent=plan,
            id_type_document=eval_type,
            statut='draft',
            version=plan.get_next_version(),
            annee_debut=plan.annee_debut,
            annee_fin=plan.annee_fin,
            rang=plan.rang,
            surface=plan.surface,
            gestion_partagee=plan.gestion_partagee,
            ct88=plan.ct88,
            risque_incendie=plan.risque_incendie,
            id_evaluation=plan.id_evaluation,
            id_redacteur_type=plan.id_redacteur_type,
            redacteur_nom=plan.redacteur_nom,
            id_utilisateur_ajout=request.user,
            id_utilisateur_maj=request.user,
        )

        # Copier les sites
        for cor_site in plan.sites.all():
            CorSitePg.objects.create(
                plan_de_gestion=new_plan,
                site=cor_site.site,
                rang=cor_site.rang,
            )

        # Copier les référents
        new_plan.referents.set(plan.referents.all())

        # Copier les membres (CorRolePlan)
        from .models import CorRolePlan
        for membre in plan.membres.all():
            CorRolePlan.objects.create(
                id_role=membre.id_role,
                plan_de_gestion=new_plan,
                referent=membre.referent,
            )

        # Log activity
        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='create',
                entity_type='plan',
                entity_id=new_plan.id_pg,
                entity_name=new_plan.nom,
                description=f"Évaluation mi-parcours créée depuis le plan '{plan.nom}'",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(new_plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 15))  # Cache 15 minutes
    def stats(self, request):
        """
        Statistiques des Plans de Gestion.
        
        GET /api/plans/stats/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'par_statut': {},
            'par_periode': {},
            'gestion_partagee': queryset.filter(gestion_partagee=True).count(),
            'avec_geometrie': queryset.filter(geometrie__isnull=False).count(),
            'ct88': queryset.filter(ct88=True).count(),
            'risque_incendie': queryset.filter(risque_incendie=True).count(),
        }
        
        # Statistiques par statut
        for statut, _ in PlanGestion.STATUT_CHOICES:
            stats['par_statut'][statut] = queryset.filter(statut=statut).count()
        
        # Statistiques par période (dernières années)
        from datetime import datetime
        current_year = datetime.now().year
        for year in range(current_year - 5, current_year + 5):
            count = queryset.filter(
                annee_debut__lte=year,
                annee_fin__gte=year
            ).count()
            if count > 0:
                stats['par_periode'][year] = count
        
        return Response(stats)


class CorPgFichierViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les fichiers de Plans de Gestion.
    
    Fonctionnalités:
    - Upload de fichiers
    - Téléchargement sécurisé
    - Filtres par type de fichier
    - Permissions selon le plan
    """
    
    queryset = CorPgFichier.objects.all().select_related(
        'plan_de_gestion', 'id_utilisateur_upload'
    )
    serializer_class = CorPgFichierSerializer
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CorPgFichierFilter
    search_fields = ['nom_fichier', 'titre', 'description', 'auteur']
    ordering_fields = ['nom_fichier', 'type_fichier', 'ordre_affichage', 'date_upload']
    ordering = ['ordre_affichage', 'nom_fichier']
    
    def get_queryset(self):
        """Filtrer les fichiers selon les permissions sur les plans."""
        user = self.request.user

        if user.is_super_admin():
            return self.queryset

        # Filtrer selon les plans accessibles à l'utilisateur
        plan_viewset = PlanGestionViewSet()
        plan_viewset.request = self.request
        plan_viewset.kwargs = {}
        plan_ids = plan_viewset.get_queryset().values_list('id_pg', flat=True)
        return self.queryset.filter(plan_de_gestion__id_pg__in=plan_ids)
    
    def perform_create(self, serializer):
        """Définir l'utilisateur qui upload le fichier."""
        serializer.save(id_utilisateur_upload=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Télécharger un fichier.
        
        GET /api/plans/fichiers/{id}/download/
        """
        fichier = self.get_object()
        
        # Vérifier si le fichier est public ou si l'utilisateur a les permissions
        if not fichier.public:
            plan_viewset = PlanGestionViewSet()
            plan_viewset.request = request
            plan_viewset.kwargs = {}
            plan_queryset = plan_viewset.get_queryset()

            if not plan_queryset.filter(id_pg=fichier.plan_de_gestion.id_pg).exists():
                return Response({'error': 'Permissions insuffisantes'},
                              status=status.HTTP_403_FORBIDDEN)

        # Résoudre le chemin absolu du fichier
        from django.conf import settings
        chemin = fichier.chemin_fichier or ''
        if not os.path.isabs(chemin):
            chemin = os.path.join(settings.MEDIA_ROOT, chemin)

        # Vérifier que le fichier existe
        if not chemin or not os.path.exists(chemin):
            return HttpResponse(
                b'Fichier non disponible sur le serveur',
                content_type='text/plain',
                status=404
            )

        # Déterminer le content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(fichier.nom_fichier)
        if not content_type:
            content_type = 'application/octet-stream'

        # Servir le fichier
        try:
            with open(chemin, 'rb') as f:
                file_content = f.read()

            response = HttpResponse(file_content, content_type=content_type)

            # Inline pour PDF et images, attachment pour le reste
            ext = (fichier.extension or '').lower().lstrip('.')
            if ext in ('pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'):
                disposition = 'inline'
            else:
                disposition = 'attachment'
            response['Content-Disposition'] = f'{disposition}; filename="{fichier.nom_fichier}"'
            response['Content-Length'] = len(file_content)

            return response

        except Exception as e:
            return HttpResponse(
                f'Erreur lors du téléchargement: {str(e)}'.encode(),
                content_type='text/plain',
                status=500
            )


# Vues fonctionnelles pour actions spécifiques

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminOrganisme])
def bulk_assign_sites(request):
    """
    Assigner plusieurs sites à plusieurs plans.
    
    POST /api/plans/bulk_assign_sites/
    Body: {
        "plan_ids": [1, 2, 3],
        "site_ids": [4, 5, 6],
        "commentaire": "Assignation en masse"
    }
    """
    plan_ids = request.data.get('plan_ids', [])
    site_ids = request.data.get('site_ids', [])
    commentaire = request.data.get('commentaire', 'Assignation en masse')
    
    if not plan_ids or not site_ids:
        return Response({'error': 'plan_ids et site_ids requis'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.users.models import Site
        plans = PlanGestion.objects.filter(id_pg__in=plan_ids)
        sites = Site.objects.filter(id_site__in=site_ids)
        
        # Vérifier les permissions sur tous les sites
        for site in sites:
            if not request.user.can_manage_site(site):
                return Response({'error': f'Permissions insuffisantes pour le site {site.nom_site}'}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        created_relations = []
        for plan in plans:
            for i, site in enumerate(sites, 1):
                cor_site_pg, created = CorSitePg.objects.get_or_create(
                    plan_de_gestion=plan,
                    site=site,
                    defaults={
                        'rang': i,
                        'commentaire': commentaire
                    }
                )
                if created:
                    created_relations.append(f'{plan.nom} ↔ {site.nom_site}')
        
        return Response({
            'message': f'{len(created_relations)} relations créées',
            'relations': created_relations
        })
        
    except Exception as e:
        return Response({'error': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@method_decorator(cache_page(60 * 30))
def export_geojson(request):
    """
    Export GeoJSON complet des plans avec géométries.
    
    GET /api/plans/export_geojson/
    """
    # Utiliser le même filtrage que le ViewSet
    viewset = PlanGestionViewSet()
    viewset.request = request
    queryset = viewset.get_queryset().filter(geometrie__isnull=False)
    
    features = []
    for plan in queryset:
        properties = {
            'id_pg': plan.id_pg,
            'nom': plan.nom,
            'periode': plan.get_periode_gestion(),
            'statut': plan.statut,
            'gestion_partagee': plan.gestion_partagee,
            'nb_sites': plan.sites.count(),
            'organismes': plan.get_organismes_gestionnaires(),
        }
        
        feature = {
            'type': 'Feature',
            'geometry': plan.geometrie.__geo_interface__,
            'properties': properties
        }
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'crs': {
            'type': 'name',
            'properties': {'name': 'EPSG:4326'}
        },
        'features': features
    }
    
    return JsonResponse(geojson, json_dumps_params={'ensure_ascii': False})