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

from django.db.models import Count

from .models import PlanGestion, CorSitePg, CorPgFichier, CorRolePlan
from .serializers import (
    PlanGestionListSerializer, PlanGestionDetailSerializer,
    PlanGestionGeoJSONSerializer,
    PlanDuplicateOptionsSerializer,
    CorSitePgSerializer, CorPgFichierSerializer
)
from .services import PlanDuplicationService
from .services_import import (
    build_arborescence_workbook,
    build_example_workbook,
    parse_workbook,
    validate_import,
    execute_import,
    ArborescenceImportError,
    describe_schema,
    public_parsed,
    sanitize_parsed,
    read_any_workbook,
    count_existing_arborescence,
)
from .services_import_actions import (
    build_actions_workbook,
    build_actions_example_workbook,
    parse_actions_workbook,
    validate_actions_import,
    execute_actions_import,
    describe_actions_schema,
    sanitize_actions_parsed,
    public_actions_parsed,
)
from urllib.parse import quote as _url_quote
from .filters import PlanGestionFilter, CorPgFichierFilter
from apps.users.permissions import (
    IsReferent, IsSuperAdmin, IsAdminOrganisme
)
from apps.users.pagination import StandardPagination
from .permissions import CanModifyOnlyDraftPlan


# Sentinel pour distinguer "step manquant" de "step=null" dans csrpn_step.
_MISSING = object()


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
        """Vérifie si l'utilisateur peut gérer ce plan (admin_og+, référent, ou organisme rédacteur)."""
        if user.is_admin_organisme():
            return True
        if plan.referents.filter(pk=user.pk).exists():
            return True
        # Utilisateur d'un organisme rédacteur du plan
        if user.id_organisme and plan.organismes_redacteurs.filter(uuid_og=user.id_organisme).exists():
            return True
        return False

    def _can_delete_plan(self, user, plan):
        """Suppression : référent du plan, admin_og ou super_admin (hors rédacteur principal).

        Aligné avec `can_manage_plan_lifecycle` : la suppression est un acte de
        cycle de vie, le rédacteur principal en est donc exclu.
        """
        if user.is_super_admin():
            return True
        if user.can_manage_plan_lifecycle():
            return True
        return plan.referents.filter(pk=user.pk).exists()

    def destroy(self, request, *args, **kwargs):
        """Suppression d'un plan de gestion avec notifications.

        - Permissions : référent du plan, admin_og, super_admin
        - Capture les référents/membres/organismes rédacteurs avant la suppression
        - CASCADE Django sur CorSitePg, CorRolePlan, CorRedacteurPlan, CorPgFichier,
          Enjeu, Operation, SuiviInventaire — les sites/utilisateurs/organismes
          eux-mêmes ne sont pas supprimés, seules les liaisons le sont
        - Notifie les acteurs liés après suppression
        """
        from apps.notifications.services import NotificationService

        plan = self.get_object()

        if not self._can_delete_plan(request.user, plan):
            return Response(
                {'detail': "Vous n'avez pas les droits pour supprimer ce plan de gestion."},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan_name = plan.nom
        plan_id = plan.id_pg
        deleted_by = request.user

        referent_ids = list(plan.referents.values_list('id_role', flat=True))
        member_ids = list(
            CorRolePlan.objects.filter(plan_de_gestion=plan)
            .values_list('id_role', flat=True)
        )
        org_ids = list(plan.organismes_redacteurs.values_list('uuid_og', flat=True))

        plan.delete()

        NotificationService.notify_plan_deleted(
            plan_name=plan_name,
            plan_id=plan_id,
            deleted_by=deleted_by,
            referent_ids=referent_ids,
            org_ids=org_ids,
            member_ids=member_ids,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    queryset = PlanGestion.objects.all().select_related(
        'id_evaluation', 'id_redacteur_type',
        'id_utilisateur_ajout', 'id_utilisateur_maj',
        'plan_parent', 'id_type_document'
    ).prefetch_related('sites__site__id_type_site', 'fichiers', 'referents', 'children', 'membres__id_role')

    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action == 'create':
            # La création d'un plan n'a pas de plan associé existant : pas
            # de check draft à appliquer.
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

        # Queryset léger pour la liste (pas de fichiers, évaluations, etc.)
        if getattr(self, 'action', None) == 'list':
            queryset = PlanGestion.objects.select_related(
                'plan_parent', 'id_type_document'
            ).prefetch_related(
                'sites__site', 'referents', 'membres__id_role'
            ).annotate(
                children_count=Count('children', distinct=True),
                enjeux_count=Count('enjeux', distinct=True),
            )
        else:
            queryset = self.queryset
        scope = self.request.query_params.get('scope')

        # Super admin : voir tous les plans
        if user.is_super_admin():
            return queryset

        # Rédacteur principal : voir tous les plans
        if user.is_redacteur_principal():
            return queryset

        # Admin organisme : voir les plans des sites de son organisme + plans rédacteur
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(organismes_redacteurs__uuid_og=user.id_organisme)
            ).distinct()

        # Référent / Utilisateur : plans personnels + plans de l'organisme
        conditions = Q()

        # Plans des sites assignés à l'utilisateur
        conditions |= Q(sites__site__corrolesite__id_role=user)

        # Plans dont il est référent
        conditions |= Q(referents=user)

        # Plans dont il est membre direct (CorRolePlan)
        conditions |= Q(membres__id_role=user)

        # Plans dont son organisme est rédacteur
        if user.id_organisme:
            conditions |= Q(organismes_redacteurs__uuid_og=user.id_organisme)

        # Plans de son organisme (pour pouvoir en demander l'accès)
        # Exclus si scope=mine (ex: page de duplication)
        if scope != 'mine' and user.id_organisme:
            conditions |= Q(sites__site__corogsite__uuid_og=user.id_organisme)

        return queryset.filter(conditions).distinct()
    
    def perform_create(self, serializer):
        """Définir l'utilisateur créateur et, le cas échéant, rattacher le plan
        au plan validé du rang précédent (conserve la chaîne de versions).

        Le frontend peut envoyer `plan_parent_id` lors de la création standard
        d'un PG (page « Créer un plan ») quand l'utilisateur confirme le
        rattachement au plan validé du rang précédent sur le même site. On
        valide ce parent côté serveur avant de poser le lien.
        """
        plan = serializer.save(id_utilisateur_ajout=self.request.user)

        # Le créateur devient référent de son plan. Sans cela, un non-admin
        # (référent/utilisateur) perd immédiatement l'accès en édition sur le
        # plan qu'il vient de créer : côté frontend `canEditPlan` /
        # `canManageLifecycle` exigent le statut de référent du plan pour les
        # non-admins. Idempotent vis-à-vis d'éventuels `referents_ids` envoyés.
        plan.referents.add(self.request.user)

        parent_id = self.request.data.get('plan_parent_id')
        if parent_id and not plan.plan_parent_id:
            parent = PlanGestion.objects.filter(pk=parent_id).first()
            if parent and self._is_valid_rang_parent(parent, plan):
                plan.plan_parent = parent
                plan.save(update_fields=['plan_parent'])

    @staticmethod
    def _is_valid_rang_parent(parent, plan):
        """Vrai si `parent` est un parent de rang valide pour `plan` lors d'une
        création standard : rang strictement inférieur et au moins un site en
        commun. Le statut du parent n'est PAS contraint — on autorise aussi le
        rattachement à un plan en **brouillon** (anti-prolifération : permet de
        chaîner un nouveau rang à un plan existant non encore validé)."""
        if parent.pk == plan.pk:
            return False
        if (parent.rang or 1) >= (plan.rang or 1):
            return False
        plan_sites = set(plan.sites.values_list('site_id', flat=True))
        parent_sites = set(parent.sites.values_list('site_id', flat=True))
        return bool(plan_sites & parent_sites)

    def perform_update(self, serializer):
        """Définir l'utilisateur modificateur et, le cas échéant, mettre à jour
        le rattachement au plan du rang précédent (chaîne de versions).

        Le formulaire de modification peut envoyer `plan_parent_id` pour
        **établir un lien entre les rangs de deux PG séparés** (#506) :
        - une valeur valide → pose/remplace le lien (après validation serveur) ;
        - `null` / `0` / chaîne vide → retire le lien (plan redevenu indépendant).
        Si la clé est absente du payload, le rattachement courant est inchangé.
        """
        plan = serializer.save(id_utilisateur_maj=self.request.user)

        if 'plan_parent_id' not in self.request.data:
            return

        parent_id = self.request.data.get('plan_parent_id')
        if not parent_id:
            # Détacher explicitement le plan de sa chaîne de versions.
            if plan.plan_parent_id:
                plan.plan_parent = None
                plan.save(update_fields=['plan_parent'])
            return

        parent = PlanGestion.objects.filter(pk=parent_id).first()
        if parent and self._is_valid_rang_parent(parent, plan) \
                and not self._would_create_cycle(parent, plan):
            if plan.plan_parent_id != parent.pk:
                plan.plan_parent = parent
                plan.save(update_fields=['plan_parent'])

    @staticmethod
    def _would_create_cycle(parent, plan):
        """Vrai si rattacher `plan` sous `parent` créerait un cycle, c.-à-d. si
        `parent` est lui-même un descendant de `plan` (remonte la chaîne des
        ancêtres de `parent` jusqu'à la racine)."""
        ancestor = parent
        seen = set()
        while ancestor is not None and ancestor.pk not in seen:
            if ancestor.pk == plan.pk:
                return True
            seen.add(ancestor.pk)
            ancestor = ancestor.plan_parent
        return False
    
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

        serializer = PlanGestionDetailSerializer(plan, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='for-sites')
    def for_sites(self, request):
        """
        Plans validés/archivés associés à un ou plusieurs sites, groupés par
        site et triés par rang.

        GET /api/plans/plans/for-sites/?site_ids=1,2

        Sert, lors de la création d'un plan, à :
        - alerter si un PG du même rang existe déjà sur le site ;
        - proposer de rattacher le nouveau plan au plan du rang précédent
          (conservation de la chaîne de versions) ;
        - afficher le détail des PG déjà rattachés au site.

        Tous les statuts sont renvoyés, **y compris les brouillons** (anti-
        prolifération : on veut voir tout plan déjà existant sur le site pour
        éviter d'en créer un doublon, et pouvoir s'y rattacher).
        Le scope respecte les permissions de l'utilisateur (get_queryset).
        """
        raw = request.query_params.get('site_ids', '')
        site_ids = [int(c) for c in (chunk.strip() for chunk in raw.split(',')) if c.isdigit()]
        if not site_ids:
            return Response({'sites': []})

        from apps.users.models import Site

        qs = (
            self.get_queryset()
            .filter(sites__site_id__in=site_ids)
            .distinct()
        )
        names = dict(
            Site.objects.filter(id_site__in=site_ids).values_list('id_site', 'nom_site')
        )

        sites_payload = []
        for sid in site_ids:
            plans = qs.filter(sites__site_id=sid).order_by('rang', 'version')
            sites_payload.append({
                'site_id': sid,
                'site_nom': names.get(sid),
                'plans': [
                    {
                        'id_pg': p.id_pg,
                        'nom': p.nom,
                        'slug': p.slug,
                        'statut': p.statut,
                        'statut_display': p.get_statut_display(),
                        'rang': p.rang,
                        'version': p.version,
                        'annee_debut': p.annee_debut,
                        'annee_fin': p.annee_fin,
                        'is_mi_parcours': bool(p.is_mi_parcours),
                    }
                    for p in plans
                ],
            })
        return Response({'sites': sites_payload})

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
            ObjectifLongTerme, NiveauExigence,
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
                    'objectifs_long_terme__niveaux_exigence__indicateurs__metriques__mesures',
                    'objectifs_long_terme__niveaux_exigence__indicateurs__metriques__operations',
                    'objectifs_long_terme__niveaux_exigence__indicateurs__operations',
                    'facteurs_influence__pressions__objectifs_operationnels__resultats_attendus__indicateurs__metriques__mesures',
                    'facteurs_influence__pressions__objectifs_operationnels__resultats_attendus__indicateurs__metriques__operations',
                    'facteurs_influence__pressions__objectifs_operationnels__resultats_attendus__indicateurs__operations',
                )
                .order_by('id_enjeu')
            )

            # #416 — afficher d'abord les enjeux, puis les FCR (dans chaque
            # groupe, on conserve l'ordre par id_enjeu).
            enjeux = sorted(
                enjeux,
                key=lambda e: (
                    1 if (e.id_categorie and e.id_categorie.mnemonique == 'FCR') else 0,
                    e.id_enjeu,
                ),
            )

            def build_indicateur_node(ind):
                """Build an indicateur node with metriques and their operations nested."""
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
                        'children': [],
                    }
                    for op in met.operations.all():
                        met_node['children'].append({
                            'name': op.libelle,
                            'entityType': 'operation',
                            'id': op.id_operation,
                        })
                    ind_node['children'].append(met_node)
                # #567 — actions rattachées directement à l'indicateur (#367),
                # sans passer par une métrique : les afficher aussi dans l'arbre.
                for op in ind.operations.all():
                    ind_node['children'].append({
                        'name': op.libelle,
                        'entityType': 'operation',
                        'id': op.id_operation,
                    })
                return ind_node

            for enjeu in enjeux:
                is_fcr = enjeu.id_categorie and enjeu.id_categorie.mnemonique == 'FCR'
                enjeu_node = {
                    'name': enjeu.intitule_court or enjeu.libelle,
                    'entityType': 'fcr' if is_fcr else 'enjeu',
                    'id': enjeu.id_enjeu,
                    'slug': enjeu.slug,
                    'children': []
                }

                # Facteurs d'influence + pressions + OO
                # #416 — on construit d'abord les facteurs dans une liste, mais
                # on les rattache APRÈS l'état de l'enjeu (état actuel en premier).
                facteur_nodes = []
                for facteur in enjeu.facteurs_influence.all():
                    facteur_node = {
                        'name': facteur.libelle,
                        'entityType': 'facteur',
                        'id': facteur.id_facteur_influence,
                        'children': []
                    }
                    for pression in facteur.pressions.all():
                        pression_node = {
                            'name': pression.libelle,
                            'entityType': 'pression',
                            'id': pression.id_pression,
                            'children': []
                        }
                        # OO branch (nested under pression)
                        for oo in pression.objectifs_operationnels.all():
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
                            pression_node['children'].append(oo_node)
                        facteur_node['children'].append(pression_node)
                    facteur_nodes.append(facteur_node)

                # État de l'enjeu -> OLT branch
                # Build a virtual "état de l'enjeu" node from the etat_enjeu text field
                etat_node = {
                    'name': enjeu.etat_enjeu or 'État de l\'enjeu',
                    'entityType': 'etat_enjeu',
                    'id': enjeu.id_enjeu,
                    'children': []
                }
                for olt in enjeu.objectifs_long_terme.all():
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

                    etat_node['children'].append(olt_node)
                # #416 — état actuel d'abord, puis les facteurs d'influence
                enjeu_node['children'].append(etat_node)
                enjeu_node['children'].extend(facteur_nodes)

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

    @action(detail=True, methods=['get'], url_path='mindmap-inverse')
    def mindmap_inverse(self, request, pk=None):
        """
        GET /api/plans/plans/{id}/mindmap-inverse/
        Returns an inverted tree: Operations → Métrique → Indicateur → ... → Enjeu
        """
        plan = self.get_object()
        from .models_enjeux import (
            Enjeu, FacteurInfluence, Pression,
            ObjectifLongTerme, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
        )
        from django.db.models import Q, Prefetch
        from .models_indicateurs import Indicateur, Metrique
        from .models_operations import Operation

        # Collect all operations belonging to this plan (via M2M metriques)
        operations = (
            Operation.objects
            .filter(
                Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
                Q(metriques__id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux__id_pg=plan) |
                # #567 — actions rattachées directement à un indicateur (#367)
                Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan) |
                Q(id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux__id_pg=plan)
            )
            .distinct()
            .select_related(
                'id_indicateur',
                'id_indicateur__id_ne',
                'id_indicateur__id_ne__id_olt',
                'id_indicateur__id_ne__id_olt__id_enjeu',
                'id_indicateur__id_ne__id_olt__id_enjeu__id_categorie',
                'id_indicateur__id_resultat_attendu',
                'id_indicateur__id_resultat_attendu__id_oo',
            )
            .prefetch_related(
                'id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux',
                Prefetch('metriques', queryset=Metrique.objects.select_related(
                    'id_indicateur',
                    'id_indicateur__id_ne',
                    'id_indicateur__id_ne__id_olt',
                    'id_indicateur__id_ne__id_olt__id_enjeu',
                    'id_indicateur__id_ne__id_olt__id_enjeu__id_categorie',
                    'id_indicateur__id_resultat_attendu',
                    'id_indicateur__id_resultat_attendu__id_oo',
                ).prefetch_related(
                    'id_indicateur__id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux',
                ))
            )
        )

        root = {
            'name': plan.nom,
            'entityType': 'plan',
            'id': plan.id_pg,
            'children': []
        }

        def build_ind_olt_ancestry(ind):
            """Ascendance au niveau indicateur : Indicateur → NE → OLT → État de l'enjeu → Enjeu"""
            ne = ind.id_ne
            olt = ne.id_olt
            enjeu = olt.id_enjeu
            is_fcr = enjeu.id_categorie and enjeu.id_categorie.mnemonique == 'FCR'

            return {
                'name': ind.nom_indicateur,
                'entityType': 'indicateur',
                'id': ind.id_indicateur,
                'children': [{
                    'name': ne.libelle,
                    'entityType': 'niveau_exigence',
                    'id': ne.id_ne,
                    'children': [{
                        'name': olt.libelle,
                        'entityType': 'olt',
                        'id': olt.id_olt,
                        'children': [{
                            'name': enjeu.etat_enjeu or 'État de l\'enjeu',
                            'entityType': 'etat_enjeu',
                            'id': enjeu.id_enjeu,
                            'children': [{
                                'name': enjeu.intitule_court or enjeu.libelle,
                                'entityType': 'fcr' if is_fcr else 'enjeu',
                                'id': enjeu.id_enjeu,
                            }]
                        }]
                    }]
                }]
            }

        def build_olt_ancestry(met):
            """Build inverted path: Métrique → Indicateur → NE → OLT → État de l'enjeu → Enjeu"""
            return {
                'name': met.nom_metrique,
                'entityType': 'metrique',
                'id': met.id_metrique,
                'children': [build_ind_olt_ancestry(met.id_indicateur)]
            }

        def build_ind_oo_ancestry(ind):
            """Ascendance au niveau indicateur : Indicateur → RA → OO → Pression → Facteur → Enjeu
            Note: OO is M2M with Pression, we pick the first pression for the ancestry path."""
            ra = ind.id_resultat_attendu
            oo = ra.id_oo
            # M2M: pick first pression (prefetched)
            oo_pressions = list(oo.pressions.all())
            pression = oo_pressions[0] if oo_pressions else None
            if not pression:
                return None
            facteur = pression.id_facteur_influence
            # #552 — facteur partagé entre plusieurs enjeux (M2M) : on retient le
            # premier lié, comme pour la pression ci-dessus (chemin d'ascendance).
            enjeu = facteur.enjeux.first()
            if not enjeu:
                return None
            is_fcr = enjeu.id_categorie and enjeu.id_categorie.mnemonique == 'FCR'

            return {
                'name': ind.nom_indicateur,
                'entityType': 'indicateur',
                'id': ind.id_indicateur,
                'children': [{
                    'name': ra.libelle,
                    'entityType': 'resultat_attendu',
                    'id': ra.id_ra,
                    'children': [{
                        'name': oo.libelle,
                        'entityType': 'oo',
                        'id': oo.id_oo,
                        'children': [{
                            'name': pression.libelle,
                            'entityType': 'pression',
                            'id': pression.id_pression,
                            'children': [{
                                'name': facteur.libelle,
                                'entityType': 'facteur',
                                'id': facteur.id_facteur_influence,
                                'children': [{
                                    'name': enjeu.intitule_court or enjeu.libelle,
                                    'entityType': 'fcr' if is_fcr else 'enjeu',
                                    'id': enjeu.id_enjeu,
                                }]
                            }]
                        }]
                    }]
                }]
            }

        def build_oo_ancestry(met):
            """Build inverted path: Métrique → Indicateur → RA → OO → Pression → Facteur → Enjeu"""
            node = build_ind_oo_ancestry(met.id_indicateur)
            if node is None:
                return None
            return {
                'name': met.nom_metrique,
                'entityType': 'metrique',
                'id': met.id_metrique,
                'children': [node]
            }

        def build_ancestry_from_indicateur(ind):
            """#567 — ascendance d'une action rattachée directement à un indicateur."""
            if ind.id_ne:
                return build_ind_olt_ancestry(ind)
            if ind.id_resultat_attendu:
                return build_ind_oo_ancestry(ind)
            return None

        # Build operation nodes — group all métriques under each operation
        for op in operations:
            ancestry_children = []
            for met in op.metriques.all():
                ind = met.id_indicateur
                if not ind:
                    continue
                if ind.id_ne:
                    ancestry_children.append(build_olt_ancestry(met))
                elif ind.id_resultat_attendu:
                    node = build_oo_ancestry(met)
                    if node:
                        ancestry_children.append(node)
            # #567 — action rattachée directement à un indicateur (#367), sans
            # métrique : son ascendance part du nœud indicateur.
            if op.id_indicateur:
                node = build_ancestry_from_indicateur(op.id_indicateur)
                if node:
                    ancestry_children.append(node)
            if ancestry_children:
                op_node = {
                    'name': op.libelle,
                    'entityType': 'operation',
                    'id': op.id_operation,
                    'children': ancestry_children
                }
                root['children'].append(op_node)

        return Response(root)

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, pk=None):
        """
        Dupliquer un plan de gestion pour en créer une nouvelle version
        (brouillon enfant, même rang). Sert au workflow « créer une nouvelle
        modification » à partir d'un plan validé.

        POST /api/plans/plans/{id}/duplicate/
        Body: {
            "copy_sites": true,
            "copy_referents": true,
            "copy_fichiers": false,
            "copy_enjeux": true,
            "copy_sub_elements": true
        }

        Conditions :
        - Source dans DRAFTABLE_PARENT_STATUSES (valide / modifie / archive).
        - Pas de brouillon enfant déjà présent (règle « un brouillon max
          par parent en même temps »).
        """
        plan = self.get_object()

        if plan.statut not in PlanGestion.DRAFTABLE_PARENT_STATUSES:
            return Response(
                {'error': "Seuls les plans validés (validé, modifié ou archivé) peuvent servir de base pour créer un nouveau plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if plan.has_draft_child():
            return Response(
                {'error': "Un brouillon est déjà en cours sur ce plan. Validez ou supprimez le brouillon existant avant d'en créer un nouveau."},
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

    @action(detail=False, methods=['get'], url_path='example-arborescence-xlsx',
            permission_classes=[permissions.IsAuthenticated])
    def example_arborescence_xlsx(self, request):
        """
        Télécharger un exemple complet d'arborescence (indépendant d'un plan).

        GET /api/plans/plans/example-arborescence-xlsx/

        Classeur pédagogique fictif, entièrement rempli, illustrant tous les
        onglets et les liens entre eux. Sert de référence aux utilisateurs pour
        comprendre le format avant de remplir le leur.
        """
        content = build_example_workbook()
        filename = 'exemple-arborescence-plan-de-gestion.xlsx'
        response = HttpResponse(
            content,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{_url_quote(filename)}"
        )
        return response

    @action(detail=True, methods=['get'], url_path='export-arborescence-xlsx')
    def export_arborescence_xlsx(self, request, pk=None):
        """
        Exporter l'arborescence d'un plan au format Excel (modèle d'import).

        GET /api/plans/plans/{id}/export-arborescence-xlsx/
        Query params:
            - empty=1 : produire un modèle vierge (ne pas pré-remplir avec le
              contenu du plan).

        Le classeur suit le format multi-onglets d'import (V1). Pré-rempli avec
        l'arborescence du plan par défaut ; sert aussi d'export / sauvegarde et
        de point de départ pour dériver un autre plan.
        """
        plan = self.get_object()
        empty = request.query_params.get('empty') in ('1', 'true', 'True')

        content = build_arborescence_workbook(plan=None if empty else plan)

        suffix = 'modele' if empty else (plan.slug or f'plan-{plan.pk}')
        filename = f'arborescence-{suffix}.xlsx'
        response = HttpResponse(
            content,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{_url_quote(filename)}"
        )
        return response

    @action(detail=True, methods=['post'], url_path='import-arborescence/validate',
            parser_classes=[MultiPartParser, FormParser])
    def import_arborescence_validate(self, request, pk=None):
        """
        Valider (sans écrire) un fichier d'import d'arborescence.

        POST /api/plans/plans/{id}/import-arborescence/validate/
        multipart/form-data : champ « file » = classeur .xlsx.

        Renvoie le rapport de validation (anomalies par onglet/ligne + décompte
        de ce qui serait créé). N'écrit rien en base.
        """
        return self._run_import(request, execute=False)

    @action(detail=True, methods=['post'], url_path='import-arborescence',
            parser_classes=[MultiPartParser, FormParser])
    def import_arborescence(self, request, pk=None):
        """
        Importer l'arborescence dans le plan (création seule, transaction).

        POST /api/plans/plans/{id}/import-arborescence/
        multipart/form-data : champ « file » = classeur .xlsx.

        Refuse si le plan contient déjà une arborescence ou si la validation
        échoue (le rapport est renvoyé en 400).
        """
        return self._run_import(request, execute=True)

    def _run_import(self, request, execute):
        plan = self.get_object()
        # Mode : create (défaut), add (ajout), replace (remplacement destructif).
        mode = request.data.get('mode') or request.query_params.get('mode') or 'create'

        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response(
                {'error': "Aucun fichier reçu (champ « file » attendu)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed = parse_workbook(uploaded)
        except ArborescenceImportError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not execute:
            report = validate_import(plan, parsed, mode=mode)
            payload = report.as_dict()
            # Données parsées renvoyées pour la correction interactive (#9).
            payload['data'] = public_parsed(parsed)
            return Response(payload, status=status.HTTP_200_OK)

        try:
            counts = execute_import(plan, parsed, request.user, mode=mode)
        except ValueError as exc:
            # Validation échouée : le rapport est joint à l'exception.
            report = exc.args[0] if exc.args else None
            payload = report.as_dict() if hasattr(report, 'as_dict') else {'error': str(exc)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'created': counts, 'total': sum(counts.values())},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='import-arborescence-schema',
            permission_classes=[permissions.IsAuthenticated])
    def import_arborescence_schema(self, request):
        """
        Décrit les onglets/colonnes du format d'arborescence.

        GET /api/plans/plans/import-arborescence-schema/
        Sert à piloter la grille de correction (#9) et les cibles du mapping (#10).
        """
        return Response({'sheets': describe_schema()}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='import-arborescence/validate-data')
    def import_arborescence_validate_data(self, request, pk=None):
        """
        Valider des données d'arborescence éditées (JSON), sans fichier (#9).

        POST /api/plans/plans/{id}/import-arborescence/validate-data/
        Body : { "data": { "enjeux": [...], ... } }.
        """
        plan = self.get_object()
        mode = (request.data or {}).get('mode') or 'create'
        parsed = sanitize_parsed((request.data or {}).get('data') or {})
        report = validate_import(plan, parsed, mode=mode)
        payload = report.as_dict()
        payload['data'] = public_parsed(parsed)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='import-arborescence/existing-summary')
    def import_arborescence_existing_summary(self, request, pk=None):
        """
        Résumé du contenu existant du plan (pour la confirmation de remplacement).

        GET /api/plans/plans/{id}/import-arborescence/existing-summary/
        """
        plan = self.get_object()
        return Response(count_existing_arborescence(plan), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='import-arborescence/import-data')
    def import_arborescence_import_data(self, request, pk=None):
        """
        Importer des données d'arborescence éditées (JSON), sans fichier (#9/#10).

        POST /api/plans/plans/{id}/import-arborescence/import-data/
        Body : { "data": { ... }, "mode": "create|add|replace" }.
        """
        plan = self.get_object()
        mode = (request.data or {}).get('mode') or 'create'
        parsed = sanitize_parsed((request.data or {}).get('data') or {})
        try:
            counts = execute_import(plan, parsed, request.user, mode=mode)
        except ValueError as exc:
            report = exc.args[0] if exc.args else None
            payload = (
                report.as_dict() if hasattr(report, 'as_dict') else {'error': str(exc)}
            )
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'created': counts, 'total': sum(counts.values())},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='read-xlsx',
            parser_classes=[MultiPartParser, FormParser],
            permission_classes=[permissions.IsAuthenticated])
    def read_xlsx(self, request):
        """
        Lire un classeur Excel quelconque (mapping #10).

        POST /api/plans/plans/read-xlsx/ — multipart, champ « file ».
        Renvoie { "sheets": [ { "name", "headers", "rows" } ] }.
        """
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response(
                {'error': "Aucun fichier reçu (champ « file » attendu)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sheets = read_any_workbook(uploaded)
        except ArborescenceImportError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'sheets': sheets}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='example-actions-xlsx',
            permission_classes=[permissions.IsAuthenticated])
    def example_actions_xlsx(self, request):
        """
        Télécharger un exemple complet de classeur d'actions (indépendant).

        GET /api/plans/plans/example-actions-xlsx/

        Classeur pédagogique fictif : actions rattachées à des indicateurs de
        référence, avec budgets et RH renseignés, illustrant les liens entre
        onglets. À consulter (pas à importer tel quel).
        """
        content = build_actions_example_workbook()
        filename = 'exemple-actions-plan-de-gestion.xlsx'
        response = HttpResponse(
            content,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{_url_quote(filename)}"
        )
        return response

    @action(detail=True, methods=['get'], url_path='export-actions-xlsx')
    def export_actions_xlsx(self, request, pk=None):
        """
        Exporter le classeur d'import des actions d'un plan (module 2).

        GET /api/plans/plans/{id}/export-actions-xlsx/

        L'onglet « Indicateurs » est pré-rempli avec les indicateurs existants du
        plan (référence de rattachement) ; l'onglet « Actions » est vierge (ou
        pré-rempli si des actions existent déjà).
        """
        plan = self.get_object()
        content = build_actions_workbook(plan=plan)
        filename = f'actions-{plan.slug or f"plan-{plan.pk}"}.xlsx'
        response = HttpResponse(
            content,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{_url_quote(filename)}"
        )
        return response

    @action(detail=True, methods=['post'], url_path='import-actions/validate',
            parser_classes=[MultiPartParser, FormParser])
    def import_actions_validate(self, request, pk=None):
        """
        Valider (sans écrire) un fichier d'import d'actions.
        POST /api/plans/plans/{id}/import-actions/validate/ — champ « file ».
        """
        return self._run_actions_import(request, execute=False)

    @action(detail=True, methods=['post'], url_path='import-actions',
            parser_classes=[MultiPartParser, FormParser])
    def import_actions(self, request, pk=None):
        """
        Importer les actions dans le plan (création seule, transaction).
        POST /api/plans/plans/{id}/import-actions/ — champ « file ».
        """
        return self._run_actions_import(request, execute=True)

    def _run_actions_import(self, request, execute):
        plan = self.get_object()
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response(
                {'error': "Aucun fichier reçu (champ « file » attendu)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            parsed = parse_actions_workbook(uploaded)
        except ArborescenceImportError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not execute:
            report = validate_actions_import(plan, parsed)
            payload = report.as_dict()
            # Données parsées renvoyées pour la correction interactive (#9).
            payload['data'] = public_actions_parsed(parsed)
            return Response(payload, status=status.HTTP_200_OK)

        try:
            counts = execute_actions_import(plan, parsed, request.user)
        except ValueError as exc:
            report = exc.args[0] if exc.args else None
            payload = report.as_dict() if hasattr(report, 'as_dict') else {'error': str(exc)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'created': counts, 'total': counts.get('actions', 0)},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='import-actions-schema',
            permission_classes=[permissions.IsAuthenticated])
    def import_actions_schema(self, request, pk=None):
        """
        Décrit le format actions + les indicateurs/postes de référence du plan.

        GET /api/plans/plans/{id}/import-actions-schema/
        Sert à piloter la grille de correction (#9) et à fournir à l'extraction
        IA les codes de rattachement (indicateurs, postes) valides.
        """
        plan = self.get_object()
        return Response(describe_actions_schema(plan), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='import-actions/validate-data')
    def import_actions_validate_data(self, request, pk=None):
        """
        Valider des données d'actions éditées (JSON), sans fichier (#9 / IA).

        POST /api/plans/plans/{id}/import-actions/validate-data/
        Body : { "data": { "actions": [...], "budgets": [...], "rh": [...] } }.
        """
        plan = self.get_object()
        parsed = sanitize_actions_parsed(plan, (request.data or {}).get('data') or {})
        report = validate_actions_import(plan, parsed)
        payload = report.as_dict()
        payload['data'] = public_actions_parsed(parsed)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='import-actions/import-data')
    def import_actions_import_data(self, request, pk=None):
        """
        Importer des données d'actions éditées (JSON), sans fichier (#9 / IA).

        POST /api/plans/plans/{id}/import-actions/import-data/
        Body : { "data": { ... } }.
        """
        plan = self.get_object()
        parsed = sanitize_actions_parsed(plan, (request.data or {}).get('data') or {})
        try:
            counts = execute_actions_import(plan, parsed, request.user)
        except ValueError as exc:
            report = exc.args[0] if exc.args else None
            payload = (
                report.as_dict() if hasattr(report, 'as_dict') else {'error': str(exc)}
            )
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'created': counts, 'total': counts.get('actions', 0)},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='change-status',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def change_status(self, request, pk=None):
        """
        Changer le statut d'un plan de gestion.

        POST /api/plans/plans/{id}/change-status/
        Body: {"new_status": "valide", "is_mi_parcours": false}

        Statuts gérés (depuis #277 refactor) : draft, valide, modifie, archive.
        Le workflow CSRPN (avis_csrpn → comite_consultatif → arrete_pref) est
        désormais un attribut orthogonal `validation_step` exposé via l'action
        `csrpn-step`.

        Transitions autorisées (référent du plan, admin_og+) :
        - draft → valide / modifie (selon plan_parent et is_mi_parcours)
        - valide / modifie → draft (seulement sur feuille de chaîne)
        - valide / modifie → archive
        - archive → valide

        Note : si le plan est dans le workflow CSRPN (validation_step non NULL)
        et que la cible est `valide`/`modifie`, on remet validation_step à NULL.
        """
        plan = self.get_object()

        # Vérifier que l'utilisateur est référent de CE plan (ou admin_og+ hors rédacteur principal)
        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour modifier son statut.'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('new_status')
        is_mi_parcours = bool(request.data.get('is_mi_parcours', False))

        if not new_status:
            return Response({'error': 'new_status requis'},
                          status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = dict(PlanGestion.STATUT_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'error': f'Statut invalide. Choix: {", ".join(valid_statuses)}'},
                          status=status.HTTP_400_BAD_REQUEST)

        current = plan.statut
        # Transitions simplifiées : 4 statuts uniquement. Les étapes CSRPN sont
        # gérées par l'action `csrpn-step` (attribut validation_step orthogonal).
        validated_set = ['archive', 'draft']
        allowed_transitions = {
            'draft': ['valide'],
            'valide': validated_set,
            'modifie': validated_set,
            'archive': ['valide'],
        }

        if new_status not in allowed_transitions.get(current, []):
            return Response(
                {'error': f'Transition {current} → {new_status} non autorisée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Règle « toDraft uniquement sur la feuille de chaîne » : un plan
        # validé/modifié ne peut être repassé en brouillon que s'il n'a
        # AUCUN descendant direct. Sinon on créerait une chaîne incohérente
        # où un brouillon a des descendants validés/archivés.
        if new_status == 'draft' and current in ('valide', 'modifie') and plan.children.exists():
            return Response(
                {'error': (
                    "Impossible de repasser ce plan en brouillon : il a déjà "
                    "des versions ultérieures. Pour modifier ce plan, "
                    "créez une nouvelle version (brouillon enfant) à la place."
                )},
                status=status.HTTP_400_BAD_REQUEST
            )

        # #275 / #276 — Routage du `valide` cible selon la position dans la
        # chaîne plan_parent et le flag `is_mi_parcours`. Depuis #276 (refonte) :
        # `mi_parcours` n'est plus un statut, c'est un attribut bool
        # `is_mi_parcours` qui s'ajoute à `statut='modifie'`.
        set_mi_parcours_flag = False
        if new_status == 'valide' and current == 'draft' and plan.is_modification():
            if is_mi_parcours:
                if plan.chain_has_mi_parcours():
                    return Response(
                        {'error': "Une évaluation mi-parcours existe déjà dans la chaîne du plan."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                set_mi_parcours_flag = True
            new_status = 'modifie'
        elif is_mi_parcours:
            # Le flag n'a de sens que sur la validation d'un brouillon issu
            # d'une modification.
            return Response(
                {'error': "Le flag is_mi_parcours n'est applicable qu'à la validation d'un brouillon enfant d'un plan validé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = plan.statut
        plan.statut = new_status
        plan.id_utilisateur_maj = request.user

        update_fields = ['statut', 'id_utilisateur_maj', 'date_maj']

        # #276 — Poser le drapeau is_mi_parcours si demandé à la validation.
        if set_mi_parcours_flag:
            plan.is_mi_parcours = True
            update_fields.append('is_mi_parcours')

        # #347 — Les validations administratives (validation_step + dates CSRPN)
        # sont désormais ORTHOGONALES au statut plateforme : on ne les efface plus
        # à la validation. La validation plateforme et les validations
        # administratives coexistent en parallèle.

        # #347 — Retour en brouillon : on NE touche PAS aux validations
        # administratives (dates CSRPN/comité/arrêté). Elles sont orthogonales au
        # statut plateforme et conservées telles quelles.

        plan.save(update_fields=update_fields)

        # Règle « cascade de validation vers l'amont » : valider un brouillon
        # implique que son parent soit lui-même validé. Sous la Règle 2
        # (toDraft bloqué si descendants), ce filet ne devrait jamais
        # déclencher en pratique — c'est une sécurité pour la cohérence
        # des chaînes au cas où un parent serait en brouillon.
        if new_status in ('valide', 'modifie') and plan.plan_parent_id:
            ancestor = plan.plan_parent
            cascaded = []
            while ancestor is not None and ancestor.statut == 'draft':
                ancestor.statut = 'valide'
                ancestor.id_utilisateur_maj = request.user
                ancestor.save(update_fields=['statut', 'id_utilisateur_maj', 'date_maj'])
                cascaded.append(ancestor.nom)
                ancestor = ancestor.plan_parent
            if cascaded:
                try:
                    from apps.core.services import ActivityService
                    for nom in cascaded:
                        ActivityService.log(
                            user=request.user,
                            action='status_change',
                            entity_type='plan',
                            entity_id=plan.id_pg,
                            entity_name=nom,
                            description=(
                                f"Validation en cascade : '{nom}' "
                                f"automatiquement validé lors de la validation de '{plan.nom}'"
                            ),
                        )
                except Exception:
                    pass

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

    @action(detail=True, methods=['post'], url_path='csrpn-step',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def csrpn_step(self, request, pk=None):
        """
        Gérer le workflow CSRPN d'un plan (attribut orthogonal `validation_step`).

        POST /api/plans/plans/{id}/csrpn-step/
        Body: {
            "step": "avis_csrpn" | "comite_consultatif" | "arrete_pref" | null,
            "date_avis_csrpn"?: "YYYY-MM-DD",
            "date_validation_comite"?: "YYYY-MM-DD",
            "date_arrete_pref"?: "YYYY-MM-DD",
            "numero_arrete_pref"?: string
        }

        Séquence métier (draft uniquement) :
        - null → avis_csrpn         : lancer le workflow
        - avis_csrpn → comite_consultatif
        - comite_consultatif → arrete_pref  (RNN uniquement)
        - * → null                  : annuler le workflow (retour au brouillon simple)

        La validation finale (transition vers `valide`/`modifie`) reste sur
        l'action `change-status` ; elle remet automatiquement `validation_step`
        à NULL.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': "Vous devez être référent de ce plan pour gérer le workflow CSRPN."},
                status=status.HTTP_403_FORBIDDEN
            )

        # #347 — Les validations administratives sont orthogonales au statut
        # plateforme : on peut les enregistrer quel que soit le statut du plan
        # (brouillon comme validé), en parallèle de la validation plateforme.

        # `step` peut être None (annulation du workflow).
        new_step = request.data.get('step') if 'step' in request.data else _MISSING
        if new_step is _MISSING:
            return Response({'error': 'step requis'},
                            status=status.HTTP_400_BAD_REQUEST)

        valid_steps = dict(PlanGestion.VALIDATION_STEP_CHOICES).keys()
        if new_step is not None and new_step not in valid_steps:
            return Response(
                {'error': f"Étape invalide. Choix: {', '.join(valid_steps)} ou null"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # #406 — le workflow de validation administrative (CSRPN) est réservé
        # aux réserves naturelles (RNN/RNR/RNC). L'annulation (step=None) reste
        # toujours permise pour pouvoir sortir d'un état incohérent.
        if new_step is not None and not plan.is_reserve_naturelle():
            return Response(
                {'error': "La validation administrative est réservée aux réserves naturelles (RNN, RNR, RNC)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        current_step = plan.validation_step
        # Transitions autorisées du workflow CSRPN. None = pas dans le workflow.
        # #347 — auto-transitions autorisées (step == current) : permet de
        # (re)enregistrer la date d'une étape terminale sans la quitter (l'étape
        # finale n'enchaîne plus sur la validation plateforme, désormais séparée).
        allowed_step_transitions = {
            None: ['avis_csrpn'],
            'avis_csrpn': [None, 'avis_csrpn', 'comite_consultatif'],
            'comite_consultatif': [None, 'comite_consultatif', 'arrete_pref'],
            'arrete_pref': [None, 'arrete_pref'],
        }

        if new_step not in allowed_step_transitions.get(current_step, []):
            return Response(
                {'error': f"Transition CSRPN {current_step} → {new_step} non autorisée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # `comite_consultatif → arrete_pref` réservé aux RNN.
        if current_step == 'comite_consultatif' and new_step == 'arrete_pref' and not plan.is_rnn():
            return Response(
                {'error': "L'étape arrêté préfectoral est réservée aux RNN."},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_step = plan.validation_step
        plan.validation_step = new_step
        plan.id_utilisateur_maj = request.user

        update_fields = ['validation_step', 'id_utilisateur_maj', 'date_maj']

        # Persister les métadonnées CSRPN éventuellement transmises.
        for field, payload_key in (
            ('date_avis_csrpn', 'date_avis_csrpn'),
            ('date_validation_comite', 'date_validation_comite'),
            ('date_arrete_pref', 'date_arrete_pref'),
            ('numero_arrete_pref', 'numero_arrete_pref'),
        ):
            if payload_key in request.data:
                value = request.data.get(payload_key) or None
                setattr(plan, field, value)
                update_fields.append(field)

        plan.save(update_fields=update_fields)

        # Log activity
        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='status_change',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description=f"Étape CSRPN changée de {old_step or 'aucune'} à {new_step or 'aucune'}",
            )
        except Exception:
            pass

        # Notifier les référents de la transition CSRPN (entrée / changement /
        # sortie du workflow). Notification high priority avec email auto.
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_csrpn_transition(
                plan=plan,
                old_status=old_step,
                new_status=new_step,
                triggered_by=request.user,
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='admin-validation',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def admin_validation(self, request, pk=None):
        """
        Enregistrer/éditer/effacer une validation administrative INDÉPENDANTE (#347).

        POST /api/plans/plans/{id}/admin-validation/
        Body: {
            "key": "avis_csrpn" | "comite_consultatif" | "arrete_pref",
            "date": "YYYY-MM-DD" | null,     # null => efface la validation
            "numero_arrete_pref"?: string     # uniquement pour arrete_pref
        }

        Contrairement à `csrpn-step` (workflow ordonné, déprécié #347), chaque
        validation administrative est enregistrée séparément, dans n'importe quel
        ordre, quel que soit le statut plateforme du plan. L'état « validé » d'un
        élément est porté par sa date (renseignée = validé).

        - `arrete_pref` est réservé aux RNN/RNR (rejet sinon).
        - `validation_step` est maintenu (compat) sur l'étape la plus avancée
          renseignée, mais ne pilote plus l'UI.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': "Vous devez être référent de ce plan pour gérer les validations administratives."},
                status=status.HTTP_403_FORBIDDEN
            )

        key = request.data.get('key')
        key_to_date_field = {
            'avis_csrpn': 'date_avis_csrpn',
            'comite_consultatif': 'date_validation_comite',
            'arrete_pref': 'date_arrete_pref',
        }
        if key not in key_to_date_field:
            return Response(
                {'error': f"Clé invalide. Choix : {', '.join(key_to_date_field)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # #406 — la validation administrative est réservée aux réserves
        # naturelles (RNN/RNR/RNC). L'effacement (date=null) reste autorisé.
        if (request.data.get('date') or None) and not plan.is_reserve_naturelle():
            return Response(
                {'error': "La validation administrative est réservée aux réserves naturelles (RNN, RNR, RNC)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if key == 'arrete_pref' and not plan.is_rnn():
            return Response(
                {'error': "L'arrêté préfectoral est réservé aux RNN/RNR."},
                status=status.HTTP_400_BAD_REQUEST
            )

        date_value = request.data.get('date') or None
        date_field = key_to_date_field[key]
        setattr(plan, date_field, date_value)
        update_fields = [date_field, 'id_utilisateur_maj', 'date_maj']

        if key == 'arrete_pref':
            # Le n° d'arrêté suit la date : effacé si la date est effacée.
            plan.numero_arrete_pref = (request.data.get('numero_arrete_pref') or None) if date_value else None
            update_fields.append('numero_arrete_pref')

        # Maintenir `validation_step` (compat) sur l'étape la plus avancée renseignée.
        if plan.date_arrete_pref:
            plan.validation_step = 'arrete_pref'
        elif plan.date_validation_comite:
            plan.validation_step = 'comite_consultatif'
        elif plan.date_avis_csrpn:
            plan.validation_step = 'avis_csrpn'
        else:
            plan.validation_step = None
        update_fields.append('validation_step')

        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=update_fields)

        try:
            from apps.core.services import ActivityService
            verb = 'enregistrée' if date_value else 'effacée'
            ActivityService.log(
                user=request.user,
                action='status_change',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description=f"Validation administrative « {key} » {verb}",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='extend-duration',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def extend_duration(self, request, pk=None):
        """
        Prolonger un plan de gestion (#250 — refonte).

        POST /api/plans/plans/{id}/extend-duration/
        Body: {"years": 1}  ou  {"years": 2}

        Crée un **brouillon de nouvelle version étendue** : copie de toutes les
        métadonnées et de tout le contenu (enjeux, hiérarchie, suivis,
        opérations) du plan source, avec `annees_extension` cumulé (max 2 ans).
        Le gestionnaire complète ce brouillon (actions / suivi des années
        ajoutées) puis le valide ; le plan d'origine peut alors être archivé
        (pop-up #246). Une première prolongation de 1 an peut être reconduite
        d'une année supplémentaire (cumul max 2 ans) en repartant de la version
        étendue validée.

        Conditions :
        - Référent du plan, admin_og ou super_admin.
        - Plan source validé (`valide`, `modifie`), sans brouillon enfant en
          cours.
        - `annee_fin` renseignée, date courante dans la fenêtre de déclenchement
          autour de l'échéance effective (`annee_fin + annees_extension`).
        - `years` ∈ {1, 2}, cumul d'extension ≤ 2 ans.
        """
        from datetime import date

        plan = self.get_object()

        # Vérifier les droits (référent du plan, admin_og+).
        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour le prolonger.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Statut compatible : plan validé (validé / modifié).
        if plan.statut not in PlanGestion.EXTENDABLE_STATUSES:
            return Response(
                {'error': "Seul un plan validé (validé ou modifié) peut être prolongé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Un seul brouillon enfant à la fois.
        if plan.has_draft_child():
            return Response(
                {'error': "Un brouillon est déjà en cours sur ce plan. Validez ou supprimez le brouillon existant avant de prolonger."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Année de fin renseignée.
        if not plan.annee_fin:
            return Response(
                {'error': "L'année de fin du plan doit être renseignée pour le prolonger."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cumul d'extension ≤ 2 ans.
        current_ext = plan.annees_extension or 0
        remaining = 2 - current_ext
        if remaining <= 0:
            return Response(
                {'error': "Ce plan est déjà prolongé au maximum (2 ans cumulés)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fenêtre de déclenchement autour de l'échéance effective.
        effective_end = plan.annee_fin + current_ext
        current_year = date.today().year
        if not (effective_end - 1 <= current_year <= effective_end + 2):
            return Response(
                {'error': (
                    f"Le plan ne peut être prolongé qu'entre {effective_end - 1} "
                    f"et {effective_end + 2} (année actuelle : {current_year})."
                )},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Valeur d'extension : 1 ou 2, dans la limite du cumul restant.
        try:
            years = int(request.data.get('years'))
        except (TypeError, ValueError):
            years = None

        if years not in (1, 2) or years > remaining:
            choices = "1 ou 2" if remaining >= 2 else "1"
            return Response(
                {'error': f"Le paramètre 'years' doit valoir {choices} (cumul max 2 ans)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_extension = current_ext + years

        # Créer le brouillon de version étendue (copie métadonnées + contenu),
        # même rang que le plan source — il sera validé en `modifie` puis le
        # plan d'origine archivé (pop-up #246). #377 — copie complète.
        new_plan = PlanDuplicationService.build_version_plan(
            plan, request.user,
            nom=f"Plan de gestion étendu - {plan.nom}",
            version=plan.get_next_version(),
            annees_extension=new_extension,
        )
        new_plan.save()

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

        # #377 — Copier tout le contenu pour que la version étendue soit
        # éditable (ajout d'actions, suivi) sans impacter la version source.
        PlanDuplicationService.copy_content(plan, new_plan, request.user)
        new_plan.update_geometrie()

        # Log activity
        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='create',
                entity_type='plan',
                entity_id=new_plan.id_pg,
                entity_name=new_plan.nom,
                description=(
                    f"Brouillon de version étendue (+{years} an{'s' if years > 1 else ''}, "
                    f"cumul {new_extension} an{'s' if new_extension > 1 else ''}) "
                    f"créé depuis '{plan.nom}'"
                ),
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(new_plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='remove-extension',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def remove_extension(self, request, pk=None):
        """
        Retirer l'extension de durée d'un plan (#250).

        POST /api/plans/plans/{id}/remove-extension/

        Repasse `annees_extension` à 0 sans toucher au statut. Réservé aux
        référents du plan, admin_og et super_admin.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour retirer son extension.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not plan.is_extended():
            return Response(
                {'error': "Ce plan n'est pas prolongé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_years = plan.annees_extension
        plan.annees_extension = 0
        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=['annees_extension', 'id_utilisateur_maj', 'date_maj'])

        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='update',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description=f"Extension de {old_years} an(s) retirée",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='start-revision',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def start_revision(self, request, pk=None):
        """
        Marquer un plan validé comme « en cours de révision » (#278).

        POST /api/plans/plans/{id}/start-revision/
        Body (optionnel): {"next_rang_plan_id": <id>}

        Met `en_revision` à True et lie éventuellement le plan du rang suivant.
        Ne modifie pas le statut : le plan reste validé fonctionnellement.
        La révision peut être lancée avant ou après le dépassement de
        `annee_fin` — pas de contrainte de fenêtre temporelle.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour lancer sa révision.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if plan.statut not in PlanGestion.EXTENDABLE_STATUSES:
            return Response(
                {'error': "Seul un plan validé (validé, modifié ou mi-parcours) peut entrer en révision."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if plan.en_revision:
            return Response(
                {'error': "Ce plan est déjà en cours de révision."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lien éventuel vers le brouillon du rang suivant
        next_rang_plan_id = request.data.get('next_rang_plan_id')
        next_rang_plan = None
        if next_rang_plan_id is not None:
            try:
                next_rang_plan = PlanGestion.objects.get(pk=next_rang_plan_id)
            except PlanGestion.DoesNotExist:
                return Response(
                    {'error': f"Plan id={next_rang_plan_id} introuvable."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if next_rang_plan.pk == plan.pk:
                return Response(
                    {'error': "Un plan ne peut pas être son propre rang suivant."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        plan.en_revision = True
        if next_rang_plan is not None:
            plan.next_rang_plan = next_rang_plan
        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=['en_revision', 'next_rang_plan', 'id_utilisateur_maj', 'date_maj'])

        try:
            from apps.core.services import ActivityService
            link_info = f" (rang suivant : {next_rang_plan.nom})" if next_rang_plan else ""
            ActivityService.log(
                user=request.user,
                action='update',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description=f"Plan placé en cours de révision{link_info}",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='end-revision',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def end_revision(self, request, pk=None):
        """
        Arrêter la révision d'un plan (#278).

        POST /api/plans/plans/{id}/end-revision/

        Repasse `en_revision` à False et retire le lien `next_rang_plan`.
        Le statut du plan n'est pas modifié.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour arrêter sa révision.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not plan.en_revision:
            return Response(
                {'error': "Ce plan n'est pas en cours de révision."},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan.en_revision = False
        plan.next_rang_plan = None
        plan.id_utilisateur_maj = request.user
        plan.save(update_fields=['en_revision', 'next_rang_plan', 'id_utilisateur_maj', 'date_maj'])

        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='update',
                entity_type='plan',
                entity_id=plan.id_pg,
                entity_name=plan.nom,
                description="Révision arrêtée",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='delete-version',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def delete_version(self, request, pk=None):
        """
        Supprime définitivement une version (plan) d'une chaîne de versions (#348).

        POST /api/plans/plans/{id}/delete-version/

        Utilisé par la page « Paramètres du plan de gestion » pour supprimer une
        version quelconque de la chaîne — y compris l'évaluation mi-parcours.

        - Réservé au référent du plan, admin_og, super_admin (`_can_delete_plan`).
        - Supprime le plan et, par CASCADE Django, ses liens (sites, membres,
          référents, organismes rédacteurs, fichiers, enjeux, opérations,
          suivis). Les sites / utilisateurs / organismes eux-mêmes ne sont pas
          supprimés, seules les liaisons le sont.
        - Répare la chaîne : les enfants directs sont re-rattachés au parent du
          plan supprimé (la chaîne reste connectée), puis les versions du/des
          rang(s) impacté(s) sont renumérotées de façon contiguë (1..N).
        - Notifie les acteurs liés.

        Renvoie l'identifiant supprimé et la chaîne de versions restante.
        """
        from django.db import transaction
        from apps.notifications.services import NotificationService

        plan = self.get_object()

        if not self._can_delete_plan(request.user, plan):
            return Response(
                {'detail': "Vous n'avez pas les droits pour supprimer cette version."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Capturer la chaîne et les acteurs AVANT la suppression.
        chain_ids = [item['id_pg'] for item in plan.get_version_chain()]
        parent = plan.plan_parent
        plan_name = plan.nom
        plan_id = plan.id_pg
        deleted_by = request.user
        referent_ids = list(plan.referents.values_list('id_role', flat=True))
        member_ids = list(
            CorRolePlan.objects.filter(plan_de_gestion=plan).values_list('id_role', flat=True)
        )
        org_ids = list(plan.organismes_redacteurs.values_list('uuid_og', flat=True))

        with transaction.atomic():
            # Re-rattacher les enfants au parent du plan supprimé pour garder la
            # chaîne connectée (plan_parent est SET_NULL : sans cela les enfants
            # deviendraient des racines orphelines).
            plan.children.update(plan_parent=parent)
            plan.delete()
            # Renuméroter les versions restantes de la chaîne, par rang.
            survivors = list(
                PlanGestion.objects.filter(id_pg__in=chain_ids).exclude(pk=plan_id)
            )
            PlanGestion.renumber_versions_per_rang(survivors)

        try:
            NotificationService.notify_plan_deleted(
                plan_name=plan_name,
                plan_id=plan_id,
                deleted_by=deleted_by,
                referent_ids=referent_ids,
                org_ids=org_ids,
                member_ids=member_ids,
            )
        except Exception:
            pass

        # Construire la chaîne restante pour le frontend.
        anchor = None
        if parent is not None:
            parent.refresh_from_db()
            anchor = parent
        else:
            anchor = PlanGestion.objects.filter(id_pg__in=chain_ids).exclude(pk=plan_id).first()
        remaining = anchor.get_version_chain() if anchor is not None else []

        return Response({'deleted_id': plan_id, 'version_chain': remaining},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='create-next-rang',
            permission_classes=[permissions.IsAuthenticated, IsReferent])
    def create_next_rang(self, request, pk=None):
        """
        Créer un brouillon du rang suivant à partir d'un plan validé (#278).

        POST /api/plans/plans/{id}/create-next-rang/
        Body (optionnel) : {
            "nom": str,           # défaut: "Plan de gestion - rang N+1 - <source>"
            "annee_debut": int,   # défaut: plan.annee_fin + 1
            "annee_fin": int,     # défaut: plan.annee_fin + 10
        }

        Le plan source doit être validé (`valide`/`modifie`/`mi_parcours`).
        Accessible aux référents du plan, admin_og+.

        Crée un nouveau plan enfant avec :
        - `plan_parent` = plan source
        - `rang` = plan.rang + 1
        - `id_type_document` = PLAN_REVISE
        - `statut` = draft
        - Copie des sites et référents

        Utilisé notamment lors du lancement d'une révision (#278) pour
        matérialiser le brouillon du rang suivant.
        """
        plan = self.get_object()

        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour créer son rang suivant.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if plan.statut not in PlanGestion.DRAFTABLE_PARENT_STATUSES:
            return Response(
                {'error': "Le rang suivant ne peut être créé que depuis un plan validé (validé, modifié ou archivé)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if plan.has_draft_child():
            return Response(
                {'error': "Un brouillon est déjà en cours sur ce plan. Validez ou supprimez le brouillon existant avant d'en créer un nouveau."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.core.models import Nomenclature
        try:
            revise_type = Nomenclature.objects.get(mnemonique='PLAN_REVISE')
        except Nomenclature.DoesNotExist:
            return Response(
                {'error': "Nomenclature PLAN_REVISE non trouvée. Lancez 'python manage.py import_nomenclatures --force'."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Paramètres avec valeurs par défaut dérivées du plan source
        annee_debut_source = plan.annee_fin + 1 if plan.annee_fin else None
        annee_fin_source = plan.annee_fin + 10 if plan.annee_fin else None
        new_rang = (plan.rang or 1) + 1

        nom = request.data.get('nom') or f"Plan de gestion rang {new_rang} - {plan.nom}"
        try:
            annee_debut = request.data.get('annee_debut')
            annee_debut = int(annee_debut) if annee_debut is not None else annee_debut_source
        except (TypeError, ValueError):
            annee_debut = annee_debut_source
        try:
            annee_fin = request.data.get('annee_fin')
            annee_fin = int(annee_fin) if annee_fin is not None else annee_fin_source
        except (TypeError, ValueError):
            annee_fin = annee_fin_source

        # Nouveau rang → nouvelle numérotation (v1). Un changement de rang
        # correspond à un NOUVEAU plan de gestion, pas à une nouvelle version.
        # #377 — copie de toutes les métadonnées du plan source (sauf statut).
        new_plan = PlanDuplicationService.build_version_plan(
            plan, request.user,
            nom=nom,
            id_type_document=revise_type,
            version=plan.get_first_version_for_next_rang(),
            annee_debut=annee_debut,
            annee_fin=annee_fin,
            rang=new_rang,
        )
        new_plan.save()

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

        # #377 — Copier tout le contenu (enjeux, hiérarchie, suivis, opérations)
        # pour que le rang suivant soit éditable sans impacter la version source.
        PlanDuplicationService.copy_content(plan, new_plan, request.user)

        try:
            from apps.core.services import ActivityService
            ActivityService.log(
                user=request.user,
                action='create',
                entity_type='plan',
                entity_id=new_plan.id_pg,
                entity_name=new_plan.nom,
                description=f"Brouillon du rang {new_rang} créé depuis '{plan.nom}'",
            )
        except Exception:
            pass

        serializer = PlanGestionDetailSerializer(new_plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

        # Vérifier que l'utilisateur est référent de CE plan (ou admin_og+ hors rédacteur principal)
        user = request.user
        if not user.can_manage_plan_lifecycle() and not plan.referents.filter(pk=user.pk).exists():
            return Response(
                {'error': 'Vous devez être référent de ce plan pour créer une évaluation.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if plan.statut not in PlanGestion.DRAFTABLE_PARENT_STATUSES:
            return Response(
                {'error': "Seul un plan validé (validé, modifié ou archivé) peut donner lieu à une évaluation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if plan.has_draft_child():
            return Response(
                {'error': "Un brouillon est déjà en cours sur ce plan. Validez ou supprimez le brouillon existant avant d'en créer un nouveau."},
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

        # Créer le nouveau plan.
        # #377 — copie de toutes les métadonnées du plan source (sauf statut).
        new_plan = PlanDuplicationService.build_version_plan(
            plan, request.user,
            nom=f"Évaluation mi-parcours - {plan.nom}",
            id_type_document=eval_type,
            version=plan.get_next_version(),
        )
        new_plan.save()

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

        # #377 — Copier tout le contenu pour que l'évaluation mi-parcours soit
        # éditable sans impacter la version source.
        PlanDuplicationService.copy_content(plan, new_plan, request.user)

        # #349 — Marquer l'évaluation comme mi-parcours DÈS le brouillon (et non
        # seulement à sa validation), afin qu'elle soit identifiée comme
        # évaluation mi-parcours pendant sa rédaction. Posé uniquement si aucune
        # mi-parcours n'existe déjà dans la chaîne (unicité). Le flag est préservé
        # à la validation (change_status ne le réinitialise pas).
        if not plan.chain_has_mi_parcours():
            new_plan.is_mi_parcours = True
            new_plan.save(update_fields=['is_mi_parcours'])

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

    @action(detail=True, methods=['get'], url_path='operation-codes')
    def operation_codes(self, request, pk=None):
        """
        Renvoie le dict {id_operation: code_affichage} pour un plan.

        GET /api/plans/plans/{id}/operation-codes/

        Endpoint léger appelé après un DnD pour rafraîchir uniquement les
        codes (préfixe + rang) sans recharger la totalité de l'arbre du
        plan via `enjeux/by-plan/`. Le calcul lui-même est ~14 requêtes
        SQL grâce au prefetch (#228).
        """
        plan = self.get_object()
        from .serializers_operations import compute_operation_codes_for_plan
        codes = compute_operation_codes_for_plan(plan.pk)
        return Response(codes)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques des Plans de Gestion — applique les mêmes filtres que la liste.

        GET /api/plans/plans/stats/?organisme=&statut=&search=…

        #184 : avant ce fix, l'endpoint utilisait `get_queryset()` sans
        passer par `filter_queryset()`, donc les vignettes côté admin
        ignoraient le filtre organisme/statut. Le cache 15 min a aussi été
        retiré (les compteurs doivent refléter immédiatement le choix de
        l'utilisateur).
        """
        queryset = self.filter_queryset(self.get_queryset())
        
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
    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]

    def get_plan_for_payload(self, data):
        """Pour le check draft à la création : remonte le plan depuis l'id."""
        plan_id = data.get('plan_de_gestion') or data.get('id_pg')
        if not plan_id:
            return None
        try:
            return PlanGestion.objects.only('statut').get(pk=plan_id)
        except PlanGestion.DoesNotExist:
            return None
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CorPgFichierFilter
    search_fields = ['nom_fichier', 'titre', 'description', 'auteur']
    ordering_fields = ['nom_fichier', 'type_fichier', 'ordre_affichage', 'date_upload']
    ordering = ['ordre_affichage', 'nom_fichier']
    
    def get_permissions(self):
        """
        #372 — Lecture (list/retrieve/download) accessible à tout utilisateur
        authentifié : l'accès réel est déjà borné par ``get_queryset()`` (plans
        accessibles) et par la vérification du plan dans l'action ``download``.
        Exiger ``IsReferent`` au niveau vue bloquait à tort le téléchargement
        pour les non-référents légitimes (admin d'organisme, membre du plan).
        Les écritures (upload/suppression) restent réservées aux référents et
        au brouillon uniquement.
        """
        if self.action in ('list', 'retrieve', 'download'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsReferent(), CanModifyOnlyDraftPlan()]

    def get_queryset(self):
        """Filtrer les fichiers selon les permissions sur les plans."""
        user = self.request.user

        if user.is_super_admin() or user.is_redacteur_principal():
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