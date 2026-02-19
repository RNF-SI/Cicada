"""
Vues API REST pour les Plans de Gestion.
"""
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

from .models import PlanGestion, CorSitePg, CorPgFichier
from .serializers import (
    PlanGestionListSerializer, PlanGestionDetailSerializer,
    PlanGestionGeoJSONSerializer, PlanGestionCreateSerializer,
    CorSitePgSerializer, CorPgFichierSerializer
)
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
    
    queryset = PlanGestion.objects.all().select_related(
        'id_evaluation', 'id_redacteur_type',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('sites__site__id_type_site', 'fichiers', 'referents')
    
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
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
        """Filtrer selon les permissions utilisateur."""
        user = self.request.user
        queryset = self.queryset

        # Super admin : voir tous les plans
        if user.is_super_admin():
            return queryset

        # Admin organisme : voir les plans des sites de son organisme
        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        # Référent : voir les plans des sites assignés + plans dont il est référent
        if user.is_referent():
            from django.db.models import Q
            return queryset.filter(
                Q(sites__site__corrolesite__id_role=user) |
                Q(referents=user)
            ).distinct()

        # Utilisateur : voir les plans publics
        return queryset.filter(statut='valide')
    
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
                'geometry': plan.geometrie.__geo_interface__ if plan.geometrie else None,
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
            'geometry': plan.geometrie.__geo_interface__,
            'properties': serializer.data
        }
        
        return Response(feature)
    
    @action(detail=True, methods=['post'], 
            permission_classes=[permissions.IsAuthenticated, IsAdminOrganisme])
    def assign_site(self, request, pk=None):
        """
        Assigner un site à un plan.
        
        POST /api/plans/{id}/assign_site/
        Body: {"site_id": 123, "rang": 1, "commentaire": "Site principal"}
        """
        plan = self.get_object()
        site_id = request.data.get('site_id')
        rang = request.data.get('rang')
        commentaire = request.data.get('commentaire', '')
        
        if not site_id:
            return Response({'error': 'site_id requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.users.models import Site
            site = Site.objects.get(id_site=site_id)
            
            # Vérifier les permissions sur le site
            if not request.user.can_manage_site(site):
                return Response({'error': 'Permissions insuffisantes pour ce site'}, 
                              status=status.HTTP_403_FORBIDDEN)
            
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
            permission_classes=[permissions.IsAuthenticated, IsAdminOrganisme])
    def remove_site(self, request, pk=None):
        """
        Retirer un site d'un plan.
        
        DELETE /api/plans/{id}/remove_site/?site_id=123
        """
        plan = self.get_object()
        site_id = request.query_params.get('site_id')
        
        if not site_id:
            return Response({'error': 'site_id requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cor_site_pg = CorSitePg.objects.get(
                plan_de_gestion=plan,
                site__id_site=site_id
            )
            
            # Vérifier les permissions
            if not request.user.can_manage_site(cor_site_pg.site):
                return Response({'error': 'Permissions insuffisantes'}, 
                              status=status.HTTP_403_FORBIDDEN)
            
            cor_site_pg.delete()
            
            return Response({'message': 'Site retiré du plan'})
            
        except CorSitePg.DoesNotExist:
            return Response({'error': 'Relation non trouvée'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsAdminOrganisme])
    def replace_site(self, request, pk=None):
        """
        Remplacer un site par un autre dans un plan.
        Utile pour réassigner un plan lié à un site rejeté/invalide.

        POST /api/plans/{id}/replace_site/
        Body: {"old_site_id": 123, "new_site_id": 456}
        """
        from apps.users.models import Site

        plan = self.get_object()
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

        # Vérifier les permissions sur le nouveau site
        if not request.user.can_manage_site(new_site):
            return Response({'error': 'Permissions insuffisantes sur le nouveau site'},
                          status=status.HTTP_403_FORBIDDEN)

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
            permission_classes=[permissions.IsAuthenticated, IsAdminOrganisme])
    def assign_referent(self, request, pk=None):
        """
        Assigner un référent à un plan.

        POST /api/plans/{id}/assign_referent/
        Body: {"referent_id": 123}
        """
        plan = self.get_object()
        referent_id = request.data.get('referent_id')
        
        if not referent_id:
            return Response({'error': 'referent_id requis'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.users.models import Role
            referent = Role.objects.get(id_role=referent_id)
            
            # Vérifier que l'utilisateur est au moins référent
            if not referent.is_referent():
                return Response({'error': 'L\'utilisateur doit être au moins référent'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            plan.referents.add(referent)
            
            return Response({'message': f'Référent {referent} assigné au plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'],
            permission_classes=[permissions.IsAuthenticated, IsAdminOrganisme])
    def remove_referent(self, request, pk=None):
        """
        Retirer un référent d'un plan.

        DELETE /api/plans/{id}/remove_referent/?referent_id=123
        """
        plan = self.get_object()
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

            return Response({'message': f'Référent {referent} retiré du plan'})

        except Role.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'},
                          status=status.HTTP_404_NOT_FOUND)

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
        plan_ids = PlanGestionViewSet().get_queryset().values_list('id_pg', flat=True)
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
            plan_queryset = plan_viewset.get_queryset()
            
            if not plan_queryset.filter(id_pg=fichier.plan_de_gestion.id_pg).exists():
                return Response({'error': 'Permissions insuffisantes'}, 
                              status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier que le fichier existe
        if not os.path.exists(fichier.chemin_fichier):
            return Response({'error': 'Fichier non trouvé sur le serveur'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Servir le fichier
        try:
            with open(fichier.chemin_fichier, 'rb') as f:
                file_content = f.read()
            
            response = HttpResponse(
                file_content,
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{fichier.nom_fichier}"'
            response['Content-Length'] = len(file_content)
            
            return response
            
        except Exception as e:
            return Response({'error': f'Erreur lors du téléchargement: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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