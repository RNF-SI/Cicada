"""
ViewSets pour les API Organismes et Sites avec permissions et filtrage.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import BibOrganismes, Site, CorRoleSite, CorOgSite, Role
from .serializers_org_sites import (
    OrganismeListSerializer, OrganismeDetailSerializer, OrganismeCreateUpdateSerializer,
    SiteListSerializer, SiteGeoJSONSerializer, SiteDetailSerializer, SiteCreateUpdateSerializer,
    OrganismeSiteAssignmentSerializer, BulkSiteAssignmentSerializer
)
from .permissions import IsSuperAdmin, IsAdminOrganisme, IsReferent
from .pagination import StandardPagination
from .filters_org_sites import OrganismeFilter, SiteFilter


class OrganismeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des organismes.
    
    Permissions:
    - Liste/Détail: Authentifié (filtrage selon rôle)
    - Création: Admin Organisme+
    - Modification: Admin de l'organisme OU Super Admin
    - Suppression: Super Admin seulement
    """
    
    pagination_class = StandardPagination
    filterset_class = OrganismeFilter
    search_fields = ['nom_organisme', 'ville_organisme', 'email_organisme']
    ordering_fields = ['nom_organisme', 'ville_organisme']
    ordering = ['nom_organisme']
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'list':
            return OrganismeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OrganismeCreateUpdateSerializer
        else:
            return OrganismeDetailSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['create']:
            permission_classes = [IsAdminOrganisme]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAdminOrganisme]  # Vérifié dans get_object
        elif self.action in ['destroy']:
            permission_classes = [IsSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        
        if user.is_super_admin():
            # Super admin voit tous les organismes
            return BibOrganismes.objects.all().select_related('id_parent')
        
        elif user.is_admin_organisme() and user.id_organisme:
            # Admin organisme voit son organisme et ses enfants
            org_ids = [user.id_organisme.id_organisme]
            
            # Ajouter les organismes enfants
            children = BibOrganismes.objects.filter(id_parent=user.id_organisme)
            org_ids.extend(children.values_list('id_organisme', flat=True))
            
            return BibOrganismes.objects.filter(
                id_organisme__in=org_ids
            ).select_related('id_parent')
        
        elif user.is_referent() and user.id_organisme:
            # Référent voit seulement son organisme
            return BibOrganismes.objects.filter(
                id_organisme=user.id_organisme.id_organisme
            ).select_related('id_parent')
        
        else:
            # Utilisateur normal voit seulement son organisme
            if user.id_organisme:
                return BibOrganismes.objects.filter(
                    id_organisme=user.id_organisme.id_organisme
                ).select_related('id_parent')
        
        return BibOrganismes.objects.none()
    
    def get_object(self):
        """Vérification des permissions d'objet."""
        obj = super().get_object()
        user = self.request.user
        
        # Super admin peut tout faire
        if user.is_super_admin():
            return obj
        
        # Admin organisme peut modifier son organisme et ses enfants
        if user.is_admin_organisme() and user.id_organisme:
            if (obj.id_organisme == user.id_organisme.id_organisme or 
                obj.id_parent == user.id_organisme):
                return obj
        
        # Pour les autres actions (lecture), utiliser get_queryset
        if self.action in ['retrieve']:
            return obj
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Vous n'avez pas la permission de modifier cet organisme.")
    
    def perform_create(self, serializer):
        """Logique de création d'organisme."""
        user = self.request.user
        
        # Admin organisme ne peut créer que des enfants de son organisme
        if user.is_admin_organisme() and not user.is_super_admin():
            # Forcer l'organisme parent
            serializer.save(id_parent=user.id_organisme)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def assign_site(self, request, pk=None):
        """Assigne un site à un organisme."""
        organisme = self.get_object()
        serializer = OrganismeSiteAssignmentSerializer(data=request.data)
        
        if serializer.is_valid():
            site_id = serializer.validated_data['site_id']
            site = get_object_or_404(Site, id_site=site_id)
            
            # Vérifier que l'utilisateur peut gérer ce site
            if not request.user.is_super_admin():
                if not request.user.can_manage_site(site):
                    return Response(
                        {'error': 'Vous ne pouvez pas gérer ce site.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Créer ou récupérer la relation
            cor_og_site, created = CorOgSite.objects.get_or_create(
                uuid_og=organisme,
                id_site=site
            )
            
            if created:
                return Response(
                    {'message': f'Site {site.nom_site} assigné à {organisme.nom_organisme}'},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'message': 'Le site est déjà assigné à cet organisme'},
                    status=status.HTTP_200_OK
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def bulk_assign_sites(self, request, pk=None):
        """Assignation en masse de sites à un organisme."""
        organisme = self.get_object()
        serializer = BulkSiteAssignmentSerializer(data=request.data)
        
        if serializer.is_valid():
            site_ids = serializer.validated_data['site_ids']
            sites = Site.objects.filter(id_site__in=site_ids)
            
            results = {'assigned': [], 'already_assigned': [], 'forbidden': []}
            
            with transaction.atomic():
                for site in sites:
                    # Vérifier permissions
                    if not request.user.is_super_admin():
                        if not request.user.can_manage_site(site):
                            results['forbidden'].append({
                                'id_site': site.id_site,
                                'nom_site': site.nom_site
                            })
                            continue
                    
                    # Créer la relation
                    cor_og_site, created = CorOgSite.objects.get_or_create(
                        uuid_og=organisme,
                        id_site=site
                    )
                    
                    if created:
                        results['assigned'].append({
                            'id_site': site.id_site,
                            'nom_site': site.nom_site
                        })
                    else:
                        results['already_assigned'].append({
                            'id_site': site.id_site,
                            'nom_site': site.nom_site
                        })
            
            return Response(results, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def unassign_site(self, request, pk=None, organisme_pk=None, site_pk=None):
        """Désassigne un site d'un organisme."""
        # Support both pk (from router) and organisme_pk (from manual URL)
        organisme_id = pk or organisme_pk
        organisme = get_object_or_404(BibOrganismes, id_organisme=organisme_id)
        site = get_object_or_404(Site, id_site=site_pk)
        
        # Vérifier permissions
        if not request.user.is_super_admin():
            if not request.user.can_manage_site(site):
                return Response(
                    {'error': 'Vous ne pouvez pas gérer ce site.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        try:
            cor_og_site = CorOgSite.objects.get(uuid_og=organisme, id_site=site)
            cor_og_site.delete()
            
            return Response(
                {'message': f'Site {site.nom_site} désassigné de {organisme.nom_organisme}'},
                status=status.HTTP_204_NO_CONTENT
            )
        except CorOgSite.DoesNotExist:
            return Response(
                {'error': 'Ce site n\'est pas assigné à cet organisme.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def sites(self, request, pk=None):
        """Liste des sites gérés par un organisme."""
        organisme = self.get_object()
        cor_sites = CorOgSite.objects.filter(uuid_og=organisme).select_related('id_site')

        sites_data = []
        for cor in cor_sites:
            site = cor.id_site
            sites_data.append({
                'id_site': site.id_site,
                'nom_site': site.nom_site,
                'surf_off': site.surf_off,
                'type_site': site.id_type_site.label if site.id_type_site else None,
                'active': site.active,
                'principal': cor.principal
            })

        return Response(sites_data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrganisme])
    def stats(self, request):
        """Statistiques des organismes."""
        queryset = self.get_queryset()
        
        total_organismes = queryset.count()
        active_organismes = queryset.filter(active=True).count()
        
        # Statistiques par type (parent/enfant)
        organismes_parents = queryset.filter(id_parent__isnull=True).count()
        organismes_enfants = queryset.filter(id_parent__isnull=False).count()
        
        return Response({
            'total_organismes': total_organismes,
            'active_organismes': active_organismes,
            'organismes_parents': organismes_parents,
            'organismes_enfants': organismes_enfants
        })


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des sites.
    
    Permissions:
    - Liste/Détail: Authentifié (filtrage selon rôle)
    - Création: Admin Organisme+
    - Modification: Référent du site OU Admin de l'organisme gestionnaire OU Super Admin
    - Suppression: Admin Organisme+ (dans son scope)
    """
    
    pagination_class = StandardPagination
    filterset_class = SiteFilter
    search_fields = ['nom_site', 'id_local', 'id_inpn']
    ordering_fields = ['nom_site', 'surf_off', 'date_crea']
    ordering = ['nom_site']
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'list':
            return SiteListSerializer
        elif self.action == 'geojson':
            return SiteGeoJSONSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SiteCreateUpdateSerializer
        else:
            return SiteDetailSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['create']:
            permission_classes = [IsAdminOrganisme]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsReferent]  # Vérifié dans get_object
        elif self.action in ['destroy']:
            permission_classes = [IsAdminOrganisme]  # Vérifié dans get_object
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        
        if user.is_super_admin():
            # Super admin voit tous les sites
            return Site.objects.all().select_related('id_type_site')
        
        elif user.is_admin_organisme() and user.id_organisme:
            # Admin organisme voit les sites de son organisme
            managed_sites = CorOgSite.objects.filter(
                uuid_og=user.id_organisme
            ).values_list('id_site', flat=True)
            
            return Site.objects.filter(id_site__in=managed_sites).select_related('id_type_site')
        
        elif user.is_referent():
            # Référent voit les sites qui lui sont assignés + sites de son organisme
            assigned_sites = CorRoleSite.objects.filter(id_role=user).values_list('id_site', flat=True)
            
            queryset = Site.objects.filter(id_site__in=assigned_sites)
            
            # Ajouter les sites de son organisme si il en a un
            if user.id_organisme:
                org_sites = CorOgSite.objects.filter(
                    uuid_og=user.id_organisme
                ).values_list('id_site', flat=True)
                
                queryset = Site.objects.filter(
                    Q(id_site__in=assigned_sites) | Q(id_site__in=org_sites)
                ).distinct()
            
            return queryset.select_related('id_type_site')
        
        else:
            # Utilisateur normal voit les sites de son organisme
            if user.id_organisme:
                org_sites = CorOgSite.objects.filter(
                    uuid_og=user.id_organisme
                ).values_list('id_site', flat=True)
                
                return Site.objects.filter(id_site__in=org_sites).select_related('id_type_site')
        
        return Site.objects.none()
    
    def get_object(self):
        """Vérification des permissions d'objet."""
        obj = super().get_object()
        user = self.request.user
        
        # Super admin peut tout faire
        if user.is_super_admin():
            return obj
        
        # Pour modification/suppression, vérifier permissions spécifiques
        if self.action in ['update', 'partial_update', 'destroy']:
            if user.can_manage_site(obj):
                return obj
            
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce site.")
        
        # Pour lecture, utiliser get_queryset
        return obj
    
    @action(detail=True, methods=['get'])
    def geojson(self, request, pk=None):
        """Retourne le site au format GeoJSON complet."""
        site = self.get_object()
        serializer = SiteGeoJSONSerializer(site)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def geojson_list(self, request):
        """Retourne tous les sites visibles au format GeoJSON."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Limiter à 100 sites pour les performances
        if queryset.count() > 100:
            queryset = queryset[:100]
        
        serializer = SiteGeoJSONSerializer(queryset, many=True)
        
        # Encapsuler dans une FeatureCollection GeoJSON
        geojson_data = {
            'type': 'FeatureCollection',
            'features': serializer.data,
            'properties': {
                'count': len(serializer.data),
                'note': 'Limité à 100 sites pour les performances'
            }
        }
        
        return Response(geojson_data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def assign_user(self, request, pk=None):
        """Assigne un utilisateur au site."""
        site = self.get_object()
        
        # Vérifier que l'utilisateur peut gérer ce site
        if not request.user.can_manage_site(site):
            return Response(
                {'error': 'Vous ne pouvez pas gérer ce site.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        referent = request.data.get('referent', False)
        referent_valid = request.data.get('referent_valid', False)
        conservateur = request.data.get('conservateur', False)
        
        if not user_id:
            return Response(
                {'error': 'user_id requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = Role.objects.get(id_role=user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Créer ou mettre à jour la relation
        cor_role_site, created = CorRoleSite.objects.update_or_create(
            id_site=site,
            id_role=user,
            defaults={
                'referent': referent,
                'referent_valid': referent_valid,
                'conservateur': conservateur
            }
        )
        
        action_word = "assigné" if created else "mis à jour"
        return Response(
            {'message': f'Utilisateur {user.email} {action_word} au site {site.nom_site}'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['delete'])
    def unassign_user(self, request, pk=None, user_pk=None):
        """Désassigne un utilisateur du site."""
        site = self.get_object()
        
        # Vérifier permissions
        if not request.user.can_manage_site(site):
            return Response(
                {'error': 'Vous ne pouvez pas gérer ce site.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = get_object_or_404(Role, id_role=user_pk)
        
        try:
            cor_role_site = CorRoleSite.objects.get(id_site=site, id_role=user)
            cor_role_site.delete()
            
            return Response(
                {'message': f'Utilisateur {user.email} désassigné du site {site.nom_site}'},
                status=status.HTTP_204_NO_CONTENT
            )
        except CorRoleSite.DoesNotExist:
            return Response(
                {'error': 'Cet utilisateur n\'est pas assigné à ce site.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Liste des utilisateurs assignés au site."""
        site = self.get_object()
        cor_users = CorRoleSite.objects.filter(id_site=site).select_related('id_role')
        
        users_data = []
        for cor in cor_users:
            user = cor.id_role
            users_data.append({
                'id_role': user.id_role,
                'nom_complet': f"{user.prenom_role} {user.nom_role}".strip(),
                'email': user.email,
                'role_level': user.role_level,
                'referent': cor.referent,
                'referent_valid': cor.referent_valid,
                'conservateur': cor.conservateur
            })
        
        return Response(users_data)
    
    @action(detail=True, methods=['get'])
    def organismes(self, request, pk=None):
        """Liste des organismes gestionnaires du site."""
        site = self.get_object()
        cor_orgs = CorOgSite.objects.filter(id_site=site).select_related('uuid_og')

        orgs_data = []
        for cor in cor_orgs:
            org = cor.uuid_og
            orgs_data.append({
                'id_organisme': org.id_organisme,
                'nom_organisme': org.nom_organisme,
                'ville_organisme': org.ville_organisme,
                'email_organisme': org.email_organisme,
                'principal': cor.principal
            })

        return Response(orgs_data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsReferent])
    def stats(self, request):
        """Statistiques des sites."""
        queryset = self.get_queryset()

        total_sites = queryset.count()
        active_sites = queryset.filter(active=True).count()
        sites_marins = queryset.filter(marin=True).count()
        sites_outre_mer = queryset.filter(outre_mer=True).count()

        # Surface totale
        from django.db.models import Sum
        surface_totale = queryset.aggregate(Sum('surf_off'))['surf_off__sum'] or 0

        return Response({
            'total_sites': total_sites,
            'active_sites': active_sites,
            'sites_marins': sites_marins,
            'sites_outre_mer': sites_outre_mer,
            'surface_totale_ha': round(surface_totale, 2)
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrganisme])
    def available_for_assignment(self, request):
        """
        Liste tous les sites actifs disponibles pour assignation à un organisme.
        Cet endpoint ne filtre pas par organisme, permettant aux admins d'organisme
        de voir tous les sites qu'ils peuvent potentiellement ajouter.
        GET /api/users/sites/available_for_assignment/
        """
        # Retourner tous les sites actifs sans filtrage par organisme
        sites = Site.objects.filter(active=True).select_related('id_type_site').order_by('nom_site')

        # Filtrage optionnel par recherche
        search = request.query_params.get('search', '')
        if search:
            sites = sites.filter(
                Q(nom_site__icontains=search) |
                Q(id_local__icontains=search) |
                Q(id_inpn__icontains=search)
            )

        # Pagination simple
        page_size = int(request.query_params.get('page_size', 100))
        sites = sites[:page_size]

        sites_data = []
        for site in sites:
            sites_data.append({
                'id_site': site.id_site,
                'nom_site': site.nom_site,
                'id_local': site.id_local,
                'type_site_label': site.id_type_site.label if site.id_type_site else None,
                'surf_off': site.surf_off,
                'active': site.active
            })

        return Response({
            'count': len(sites_data),
            'results': sites_data
        })